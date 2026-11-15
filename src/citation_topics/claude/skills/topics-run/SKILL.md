---
name: topics-run
description: Build research topics and broad areas for any list of works (papers, theses, projects, patents) from their citation links with the citation-topics package - Leiden clustering of the direct-citation network as CWTS does for the OpenAlex topics, plus second and third topics of every work, a description of each topic, names, and VOSviewer/CSV exports. Use whenever the user has a JSON or JSON Lines list of works with ids and references and wants topics, fields, clusters or a classification of them, wants to rerun or tune the clustering, or asks what the output files mean.
---

# Topics of a list of works with citation-topics

The package does the computation; this skill decides the parameters and explains the result. Every step
writes into one output folder, `OUT/`.

## 1. Check the input

One JSON object per work, in a JSON array or JSON Lines file (`.gz` allowed):

```json
{"id": "W1", "references": ["W7", "W9"], "year": 2019, "title": "...", "abstract": "...",
 "keywords": ["..."], "journal": "...", "categories": ["..."], "countries": ["..."], "authors": ["..."],
 "citations": 41, "url": "https://..."}
```

Only `id` (unique) and `references` (ids of other works of the list) are required. Other names are read with
`--id-field`, `--refs-field` and `--map NAME=FIELD` (for example `--map year=publication_year`). References to
ids outside the list are ignored and counted. What each optional field adds:

| Field | Adds |
|---|---|
| `year` | years of each topic, time windows (`--from-year`, `--to-year`), comparisons between epochs |
| `title`, `abstract`, `keywords`, `journal`, `categories` | the description of each topic, hence its name |
| `citations` | most cited works by that count (otherwise by citations inside the list) |
| `countries`, `authors`, `url` | countries per topic in the description; kept for the boards; links |

Before a long run, look at a few lines of the input and tell the user which optional fields it has and what
will be missing.

## 2. Run

```bash
citation-topics run INPUT OUT/ [--resolution 16] [--min-size 100] [--passes 20] [--seed 1] \
    [--area-resolution 0.3] [--area-seeds 50]
```

The defaults are those of the HEP run this package was made from (1.9 million works, 304 topics, 6 areas).
For another list, tune them:

- `--min-size`: the smallest topic. Aim for topics of a few hundred to a few thousand works; for a list of
  N works, start near N / 5,000 (at least 20).
- `--resolution`: higher gives more, smaller topics. Run two or three values (for example 4, 8, 16) and compare
  the number of topics, the share of links inside topics (`share_inside` in `topics.json`, higher is more
  solid) and the unassigned works (`meta.json`).
- `--area-resolution`: 0.3 gave the steadiest areas in the HEP run; try 0.2-0.5 if the areas look too few or
  too many.
- Seeds: Leiden depends on its random seed. For a result to keep, run 3-4 seeds (`--seed 1..4`, into different
  folders) and keep the medoid with `citation-topics agreement OUT1 OUT2 OUT3 OUT4`.

Run large lists in the background: for 1.9 million works and 25 million links, about 2 GB of memory and
20-30 minutes per seed. The same input, parameters and versions (all in `meta.json`) give the same topics.

## 3. Describe and name

```bash
citation-topics describe INPUT OUT/ [--abstracts]     # OUT/dossier.json
```

Then follow the skill `topic-namer`: it names topics and areas from `dossier.json` and applies the names with
`citation-topics names OUT/ names.json`. Without titles, keywords, journals or categories the dossier has only
sizes, years and links; say so, and name only if the user can supply what a topic is about.

## 4. Export

```bash
citation-topics export OUT/            # topics_vosviewer.json, topics_map.txt, topics_network.txt, CSVs
```

`topics_vosviewer.json` opens in VOSviewer Online: `https://app.vosviewer.com/?json=URL` with a public URL of
the file.

## Output files

| File | Content |
|---|---|
| `works.jsonl.gz` | per work: `topic` and `area` from the clustering (null if none), `topics` (main, second, third with `score` = links to it / links to the main topic, capped at 1, and `links`), `n_links`, `inferred` (main topic from its links when the clustering left it out) |
| `topics.json` | per topic: area, name, works, links inside and out, `share_inside`, years, most cited works |
| `areas.json` | per area: name, works, topics, links, `share_inside` |
| `meta.json` | parameters, versions, input MD5, network counts, which optional fields were present, quality |
| `dossier.json` | description of each topic and area (after `describe`) |
| `network.npz`, `clusters.npz` | arrays used by the other commands |

Report the numbers that matter (topics, areas, works with a topic, unassigned, share of links inside) and
which steps the missing fields ruled out.
