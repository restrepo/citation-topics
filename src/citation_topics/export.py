"""Exports of a run: the graph of topics for VOSviewer, and CSV tables.

VOSviewer: one item per topic (label = its name, or "Topic N"; cluster = its area; weights: works, citation
links, links inside; score: median year when years are known) and one link per pair of topics, whose strength
is the number of distinct citation links between their works. Writes topics_vosviewer.json (VOSviewer 1.6.16+
and VOSviewer Online) and the classic topics_map.txt and topics_network.txt.

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
from .run import load


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
