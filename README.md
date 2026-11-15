# citation-topics

[![CI](https://github.com/restrepo/citation-topics/actions/workflows/ci.yml/badge.svg)](https://github.com/restrepo/citation-topics/actions/workflows/ci.yml)

Research topics and broad areas for any list of works (papers, theses, projects, patents) from their citation
links, with Leiden clustering of the direct-citation network as CWTS does for the OpenAlex topics. It also gives
each work a second and a third topic, describes every topic from whatever the input carries (titles, abstracts,
keywords, journals, categories, countries), and ships Claude skills and an agent that name the topics.

It was extracted from [restrepo/inspireauth10](https://github.com/restrepo/inspireauth10), where it groups 1.9
million INSPIRE-HEP papers into 304 topics and 6 areas
([how the topics are made](https://restrepo.github.io/inspireauth10/leiden.html)).

Status: first version, not yet on PyPI. Install from a clone:

```bash
pip install -e .
```

## Input

A JSON array or JSON Lines file (optionally gzipped), one object per work:

```json
{"id": "W1", "references": ["W7", "W9"], "year": 2019, "title": "...", "abstract": "...",
 "keywords": ["..."], "journal": "...", "categories": ["..."], "countries": ["..."],
 "authors": ["..."], "citations": 41, "url": "https://..."}
```

- `id` (unique; strings or integers, compared as strings) and `references` (ids of other works) are required.
  References to ids outside the list and self-citations are ignored and counted.
- Every other field is optional. Other names are read with `--id-field`, `--refs-field` and
  `--map NAME=FIELD` (for example `--map year=publication_year`).

| Optional field | Adds |
|---|---|
| `year` | years of each topic, time windows (`--from-year`, `--to-year`), comparisons between epochs |
| `title`, `abstract`, `keywords`, `journal`, `categories` | the description of each topic (`describe`), hence its name |
| `citations` | most cited works by that count (otherwise by citations inside the list) |
| `countries` | countries of each topic in the description |
| `authors`, `url` | counted in `meta.json`; `url` is copied to the most cited works of the description |

## Commands

```bash
citation-topics run works.jsonl.gz out/            # network, topics, areas, second and third topics
citation-topics describe works.jsonl.gz out/       # out/dossier.json: what each topic is about
citation-topics names out/ names.json              # put names into topics.json and areas.json
citation-topics export out/                        # VOSviewer JSON and map/network files, CSVs
citation-topics agreement out_s1/ out_s2/ ...      # NMI/ARI between seeds, and the medoid to keep
citation-topics compare old/ new/ cmp/             # where earlier topics went; names carried over
citation-topics skills install                     # Claude skills and the topic-namer agent into ./.claude
```

`run` options and defaults (those of the INSPIRE run): `--resolution 16` (higher = more, smaller topics),
`--min-size 100` (smaller topics are merged into the topic they share the most links with), `--passes 20`
(stops early when the quality stops rising), `--seed 1`, `--area-resolution 0.3`, `--area-seeds 50` (the best
of that many runs). Tune them for other lists; the skill `topics-run` explains how.

## Method

1. **Network**: one node per work, an edge for each reference to another work of the list; undirected, each
   pair of works once.
2. **Topics**: Leiden maximizing modularity with a resolution parameter (the RB configuration model), with
   igraph's `community_leiden`, pass after pass until the quality stops rising. Works with no link stay
   unassigned; topics under `--min-size` are merged into their most linked neighbour; topics are numbered by
   size.
3. **Areas**: Leiden (leidenalg) on the graph of topics weighted by the links between them, with the links
   inside each topic as self-loops, the best of `--area-seeds` runs. Every topic is in one area.
4. **Second and third topics**: a work's links are counted by the topic at the other end; the second and third
   topics are the most linked other topics, scored as links to them / links to the main topic, capped at 1.
   Works the clustering left out take as main topic the one they link to most (`inferred`).
5. **Description** (`describe`): per topic, its distinctive terms (shares in the topic against the rest of the
   list), journals, categories, keywords, countries, years, linked topics and most cited works.
6. **Names**: written by Claude from the description (skill `topic-namer`), never by the package. `compare`
   carries names over from an earlier run: a topic sharing 60% of its works both ways with an earlier one keeps
   its name.

The same input, parameters and versions of igraph and leidenalg give the same topics; `meta.json` records them
with the MD5 of the input.

## Output

| File | Content |
|---|---|
| `works.jsonl.gz` | per work: `id`, `topic`, `area` (null if none), `topics` (three, with `score` and `links`), `n_links`, `inferred` |
| `topics.json` | per topic: area, name, works, links inside and out, `share_inside`, years, most cited works |
| `areas.json` | per area: name, works, topics, links, `share_inside` |
| `meta.json` | parameters, versions, input MD5, network counts, optional fields present, quality |
| `dossier.json` | description of each topic and area (`describe`) |
| `topics_vosviewer.json`, `topics_map.txt`, `topics_network.txt` | graph of topics for VOSviewer (`export`) |
| `topics.csv`, `works_topics.csv.gz` | the same as tables (`export`) |
| `network.npz`, `clusters.npz` | arrays reused by the other commands |

## Claude skills

`citation-topics skills install` copies into `./.claude` (or `~/.claude` with `--user`):

- `topics-run`: checks the input, chooses the parameters, runs, describes and exports, and explains the result;
- `topic-namer`: names topics and areas from `dossier.json` and applies them, after carrying over earlier names;
- `topics-compare`: seeds (which run to keep) and earlier runs or time windows (fates, flows, names);
- the agent `topic-namer`, which names a batch of topics when the skill hands it one.

In Claude Desktop or Claude Code, ask for topics of a list of works and the skills take it from there.

## Development

```bash
python -m pip install -e ".[dev]"
python -m pytest
ruff check . && ruff format --check .
```

Releases are published to PyPI from GitHub Actions when a `v*` tag is pushed; see [PUBLISHING.md](PUBLISHING.md)
and [CHANGELOG.md](CHANGELOG.md).
