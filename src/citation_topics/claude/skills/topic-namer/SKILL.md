---
name: topic-namer
description: Name the topics and areas found by citation-topics from their dossier (dossier.json) - short, specific names written from each topic's distinctive terms and most cited titles, checked against its journals, categories and keywords - and apply them with `citation-topics names`; carries names over from an earlier run first so only new topics are named. Use whenever a citation-topics output folder has unnamed topics, the user asks to name, rename or check topic names, or after `citation-topics run` and `describe`.
---

# Naming topics and areas

Names are the one step that needs reading; everything else is computed. They are written by Claude, so they
are not exactly repeatable: record who named them and when.

## 1. Prepare

- `OUT/dossier.json` must exist (`citation-topics describe INPUT OUT/`). Check its `missing` list: without
  titles, keywords, journals or categories there is nothing to name from; tell the user and stop.
- If an earlier run of the same or an overlapping list was named, carry its names over first:

  ```bash
  citation-topics compare OLD_OUT/ OUT/ CMP/      # CMP/names_carried.json: names + "to_name"
  citation-topics names OUT/ CMP/names_carried.json
  ```

  Then name only the topics in `to_name`.

## 2. Name

For each topic, read in `dossier.json`: `terms` (with the share of its works using them), `most_cited` (titles,
years, and the start of the abstract of the first three), `journals`, `categories`, `keywords`, `years`,
`linked_topics`. Write:

- **2 to 7 words**, specific to what sets the topic apart: "Neutrino oscillations", "Lattice QCD at finite
  temperature", "Dark matter direct detection". Not generic ("Physics", "Theory"), not a list of every term.
- Grounded in the dossier: the most cited titles and the top terms should agree; check the name against the
  journals and categories. If they disagree, prefer what most of its works share (terms, categories) over a
  single famous work.
- Distinct: two topics never get the same name; when two are close, name what differs (method, object,
  energy range, period). `linked_topics` shows the neighbours to tell apart.
- A one-line `reason` citing the evidence (terms, titles, categories).

Areas: broader names (3 to 10 words) covering their topics (`areas[].topics` lists them with their names).

With many topics, work in batches of about 30. If the `topic-namer` agent is installed (`.claude/agents/`),
give each batch to it: the topic numbers, the path of `dossier.json` and the file to write; check its names
for duplicates afterwards.

## 3. Apply

Write `names.json`:

```json
{"topics": {"0": {"name": "...", "reason": "..."}},
 "areas": {"0": {"name": "...", "reason": "..."}},
 "meta": {"by": "topic-namer", "model": "<the model you are>", "date": "YYYY-MM-DD"}}
```

and merge it (it can be applied in parts; later files add to earlier ones):

```bash
citation-topics names OUT/ names.json
citation-topics export OUT/              # VOSviewer and CSVs with the names
```

The command lists any topic still unnamed. Show the user a table of number, works and name, and say which
names were carried over and which are new.
