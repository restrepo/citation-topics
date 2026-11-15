"""Description of every topic and area from the optional fields of the input (dossier.json), the material the
topic-namer agent reads to name them. No AI here: the same input and run give the same dossier.

Per topic: works, years, share of links inside, the topics it links to most, the terms that set its titles
(and abstracts, with abstracts=True) and keywords apart from the rest of the list, its main journals, categories,
keywords and countries (share of its works), and its most cited works with title, year, citations and, for the
first three, the start of the abstract. Per area: the same summary over its topics. Every part needs its field;
what the input lacks is left out and listed in "missing".
"""

import heapq
import json
import math
import re
from collections import Counter
from pathlib import Path

import numpy as np

from .cluster import topic_links
from .io import Fields, as_list, as_year, iter_works
from .run import load

STOP = set(
    [
        "a",
        "an",
        "the",
        "of",
        "in",
        "on",
        "at",
        "to",
        "for",
        "from",
        "by",
        "with",
        "without",
        "and",
        "or",
        "nor",
        "but",
        "not",
        "no",
        "as",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "this",
        "that",
        "these",
        "those",
        "it",
        "its",
        "into",
        "onto",
        "over",
        "under",
        "between",
        "among",
        "via",
        "using",
        "use",
        "used",
        "new",
        "study",
        "studies",
        "analysis",
        "we",
        "our",
        "their",
        "his",
        "her",
        "than",
        "then",
        "there",
        "here",
        "which",
        "who",
        "whom",
        "whose",
        "what",
        "when",
        "where",
        "why",
        "how",
        "all",
        "any",
        "each",
        "both",
        "more",
        "most",
        "other",
        "some",
        "such",
        "only",
        "own",
        "same",
        "so",
        "too",
        "very",
        "can",
        "will",
        "just",
        "do",
        "does",
        "did",
        "done",
        "also",
        "may",
        "might",
        "must",
        "shall",
        "should",
        "would",
        "could",
        "about",
        "above",
        "after",
        "again",
        "against",
        "before",
        "below",
        "during",
        "through",
        "up",
        "down",
        "out",
        "off",
        "further",
        "once",
        "two",
        "three",
        "one",
        "first",
        "second",
        "based",
        "results",
        "result",
        "effect",
        "effects",
        "case",
        "cases",
        "approach",
        "method",
        "methods",
        "model",
        "models",
        "paper",
        "review",
        "report",
        "part",
        "non",
        "vs",
        "ii",
        "iii",
        "iv",
    ]
)
WORD = re.compile(r"[a-z][a-z0-9\-]+")


def terms_of(text):
    """Distinct unigrams and bigrams of a text, lowercased, without stop words; LaTeX math is dropped."""
    text = re.sub(r"\$[^$]*\$", " ", (text or "").lower())
    out, prev = set(), None
    for w in WORD.findall(text):
        w = w.strip("-")
        if len(w) < 3 or w in STOP:
            prev = None
            continue
        out.add(w)
        if prev:
            out.add(f"{prev} {w}")
        prev = w
    return out


def shares(counter, total, k):
    return [[x, round(100 * c / total, 1)] for x, c in counter.most_common(k)] if total else []


def distinctive(df_k, n_k, df, n, k=15, min_df=3):
    """Terms of a topic ranked by p * log(p / q): p its share of the topic's works, q its share elsewhere; only
    terms used by 2% of the topic and twice as often as elsewhere."""
    out = []
    for term, c in df_k.items():
        if c < min_df:
            continue
        p = c / n_k
        if p < 0.02:
            continue
        q = (df[term] - c) / max(n - n_k, 1)
        if p < 2 * q:  # not distinctive: as common elsewhere
            continue
        out.append((p * math.log((p + 1e-6) / (q + 1e-6)), term, p))
    out.sort(reverse=True)
    return [[t, round(100 * p, 1)] for _, t, p in out[:k]]


class _Counts:
    """Per-topic term counts with lossy pruning, so millions of titles fit in memory."""

    def __init__(self, limit=6_000_000):
        self.c, self.size, self.limit, self.floor = {}, 0, limit, 0

    def add(self, key, terms):
        d = self.c.setdefault(key, Counter())
        before = len(d)
        d.update(terms)
        self.size += len(d) - before
        if self.size > self.limit:
            self.floor += 1
            for d in self.c.values():
                for t in [t for t, v in d.items() if v <= self.floor]:
                    del d[t]
            self.size = sum(len(d) for d in self.c.values())


def describe(input, out, fields=None, top=8, abstracts=False, terms=15, log=print):
    fields = fields or Fields()
    out = Path(out)
    net, cl = load(out)
    topic, area_of_topic = cl["topic"], cl["area_of_topic"]
    m = int(topic.max()) + 1
    node = {k: i for i, k in enumerate(net.ids)}
    d = np.unique(net.src.astype(np.int64) * net.n + net.dst)
    cites_inside = np.bincount(d % net.n, minlength=net.n)
    names = {e["topic"]: e.get("name") for e in json.loads((out / "topics.json").read_text())}
    anames = {e["area"]: e.get("name") for e in json.loads((out / "areas.json").read_text())}

    counts = _Counts()
    journals, cats, kws, countries = (dict() for _ in range(4))
    best = {k: [] for k in range(m)}  # heap of (citations, -node, info) per topic
    seen = Counter()
    for w in iter_works(input):
        i = node.get(str(w.get(fields.id)))
        if i is None:
            continue
        k = int(topic[i])
        title, kw = fields.get(w, "title"), as_list(fields.get(w, "keywords"))
        text = (title or "") + (" " + (fields.get(w, "abstract") or "") if abstracts else "")
        tset = terms_of(text) | {x.lower() for x in kw if isinstance(x, str)}
        for f in ("title", "abstract", "keywords", "journal", "categories", "countries", "citations", "url"):
            if fields.get(w, f) not in (None, "", []):
                seen[f] += 1
        counts.add(k, tset)
        if k < 0:
            continue
        if (j := fields.get(w, "journal")) and isinstance(j, str):
            journals.setdefault(k, Counter())[j] += 1
        for name, src in ((cats, "categories"), (countries, "countries")):
            vals = {x for x in as_list(fields.get(w, src)) if isinstance(x, str)}
            if vals:
                name.setdefault(k, Counter()).update(vals)
        if kw:
            kws.setdefault(k, Counter()).update({x.lower() for x in kw if isinstance(x, str)})
        c = fields.get(w, "citations")
        c = int(c) if isinstance(c, (int, float)) else int(cites_inside[i])
        info = {"id": net.ids[i], "title": title, "year": as_year(fields.get(w, "year")) or None, "citations": c}
        if fields.get(w, "url"):
            info["url"] = fields.get(w, "url")
        if fields.get(w, "abstract"):
            info["abstract"] = str(fields.get(w, "abstract"))[:600]
        item = (c, -i, info)
        if len(best[k]) < top:
            heapq.heappush(best[k], item)
        elif item[:2] > best[k][0][:2]:
            heapq.heapreplace(best[k], item)

    df = Counter()
    for c in counts.c.values():
        df.update(c)
    n_all = net.n
    size = np.bincount(topic[topic >= 0], minlength=m)
    lo, hi = net.pairs()
    s, t, wgt = topic_links(topic, lo, hi) if m else (np.zeros(0, int),) * 3
    neigh = {k: Counter() for k in range(m)}
    inside = Counter()
    for a, b, x in zip(s.tolist(), t.tolist(), wgt.tolist()):
        if a == b:
            inside[a] += x
        else:
            neigh[a][b] += x
            neigh[b][a] += x
    yr = net.year
    rows = []
    for k in range(m):
        n_k = int(size[k])
        e = {
            "topic": k,
            "area": int(area_of_topic[k]),
            "name": names.get(k),
            "works": n_k,
            "share_inside": round(inside[k] / max(inside[k] + sum(neigh[k].values()), 1), 3),
        }
        y = yr[topic == k]
        y = y[y > 0]
        if len(y):
            e["years"] = {
                "median": int(np.median(y)),
                "p10": int(np.percentile(y, 10)),
                "p90": int(np.percentile(y, 90)),
            }
        e["linked_topics"] = [[b, x, names.get(b)] for b, x in neigh[k].most_common(5)]
        e["terms"] = distinctive(counts.c.get(k, Counter()), n_k, df, n_all, terms)
        e["journals"] = shares(journals.get(k, Counter()), n_k, 5)
        e["categories"] = shares(cats.get(k, Counter()), n_k, 5)
        e["keywords"] = shares(kws.get(k, Counter()), n_k, 8)
        e["countries"] = shares(countries.get(k, Counter()), n_k, 5)
        top_works = [info for _, _, info in sorted(best[k], key=lambda x: x[:2], reverse=True)]
        for j, info in enumerate(top_works):
            if j >= 3:
                info.pop("abstract", None)
        e["most_cited"] = top_works
        rows.append({x: v for x, v in e.items() if v not in ([], None) or x == "name"})
    areas = []
    for a in sorted(set(area_of_topic.tolist())):
        ts = [k for k in range(m) if area_of_topic[k] == a]
        n_a = int(size[ts].sum())
        tc, jc, cc = Counter(), Counter(), Counter()
        for k in ts:
            tc.update(counts.c.get(k, Counter()))
            jc.update(journals.get(k, Counter()))
            cc.update(cats.get(k, Counter()))
        areas.append(
            {
                "area": a,
                "name": anames.get(a),
                "works": n_a,
                "topics": [[k, int(size[k]), names.get(k)] for k in ts],
                "terms": distinctive(tc, n_a, df, n_all, terms),
                "journals": shares(jc, n_a, 5),
                "categories": shares(cc, n_a, 6),
            }
        )
    used = sorted(seen)
    missing = sorted({"title", "abstract", "keywords", "journal", "categories", "countries", "citations"} - set(used))
    dossier = {
        "works": n_all,
        "fields_used": used,
        "missing": missing,
        "abstracts_in_terms": abstracts,
        "topics": rows,
        "areas": areas,
    }
    (out / "dossier.json").write_text(json.dumps(dossier, indent=1, ensure_ascii=False))
    log(
        f"dossier of {m} topics and {len(areas)} areas -> {out / 'dossier.json'}"
        + (f" (missing fields: {', '.join(missing)})" if missing else "")
    )
    return dossier
