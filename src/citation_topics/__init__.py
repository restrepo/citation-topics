"""Research topics and areas from the citation links of any list of works, with Leiden clustering as CWTS does
for the OpenAlex topics."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("citation-topics")
except PackageNotFoundError:  # running from a source tree that was never installed
    __version__ = "0.0.0"

__all__ = ["__version__"]
