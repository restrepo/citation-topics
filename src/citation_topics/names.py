"""Names of topics and areas: names.json, written by the topic-namer agent (or carried over by `compare`), is
merged into topics.json and areas.json.

names.json:
  {"topics": {"0": {"name": "Neutrino oscillations", "reason": "..."}, ...},
   "areas": {"0": {"name": "...", "reason": "..."}, ...},
   "meta": {"by": "topic-namer agent", "model": "...", "date": "2026-11-15"}}
A plain string instead of {"name": ..., "reason": ...} is accepted.
"""

import json
from pathlib import Path


def read_names(path):
    d = json.loads(Path(path).read_text())

    def norm(part):
        out = {}
        for k, v in (d.get(part) or {}).items():
            v = {"name": v} if isinstance(v, str) else dict(v)
            if not v.get("name"):
                raise ValueError(f"{part} {k}: empty name")
            out[int(k)] = v
        return out

    return norm("topics"), norm("areas"), d.get("meta") or {}


def apply_names(out, names_path, log=print):
    out = Path(out)
    topics_n, areas_n, meta = read_names(names_path)
    result = {}
    for part, key, given in (("topics", "topic", topics_n), ("areas", "area", areas_n)):
        f = out / f"{part}.json"
        rows = json.loads(f.read_text())
        known = {r[key] for r in rows}
        extra = sorted(set(given) - known)
        if extra:
            raise ValueError(f"{names_path}: {part} {extra} are not in {f}")
        for r in rows:
            if r[key] in given:
                r["name"] = given[r[key]]["name"]
                if given[r[key]].get("reason"):
                    r["name_reason"] = given[r[key]]["reason"]
        f.write_text(json.dumps(rows, indent=1, ensure_ascii=False))
        unnamed = [r[key] for r in rows if not r.get("name")]
        result[part] = {"named": len(rows) - len(unnamed), "unnamed": unnamed}
        log(
            f"{part}: {len(rows) - len(unnamed)} of {len(rows)} named"
            + (f"; unnamed: {unnamed[:20]}" if unnamed else "")
        )
    mf = out / "meta.json"
    if mf.exists():
        m = json.loads(mf.read_text())
        m["names"] = {"file": Path(names_path).name, **meta}
        mf.write_text(json.dumps(m, indent=1, ensure_ascii=False))
    return result
