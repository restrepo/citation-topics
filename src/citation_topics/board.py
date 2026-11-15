"""A self-contained HTML board of a run: one page, its data inside it, with a tab for each view the input's
fields allow.

Tabs, and what each needs:
  Overview    always: headline figures, the map of topics, the table of topics
  Timeline    year: works per topic and year
  Works       title: searchable table of the most cited works with topic and second topic
  Highlight   --highlight FIELD: the works where FIELD is true (an author's own papers, a group's works...)
  Countries   countries: share of each topic's works by country
  Authors     authors: the authors with most works in each topic
  About       always: parameters, versions, counts and which fields were present
The page loads d3 from cdnjs; everything else, data included, is in the file.
"""

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from importlib.resources import files
from pathlib import Path

import numpy as np

from . import __version__
from .io import Fields, as_list, as_year, iter_works
from .run import load


def board(
    input,
    out,
    fields=None,
    html=None,
    highlight=None,
    highlight_label="Highlighted works",
    title=None,
    max_works=5000,
    log=print,
):
    fields = fields or Fields()
    out = Path(out)
    net, cl = load(out)
    topics = json.loads((out / "topics.json").read_text())
    areas = {a["area"]: a for a in json.loads((out / "areas.json").read_text())}
    meta_run = json.loads((out / "meta.json").read_text())
    dossier = out / "dossier.json"
    terms = (
        {t["topic"]: [x[0] for x in t.get("terms", [])[:6]] for t in json.loads(dossier.read_text())["topics"]}
        if dossier.exists()
        else {}
    )
    node = {k: i for i, k in enumerate(net.ids)}
    topic, T2 = cl["topic"], cl["topics"]
    d = np.unique(net.src.astype(np.int64) * net.n + net.dst)
    cites_inside = np.bincount(d % net.n, minlength=net.n)

    seen = Counter()
    works = []
    years = Counter()
    country_topic = defaultdict(Counter)
    author_topic = defaultdict(Counter)
    hl = Counter()
    hl_cites = Counter()
    for w in iter_works(input):
        i = node.get(str(w.get(fields.id)))
        if i is None:
            continue
        k = int(topic[i])
        y = as_year(fields.get(w, "year"))
        title_w = fields.get(w, "title")
        c = fields.get(w, "citations")
        c = int(c) if isinstance(c, (int, float)) else int(cites_inside[i])
        flag = bool(w.get(highlight)) if highlight else False
        for f in ("year", "title", "countries", "authors", "url", "citations"):
            if fields.get(w, f) not in (None, "", [], 0):
                seen[f] += 1
        if flag:
            seen["highlight"] += 1
            hl[k] += 1
            hl_cites[k] += c
        if k >= 0 and y > 0:
            years[k, y] += 1
        if k >= 0:
            for x in {x for x in as_list(fields.get(w, "countries")) if isinstance(x, str)}:
                country_topic[x][k] += 1
            for x in {x for x in as_list(fields.get(w, "authors")) if isinstance(x, (str, int))}:
                author_topic[k][str(x)] += 1
        works.append(
            [
                net.ids[i],
                title_w,
                y or None,
                c,
                k if k >= 0 else None,
                int(T2[i, 1]) if T2[i, 1] >= 0 else None,
                fields.get(w, "url"),
                flag,
            ]
        )
    total_works = len(works)
    keep = sorted(works, key=lambda r: (-r[3], r[0]))[:max_works]
    kept = {r[0] for r in keep}
    keep += [r for r in works if r[7] and r[0] not in kept]
    tabs = ["overview"]
    if seen["year"]:
        tabs.append("timeline")
    if seen["title"]:
        tabs.append("works")
    if highlight and seen["highlight"]:
        tabs.append("highlight")
    if seen["countries"]:
        tabs.append("countries")
    if seen["authors"]:
        tabs.append("authors")
    tabs.append("about")

    lo, hi = net.pairs()
    from .cluster import topic_links

    s, t, wgt = topic_links(topic, lo, hi)
    links = [[int(a), int(b), int(x)] for a, b, x in zip(s, t, wgt) if a != b]
    trows = [
        {
            "topic": e["topic"],
            "name": e.get("name") or f"Topic {e['topic']}",
            "area": e["area"],
            "area_name": areas[e["area"]].get("name") or f"Area {e['area']}",
            "works": e["works"],
            "share_inside": e["share_inside"],
            "year_median": e.get("year_median"),
            "terms": ", ".join(terms.get(e["topic"], [])),
            "hl": hl[e["topic"]],
            "hl_citations": hl_cites[e["topic"]],
        }
        for e in topics
    ]
    top_countries = sorted(country_topic, key=lambda x: -sum(country_topic[x].values()))[:25]
    data = {
        "meta": {
            "title": title or "Citation topics",
            "tabs": tabs,
            "highlight_label": highlight_label,
            "created": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "version": __version__,
            "works": net.n,
            "works_with_topic": int((topic >= 0).sum()),
            "links": len(lo),
            "topics": len(trows),
            "areas": len(areas),
            "highlighted": seen["highlight"],
            "works_listed": len(keep),
            "works_total": total_works,
            "fields": dict(seen),
            "parameters": meta_run.get("parameters"),
            "versions": meta_run.get("versions"),
            "names": meta_run.get("names"),
            "input": meta_run.get("input"),
        },
        "topics": trows,
        "links": links,
        "years": [[k, y, n] for (k, y), n in sorted(years.items())],
        "works": keep,
        "countries": [[c, [[k, n] for k, n in sorted(country_topic[c].items())]] for c in top_countries],
        "authors": {str(k): v.most_common(10) for k, v in author_topic.items()},
    }
    tpl = (files("citation_topics") / "board_template.html").read_text(encoding="utf-8")
    page = tpl.replace("__TITLE__", _esc(data["meta"]["title"])).replace(
        "__DATA__", json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    )
    html = Path(html) if html else out / "board.html"
    html.write_text(page, encoding="utf-8")
    log(f"board with tabs {', '.join(tabs)} -> {html} ({html.stat().st_size / 1e6:.1f} MB)")
    return tabs


def _esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
