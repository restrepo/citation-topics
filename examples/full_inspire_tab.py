"""Add a "Full INSPIRE" tab to the sample board: how the topics of the profile's citation community match the topics
of the whole INSPIRE-HEP citation network (restrepo/inspireauth10: 1.9 million papers, 304 topics, 6 areas).

Usage: python full_inspire_tab.py BOARD_DIR INSPIREAUTH10
BOARD_DIR holds the board (index.html) and works_vosviewer.json; INSPIREAUTH10 is a clone of restrepo/inspireauth10
with its clustering out/clusters/steady_r16_s1.npz (built locally, not in git) and reproduce/topics/names.py.
Needs numpy and igraph (both installed with citation-topics). Running it again replaces the tab.
"""

import html
import importlib.util
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import igraph as ig
import numpy as np

OWN = "The author's papers"
START, END = "<!-- full-inspire-tab -->", "<!-- /full-inspire-tab -->"


def pct(x):
    return f"{100 * x:.0f}%"


def main(board_dir, repo):
    board_dir, repo = Path(board_dir), Path(repo)
    spec = importlib.util.spec_from_file_location("names", repo / "reproduce/topics/names.py")
    names = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(names)
    f = np.load(repo / "out/clusters/steady_r16_s1.npz")
    full = dict(zip(f["recid"].tolist(), f["topic"].tolist()))
    area_of = f["area_of_topic"].tolist()

    with open(board_dir / "works_vosviewer.json", encoding="utf-8") as fh:
        net = json.load(fh)["network"]
    label = {c["cluster"] - 1: c["label"] for c in net["clusters"]}
    rows = [(int(i["id"]), i["cluster"] - 1, OWN in i["description"]) for i in net["items"] if i.get("cluster")]
    both = [(t, o, full[r]) for r, t, o in rows if full.get(r, -1) >= 0]
    a, b = [x[0] for x in both], [x[2] for x in both]
    nmi, ari = ig.compare_communities(a, b, "nmi"), ig.compare_communities(a, b, "adjusted_rand")

    by, own = defaultdict(Counter), defaultdict(Counter)
    for t, o, k in both:
        by[t][k] += 1
        if o:
            own[t][k] += 1
    rev = defaultdict(Counter)
    for t, _, k in both:
        rev[k][t] += 1
    own_area = Counter(area_of[k] for _, o, k in both if o)

    e = html.escape
    tn = lambda k: f"#{k} {e(names.TOPICS[k])}"  # noqa: E731
    out = [
        START,
        '  <section class="panel" id="p-full" role="tabpanel" hidden>',
        '    <div class="sec">',
        "      <h2>The topics of this community in the full INSPIRE-HEP map</h2>",
        '      <p class="note">The full map is the clustering of the whole INSPIRE-HEP citation network made with this '
        'package in <a href="https://github.com/restrepo/inspireauth10">restrepo/inspireauth10</a>: 1,872,221 '
        "papers, 304 topics in 6 areas (resolution 16, seed 1). It is the same method at another scale, so a topic "
        "of this board can be a piece of a full topic, match it, or spread over several.</p>",
        f"      <p>Of the {len(rows):,} works with a topic here, <b>{len(both):,}</b> "
        f"({pct(len(both) / len(rows))}) have a topic in the full map; they fall in <b>{len(set(b))}</b> of its "
        "304 topics. Agreement between the two "
        f"partitions: NMI <b>{nmi:.2f}</b>, ARI <b>{ari:.2f}</b>, moderate, as expected between a fine local split "
        "and a coarse global one.</p>",
        '      <ul class="note" style="max-width:none;color:var(--fg);font-size:14px">',
        "        <li><b>Strong matches.</b> R-parity violation, the DUNE experiments, singlet-doublet dark matter and "
        "the Z&prime; models each sit mostly (49% to 67%) in one full topic; the author's 19 R-parity papers all "
        "fall in the full topic of R-parity violation and leptoquarks.</li>",
        "        <li><b>Merged in the full map.</b> The full topic of neutrino mass models and lepton flavour "
        "violation is the largest piece of this community: it holds most of three topics here (scotogenic, seesaw "
        "and Dirac neutrino masses), which the local clustering separates.</li>",
        "        <li><b>Spread out.</b> Supersymmetry at the LHC and ILC spreads over supersymmetric model building, "
        "supersymmetry at colliders and composite Higgs; gravitino dark matter sits between R-parity violation and "
        "cosmic-ray positrons (in the astrophysics area); the diboson-excess topic splits between neutrino mass "
        "models and diphoton resonances.</li>",
        "        <li><b>A name to read with care.</b> The topic of LHC searches with lepton universality sits mostly "
        "in the full topic of B physics at LHCb and Belle II: its works are mainly about the lepton-universality "
        "anomalies.</li>",
        "        <li><b>Areas.</b> All the areas of this board are inside one full area, "
        f"{e(names.AREAS[0])}, which holds {own_area[0]} of the author's {sum(own_area.values())} papers "
        "with a full topic.</li>",
        "      </ul>",
        "    </div>",
        '    <div class="sec">',
        "      <h2>Each topic of this board in the full map</h2>",
        '      <p class="note">The three full topics holding most of its works, with their share, and where the '
        "author's own papers fall.</p>",
        '      <div class="tw"><table><thead><tr><th>Topic here</th><th class="n">Works</th><th>Main full topics'
        "</th><th>Author's papers</th></tr></thead><tbody>",
    ]
    for t in sorted(by):
        n = sum(by[t].values())
        main_ = "<br>".join(
            f'{pct(c / n)} {tn(k)} <span style="color:var(--muted)">({e(names.AREAS[area_of[k]].split(":")[0])})</span>'
            for k, c in by[t].most_common(3)
        )
        mine = ", ".join(f"#{k} &times; {c}" for k, c in own[t].most_common(4)) or "&ndash;"
        cells = f'<td>{e(label[t])}</td><td class="n">{n:,}</td><td>{main_}</td><td class="s">{mine}</td>'
        out.append(f"        <tr>{cells}</tr>")
    out += [
        "      </tbody></table></div>",
        "    </div>",
        '    <div class="sec">',
        "      <h2>The full topics holding most of this community</h2>",
        '      <div class="tw"><table><thead><tr><th>Full topic</th><th class="n">Works here</th><th>From the topics '
        "here</th></tr></thead><tbody>",
    ]
    for k, c in Counter(b).most_common(10):
        src = "<br>".join(f"{e(label[t])} ({n})" for t, n in rev[k].most_common(3))
        out.append(f'        <tr><td>{tn(k)}</td><td class="n">{c:,}</td><td class="s">{src}</td></tr>')
    out += [
        "      </tbody></table></div>",
        '      <p class="note">The author\'s papers by full area: '
        + "; ".join(f"{e(names.AREAS[k])}: {c}" for k, c in own_area.most_common())
        + ". Citing papers added to INSPIRE after the full download have no full topic. Made with "
        "examples/full_inspire_tab.py.</p>",
        "    </div>",
        "  </section>",
        END,
    ]
    script = [
        START,
        "<script>",
        "TABS.full = 'Full INSPIRE';",
        "DRAW.full = () => {};",
        "{ const b = el('button', {role: 'tab', 'data-tab': 'full', 'aria-selected': 'false'}, TABS.full);",
        "  b.onclick = () => open('full');",
        "  nav.insertBefore(b, nav.querySelector('[data-tab=\"about\"]'));",
        # the page's URL as loaded: the board's first open() has already rewritten the hash
        "  const nav0 = (performance.getEntriesByType('navigation')[0] || {}).name || '';",
        "  if (nav0.endsWith('#full')) open('full'); }",
        "</script>",
        END,
    ]
    page = board_dir / "index.html"
    s = page.read_text(encoding="utf-8")
    s = re.sub(re.escape(START) + ".*?" + re.escape(END) + "\n", "", s, flags=re.S)
    anchor = '  <section class="panel" id="p-about"'
    s = s.replace(anchor, "\n".join(out) + "\n" + anchor, 1)
    s = s.replace("</body>", "\n".join(script) + "\n</body>", 1)
    page.write_text(s, encoding="utf-8")
    print(f"{page}: Full INSPIRE tab, {len(both)} works, NMI {nmi:.2f}, ARI {ari:.2f}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(*sys.argv[1:])
