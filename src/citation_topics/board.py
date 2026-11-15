"""A self-contained HTML board of a run: one page, its data inside it, with a tab for each view the input's
fields allow.

Tabs, and what each needs:
  Overview    always: headline figures, the map of topics, the table of topics
  Timeline    year: works per topic and year
  Works       title: searchable table of the most cited works with topic and second topic
  Network     at most --network-max works (10,000): every work with a citation link, each topic a cluster of
              its works labelled with its name, coloured by area
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
from urllib.parse import quote

import numpy as np

from . import __version__
from .export import VOSVIEWER_ONLINE, _authors, _first_author
from .io import Fields, as_list, as_year, iter_works
from .layout import work_positions
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
    network_max=10000,
    vosviewer_url=None,
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
                _authors(fields, w),
                _first_author(fields, w),
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
    network = None
    if 0 < net.n <= network_max:
        tabs.append("network")
        flags = {r[0]: r[7] for r in works}
        info = {r[0]: r for r in works}
        network = _network(net, topic, info, flags)
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
            "vosviewer": VOSVIEWER_ONLINE + quote(vosviewer_url, safe="") if vosviewer_url and network else None,
        },
        "topics": trows,
        "links": links,
        "years": [[k, y, n] for (k, y), n in sorted(years.items())],
        "works": keep,
        "countries": [[c, [[k, n] for k, n in sorted(country_topic[c].items())]] for c in top_countries],
        "authors": {str(k): v.most_common(10) for k, v in author_topic.items()},
        "network": network,
    }
    tpl = (files("citation_topics") / "board_template.html").read_text(encoding="utf-8")
    page = tpl.replace("__TITLE__", _esc(data["meta"]["title"])).replace(
        "__DATA__", json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    )
    html = Path(html) if html else out / "board.html"
    html.write_text(page, encoding="utf-8")
    log(f"board with tabs {', '.join(tabs)} -> {html} ({html.stat().st_size / 1e6:.1f} MB)")
    return tabs


def _network(net, topic, info, flags, seed=1):
    """Every work with a citation link, placed so that each topic is its own cluster (layout.py), the links among
    them and where to label each topic."""
    pos = work_positions(net, topic, seed)
    if pos is None:
        return None
    linked, xy, a, b, both = pos
    t = topic[linked]
    labels = [  # topic, x of its centre, y just above and just below its works
        [int(k), *(round(float(v), 1) for v in (np.median(xy[t == k, 0]), *np.quantile(xy[t == k, 1], [0.03, 0.97])))]
        for k in np.unique(t[t >= 0])
    ]
    nodes = []
    for j, i in enumerate(linked):
        r = info.get(net.ids[i]) or [net.ids[i], None, None, 0, None, None, None, False, None, None]
        title = r[1] if isinstance(r[1], str) else ""
        nodes.append(
            [
                round(float(xy[j, 0]), 1),
                round(float(xy[j, 1]), 1),
                int(t[j]) if t[j] >= 0 else None,
                r[3],
                r[2],
                1 if flags.get(net.ids[i]) else 0,
                title[:140],
                r[6] if isinstance(r[6], str) else None,
                r[8],
                r[9],
            ]
        )
    return {
        "nodes": nodes,
        "links": np.column_stack([a, b]).ravel().tolist(),  # pairs: the first cites the second
        "mutual": np.flatnonzero(both).tolist(),  # pairs that also cite the other way
        "labels": labels,
    }


def _esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
