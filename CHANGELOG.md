# Changelog

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- `run`: direct-citation network of a JSON or JSON Lines list of works, Leiden topics (igraph) and areas
  (leidenalg, best of several seeds), second and third topics of every work; `works.jsonl.gz`, `topics.json`,
  `areas.json`, `meta.json`.
- `describe`: dossier of every topic and area from the optional fields.
- `names`, `compare` (fates and names carried over), `agreement` (NMI/ARI, medoid), `export` (VOSviewer, CSV).
- Claude skills `topics-run`, `topic-namer`, `topics-compare` and the agent `topic-namer` (`skills install`).

[Unreleased]: https://github.com/restrepo/citation-topics/commits/main
