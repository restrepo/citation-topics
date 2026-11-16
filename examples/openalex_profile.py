"""Input for citation-topics from an OpenAlex author profile: the author's works and every work citing them, with
the references, year, title, abstract, keywords, journal, field and subfield (as categories), countries, authors
(the first 10, with the author count), citation count and link of each.

Usage: python openalex_profile.py AUTHOR works.jsonl
AUTHOR is the OpenAlex author id (https://openalex.org/A5010397600 -> A5010397600) or the author's ORCID.
Only the Python standard library is needed. Each work also gets "own": true for the author's works.
Without an API key OpenAlex shares a small free daily budget per network; a profile of a hundred works and a few
thousand citations takes a few dozen requests. To use your own key, set the environment variable OPENALEX_API_KEY.
"""

import json
import os
import sys
import time
import urllib.parse
import urllib.request

API = "https://api.openalex.org"
SELECT = (
    "id,doi,title,publication_year,referenced_works,abstract_inverted_index,keywords,primary_location,"
    "primary_topic,authorships,cited_by_count"
)
MAX_AUTHORS = 10
CHUNK = 50  # works per `cites:` filter


def get(path, **args):
    if key := os.environ.get("OPENALEX_API_KEY"):
        args["api_key"] = key
    url = f"{API}/{path}?" + urllib.parse.urlencode(args)
    for k in range(5):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "citation-topics example"})
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.load(r)
        except Exception:
            if k == 4:
                raise
            time.sleep(5 * (k + 1))


def search(flt):
    # page numbers, not cursors: paging with cursor= needs an API key; pages reach 10,000 results per filter
    hits, page = [], 1
    while True:
        d = get("works", filter=flt, select=SELECT, per_page=200, page=page)
        hits += d["results"]
        if len(hits) >= d["meta"]["count"] or not d["results"]:
            return hits
        page += 1
        time.sleep(0.2)


def short(oid):
    return oid.rsplit("/", 1)[-1] if oid else oid


def abstract(inv):
    if not inv:
        return None
    pos = sorted((i, w) for w, ii in inv.items() for i in ii)
    return " ".join(w for _, w in pos)


def work(m, country):
    wid = short(m["id"])
    au = m.get("authorships") or []
    src = ((m.get("primary_location") or {}).get("source") or {}).get("display_name")
    topic = m.get("primary_topic") or {}
    cats = [x["display_name"] for x in (topic.get("field"), topic.get("subfield")) if x]
    codes = sorted({c for a in au for c in a.get("countries") or []})
    return {
        "id": wid,
        "references": [short(r) for r in m.get("referenced_works") or []],
        "year": m.get("publication_year"),
        "title": m.get("title"),
        "abstract": abstract(m.get("abstract_inverted_index")),
        "keywords": [k["display_name"] for k in m.get("keywords") or [] if k.get("display_name")],
        "journal": src,
        "categories": cats,
        "countries": [country.get(c, c) for c in codes],
        "authors": [a["author"]["display_name"] for a in au[:MAX_AUTHORS] if a.get("author", {}).get("display_name")],
        "author_count": len(au),
        "citations": m.get("cited_by_count", 0),
        "url": m.get("doi") or f"https://openalex.org/{wid}",
    }


def main(author, out):
    a = get(f"authors/{author if author.startswith('A') else 'orcid:' + author}", select="id")
    aid = short(a["id"])
    country = {short(c["id"]).upper(): c["display_name"] for c in get("countries", per_page=200)["results"]}
    own = search(f"author.id:{aid}")
    mine = [short(m["id"]) for m in own]
    is_own = set(mine)
    citing = []
    for i in range(0, len(mine), CHUNK):
        citing += search("cites:" + "|".join(mine[i : i + CHUNK]))
    works = {}
    for m in own + citing:
        w = work(m, country)
        works.setdefault(w["id"], {**w, "own": w["id"] in is_own})
    with open(out, "w", encoding="utf-8") as f:
        for w in works.values():
            f.write(json.dumps(w, ensure_ascii=False) + "\n")
    print(f"{aid}: {len(own)} works, {len(works) - len(own)} citing works, {len(works)} works -> {out}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(*sys.argv[1:])
