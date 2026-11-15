# Changelog

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- `board`: a Network tab when the list has at most `--network-max` works (10,000): every work with a citation
  link, each topic its own cluster labelled with its name, coloured by area; zoom, hover and topic focus.
  `--vosviewer-url` links it to VOSviewer Online.
- `export --works INPUT`: `works_vosviewer.json`, the network of works for VOSviewer with the board's positions and
  one named cluster per topic.
- Site on GitHub Pages (`docs/`, published by the `pages.yml` workflow on every merge to main): how the topics are
  made, and the sample board of the INSPIRE-HEP author 991924 with its VOSviewer files.

## [0.2.0] - 2026-11-15

### Added
- `board`: one self-contained HTML page of a run, with a tab for each view the input's fields allow (Overview,
  Timeline, Works, a highlight tab for a true/false field such as `own`, Countries, Authors, About), and the
  Claude skill `topics-board`.
- `examples/inspire_profile.py` and a README walk-through: the topics of an INSPIRE-HEP author's papers and
  the papers citing them, named with or without Claude.

## [0.1.0] - 2026-11-15

### Added
- `run`: direct-citation network of a JSON or JSON Lines list of works, Leiden topics (igraph) and areas
  (leidenalg, best of several seeds), second and third topics of every work; `works.jsonl.gz`, `topics.json`,
  `areas.json`, `meta.json`.
- `describe`: dossier of every topic and area from the optional fields.
- `names`, `compare` (fates and names carried over), `agreement` (NMI/ARI, medoid), `export` (VOSviewer, CSV).
- Claude skills `topics-run`, `topic-namer`, `topics-compare` and the agent `topic-namer` (`skills install`).

[Unreleased]: https://github.com/restrepo/citation-topics/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/restrepo/citation-topics/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/restrepo/citation-topics/releases/tag/v0.1.0
