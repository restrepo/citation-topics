"""Second and third topics of every work, scored against its main topic.

A work's citation links (references and citing works, each pair once) are counted by the topic of the work at
the other end. The main topic is the work's own topic (score 1); the second and third are the other topics with
the most links, scored as links to that topic / links to the main topic, capped at 1. Works with no topic from
the clustering get as main topic the topic they have most links to, marked as inferred. Works with no link to
any topic keep no topic.
"""

from dataclasses import dataclass

import numpy as np


@dataclass
class Secondary:
    topic: np.ndarray  # (n, 3) main, second, third topic; -1 if none
    score: np.ndarray  # (n, 3)
    links: np.ndarray  # (n, 3) links to each of the three topics
    n_links: np.ndarray  # links to works with a topic
    inferred: np.ndarray  # main topic inferred (no topic from the clustering)


def secondary(net, topic):
    n = net.n
    lo, hi = net.pairs(drop_self=True)
    lo, hi = lo.astype(np.int64), hi.astype(np.int64)
    m = max(int(topic.max()) + 1, 1)
    p = np.concatenate([lo[topic[hi] >= 0], hi[topic[lo] >= 0]])
    t = np.concatenate([topic[hi[topic[hi] >= 0]], topic[lo[topic[lo] >= 0]]])
    del lo, hi
    k, c = np.unique(p * m + t, return_counts=True)
    p, t = k // m, k % m
    o = np.lexsort((-c, p))  # by work, most links first
    p, t, c = p[o], t[o], c[o]
    n_links = np.bincount(p, weights=c, minlength=n).astype(np.int64)

    main = topic.copy()
    inferred = (main < 0) & (n_links > 0)
    first = np.r_[True, p[1:] != p[:-1]] if len(p) else np.zeros(0, bool)
    main[p[first & inferred[p]]] = t[first & inferred[p]]
    own = t == main[p]
    main_links = np.zeros(n, dtype=np.int64)
    main_links[p[own]] = c[own]
    p, t, c = p[~own], t[~own], c[~own]
    start = np.r_[0, np.flatnonzero(p[1:] != p[:-1]) + 1] if len(p) else np.zeros(0, np.int64)
    rank = np.arange(len(p)) - np.repeat(start, np.diff(np.r_[start, len(p)]))

    T = -np.ones((n, 3), dtype=np.int32)
    L = np.zeros((n, 3), dtype=np.int32)
    T[:, 0], L[:, 0] = main, main_links
    for r in (1, 2):
        s = rank == r - 1
        T[p[s], r], L[p[s], r] = t[s], c[s]
    S = np.zeros((n, 3), dtype=np.float32)
    S[main >= 0, 0] = 1
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.where(L[:, 0:1] > 0, L[:, 1:] / L[:, 0:1], 1.0)
    S[:, 1:] = np.where(T[:, 1:] >= 0, np.minimum(ratio, 1), 0)
    return Secondary(T, S, L, n_links, inferred)
