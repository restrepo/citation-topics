---
name: community-graph
description: Make the citation community graph of a set of works with citation-topics - every real work a dot, each topic a labelled cluster of its works, a click showing the works it cites and the works citing it in two colours, plus the board, a VOSviewer file and an optional VOSviewer Online link - starting from an INSPIRE-HEP author profile (its papers and every paper citing them) or from any JSON list of works with ids and references. Use whenever the user wants the community, citation network, research landscape or "who cites whom" graph of an author, a group, a paper list or a small field, asks to redo the INSPIRE sample board for another profile, or asks how large such a graph can be.
---

# Citation community graph

The result is one HTML page (the board, with its Network tab) and `works_vosviewer.json`. It needs
citation-topics 0.3.0 or newer (`pip install -U citation-topics`; `citation-topics board --help` must list
`--network-max`).

## 1. The works

- **INSPIRE-HEP author** (a profile number such as 991924, or an INSPIRE BAI): the author's papers and every
  paper citing them, with titles, abstracts, keywords, journals, categories, authors, citations and links, and
  `"own": true` on the author's papers.

  ```bash
  curl -O https://raw.githubusercontent.com/restrepo/citation-topics/main/examples/inspire_profile.py
  python inspire_profile.py 991924 works.jsonl
  ```

- **Any other list**: a JSON array or JSON Lines file with `id` and `references` (ids of other works of the
  list). Titles name the topics and the dots; `authors` (or `author_count`, `collaborations`) fill the first
  author and the author line; `year`, `citations` and `url` fill the details; a true/false field such as `own`
  rings the works to follow. Map other names with `--map title=display_name` and so on.

Check the size before going on (section 4). Tell the user what the list holds: works, links, which fields.

## 2. Topics

```bash
citation-topics run works.jsonl out/ --resolution 1 --min-size 20
```

The defaults (resolution 16, min size 100) suit millions of works. For a community of a few thousand works start
at resolution 1 and min size 20; try 2 and 4 too and keep the run whose topics are solid (`share_inside` in
`out/topics.json`, ideally above 0.5) and few enough to label (about 8 to 30). Run seeds 1 to 4 into separate
folders and keep the one `citation-topics agreement out_s*/` calls the medoid.

## 3. Names, board and VOSviewer

```bash
citation-topics describe works.jsonl out/ --abstracts
```

Name the topics and areas with the `topic-namer` skill, which writes `names.json` and applies it. Then:

```bash
citation-topics export out/ --works works.jsonl --highlight own --highlight-label "The author's papers"
citation-topics board works.jsonl out/ --highlight own --highlight-label "The author's papers" \
    --title "INSPIRE author 991924: citation topics" [--vosviewer-url URL]
```

Leave out `--highlight` when the list has no such field. Give the title the user wants; when the user asks to
keep a person out of the page, use the profile number, not the name, and say that author lists in the details
still show names unless the input leaves `authors` out.

The Network tab: dots coloured by area and sized by citations; each topic's works form one cluster labelled with
its name; a click on a work keeps only its links, magenta to the works it cites and amber to the works citing
it, puts its first author beside it and its title, authors, year, citations, topic and link below the graph.

## 4. How large the graph can be

Measured on synthetic lists with the density of the INSPIRE sample (about 8.6 citation links per work):

| Works | Citation links | Topics (resolution 1, min 20) | `run` | `board` | board.html | works_vosviewer.json | One redraw (zoom, pan) |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 2,000 | 17,500 | 11 | 0.3 s | 0.8 s | 0.6 MB | 1.5 MB | a few ms |
| 10,000 | 88,000 | 55 | 2 s | 4 s | 2.7 MB | 7.5 MB | 26 ms |
| 20,000 | 175,000 | 111 | 7 s | 9 s | 5.0 MB | 15 MB | 60 ms |
| 40,000 | 350,000 | 222 | 28 s | 21 s | 9.8 MB | 31 MB | 850 ms with links, 22 ms without |

Redraw times are from Chromium on this project's development computer, and they grow with the links drawn, not
with the works. So:

- **Up to 10,000 works and about 50 topics**: comfortable, the default (`--network-max 10000`).
- **10,000 to 20,000 works**: still usable (`--network-max 20000`); zooming is a little slow, and the files are
  5 MB (board) and 15 MB (VOSviewer). Above 150,000 links the board starts with the links hidden; the reader
  can switch them on.
- **Beyond 20,000 works**: drawing every link stalls; split the list (one topic, one area, one period) instead.
  Artifacts take pages up to 16 MB.

- The Network tab is drawn when the list has at most `--network-max` works (10,000 by default).
- Labels: every topic gets one, but labels that would overlap are skipped until the reader zooms in. Up to about
  30 topics all show at once; colours follow the areas (at most 8), so clusters are told apart by their labels
  and positions, not by colour.
- Beyond the limit, keep the topic map of the Overview tab, or show one topic or one period at a time (run on
  a subset with `--from-year`/`--to-year`, or filter the input).

## 5. Deliver

- Send `out/board.html` (the user opens it in any browser) or publish it as an artifact if the user wants a link.
- A VOSviewer Online link needs `works_vosviewer.json` at a public address that allows cross-site reads, such as
  GitHub Pages: `https://app.vosviewer.com/?json=` followed by the URL, percent-encoded. Never upload the user's
  files anywhere without asking. Pass the same URL to `board --vosviewer-url` to put the link in the Network tab.
- Report: works, links, topics and areas, the resolution kept and why, the largest topics by name, and anything
  missing (no titles: unnamed topics; no authors: no author line).
