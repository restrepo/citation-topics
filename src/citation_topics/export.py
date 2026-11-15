"""Exports of a run: the graph of topics for VOSviewer, and CSV tables.

VOSviewer: one item per topic (label = its name, or "Topic N"; cluster = its area; weights: works, citation
links, links inside; score: median year when years are known) and one link per pair of topics, whose strength
is the number of distinct citation links between their works. Writes topics_vosviewer.json (VOSviewer 1.6.16+
and VOSviewer Online) and the classic topics_map.txt and topics_network.txt.

VOSviewer, works (`export --works INPUT`, at most --network-max works): one item per work with a citation link,
placed as in the board's Network tab (each topic its own cluster), cluster = its topic (named), weights: citations
and citation links, score: year, a link per citation link. Writes works_vosviewer.json; VOSviewer Online opens it
from a public URL as https://app.vosviewer.com/?json=URL.

CSV: topics.csv (topic, name, area, area name, works, share of links inside) and works_topics.csv.gz (one row
per work with a topic: id and, for each of its three topics, the topic, score and links, then n_links and
inferred).
"""

import csv
import gzip
import json
from pathlib import Path

import numpy as np

from .cluster import topic_links
from .io import Fields, as_year, iter_works
from .layout import work_positions
from .run import load

VOSVIEWER_ONLINE = "https://app.vosviewer.com/?json="


def _rows(out):
    out = Path(out)
    return json.loads((out / "topics.json").read_text()), json.loads((out / "areas.json").read_text())


def export_vosviewer(out, min_links=1, log=print):
    out = Path(out)
    net, c = load(out)
    topic = c["topic"]
    m = int(topic.max()) + 1
    topics, areas = _rows(out)
    aname = {a["area"]: a.get("name") or f"Area {a['area']}" for a in areas}
    lo, hi = net.pairs()
    s, t, w = topic_links(topic, lo, hi)
    inside = np.bincount(s[s == t], weights=w[s == t], minlength=m).astype(int)
    cross = (s != t) & (w >= min_links)
    s, t, w = s[cross], t[cross], w[cross]
    links_of = np.bincount(np.concatenate([s, t]), weights=np.concatenate([w, w]), minlength=m).astype(int)
    items = []
    for e in topics:
        i = e["topic"]
        label = e.get("name") or f"Topic {i}"
        years = f", {e['year_p10']}–{e['year_p90']}" if "year_p10" in e else ""  # noqa: RUF001
        it = {
            "id": i + 1,
            "label": label,
            "cluster": e["area"] + 1,
            "description": f"<b>{label}</b><br>{aname[e['area']]}<br>{e['works']:,} works{years}",
            "weights": {
                "Works": e["works"],
                "Citation links": int(links_of[i]),
                "Internal citation links": int(inside[i]),
            },
        }
        if "year_median" in e:
            it["scores"] = {"Median year": e["year_median"]}
        items.append(it)
    links = [{"source_id": int(i) + 1, "target_id": int(j) + 1, "strength": int(x)} for i, j, x in zip(s, t, w)]
    vos = {
        "network": {"items": items, "links": links},
        "config": {
            "terminology": {
                "item": "topic",
                "items": "topics",
                "link": "citation link",
                "links": "citation links",
                "link_strength": "citation links",
                "total_link_strength": "total citation links",
            }
        },
    }
    (out / "topics_vosviewer.json").write_text(json.dumps(vos, ensure_ascii=False))
    has_year = all("scores" in it for it in items)
    with open(out / "topics_map.txt", "w", encoding="utf-8") as f:
        f.write(
            "id\tlabel\tcluster\tweight<Works>\tweight<Citation links>"
            + ("\tscore<Median year>" if has_year else "")
            + "\n"
        )
        for it in items:
            f.write(
                f"{it['id']}\t{it['label']}\t{it['cluster']}\t{it['weights']['Works']}\t"
                f"{it['weights']['Citation links']}" + (f"\t{it['scores']['Median year']}" if has_year else "") + "\n"
            )
    with open(out / "topics_network.txt", "w", encoding="utf-8") as f:
        for li in links:
            f.write(f"{li['source_id']}\t{li['target_id']}\t{li['strength']}\n")
    log(f"VOSviewer: {m} topics, {len(links)} links -> {out / 'topics_vosviewer.json'}")


def export_works_vosviewer(input, out, fields=None, highlight=None, highlight_label=None, network_max=10000, log=print):
    """works_vosviewer.json: the network of works, with the board's positions. Returns its path, or None when the
    run has more than network_max works or no links."""
    fields = fields or Fields()
    out = Path(out)
    net, c = load(out)
    if net.n > network_max:
        log(f"VOSviewer works: {net.n:,} works, more than {network_max:,}; not written (see --network-max)")
        return None
    pos = work_positions(net, c["topic"])
    if pos is None:
        return None
    linked, xy, a, b = pos
    topics, _ = _rows(out)
    tname = {e["topic"]: e.get("name") or f"Topic {e['topic']}" for e in topics}
    want = {net.ids[i]: j for j, i in enumerate(linked)}
    info = {}
    for w in iter_works(input):
        k = str(w.get(fields.id))
        if k in want:
            info[k] = w
    degree = np.bincount(np.r_[a, b], minlength=len(linked))
    label_hl = highlight_label or highlight
    items = []
    for j, i in enumerate(linked):
        k, w = net.ids[i], info.get(net.ids[i], {})
        title = fields.get(w, "title")
        title = title if isinstance(title, str) and title else k
        year = as_year(fields.get(w, "year"))
        cites = fields.get(w, "citations")
        url = fields.get(w, "url")
        t = int(c["topic"][i])
        lines = [f"<b>{_html(title)}</b>"]
        if t >= 0:
            lines.append(_html(tname.get(t, f"Topic {t}")))
        lines.append(
            ", ".join(
                x
                for x in (
                    str(year) if year else "",
                    f"{int(cites):,} citations" if isinstance(cites, (int, float)) else "",
                    _html(label_hl) if highlight and w.get(highlight) else "",
                )
                if x
            )
        )
        it = {
            "id": k,
            "label": title if len(title) <= 60 else title[:58] + "…",
            "x": round(float(xy[j, 0]) / 100, 3),
            "y": round(-float(xy[j, 1]) / 100, 3),  # VOSviewer's y grows upwards
            "description": "<br>".join(x for x in lines if x),
            "weights": {"Citation links": int(degree[j])},
        }
        if t >= 0:
            it["cluster"] = t + 1
        if isinstance(cites, (int, float)):
            it["weights"]["Citations"] = int(cites)
        if year:
            it["scores"] = {"Year": year}
        if isinstance(url, str) and url:
            it["url"] = url
        items.append(it)
    ids = [net.ids[i] for i in linked]
    vos = {
        "network": {
            "items": items,
            "links": [{"source_id": ids[x], "target_id": ids[y], "strength": 1} for x, y in zip(a, b)],
            "clusters": [{"cluster": e["topic"] + 1, "label": tname[e["topic"]]} for e in topics],
        },
        "config": {
            "terminology": {
                "item": "work",
                "items": "works",
                "link": "citation link",
                "links": "citation links",
                "cluster": "topic",
                "clusters": "topics",
                "link_strength": "citation links",
                "total_link_strength": "citation links",
            },
            "parameters": {"largest_component": False, "max_n_links": len(a), "item_size_variation": 0.3},
        },
        "info": {
            "title": "Network of works by topic",
            "description": f"{len(items):,} works with a citation link and {len(a):,} citation links, in "
            f"{len(topics)} topics (citation-topics).",
        },
    }
    path = out / "works_vosviewer.json"
    path.write_text(json.dumps(vos, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    log(f"VOSviewer: {len(items):,} works, {len(a):,} links -> {path}")
    return path


def _html(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def export_csv(out, log=print):
    out = Path(out)
    net, c = load(out)
    topics, areas = _rows(out)
    aname = {a["area"]: a.get("name") or "" for a in areas}
    with open(out / "topics.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["topic", "name", "area", "area_name", "works", "share_inside"])
        w.writerows(
            [e["topic"], e.get("name") or "", e["area"], aname[e["area"]], e["works"], e["share_inside"]]
            for e in topics
        )
    T, S, L = c["topics"], c["score"], c["links"]
    with gzip.open(out / "works_topics.csv.gz", "wt", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            ["id"] + [f"{x}_{r}" for r in (1, 2, 3) for x in ("topic", "score", "links")] + ["n_links", "inferred"]
        )
        for i in np.flatnonzero(T[:, 0] >= 0):
            row = [net.ids[i]]
            for r in range(3):
                row += [int(T[i, r]), f"{S[i, r]:.4f}", int(L[i, r])] if T[i, r] >= 0 else ["", "", ""]
            w.writerow([*row, int(c["n_links"][i]), int(bool(c["inferred"][i]))])
    log(f"CSV: topics.csv, works_topics.csv.gz -> {out}")
