"""Topics and areas by Leiden clustering, as CWTS does for the OpenAlex topics.

Topics: Leiden maximizing modularity with a resolution (the RB configuration model; higher = more, smaller
topics) on the undirected citation graph, each pair of works once, with igraph's community_leiden. Topics
smaller than `min_size` works are merged into the topic they share the most links with; works with no link
stay unassigned (-1). Topics are numbered by size, largest first.

Areas: Leiden (leidenalg, RB configuration model) on the graph of topics weighted by the links between them,
with the links inside each topic as self-loops (the network coarsened to topics), the best of `area_seeds`
runs. Areas are numbered by size; every topic belongs to one area, so the hierarchy nests.
"""

import random
import time
from dataclasses import dataclass

import numpy as np


@dataclass
class Clusters:
    topic: np.ndarray  # topic of each node, -1 if none
    area: np.ndarray  # area of each node, -1 if none
    area_of_topic: np.ndarray
    quality: float
    area_quality: float
    passes: int
    area_runs: dict  # number of areas -> number of seeds that found it


def leiden_topics(lo, hi, n, resolution=16.0, min_size=100, passes=20, seed=1, log=print):
    """Topic of each node from the undirected pairs (lo, hi). Returns (topic, quality, passes run)."""
    import igraph as ig

    t0 = time.time()
    g = ig.Graph(n=n, edges=np.column_stack([lo, hi]), directed=False)
    log(f"graph: {n} works, {g.ecount()} links")
    rng = random.Random(seed)
    ig.set_random_number_generator(rng)
    try:
        part, last, done = None, None, 0
        for i in range(passes):
            part = g.community_leiden(
                objective_function="modularity",
                resolution=resolution,
                n_iterations=1,
                initial_membership=part.membership if part else None,
            )
            done = i + 1
            log(f"leiden pass {done}: {len(part)} clusters, quality {part.quality:.6g} ({time.time() - t0:.0f} s)")
            if last is not None and part.quality - last <= 1e-7 * abs(last):
                break
            last = part.quality
    finally:
        ig.set_random_number_generator(random)
    topic = np.array(part.membership) if part else np.zeros(n, dtype=np.int64)
    quality = part.quality if part else 0.0
    topic = merge_small(topic, lo, hi, n, min_size)
    log(
        f"topics: {topic.max() + 1} with {min_size}+ works, {np.count_nonzero(topic >= 0)} works assigned, "
        f"{np.count_nonzero(topic < 0)} unassigned"
    )
    return topic, quality, done


def merge_small(topic, lo, hi, n, min_size):
    """Unassign works with no link, merge topics under min_size into the topic they share the most links with
    (repeatedly), unassign what is still too small, and number the topics by size."""
    topic = topic.copy()
    deg = np.bincount(np.r_[lo, hi], minlength=n)
    topic[deg == 0] = -1
    if not (topic >= 0).any():
        return topic
    for _ in range(20):
        size = np.bincount(topic[topic >= 0])
        small = np.flatnonzero((size > 0) & (size < min_size))
        if not len(small):
            break
        tl, th = topic[lo], topic[hi]
        ok = (tl >= 0) & (th >= 0) & (tl != th)
        a_, b_ = np.r_[tl[ok], th[ok]], np.r_[th[ok], tl[ok]]
        from_small = np.isin(a_, small) & ~np.isin(b_, small)
        if not from_small.any():
            break
        m = topic.max() + 1
        k, c = np.unique(a_[from_small].astype(np.int64) * m + b_[from_small], return_counts=True)
        best = {}
        for s, d, cnt in zip(k // m, k % m, c):
            if cnt > best.get(s, (0, -1))[0]:
                best[s] = (cnt, d)
        remap = np.arange(m)
        for s, (_, d) in best.items():
            remap[s] = d
        topic = np.where(topic >= 0, remap[np.maximum(topic, 0)], -1)
    size = np.bincount(topic[topic >= 0])
    topic = np.where(topic >= 0, np.where(size[np.maximum(topic, 0)] >= min_size, topic, -1), -1)
    if not (topic >= 0).any():
        return topic
    ids, cnt = np.unique(topic[topic >= 0], return_counts=True)
    rank = np.empty(topic.max() + 1, dtype=np.int64)
    rank[ids[np.argsort(-cnt)]] = np.arange(len(ids))
    return np.where(topic >= 0, rank[np.maximum(topic, 0)], -1)


def topic_links(topic, lo, hi):
    """Links between topics: (s, t, weight) with s <= t; s == t counts the links inside a topic."""
    m = int(topic.max()) + 1
    tl, th = topic[lo], topic[hi]
    ok = (tl >= 0) & (th >= 0)
    k, w = np.unique(np.minimum(tl[ok], th[ok]).astype(np.int64) * m + np.maximum(tl[ok], th[ok]), return_counts=True)
    return k // m, k % m, w


def leiden_areas(topic, lo, hi, resolution=0.3, seeds=50, log=print):
    """Area of each topic: the best of `seeds` Leiden runs on the graph of topics. Returns
    (area_of_topic, quality, {number of areas: runs})."""
    import igraph as ig
    import leidenalg as la

    m = int(topic.max()) + 1
    if m <= 0:
        return np.zeros(0, dtype=np.int64), 0.0, {}
    s, t, w = topic_links(topic, lo, hi)
    tg = ig.Graph(n=m, edges=np.column_stack([s, t]), directed=False)
    tg.es["weight"] = w.tolist()
    runs = [
        la.find_partition(
            tg,
            la.RBConfigurationVertexPartition,
            weights="weight",
            resolution_parameter=resolution,
            n_iterations=-1,
            seed=k,
        )
        for k in range(1, seeds + 1)
    ]
    best = max(runs, key=lambda q: q.quality())
    counts = np.bincount([len(q) for q in runs])
    found = {int(k): int(c) for k, c in enumerate(counts) if c}
    log("areas over seeds: " + ", ".join(f"{c} runs with {k}" for k, c in found.items()))
    area_of_topic = np.array(best.membership)
    asize = np.bincount(area_of_topic, weights=np.bincount(topic[topic >= 0], minlength=m))
    rank = np.empty(len(asize), dtype=np.int64)
    rank[np.argsort(-asize)] = np.arange(len(asize))
    return rank[area_of_topic], best.quality(), found


def cluster(net, resolution=16.0, min_size=100, passes=20, seed=1, area_resolution=0.3, area_seeds=50, log=print):
    lo, hi = net.pairs()
    topic, quality, done = leiden_topics(lo, hi, net.n, resolution, min_size, passes, seed, log)
    area_of_topic, area_quality, found = leiden_areas(topic, lo, hi, area_resolution, area_seeds, log)
    area = np.where(topic >= 0, area_of_topic[np.maximum(topic, 0)], -1) if len(area_of_topic) else topic.copy()
    log(f"areas: {len(set(area_of_topic.tolist()))}")
    return Clusters(topic, area, area_of_topic, float(quality), float(area_quality), done, found)
