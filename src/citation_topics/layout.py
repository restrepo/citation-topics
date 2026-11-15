"""Positions of the works for drawing the network of works (the board's Network tab, works_vosviewer.json).

Each topic is its own cluster: the topics are discs, with area proportional to their works, placed by the links
between them and then moved apart until none overlap; each topic's works are laid out inside its disc by the
links among them (Fruchterman-Reingold, igraph). Works with no citation link are left out; works with a link but
no topic form one more disc. The result is the same for the same run and seed.
"""

import random

import numpy as np


def work_positions(net, topic, seed=1):
    """Returns (linked, xy, a, b): the nodes with at least one link, their positions scaled into 0..1000, and
    the links as pairs of indices into `linked`. None if no work has a link."""
    import igraph as ig

    lo, hi = net.pairs()
    linked = np.flatnonzero(np.bincount(np.r_[lo, hi], minlength=net.n) > 0)
    if not len(linked):
        return None
    sub = np.full(net.n, -1)
    sub[linked] = np.arange(len(linked))
    a, b = sub[lo], sub[hi]
    t = topic[linked]
    groups = np.where(t >= 0, t, t.max() + 1 if (t >= 0).any() else 0)  # works with no topic form one group
    m = int(groups.max()) + 1
    radius = np.sqrt(np.bincount(groups, minlength=m))
    ga, gb = groups[a], groups[b]
    xy = np.zeros((len(linked), 2))
    ig.set_random_number_generator(random.Random(seed))
    try:
        x, y = ga[ga != gb], gb[ga != gb]
        k, w = np.unique(np.minimum(x, y) * m + np.maximum(x, y), return_counts=True)
        tg = ig.Graph(n=m, edges=np.column_stack([k // m, k % m]), directed=False)
        centre = np.array(tg.layout_fruchterman_reingold(weights=(w / max(w.max(), 1)).tolist(), niter=2000).coords)
        centre = _separate(centre * radius.mean() * 2, radius, gap=radius.mean())
        for g in range(m):
            idx = np.flatnonzero(groups == g)
            inside = (ga == g) & (gb == g)
            pos = np.searchsorted(idx, np.column_stack([a[inside], b[inside]]))
            p = np.array(ig.Graph(n=len(idx), edges=pos, directed=False).layout_fruchterman_reingold(niter=500).coords)
            p -= np.median(p, 0)
            p /= max(np.quantile(np.linalg.norm(p, axis=1), 0.98), 1e-9)
            p *= radius[g] / np.maximum(1, np.linalg.norm(p, axis=1))[:, None]  # the few outliers on the rim
            xy[idx] = centre[g] + p
    finally:
        ig.set_random_number_generator(random)
    lo_, hi_ = xy.min(0), xy.max(0)
    xy = (xy - lo_) * (1000 / max((hi_ - lo_).max(), 1e-9))
    return linked, xy, a, b


def _separate(c, r, gap, steps=500):
    """Move discs (centres c, radii r) apart until none overlap, keeping them near where they were."""
    c = c - c.mean(0)
    for _ in range(steps):
        d = c[:, None] - c[None]
        dist = np.linalg.norm(d, axis=2) + np.eye(len(c))
        need = r[:, None] + r[None] + gap - dist
        np.fill_diagonal(need, 0)
        if (need <= 0).all():
            break
        push = (np.maximum(need, 0) / dist)[:, :, None] * d * 0.5
        c = c + push.sum(1) - 0.01 * c
    return c
