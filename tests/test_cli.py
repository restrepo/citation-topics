import json

import pytest

from citation_topics import __version__
from citation_topics.cli import main
from citation_topics.skills import list_skills
from conftest import PARAMS


def test_version(capsys):
    with pytest.raises(SystemExit) as e:
        main(["--version"])
    assert e.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_cli_end_to_end(works_file, tmp_path):
    out = tmp_path / "out"
    args = [
        "--resolution",
        str(PARAMS["resolution"]),
        "--min-size",
        str(PARAMS["min_size"]),
        "--passes",
        "5",
        "--area-seeds",
        "5",
        "-q",
    ]
    assert main(["run", str(works_file), str(out), *args]) == 0
    assert main(["describe", str(works_file), str(out), "-q"]) == 0
    names = tmp_path / "names.json"
    names.write_text(json.dumps({"topics": {"0": "A"}}))
    assert main(["names", str(out), str(names), "-q"]) == 0
    assert main(["export", str(out), "--works", str(works_file), "-q"]) == 0
    assert (out / "topics_vosviewer.json").exists() and (out / "topics.csv").exists()
    assert (out / "works_vosviewer.json").exists()
    assert main(["board", str(works_file), str(out), "--title", "T", "-q"]) == 0
    assert "<title>T</title>" in (out / "board.html").read_text()
    assert main(["run", str(works_file), str(tmp_path / "old"), "--to-year", "2009", *args]) == 0
    assert main(["compare", str(tmp_path / "old"), str(out), str(tmp_path / "cmp"), "-q"]) == 0
    assert json.loads((tmp_path / "cmp" / "flows.json").read_text())["meta"]["works_in_both"] > 0


def test_cli_map_error(works_file, tmp_path):
    with pytest.raises(SystemExit):
        main(["run", str(works_file), str(tmp_path / "o"), "--map", "year"])


def test_skills(tmp_path, capsys):
    names = [n for n, _ in list_skills()]
    want = {"skill topics-run", "skill topic-namer", "skill topics-compare", "skill topics-board", "agent topic-namer"}
    assert want <= set(names)
    assert main(["skills", "install", "--dest", str(tmp_path / ".claude")]) == 0
    assert (tmp_path / ".claude" / "skills" / "topic-namer" / "SKILL.md").exists()
    assert (tmp_path / ".claude" / "agents" / "topic-namer.md").exists()
    (tmp_path / ".claude" / "agents" / "topic-namer.md").write_text("edited")
    main(["skills", "install", "--dest", str(tmp_path / ".claude")])
    assert (tmp_path / ".claude" / "agents" / "topic-namer.md").read_text() == "edited"
    main(["skills", "install", "--dest", str(tmp_path / ".claude"), "--force"])
    assert (tmp_path / ".claude" / "agents" / "topic-namer.md").read_text() != "edited"
