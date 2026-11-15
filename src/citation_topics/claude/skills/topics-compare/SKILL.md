---
name: topics-compare
description: Compare runs of citation-topics - agreement between seeds (NMI, ARI, medoid to keep) and where the topics of an earlier run or time window went in a later one (same, absorbed, split, scattered, with flows between topics and names carried over). Use whenever the user asks how stable the topics are, which seed to keep, how topics defined up to some year changed, how a new version of a list changes its topics, or wants to keep names from a previous run.
---

# Comparing runs of citation-topics

## Seeds of one list

```bash
for s in 1 2 3 4; do citation-topics run INPUT OUT_s$s/ --seed $s; done    # same other parameters
citation-topics agreement OUT_s1/ OUT_s2/ OUT_s3/ OUT_s4/
```

It prints NMI and ARI for every pair, for topics and areas, on the works all runs assign, and the medoid (the
run with the highest mean topic NMI to the others): keep that one. Topic NMI around 0.85 between seeds is
usual for large citation networks; much lower means the resolution is too high for the list or the list is
small.

## An earlier run against a later one

The earlier run can be a time window of the same list (`run INPUT OLD/ --to-year 2010`) or a run of an older
version of the list. Works are joined by id.

```bash
citation-topics compare OLD/ NEW/ CMP/
```

`CMP/flows.json`:

- `old`: each earlier topic with its best new topic, `share` (of its works there), `back` (of that topic's
  works that were in the earlier run) and `fate`: **same** (60% both ways), **absorbed** (60% one way),
  **split** (two or more new topics with 15% each), **scattered**.
- `new`: each new topic with its works not in the earlier run and the earlier topic it is the same as.
- `flows`: `[old, new, works]` for every pair; `meta`: counts of fates, NMI and ARI.

`CMP/names_carried.json` holds the names of the earlier topics that are the same as a new one, ready for
`citation-topics names NEW/ CMP/names_carried.json`, and the topics left to name (skill `topic-namer`).

Report the counts of each fate, NMI and ARI, the largest splits and merges by name, and how many new topics
have most of their works after the earlier run.
