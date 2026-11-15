"""Input for citation-topics from an INSPIRE-HEP author profile: the author's papers and every paper citing them,
with the references, year, title, abstract, keywords, journal, arXiv categories, authors (the first 10, with the
author count and collaboration), citation count and link of each.

Usage: python inspire_profile.py AUTHOR works.jsonl
AUTHOR is the profile's number (https://inspirehep.net/authors/991924 -> 991924) or its INSPIRE BAI (D.Restrepo.1).
Only the Python standard library is needed. Each work also gets "own": true for the author's papers.
"""

import json
import sys
import time
import urllib.parse
import urllib.request

API = "https://inspirehep.net/api"
FIELDS = (
    "control_number,titles.title,abstracts.value,keywords.value,earliest_date,citation_count,"
    "references.record,arxiv_eprints.categories,publication_info.journal_title,authors.full_name,author_count,"
    "collaborations.value"
)
MAX_AUTHORS = 10  # collaboration papers list thousands


def get(url):
    for k in range(5):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "citation-topics example"})
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.load(r)
        except Exception:
            if k == 4:
                raise
            time.sleep(5 * (k + 1))


def bai(author):
    if not author.isdigit():
        return author
    ids = get(f"{API}/authors/{author}?fields=ids")["metadata"]["ids"]
    return next(i["value"] for i in ids if i["schema"] == "INSPIRE BAI")


def search(q):
    hits, page = [], 1
    while True:
        args = {"q": q, "size": 100, "page": page, "fields": FIELDS, "sort": "mostrecent"}
        d = get(f"{API}/literature?" + urllib.parse.urlencode(args))
        hits += d["hits"]["hits"]
        if len(hits) >= d["hits"]["total"] or not d["hits"]["hits"]:
            return hits
        page += 1
        time.sleep(0.5)


def work(m):
    rid = m["control_number"]
    names = [a["full_name"] for a in m.get("authors", []) if a.get("full_name")]
    return {
        "id": rid,
        "references": [int(r["record"]["$ref"].rsplit("/", 1)[1]) for r in m.get("references", []) if "record" in r],
        "year": (m.get("earliest_date") or "")[:4],
        "title": (m.get("titles") or [{}])[0].get("title"),
        "abstract": (m.get("abstracts") or [{}])[0].get("value"),
        "keywords": [k["value"] for k in m.get("keywords", []) if k.get("value")],
        "journal": next((p["journal_title"] for p in m.get("publication_info", []) if p.get("journal_title")), None),
        "categories": sorted({c for e in m.get("arxiv_eprints", []) for c in e.get("categories", [])}),
        "authors": names[:MAX_AUTHORS],
        "author_count": m.get("author_count") or len(names),
        "collaborations": [c["value"] for c in m.get("collaborations", []) if c.get("value")],
        "citations": m.get("citation_count", 0),
        "url": f"https://inspirehep.net/literature/{rid}",
    }


def main(author, out):
    b = bai(author)
    own = search(f"a {b}")
    citing = search(f"refersto:a {b}")
    mine = {h["metadata"]["control_number"] for h in own}
    works = {}
    for h in own + citing:
        w = work(h["metadata"])
        works.setdefault(w["id"], {**w, "own": w["id"] in mine})
    with open(out, "w", encoding="utf-8") as f:
        for w in works.values():
            f.write(json.dumps(w, ensure_ascii=False) + "\n")
    print(f"{b}: {len(own)} papers, {len(citing)} citing papers, {len(works)} works -> {out}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(*sys.argv[1:])
