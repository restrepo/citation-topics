---
name: topics-board
description: Build the HTML board of a citation-topics run - one self-contained page with a tab for each view the input's fields allow (Overview with the map and table of topics always; Timeline with year; Works with title; Network, every work clustered by topic with each cluster labelled, up to 10,000 works; a highlight tab for works marked by a true/false field such as an author's own papers; Countries with countries; Authors with authors; About always) - and explain what it shows and what is missing. Use whenever the user wants a board, dashboard, page or map of the topics of a list of works, asks which tabs their data allows, or wants to follow a subset of works (their own papers, a group's papers) across the topics.
---

# Board of a citation-topics run

```bash
citation-topics board INPUT OUT/ [--highlight FIELD --highlight-label "Your papers"] [--title "..."] [--html FILE]
    [--network-max 10000] [--vosviewer-url URL]
```

It needs a finished `run` (and, for names and terms, `describe` and `names`). It writes `OUT/board.html`: one file,
its data inside it, that opens in any browser (it loads d3 from cdnjs). Send or publish that file.

## Tabs and the fields they need

| Tab | Shown when |
|---|---|
| Overview: headline figures, map of topics, table of topics | always |
| Timeline: works per topic and year | the input has `year` |
| Works: search titles, filter by topic, most cited first | the input has `title` |
| Network: every work with a citation link, each topic a labelled cluster, coloured by area; zoom, hover; a click shows only that work's citation links, its first author beside it and its details below the graph | at most `--network-max` works (10,000; 0 turns it off) |
| Highlight (named by `--highlight-label`) | `--highlight FIELD` and some works have FIELD true |
| Countries: share of each topic's works by country | the input has `countries` |
| Authors: authors with most works per topic | the input has `authors` |
| About: parameters, versions, counts, fields present, who named the topics | always |

Extra fields in the input are ignored by `run` and read here only when named, so a list can carry them from the
start (`own`, `group`, `countries`, `authors`) for a later board.

## Steps

1. Check what the input has (`meta.json` → `network.fields_present`) and tell the user which tabs they will get and
   which fields would add the others.
2. If the topics have no names, offer the skill `topic-namer` first: unnamed topics show as "Topic N".
3. Build the board. To follow a subset, the input needs a true/false field (for an INSPIRE profile made with
   `examples/inspire_profile.py` it is `own`): `--highlight own --highlight-label "Your papers"`.
4. Open or send `OUT/board.html`. The Works tab holds the `--max-works` most cited works (default 5,000) plus every
   highlighted one, so a list of millions stays a small file; say so when the list is larger.
5. **VOSviewer (optional).** `citation-topics export OUT/ --works INPUT [--highlight FIELD --highlight-label ...]`
   writes `OUT/works_vosviewer.json`, the same network of works with the same positions, one cluster per topic.
   It opens in VOSviewer Online (Open → the file). For a shareable link the file must be at a public URL that
   allows cross-site reads (GitHub Pages does); the link is `https://app.vosviewer.com/?json=` plus the URL encoded,
   and `board --vosviewer-url URL` puts it in the Network tab. Never upload the user's files anywhere without asking.
