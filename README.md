# citation-topics

[![CI](https://github.com/restrepo/citation-topics/actions/workflows/ci.yml/badge.svg)](https://github.com/restrepo/citation-topics/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/citation-topics.svg)](https://pypi.org/project/citation-topics/)
[![Python](https://img.shields.io/pypi/pyversions/citation-topics.svg)](https://pypi.org/project/citation-topics/)

Research topics and broad areas for any list of works (papers, theses, projects, patents) from their citation
links, with Leiden clustering of the direct-citation network as CWTS does for the OpenAlex topics. It also gives
each work a second and a third topic, describes every topic from whatever the input carries (titles, abstracts,
keywords, journals, categories, countries), and ships Claude skills and an agent that name the topics.

It was extracted from [restrepo/inspireauth10](https://github.com/restrepo/inspireauth10), where it groups 1.9
million INSPIRE-HEP papers into 304 topics and 6 areas
([how the topics are made](https://restrepo.github.io/inspireauth10/leiden.html)).

## Install

```bash
pip install citation-topics
citation-topics --help
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
| `authors` | the Authors tab of the board |
| `url` | links from the board and the description to each work |
| any true/false field, e.g. `own` | a tab of the board that follows those works (`board --highlight own`) |

Naming needs at least one of `title`, `abstract`, `keywords`, `journal` or `categories`: `describe` lists the
ones missing in `dossier.json` (`missing`), and the `topic-namer` skill stops and says so when none is there. No
field is fetched or inferred from elsewhere. Fields the package does not know are kept in the input and ignored,
so a list can carry them from the start for a later board.

## Commands

```bash
citation-topics run works.jsonl.gz out/            # network, topics, areas, second and third topics
citation-topics describe works.jsonl.gz out/       # out/dossier.json: what each topic is about
citation-topics names out/ names.json              # put names into topics.json and areas.json
citation-topics export out/                        # VOSviewer JSON and map/network files, CSVs
citation-topics board works.jsonl.gz out/          # out/board.html: tabs for what the fields allow
citation-topics agreement out_s1/ out_s2/ ...      # NMI/ARI between seeds, and the medoid to keep
citation-topics compare old/ new/ cmp/             # where earlier topics went; names carried over
citation-topics skills install                     # Claude skills and the topic-namer agent into ./.claude
```

`run` options and defaults (those of the INSPIRE run): `--resolution 16` (higher = more, smaller topics),
`--min-size 100` (smaller topics are merged into the topic they share the most links with), `--passes 20`
(stops early when the quality stops rising), `--seed 1`, `--area-resolution 0.3`, `--area-seeds 50` (the best
of that many runs). Tune them for other lists; the skill `topics-run` explains how.

## Example: the citation community of an INSPIRE-HEP profile

The topics of an author's papers together with every paper citing them. Tried on
[Diego Restrepo's profile](https://inspirehep.net/authors/991924): 79 papers and 1,939 citing papers, 1,967 works,
11 topics in 3 areas, in about a minute.

1. **Install** (Python 3.10 or newer):

   ```bash
   pip install citation-topics
   curl -O https://raw.githubusercontent.com/restrepo/citation-topics/main/examples/inspire_profile.py
   ```

2. **Get the works** from INSPIRE, with the number of the profile (`https://inspirehep.net/authors/991924`)
   or its INSPIRE BAI (`D.Restrepo.1`):

   ```bash
   python inspire_profile.py 991924 works.jsonl
   ```

   It writes, for each paper, its references, year, title, abstract, keywords, journal, arXiv categories,
   citation count and link, and `"own": true` for the author's papers.

3. **Topics.** A list of about 2,000 works needs smaller topics than the defaults, which suit millions of works:

   ```bash
   citation-topics run works.jsonl out/ --resolution 1 --min-size 20
   ```

   Try two or three resolutions (for example 1, 2, 4) and keep the one whose topics are solid (`share_inside` in
   `out/topics.json`) and readable in number. Optionally run seeds 1 to 4 into different folders and keep the
   one `citation-topics agreement` calls the medoid.

4. **Describe and export:**

   ```bash
   citation-topics describe works.jsonl out/ --abstracts
   citation-topics export out/
   ```

5. **Name the topics**, with or without Claude:

   - *With Claude Desktop (optional; the Code tab, or Claude Code):* install the skills in the folder, open the
     folder in the Code tab and ask, for example, "name the topics in out/ with the topic-namer skill". Claude reads
     `out/dossier.json`, writes `names.json` with a name and a reason for every topic and area, and applies it.

     ```bash
     citation-topics skills install
     ```

   - *Without Claude:* read `out/dossier.json` (distinctive terms, most cited titles, journals and categories of
     each topic), write `names.json` yourself in the format of the `names` command, and apply it:

     ```bash
     citation-topics names out/ names.json
     citation-topics export out/
     ```

     Unnamed topics are shown as "Topic N".

6. **Board:** one page with the map and table of topics, works per year, a searchable list of works and a tab
   with the author's own papers by topic:

   ```bash
   citation-topics board works.jsonl out/ --highlight own --highlight-label "Your papers" --title "Your name: citation topics"
   ```

   Open `out/board.html` in a browser, or ask Claude to publish it (skill `topics-board`).

7. **VOSviewer (optional):** open `out/topics_vosviewer.json` in [VOSviewer Online](https://app.vosviewer.com/)
   (Open → the file) or in VOSviewer.

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

**Checked against inspireauth10.** On its 1,872,221 INSPIRE papers (44 million citation links) with the
defaults, `run` gives the same network, the same 304 topics and 6 areas, the same Leiden quality and the same
second and third topics as inspireauth10's own scripts, array for array (igraph 1.0.0, leidenalg 0.12.0, numpy
2.5.4, Python 3.13). It took 45 minutes and more than 4 GB of memory; `describe` with titles, keywords,
journals, categories and countries took 10 minutes and 4.4 GB.

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
| `board.html` | self-contained board: Overview always, then Timeline, Works, highlight, Countries and Authors as the fields allow, and About (`board`) |
| `network.npz`, `clusters.npz` | arrays reused by the other commands |

## Claude skills

`citation-topics skills install` copies into `./.claude` (or `~/.claude` with `--user`):

- `topics-run`: checks the input, chooses the parameters, runs, describes and exports, and explains the result;
- `topic-namer`: names topics and areas from `dossier.json` and applies them, after carrying over earlier names;
- `topics-compare`: seeds (which run to keep) and earlier runs or time windows (fates, flows, names);
- `topics-board`: builds the board with the tabs the fields allow and says which fields would add the others;
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
