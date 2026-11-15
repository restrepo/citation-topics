"""Command line entry point: `citation-topics`."""

import argparse
import sys

from . import __version__

DESCRIPTION = """Research topics and areas from the citation links of any list of works, with Leiden clustering
as CWTS does for the OpenAlex topics. The input is a JSON array or JSON Lines file (optionally gzipped) of works,
each with a unique "id" and a list of "references" to the ids of other works; optional fields (year, title,
abstract, keywords, journal, categories, countries, authors, citations, url) enable more steps."""


def _fields(a):
    from .io import Fields

    mapping = {}
    for m in a.map or []:
        k, _, v = m.partition("=")
        if not v:
            raise SystemExit(f"--map takes NAME=FIELD, got {m!r}")
        mapping[k] = v
    return Fields(a.id_field, a.refs_field, mapping)


def _input_args(p):
    p.add_argument("--id-field", default="id", help="field with the unique id of each work (default: id)")
    p.add_argument("--refs-field", default="references", help="field with the list of cited ids (default: references)")
    p.add_argument(
        "--map",
        action="append",
        metavar="NAME=FIELD",
        help="read an optional field under another name, e.g. --map year=publication_year (repeatable)",
    )


def _log(quiet):
    return (lambda *a: None) if quiet else (lambda *a: print(*a, file=sys.stderr, flush=True))


def cmd_run(a):
    from .run import run

    run(
        a.input,
        a.out,
        _fields(a),
        a.from_year,
        a.to_year,
        log=_log(a.quiet),
        resolution=a.resolution,
        min_size=a.min_size,
        passes=a.passes,
        seed=a.seed,
        area_resolution=a.area_resolution,
        area_seeds=a.area_seeds,
    )


def cmd_describe(a):
    from .describe import describe

    describe(a.input, a.out, _fields(a), top=a.top, abstracts=a.abstracts, terms=a.terms, log=_log(a.quiet))


def cmd_names(a):
    from .names import apply_names

    apply_names(a.out, a.names, log=_log(a.quiet))


def cmd_compare(a):
    from .compare import compare

    compare(a.old, a.new, a.result, log=_log(a.quiet))


def cmd_agreement(a):
    from .compare import agreement

    agreement(a.outs, log=_log(False))


def cmd_export(a):
    from .export import export_csv, export_vosviewer

    if not (a.vosviewer or a.csv):
        a.vosviewer = a.csv = True
    if a.vosviewer:
        export_vosviewer(a.out, min_links=a.min_links, log=_log(a.quiet))
    if a.csv:
        export_csv(a.out, log=_log(a.quiet))


def cmd_board(a):
    from .board import board

    board(
        a.input,
        a.out,
        _fields(a),
        html=a.html,
        highlight=a.highlight,
        highlight_label=a.highlight_label,
        title=a.title,
        max_works=a.max_works,
        log=_log(a.quiet),
    )


def cmd_skills(a):
    from .skills import install, list_skills

    if a.action == "list":
        for name, desc in list_skills():
            print(f"{name}: {desc}")
    else:
        install(a.dest, user=a.user, force=a.force, log=_log(False))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="citation-topics", description=DESCRIPTION)
    ap.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = ap.add_subparsers(dest="command", required=True)

    p = sub.add_parser("run", help="build the network, the topics, the areas and the second and third topics")
    p.add_argument("input", help="JSON or JSON Lines file of works (.gz allowed)")
    p.add_argument("out", help="output folder")
    _input_args(p)
    p.add_argument("--resolution", type=float, help="topic resolution (default 16; higher = more, smaller topics)")
    p.add_argument("--min-size", type=int, help="smallest topic, in works (default 100)")
    p.add_argument("--passes", type=int, help="Leiden passes, stopping early when quality stops rising (default 20)")
    p.add_argument("--seed", type=int, help="random seed (default 1)")
    p.add_argument("--area-resolution", type=float, help="area resolution (default 0.3)")
    p.add_argument("--area-seeds", type=int, help="Leiden runs on the graph of topics; the best is kept (default 50)")
    p.add_argument("--from-year", type=int, help="only works from this year (needs the year field)")
    p.add_argument("--to-year", type=int, help="only works up to this year (needs the year field)")
    p.add_argument("-q", "--quiet", action="store_true")
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("describe", help="describe every topic and area from the optional fields (dossier.json)")
    p.add_argument("input")
    p.add_argument("out", help="output folder of `run`")
    _input_args(p)
    p.add_argument("--top", type=int, default=8, help="most cited works listed per topic (default 8)")
    p.add_argument("--terms", type=int, default=15, help="distinctive terms per topic (default 15)")
    p.add_argument("--abstracts", action="store_true", help="also take terms from the abstracts (slower)")
    p.add_argument("-q", "--quiet", action="store_true")
    p.set_defaults(func=cmd_describe)

    p = sub.add_parser("names", help="put the names of names.json into topics.json and areas.json")
    p.add_argument("out", help="output folder of `run`")
    p.add_argument("names", help="names.json, as written by the topic-namer agent or by `compare`")
    p.add_argument("-q", "--quiet", action="store_true")
    p.set_defaults(func=cmd_names)

    p = sub.add_parser("compare", help="where the topics of an earlier run went; carries names over")
    p.add_argument("old", help="output folder of the earlier run")
    p.add_argument("new", help="output folder of the later run")
    p.add_argument("result", help="folder for flows.json and names_carried.json")
    p.add_argument("-q", "--quiet", action="store_true")
    p.set_defaults(func=cmd_compare)

    p = sub.add_parser("agreement", help="NMI and ARI between runs of the same list (seeds); prints the medoid")
    p.add_argument("outs", nargs="+", help="output folders of `run`")
    p.set_defaults(func=cmd_agreement)

    p = sub.add_parser("export", help="VOSviewer and CSV files of a run (both by default)")
    p.add_argument("out", help="output folder of `run`")
    p.add_argument("--vosviewer", action="store_true")
    p.add_argument("--csv", action="store_true")
    p.add_argument("--min-links", type=int, default=1, help="VOSviewer: drop links between topics weaker than this")
    p.add_argument("-q", "--quiet", action="store_true")
    p.set_defaults(func=cmd_export)

    p = sub.add_parser("board", help="self-contained HTML board of a run, with a tab for each view the fields allow")
    p.add_argument("input", help="the input file of `run`")
    p.add_argument("out", help="output folder of `run`")
    _input_args(p)
    p.add_argument("--html", help="where to write the page (default OUT/board.html)")
    p.add_argument("--title", help="page title (default: Citation topics)")
    p.add_argument("--highlight", metavar="FIELD", help="true/false input field marking works to follow, e.g. own")
    p.add_argument("--highlight-label", default="Highlighted works", help="name of that tab (e.g. 'Your papers')")
    p.add_argument("--max-works", type=int, default=5000, help="most cited works kept for the Works tab (default 5000)")
    p.add_argument("-q", "--quiet", action="store_true")
    p.set_defaults(func=cmd_board)

    p = sub.add_parser("skills", help="list or install the Claude skills and the topic-namer agent")
    p.add_argument("action", choices=["list", "install"])
    p.add_argument("--dest", default=".claude", help="folder that gets skills/ and agents/ (default ./.claude)")
    p.add_argument("--user", action="store_true", help="install into ~/.claude instead")
    p.add_argument("--force", action="store_true", help="overwrite files that differ")
    p.set_defaults(func=cmd_skills)

    a = ap.parse_args(argv)
    a.func(a)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
