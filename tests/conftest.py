import gzip
import json
import random

import pytest

GROUPS, SIZE = 4, 120
WORDS = [["neutrino", "oscillation"], ["dark", "matter"], ["lattice", "qcd"], ["gravitational", "waves"]]


def planted(seed=3, groups=GROUPS, size=SIZE, cross=2):
    """Works in `groups` groups that cite mostly inside their group; ids are strings like g1_17."""
    rng = random.Random(seed)
    works = []
    for g in range(groups):
        a, b = WORDS[g % len(WORDS)]
        for i in range(size):
            refs = [f"g{g}_{rng.randrange(size)}" for _ in range(12)]
            refs += [f"g{rng.randrange(groups)}_{rng.randrange(size)}" for _ in range(cross)] + ["outside"]
            works.append(
                {
                    "id": f"g{g}_{i}",
                    "references": refs,
                    "year": 2000 + 5 * g + rng.randrange(5),
                    "title": f"{a.title()} {b} measurement number {rng.randrange(9)}",
                    "journal": f"Journal {g}",
                    "categories": [f"cat-{g}"],
                    "countries": ["Colombia"],
                    "citations": rng.randrange(100),
                }
            )
    works.append({"id": "alone", "references": []})
    return works


PARAMS = {"resolution": 1.0, "min_size": 40, "passes": 5, "area_seeds": 5}


@pytest.fixture
def works_file(tmp_path):
    p = tmp_path / "works.jsonl.gz"
    with gzip.open(p, "wt", encoding="utf-8") as f:
        for w in planted():
            f.write(json.dumps(w) + "\n")
    return p


@pytest.fixture
def run_out(works_file, tmp_path):
    from citation_topics.run import run

    out = tmp_path / "out"
    run(works_file, out, log=lambda *a: None, **PARAMS)
    return out
