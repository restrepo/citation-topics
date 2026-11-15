import gzip
import json

import numpy as np
import pytest

from citation_topics.board import board
from citation_topics.compare import agreement, compare
from citation_topics.describe import describe, terms_of
from citation_topics.export import _authors, _first_author, export_csv, export_vosviewer, export_works_vosviewer
from citation_topics.io import Fields, as_list, as_year, iter_works
from citation_topics.layout import work_positions
from citation_topics.names import apply_names
from citation_topics.network import build
from citation_topics.run import load, run
from citation_topics.secondary import secondary
from conftest import PARAMS, SIZE, planted

QUIET = {"log": lambda *a: None}


def test_iter_works_formats(tmp_path):
    ws = [{"id": 1, "references": [2]}, {"id": 2, "references": []}]
    (tmp_path / "a.json").write_text(json.dumps(ws))
    (tmp_path / "b.jsonl").write_text("\n".join(json.dumps(w) for w in ws) + "\n\n")
    with gzip.open(tmp_path / "c.jsonl.gz", "wt") as f:
        f.write("\n".join(json.dumps(w) for w in ws))
    for name in ("a.json", "b.jsonl", "c.jsonl.gz"):
        assert list(iter_works(tmp_path / name)) == ws


def test_helpers():
    assert as_year("2003-05-01") == 2003 and as_year(None) == 0 and as_year("n/a") == 0
    assert as_list("a; b, c") == ["a", "b", "c"] and as_list(None) == []
    assert terms_of("Search for $\\nu_\\mu$ dark matter") == {"search", "dark", "matter", "dark matter"}


def test_network_ids_and_references(tmp_path):
    ws = [{"id": 10, "references": [20, 10, 99]}, {"id": "20", "references": ["10", "10"]}, {"id": 30}]
    p = tmp_path / "w.json"
    p.write_text(json.dumps(ws))
    net = build(p)
    assert net.ids == ["10", "20", "30"]
    assert sorted(zip(net.src.tolist(), net.dst.tolist())) == [(0, 1), (1, 0), (1, 0)]
    assert net.stats["references"] == 5 and net.stats["self_citations"] == 1
    lo, hi = net.pairs()
    assert list(zip(lo.tolist(), hi.tolist())) == [(0, 1)]


def test_network_field_names_and_window(tmp_path):
    ws = [{"key": "a", "cites": ["b"], "py": 1990}, {"key": "b", "cites": [], "py": 2010}]
    p = tmp_path / "w.json"
    p.write_text(json.dumps(ws))
    f = Fields("key", "cites", {"year": "py"})
    assert build(p, f).n == 2
    net = build(p, f, to_year=2000)
    assert net.ids == ["a"] and len(net.src) == 0


def test_network_errors(tmp_path):
    p = tmp_path / "w.json"
    p.write_text(json.dumps([{"id": "a"}, {"id": "a"}]))
    with pytest.raises(ValueError, match="unique"):
        build(p)
    p.write_text(json.dumps([{"name": "a"}]))
    with pytest.raises(ValueError, match="no 'id'"):
        build(p)
    with pytest.raises(ValueError, match="unknown optional field"):
        Fields(mapping={"colour": "c"})


def test_run_recovers_groups(run_out):
    net, c = load(run_out)
    topic = c["topic"]
    groups = np.array([int(i[1]) if i != "alone" else -1 for i in net.ids])
    assert topic.max() + 1 == 4
    for g in range(4):  # every group is one topic
        assert len(set(topic[groups == g].tolist())) == 1
    assert topic[net.ids.index("alone")] == -1
    meta = json.loads((run_out / "meta.json").read_text())
    assert meta["result"]["topics"] == 4 and meta["network"]["fields_present"]["title"] == 4 * SIZE
    assert meta["parameters"]["resolution"] == 1.0 and meta["versions"]["igraph"]
    with gzip.open(run_out / "works.jsonl.gz", "rt") as f:
        rows = [json.loads(x) for x in f]
    assert len(rows) == net.n and rows[-1] == {
        "id": "alone",
        "topic": None,
        "area": None,
        "topics": [],
        "n_links": 0,
        "inferred": False,
    }
    t = json.loads((run_out / "topics.json").read_text())
    assert [e["works"] for e in t] == [SIZE] * 4 and all(e["share_inside"] > 0.6 for e in t)
    assert sum(len(a["topics"]) for a in json.loads((run_out / "areas.json").read_text())) == 4


def test_same_seed_same_topics(works_file, tmp_path):
    a = run(works_file, tmp_path / "a", **QUIET, **PARAMS)
    b = run(works_file, tmp_path / "b", **QUIET, **PARAMS)
    assert a["result"]["quality"] == b["result"]["quality"]
    assert (load(tmp_path / "a")[1]["topic"] == load(tmp_path / "b")[1]["topic"]).all()


def test_min_size_unassigns_small_topics(works_file, tmp_path):
    run(works_file, tmp_path / "o", **QUIET, **{**PARAMS, "min_size": 10_000})
    assert (load(tmp_path / "o")[1]["topic"] == -1).all()


def test_secondary_scores(tmp_path):
    # work x: 3 links to topic 0, 2 to topic 1, 1 to topic 2; y has no topic and links to topic 1
    ws = [{"id": "x", "references": ["a0", "a1", "a2", "b0", "b1", "c0"]}, {"id": "y", "references": ["b0"]}]
    ws += [{"id": f"{g}{i}", "references": []} for g in "abc" for i in range(3)]
    p = tmp_path / "w.json"
    p.write_text(json.dumps(ws))
    net = build(p)
    topic = np.array([0, -1, 0, 0, 0, 1, 1, 1, 2, 2, 2])
    s = secondary(net, topic)
    assert s.topic[0].tolist() == [0, 1, 2] and s.links[0].tolist() == [3, 2, 1]
    assert np.allclose(s.score[0], [1, 2 / 3, 1 / 3]) and s.n_links[0] == 6
    assert s.topic[1, 0] == 1 and s.inferred[1] and not s.inferred[0]


def test_describe(run_out, works_file):
    d = describe(works_file, run_out, top=3, **QUIET)
    t = d["topics"][0]
    assert t["works"] == SIZE and len(t["most_cited"]) == 3 and t["most_cited"][0]["title"]
    terms = [x[0] for x in t["terms"]]
    assert any(" " in x for x in terms)  # a bigram such as "dark matter"
    assert t["journals"][0][1] == 100.0 and t["countries"] == [["Colombia", 100.0]]
    assert "measurement" not in terms  # in every group: not distinctive
    assert d["missing"] == ["abstract", "keywords"]
    assert (run_out / "dossier.json").exists()


def test_names(run_out, tmp_path):
    f = tmp_path / "names.json"
    f.write_text(json.dumps({"topics": {"0": "First", "1": {"name": "Second", "reason": "r"}}, "meta": {"by": "t"}}))
    r = apply_names(run_out, f, **QUIET)
    assert r["topics"] == {"named": 2, "unnamed": [2, 3]}
    t = json.loads((run_out / "topics.json").read_text())
    assert t[1]["name"] == "Second" and t[1]["name_reason"] == "r"
    assert json.loads((run_out / "meta.json").read_text())["names"]["by"] == "t"
    f.write_text(json.dumps({"topics": {"9": "Nope"}}))
    with pytest.raises(ValueError, match="not in"):
        apply_names(run_out, f, **QUIET)


def test_compare_and_carry_names(works_file, run_out, tmp_path):
    old = tmp_path / "old"
    run(works_file, old, **QUIET, **PARAMS)
    (tmp_path / "n.json").write_text(json.dumps({"topics": {str(k): f"T{k}" for k in range(4)}}))
    apply_names(old, tmp_path / "n.json", **QUIET)
    out = compare(old, run_out, tmp_path / "cmp", **QUIET)
    assert out["meta"]["fates"] == {"same": 4} and out["meta"]["nmi"] == pytest.approx(1)
    carried = json.loads((tmp_path / "cmp" / "names_carried.json").read_text())
    assert len(carried["topics"]) == 4 and carried["to_name"]["topics"] == []


def test_compare_split(tmp_path):
    # earlier run: two groups merged into one topic; later run: separate
    ws = planted(groups=2)
    p = tmp_path / "w.json"
    p.write_text(json.dumps(ws))
    run(p, tmp_path / "new", **QUIET, **PARAMS)
    _, c = load(tmp_path / "new")
    c["topic"] = np.where(c["topic"] >= 0, 0, -1)
    np.savez_compressed(tmp_path / "new" / "clusters_merged.npz", **c)
    old = tmp_path / "old"
    old.mkdir()
    for f in ("network.npz", "topics.json", "areas.json"):
        (old / f).write_bytes((tmp_path / "new" / f).read_bytes())
    (old / "clusters.npz").write_bytes((tmp_path / "new" / "clusters_merged.npz").read_bytes())
    out = compare(old, tmp_path / "new", tmp_path / "cmp", **QUIET)
    assert out["old"][0]["fate"] == "split"


def test_agreement(works_file, run_out, tmp_path):
    run(works_file, tmp_path / "s2", **QUIET, **{**PARAMS, "seed": 2})
    best, table = agreement([str(run_out), str(tmp_path / "s2")], **QUIET)
    assert best == str(run_out) and table["topic", str(run_out), str(tmp_path / "s2")][0] == pytest.approx(1)


def test_exports(run_out):
    export_vosviewer(run_out, **QUIET)
    export_csv(run_out, **QUIET)
    v = json.loads((run_out / "topics_vosviewer.json").read_text())
    assert len(v["network"]["items"]) == 4 and v["network"]["items"][0]["label"] == "Topic 0"
    assert all(li["strength"] > 0 for li in v["network"]["links"])
    with gzip.open(run_out / "works_topics.csv.gz", "rt") as f:
        rows = list(f)
    assert rows[0].startswith("id,topic_1,score_1") and len(rows) == 1 + 4 * SIZE


def _board_data(path):
    html = path.read_text()
    start = html.index("const D = ") + len("const D = ")
    return json.loads(html[start : html.index(";\nconst M = D.meta;")].replace("<\\/", "</"))


def test_board_tabs_follow_the_fields(works_file, run_out, tmp_path):
    tabs = board(works_file, run_out, highlight="own", **QUIET)
    assert tabs == ["overview", "timeline", "works", "network", "countries", "about"]  # no own: no highlight tab
    d = _board_data(run_out / "board.html")
    assert len(d["topics"]) == 4 and d["meta"]["works_listed"] == d["meta"]["works_total"] == 4 * SIZE + 1
    assert d["countries"][0][0] == "Colombia" and "</script" not in json.dumps(d)
    # panels are laid out with display: grid, which would override the hidden attribute of the closed tabs
    assert "[hidden] { display: none !important; }" in (run_out / "board.html").read_text()
    bare = tmp_path / "bare.json"
    bare.write_text(json.dumps([{"id": w["id"], "references": w["references"]} for w in planted()]))
    run(bare, tmp_path / "b", **QUIET, **PARAMS)
    assert board(bare, tmp_path / "b", html=tmp_path / "b.html", network_max=0, **QUIET) == ["overview", "about"]


def test_board_highlight_and_limit(tmp_path):
    ws = planted()
    for i, w in enumerate(ws):
        w["own"] = i % 50 == 0
        w["authors"] = [f"A{i % 7}"]
        w["title"] = (w.get("title") or "") + " </script><b>x</b>"
    p = tmp_path / "w.json"
    p.write_text(json.dumps(ws))
    run(p, tmp_path / "o", **QUIET, **PARAMS)
    tabs = board(p, tmp_path / "o", highlight="own", highlight_label="Own", max_works=5, **QUIET)
    assert "highlight" in tabs and "authors" in tabs
    html = (tmp_path / "o" / "board.html").read_text()
    assert html.count("</script>") == 2  # the d3 tag and the page script: titles cannot close it
    d = _board_data(tmp_path / "o" / "board.html")
    own = sum(1 for w in ws if w["own"])
    assert (
        d["meta"]["highlighted"] == own
        and d["meta"]["works_listed"] == 5 + sum(1 for r in d["works"][5:] if r[7])
        and sum(r[7] for r in d["works"]) == own
    )


def test_network_and_works_vosviewer(works_file, run_out):
    board(works_file, run_out, vosviewer_url="https://example.org/w.json", **QUIET)
    d = _board_data(run_out / "board.html")
    net = d["network"]
    xy = np.array([n[:2] for n in net["nodes"]])
    assert len(net["nodes"]) == 4 * SIZE and xy.min() >= 0 and xy.max() <= 1000.01  # the isolated work is left out
    assert sorted(lab[0] for lab in net["labels"]) == [0, 1, 2, 3]
    n_, c_ = load(run_out)
    linked, _, a, b, both = work_positions(n_, c_["topic"])
    refs = {str(w["id"]): {str(r) for r in w["references"]} for w in planted()}
    for x, y in zip(a, b):  # each pair: the first cites the second
        assert n_.ids[linked[y]] in refs[n_.ids[linked[x]]]
    assert len(net["mutual"]) == int(both.sum())
    centre = {k: xy[[n[2] == k for n in net["nodes"]]].mean(0) for k in range(4)}
    spread = max(np.linalg.norm(xy[[n[2] == k for n in net["nodes"]]] - centre[k], axis=1).max() for k in range(4))
    gap = min(np.linalg.norm(centre[i] - centre[j]) for i in range(4) for j in range(i))
    assert gap > spread  # every topic is its own cluster
    assert d["meta"]["vosviewer"] == "https://app.vosviewer.com/?json=https%3A%2F%2Fexample.org%2Fw.json"
    path = export_works_vosviewer(works_file, run_out, highlight="own", **QUIET)
    v = json.loads(path.read_text())
    items = {it["id"]: it for it in v["network"]["items"]}
    assert len(items) == 4 * SIZE and len(v["network"]["links"]) == d["meta"]["links"]
    assert {it["cluster"] for it in items.values()} == {1, 2, 3, 4} and len(v["network"]["clusters"]) == 4
    first = next(iter(items.values()))
    assert {"x", "y", "label", "description"} <= first.keys() and "Year" in first["scores"]
    assert export_works_vosviewer(works_file, run_out, network_max=10, **QUIET) is None
    assert "network" not in board(works_file, run_out, network_max=10, **QUIET)


def test_author_line():
    f = Fields()
    assert _authors(f, {"authors": ["A", "B"]}) == "A; B"
    assert _authors(f, {"authors": ["A", "B", "C", "D"], "author_count": 87}) == "A; B; C et al. (87 authors)"
    assert _authors(f, {"collaborations": ["LHCb"], "author_count": 900}) == "LHCb Collaboration (900 authors)"
    assert _authors(f, {"title": "x"}) is None


def test_first_author():
    f = Fields()
    assert _first_author(f, {"authors": ["Nath, Pran", "B"]}) == "Nath, P."
    assert _first_author(f, {"authors": ["Pran Nath"]}) == "Nath, P."
    assert _first_author(f, {"authors": ["Morales-Alvarado, Manuel"]}) == "Morales-Alvarado, M."
    assert _first_author(f, {"collaborations": ["LHCb"]}) == "LHCb"
    assert _first_author(f, {}) is None
