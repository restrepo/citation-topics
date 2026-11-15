"""Direct-citation network of a list of works: one node per work (in the order of the input), one edge from a
work to each work of the list it cites. References to ids outside the list and self-citations are dropped."""

import json
from array import array
from dataclasses import dataclass, field

import numpy as np

from .io import OPTIONAL, Fields, as_year, iter_works


@dataclass
class Network:
    ids: list  # id of each node, as a string
    src: np.ndarray  # citing node of each edge
    dst: np.ndarray  # cited node of each edge
    year: np.ndarray  # year of each node, 0 if unknown
    stats: dict = field(default_factory=dict)

    @property
    def n(self):
        return len(self.ids)

    def pairs(self, drop_self=False):
        """Undirected edges, each pair of nodes once, sorted: (lo, hi) with lo <= hi."""
        lo, hi = np.minimum(self.src, self.dst), np.maximum(self.src, self.dst)
        if drop_self:
            lo, hi = lo[lo != hi], hi[lo != hi]
        p = np.unique(lo.astype(np.int64) * self.n + hi)
        return (p // self.n).astype(np.int32), (p % self.n).astype(np.int32)

    def save(self, path):
        np.savez_compressed(
            path,
            ids=np.array(self.ids, dtype=str),
            src=self.src,
            dst=self.dst,
            year=self.year,
            stats=np.array(json.dumps(self.stats)),
        )

    @classmethod
    def load(cls, path):
        z = np.load(path)
        return cls(z["ids"].tolist(), z["src"], z["dst"], z["year"], json.loads(str(z["stats"])))


def build(path, fields=None, from_year=None, to_year=None):
    """Read the works of `path` and build their citation network. With from_year or to_year, only works with a
    known year in that range become nodes (a time window)."""
    fields = fields or Fields()
    window = from_year is not None or to_year is not None
    code = {}  # every id seen, as a work or a reference -> integer code
    node_code = array("q")  # code of each node
    ref_codes, ref_end = array("q"), array("q")  # references of all nodes, concatenated; end offset of each node
    years = array("i")
    present = dict.fromkeys(OPTIONAL, 0)
    n_works = n_refs = 0
    for w in iter_works(path):
        n_works += 1
        y = as_year(fields.get(w, "year"))
        if window and (y <= 0 or (from_year is not None and y < from_year) or (to_year is not None and y > to_year)):
            continue
        wid = w.get(fields.id)
        if wid is None:
            raise ValueError(f"work number {n_works} has no {fields.id!r} field")
        c = code.setdefault(str(wid), len(code))
        node_code.append(c)
        years.append(y)
        refs = w.get(fields.references) or []
        n_refs += len(refs)
        ref_codes.extend(code.setdefault(str(r), len(code)) for r in refs)
        ref_end.append(len(ref_codes))
        for k in OPTIONAL:
            v = fields.get(w, k)
            if v not in (None, "", [], {}):
                present[k] += 1
    n = len(node_code)
    node_of = np.full(len(code), -1, dtype=np.int64)
    nc = np.frombuffer(node_code, dtype=np.int64) if n else np.zeros(0, np.int64)
    if len(np.unique(nc)) != n:
        dup = np.unique(nc, return_counts=True)
        first = int(dup[0][dup[1] > 1][0])
        raise ValueError(f"ids must be unique; repeated: {next(k for k, v in code.items() if v == first)!r}")
    node_of[nc] = np.arange(n)
    rc = np.frombuffer(ref_codes, dtype=np.int64) if len(ref_codes) else np.zeros(0, np.int64)
    end = np.frombuffer(ref_end, dtype=np.int64) if n else np.zeros(0, np.int64)
    src = np.repeat(np.arange(n), np.diff(np.r_[0, end]))
    dst = node_of[rc]
    keep = (dst >= 0) & (dst != src)
    ids = [None] * n
    for k, v in code.items():
        i = node_of[v]
        if i >= 0:
            ids[i] = k
    stats = {
        "works_read": n_works,
        "works": n,
        "references": n_refs,
        "references_inside": int(keep.sum()),
        "self_citations": int(((dst >= 0) & (dst == src)).sum()),
        "fields_present": present,
        "window": [from_year, to_year] if window else None,
    }
    return Network(
        ids,
        src[keep].astype(np.int32),
        dst[keep].astype(np.int32),
        np.frombuffer(years, dtype=np.int32).copy() if n else np.zeros(0, np.int32),
        stats,
    )
