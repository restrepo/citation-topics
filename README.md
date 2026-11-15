# citation-topics

[![CI](https://github.com/restrepo/citation-topics/actions/workflows/ci.yml/badge.svg)](https://github.com/restrepo/citation-topics/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/citation-topics.svg)](https://pypi.org/project/citation-topics/)
[![Python](https://img.shields.io/pypi/pyversions/citation-topics.svg)](https://pypi.org/project/citation-topics/)

Research topics and areas from the citation links of any list of works, with Leiden clustering as CWTS does for OpenAlex.

## Install

```bash
pip install citation-topics
citation-topics --version
```

## Development

```bash
python -m pip install -e ".[dev]"
python -m pytest
ruff check . && ruff format --check .
```

Releases are published to PyPI from GitHub Actions when a `v*` tag is pushed; see [PUBLISHING.md](PUBLISHING.md) and [CHANGELOG.md](CHANGELOG.md).
