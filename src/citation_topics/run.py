"""The whole run: input -> network -> topics and areas -> second and third topics -> output files.

Output folder:
  works.jsonl.gz  one line per work: id, topic, area, three topics with score and links, n_links, inferred
  topics.json     one entry per topic: area, works, links, share of links inside, years, most cited works, name
  areas.json      one entry per area: works, topics, links, share of links inside, name
  meta.json       parameters, versions, input MD5, counts, quality, which optional fields the input has
  network.npz     the citation network (ids, edges, years), reused by the other commands
  clusters.npz    the same results as arrays aligned with network.npz
"""

import gzip
import json
import platform
import sys
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import numpy as np

from . import __version__
from .cluster import Clusters, cluster, topic_links
from .io import Fields, md5
from .network import Network, build
from .secondary import Secondary, secondary

DEFAULTS = {"resolution": 16.0, "min_size": 100, "passes": 20, "seed": 1, "area_resolution": 0.3, "area_seeds": 50}


def versions():
    out = {"citation-topics": __version__, "python": platform.python_version()}
    for p in ("igraph", "leidenalg", "numpy"):
        try:
            out[p] = version(p)
        except PackageNotFoundError:
            out[p] = None
    return out


def run(input, out, fields=None, from_year=None, to_year=None, log=print, **params):
    p = {**DEFAULTS, **{k: v for k, v in params.items() if v is not None}}
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    fields = fields or Fields()
    log(f"reading {input}")
    net = build(input, fields, from_year, to_year)
    st = net.stats
    log(f"{st['works']} works, {st['references_inside']} of {st['references']} references inside the list")
    net.save(out / "network.npz")
    cl = cluster(net, log=log, **p)
    sec = secondary(net, cl.topic)
    save_clusters(out / "clusters.npz", net, cl, sec)
    write_outputs(out, net, cl, sec)
    meta = {
        "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "input": {"file": Path(input).name, "md5": md5(input)},
        "fields": fields.as_dict(),
        "parameters": {**p, "from_year": from_year, "to_year": to_year},
        "versions": versions(),
        "network": st,
        "result": {
            "topics": int(cl.topic.max()) + 1,
            "areas": len(set(cl.area_of_topic.tolist())),
            "works_with_topic": int((cl.topic >= 0).sum()),
            "works_inferred": int(sec.inferred.sum()),
            "works_without_topic": int((sec.topic[:, 0] < 0).sum()),
            "quality": cl.quality,
            "area_quality": cl.area_quality,
            "passes": cl.passes,
            "area_runs": cl.area_runs,
        },
        "command": " ".join(sys.argv) if sys.argv and "citation-topics" in sys.argv[0] else None,
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False))
    log(f"{meta['result']['topics']} topics, {meta['result']['areas']} areas -> {out}")
    return meta


def save_clusters(path, net, cl: Clusters, sec: Secondary):
    np.savez_compressed(
        path,
        topic=cl.topic,
        area=cl.area,
        area_of_topic=cl.area_of_topic,
        quality=cl.quality,
        area_quality=cl.area_quality,
        topics=sec.topic,
        score=sec.score,
        links=sec.links,
        n_links=sec.n_links,
        inferred=sec.inferred,
    )


def load(out):
    """(network, clusters dict) of an output folder."""
    out = Path(out)
    return Network.load(out / "network.npz"), dict(np.load(out / "clusters.npz"))


def write_outputs(out, net, cl: Clusters, sec: Secondary, top=10):
    out = Path(out)
    topic, n = cl.topic, net.n
    with gzip.open(out / "works.jsonl.gz", "wt", encoding="utf-8") as f:
        for i in range(n):
            t = int(topic[i])
            row = {
                "id": net.ids[i],
                "topic": t if t >= 0 else None,
                "area": int(cl.area[i]) if t >= 0 else None,
                "topics": [
                    {
                        "topic": int(sec.topic[i, r]),
                        "score": round(float(sec.score[i, r]), 4),
                        "links": int(sec.links[i, r]),
                    }
                    for r in range(3)
                    if sec.topic[i, r] >= 0
                ],
                "n_links": int(sec.n_links[i]),
                "inferred": bool(sec.inferred[i]),
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    m = int(topic.max()) + 1
    lo, hi = net.pairs()
    s, t, w = topic_links(topic, lo, hi) if m > 0 else (np.zeros(0, int),) * 3
    inside = np.bincount(s[s == t], weights=w[s == t], minlength=m).astype(int)
    cross = np.bincount(np.r_[s[s != t], t[s != t]], weights=np.r_[w[s != t], w[s != t]], minlength=m).astype(int)
    d = np.unique(net.src.astype(np.int64) * n + net.dst)  # each citing-cited pair once
    cites = np.bincount(d % n, minlength=n)
    yr = net.year
    topics = []
    for k in range(m):
        idx = np.flatnonzero(topic == k)
        e = {
            "topic": k,
            "area": int(cl.area_of_topic[k]),
            "name": None,
            "works": len(idx),
            "links_inside": int(inside[k]),
            "links_out": int(cross[k]),
            "share_inside": round(inside[k] / max(inside[k] + cross[k], 1), 4),
        }
        y = yr[idx][yr[idx] > 0]
        if len(y):
            e.update(
                year_median=int(np.median(y)), year_p10=int(np.percentile(y, 10)), year_p90=int(np.percentile(y, 90))
            )
        best = idx[np.lexsort((idx, -cites[idx]))][:top]
        e["most_cited"] = [{"id": net.ids[i], "citations_inside": int(cites[i])} for i in best]
        topics.append(e)
    (out / "topics.json").write_text(json.dumps(topics, indent=1, ensure_ascii=False))
    areas = []
    for a in range(len(set(cl.area_of_topic.tolist()))):
        ts = [k for k in range(m) if cl.area_of_topic[k] == a]
        at = cl.area_of_topic[s], cl.area_of_topic[t]
        a_in = int(w[(at[0] == a) & (at[1] == a)].sum())
        a_out = int(w[(at[0] == a) != (at[1] == a)].sum())
        areas.append(
            {
                "area": a,
                "name": None,
                "works": int(sum(topics[k]["works"] for k in ts)),
                "topics": ts,
                "links_inside": a_in,
                "links_out": a_out,
                "share_inside": round(a_in / max(a_in + a_out, 1), 4),
            }
        )
    (out / "areas.json").write_text(json.dumps(areas, indent=1, ensure_ascii=False))
