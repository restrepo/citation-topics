"""Reading a list of works: a JSON array or JSON Lines file, optionally gzipped.

Each work is an object with a unique id and a list of references to the ids of other works. Ids may be
strings or integers; they are compared as strings. Any other field is optional and only used by the
steps that need it (see OPTIONAL).
"""

import gzip
import hashlib
import json
from collections.abc import Iterator
from pathlib import Path

# Optional fields and what they enable. The names are the defaults; --map NAME=FIELD renames them.
OPTIONAL = {
    "year": "time windows, years of each topic, trends",
    "title": "descriptions and names of the topics, readable labels",
    "abstract": "descriptions and names of the topics (describe --abstracts)",
    "keywords": "descriptions and names of the topics",
    "journal": "descriptions and names of the topics",
    "categories": "descriptions and names of the topics",
    "countries": "countries of each topic",
    "authors": "author flows between topics",
    "citations": "most cited works of each topic (otherwise citations inside the list)",
    "url": "links to each work",
}


class Fields:
    """Names of the fields in the input: id, references and the optional ones."""

    def __init__(self, id="id", references="references", mapping=None):
        self.id = id
        self.references = references
        self.optional = {k: k for k in OPTIONAL}
        for k, v in (mapping or {}).items():
            if k not in OPTIONAL:
                raise ValueError(f"unknown optional field {k!r}; known: {', '.join(OPTIONAL)}")
            self.optional[k] = v

    def get(self, work, name):
        return work.get(self.optional[name])

    def as_dict(self):
        return {"id": self.id, "references": self.references, **self.optional}


def _open(path):
    path = Path(path)
    with open(path, "rb") as f:
        gz = f.read(2) == b"\x1f\x8b"
    return gzip.open(path, "rt", encoding="utf-8") if gz else open(path, encoding="utf-8")


def iter_works(path) -> Iterator[dict]:
    """Yield the works of a JSON array or a JSON Lines file (gzipped or not). JSON Lines is read line by
    line, so it suits large lists; a JSON array is loaded at once."""
    with _open(path) as f:
        first = ""
        while not first:
            ch = f.read(1)
            if not ch:
                return
            first = ch.strip()
        if first == "[":
            rest = f.read()
            yield from json.loads(first + rest)
            return
        line = first + f.readline()
        if line.strip():
            yield json.loads(line)
        for line in f:
            if line.strip():
                yield json.loads(line)


def md5(path, chunk=1 << 20):
    h = hashlib.md5()
    with open(path, "rb") as f:
        while b := f.read(chunk):
            h.update(b)
    return h.hexdigest()


def as_year(v):
    """A year from an integer, a string starting with four digits, or None (0 = unknown)."""
    if v is None:
        return 0
    if isinstance(v, int):
        return v
    s = str(v)[:4]
    return int(s) if s.isdigit() else 0


def as_list(v):
    if v is None or v == "":
        return []
    if isinstance(v, list):
        return v
    if isinstance(v, str):
        return [x.strip() for x in v.replace(";", ",").split(",") if x.strip()]
    return [v]
