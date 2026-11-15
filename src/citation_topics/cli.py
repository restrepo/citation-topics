"""Command line entry point: `citation-topics`."""

import argparse

from . import __version__


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="citation-topics",
        description="Research topics and areas from the citation links of any list of works, with Leiden clustering as CWTS does for OpenAlex.",
    )
    ap.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    ap.parse_args(argv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
