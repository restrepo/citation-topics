"""Comparing runs.

compare(old, new): where the topics of an earlier run went, joining works by id (an earlier run may be a time
window of the same list, or an older version of it). Each old topic gets a fate against the new topics:
  same       60% of its works in one new topic, and they are 60% of that topic's works that were in the old run
  absorbed   60% in one new topic that is not the same as it
  split      two or more new topics hold at least 15% of its works each
  scattered  the rest
A new topic that is the same as an old topic takes its name (names_carried.json, in the format of names.json);
the new topics left to name are listed. Areas carry names by the same 60% rule on their works.

agreement(runs): NMI and ARI between runs of the same list (different seeds) on the works all of them assign,
for topics and areas, and the medoid: the run with the highest mean topic NMI to the others, the one to keep.
"""

import itertools
import json
from collections import Counter
from pathlib import Path

import numpy as np

from .run import load

SAME, PART = 0.6, 0.15


def _names(out, part, key):
    f = Path(out) / f"{part}.json"
    return {r[key]: r.get("name") for r in json.loads(f.read_text())} if f.exists() else {}


def _align(old_ids, new_ids):
    """Index in the new run of every old work, -1 if absent."""
    pos = {k: i for i, k in enumerate(new_ids)}
    return np.array([pos.get(k, -1) for k in old_ids], dtype=np.int64)


def fates(a, b):
    """Fates of the labels of `a` against those of `b` (works in both, labels >= 0)."""
    no, nb = int(a.max()) + 1, int(b.max()) + 1
    both = (a >= 0) & (b >= 0)
    C = np.zeros((max(no, 0), max(nb, 0)), np.int64)
    np.add.at(C, (a[both], b[both]), 1)
    sn = C.sum(0)
    rows = []
    for i in range(no):
        tot = C[i].sum()
        j = int(C[i].argmax()) if nb else -1
        share = C[i, j] / max(tot, 1) if nb else 0.0
        back = C[i, j] / max(sn[j], 1) if nb else 0.0
        parts = int((C[i] >= PART * tot).sum()) if tot else 0
        fate = (
            "same"
            if share >= SAME and back >= SAME
            else "absorbed"
            if share >= SAME
            else "split"
            if parts >= 2
            else "scattered"
        )
        rows.append((i, j, float(share), float(back), fate))
    return C, rows


def compare(old, new, result, log=print):
    result = Path(result)
    result.mkdir(parents=True, exist_ok=True)
    net_o, co = load(old)
    net_n, cn = load(new)
    at = _align(net_o.ids, net_n.ids)
    present = at >= 0
    to, tn_all = co["topic"], cn["topic"]
    tn = np.where(present, tn_all[np.maximum(at, 0)], -1)
    C, rows = fates(np.where(present, to, -1), tn)
    names_o, names_n = _names(old, "topics", "topic"), _names(new, "topics", "topic")
    size_o = np.bincount(to[to >= 0], minlength=C.shape[0])
    lost = np.bincount(to[(to >= 0) & present & (tn < 0)], minlength=C.shape[0])
    missing = np.bincount(to[(to >= 0) & ~present], minlength=C.shape[0])
    in_old = np.zeros(net_n.n, bool)
    in_old[at[present]] = True
    nn = int(tn_all.max()) + 1
    size_n = np.bincount(tn_all[tn_all >= 0], minlength=nn)
    new_only = np.bincount(tn_all[(tn_all >= 0) & ~in_old], minlength=nn)
    old_rows = [
        {
            "topic": i,
            "works": int(size_o[i]),
            "best": j,
            "share": round(s, 3),
            "back": round(b, 3),
            "fate": f,
            "no_topic_now": int(lost[i]),
            "not_in_new_run": int(missing[i]),
            "name": names_o.get(i),
        }
        for i, j, s, b, f in rows
    ]
    carried, sources = {}, {}
    for i, j, s, b, f in rows:
        if f == "same" and names_o.get(i):
            carried[j] = {
                "name": names_o[i],
                "reason": f"carried over from topic {i} of the earlier run "
                f"({s:.0%} of its works here, {b:.0%} of this topic's)",
            }
            sources[j] = i
    # areas by the same rule
    ao, an_all = co["area"], cn["area"]
    an = np.where(present, an_all[np.maximum(at, 0)], -1)
    _, arows = fates(np.where(present, ao, -1), an) if (ao >= 0).any() and (an >= 0).any() else (None, [])
    anames_o = _names(old, "areas", "area")
    acarried = {
        j: {"name": anames_o[i], "reason": f"carried over from area {i} of the earlier run"}
        for i, j, s, b, f in arows
        if f == "same" and anames_o.get(i)
    }
    flows = [[int(i), int(j), int(C[i, j])] for i, j in zip(*np.nonzero(C))]
    mask = (to >= 0) & (tn >= 0)
    nmi = ari = None
    if mask.sum() > 1:
        import igraph as ig

        x, y = to[mask].tolist(), tn[mask].tolist()
        nmi, ari = ig.compare_communities(x, y, "nmi"), ig.compare_communities(x, y, "adjusted_rand")
    new_rows = [
        {
            "topic": j,
            "works": int(size_n[j]),
            "works_not_in_old_run": int(new_only[j]),
            "name": names_n.get(j) or carried.get(j, {}).get("name"),
            "same_as": sources.get(j),
        }
        for j in range(nn)
    ]
    counts = dict(Counter(r["fate"] for r in old_rows))
    out = {
        "old": old_rows,
        "new": new_rows,
        "flows": flows,
        "meta": {
            "old": str(old),
            "new": str(new),
            "works_old": net_o.n,
            "works_new": net_n.n,
            "works_in_both": int(present.sum()),
            "both_with_topic": int(mask.sum()),
            "fates": counts,
            "nmi": nmi,
            "ari": ari,
            "rule": {"same": SAME, "split_part": PART},
        },
    }
    (result / "flows.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    to_name = [j for j in range(nn) if j not in carried]
    (result / "names_carried.json").write_text(
        json.dumps(
            {
                "topics": {str(k): v for k, v in sorted(carried.items())},
                "areas": {str(k): v for k, v in sorted(acarried.items())},
                "to_name": {"topics": to_name, "areas": sorted(set(range(int(an_all.max()) + 1)) - set(acarried))},
                "meta": {"by": "citation-topics compare", "from": str(old)},
            },
            indent=1,
            ensure_ascii=False,
        )
    )
    log(
        f"{len(old_rows)} earlier topics: {counts}; NMI {nmi if nmi is None else round(nmi, 3)}, "
        f"ARI {ari if ari is None else round(ari, 3)}; {len(carried)} names carried over, {len(to_name)} topics to name"
    )
    return out


def agreement(outs, log=print):
    import igraph as ig

    runs = [load(o) for o in outs]
    ids0 = runs[0][0].ids
    labels = []
    for net, c in runs:
        if net.ids == ids0:
            labels.append((c["topic"], c["area"]))
        else:
            at = _align(ids0, net.ids)
            labels.append(tuple(np.where(at >= 0, c[k][np.maximum(at, 0)], -1) for k in ("topic", "area")))
    mask = np.logical_and.reduce([t >= 0 for t, _ in labels])
    log(f"{len(outs)} runs, {int(mask.sum())} works assigned in all")
    mean = np.zeros(len(outs))
    table = {}
    for level in (0, 1):
        for i, j in itertools.combinations(range(len(outs)), 2):
            a, b = labels[i][level][mask].tolist(), labels[j][level][mask].tolist()
            nmi, ari = ig.compare_communities(a, b, "nmi"), ig.compare_communities(a, b, "adjusted_rand")
            table[("topic", "area")[level], outs[i], outs[j]] = (nmi, ari)
            log(f"{('topics', 'areas')[level]}: {outs[i]} vs {outs[j]}: NMI {nmi:.3f}, ARI {ari:.3f}")
            if level == 0:
                mean[i] += nmi
                mean[j] += nmi
    best = int(np.argmax(mean)) if len(outs) > 1 else 0
    if len(outs) > 1:
        log(f"medoid: {outs[best]} (mean topic NMI {mean[best] / (len(outs) - 1):.3f})")
    return outs[best], table
