"""The Claude skills and agent shipped with the package (citation_topics/claude/), and their installation into a
project's or the user's .claude folder."""

import filecmp
import re
import shutil
from importlib.resources import files
from pathlib import Path


def _root():
    return Path(str(files("citation_topics") / "claude"))


def list_skills():
    out = []
    for kind in ("skills", "agents"):
        for f in sorted((_root() / kind).rglob("*.md")):
            m = re.search(r"^description:\s*(.+)$", f.read_text(encoding="utf-8"), re.M)
            name = f.parent.name if kind == "skills" else f.stem
            out.append((f"{kind[:-1]} {name}", (m.group(1)[:110] + "...") if m else ""))
    return out


def install(dest=".claude", user=False, force=False, log=print):
    dest = Path.home() / ".claude" if user else Path(dest)
    root = _root()
    done = []
    for src in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = src.relative_to(root)
        target = dest / rel
        if target.exists() and not filecmp.cmp(src, target, shallow=False) and not force:
            log(f"kept {target} (differs; --force to overwrite)")
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, target)
        done.append(str(target))
    log(f"installed {len(done)} files into {dest}: " + ", ".join(str(Path(d).relative_to(dest)) for d in done))
    return done
