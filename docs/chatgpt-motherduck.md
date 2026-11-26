# ChatGPT-specific remote architecture for citation-topics and MotherDuck

This optional workflow is for researchers with ChatGPT access to MotherDuck SQL and Flights. It does not require a local Python runtime. Availability, compute limits and permissions depend on the account. Connect your own database and inspect its schema; no private snapshot or credentials are distributed here.

## Scope: ChatGPT versus Claude Code

This architecture is specifically intended for **ChatGPT**, where connected MotherDuck SQL and Flights provide access to data and remote Python execution without requiring a local workstation. It is an optional integration, not a new requirement of citation-topics.

| Component | ChatGPT (remote-first) | Claude Code (local-first) |
|---|---|---|
| Python execution | MotherDuck Flights | Local Python virtual environment |
| Data access | Connected MotherDuck SQL | Local DuckDB or MotherDuck through the local DuckDB client |
| Clustering | Remote Python and citation-topics where supported | Local citation-topics CLI and existing Claude skills |
| Outputs | Authorized remote storage or private downloadable artifacts | Local files and boards |

For **Claude Code**, prefer the local environment and the existing README and Claude skills. MotherDuck may still be used as a data source, but Flights are not the default execution backend. Use remote execution there only when explicitly requested or justified by compute or data-access constraints. Both approaches share the same scientific methodology and reproducibility requirements. Neither replaces the other.

## ChatGPT instructions

Ask ChatGPT to read the current citation-topics README and MotherDuck query/Flight guides, inspect the source schema, extract a citation neighborhood, execute Python remotely, validate the run and return the results. Require explicit approval for persistent writes or publication. Do not treat a submitted job as a completed experiment.

For INSPIRE snapshots with `papers(recid, year, references STRUCT(recid BIGINT, in_corpus BOOLEAN)[])`, the following read-only Flight is a starting point. Adapt the database name and schema to your own data. The seed is an INSPIRE literature record, not an author ID.

## Remote Python example

Create an on-demand MotherDuck Flight with these requirements (tested together in November 2026; verify current MotherDuck DuckDB compatibility):

```text
duckdb==1.5.6
igraph==0.11.9
leidenalg==0.10.2
```

Set non-secret parameters DATABASE, SEED_ID, and optionally PRECURSOR_ID in the source below (or adapt to the current Flight configuration interface). The default Flight authentication is supplied by MotherDuck; never paste a token into source or logs.

```python
import duckdb
import igraph as ig
import leidenalg as la

DATABASE = "your_database"
SEED_ID = 709378
PRECURSOR_ID = 0


def main():
    db = DATABASE
    seed = int(SEED_ID)
    precursor = int(PRECURSOR_ID)
    con = duckdb.connect(f"md:{db}?attach_mode=single")
    for k in (5, 10, 20, 50):
        base = f"""WITH s AS (
            SELECT recid, "references" FROM papers
            WHERE recid={seed} OR list_contains(
                list_transform("references", r->r.recid), {seed})
        ), n AS (
            SELECT recid FROM s UNION
            SELECT r.recid FROM s, unnest(s."references") u(r)
            WHERE r.in_corpus GROUP BY r.recid
            HAVING count(DISTINCT s.recid)>={k}
        )"""
        ids = [r[0] for r in con.execute(base + " SELECT recid FROM n ORDER BY recid").fetchall()]
        edges = con.execute(
            base
            + """ SELECT DISTINCT p.recid,r.recid
            FROM papers p JOIN n ON n.recid=p.recid,
            unnest(p."references") u(r) JOIN n n2 ON n2.recid=r.recid
            WHERE p.recid<>r.recid ORDER BY 1,2"""
        ).fetchall()
        idx = {v: i for i, v in enumerate(ids)}
        assert seed in idx
        g = ig.Graph(n=len(ids), edges=[(idx[a], idx[b]) for a, b in edges])
        g.simplify()
        for resolution in (0.5, 1, 1.5, 2):
            for random_seed in (1, 2, 3, 4, 42):
                p = la.find_partition(
                    g, la.RBConfigurationVertexPartition, resolution_parameter=resolution, seed=random_seed
                )
                m = p.membership[idx[seed]]
                same = p.membership[idx[precursor]] == m if precursor in idx else None
                print(
                    dict(
                        k=k,
                        resolution=resolution,
                        seed=random_seed,
                        nodes=len(ids),
                        directed_edges=len(edges),
                        edges=g.ecount(),
                        communities=len(p),
                        modularity=g.modularity(p.membership),
                        objective=p.quality(),
                        same=same,
                    ),
                    flush=True,
                )


if __name__ == "__main__":
    main()
```

Run the Flight and poll its run status and logs until terminal. Check exit code, expected 80 experiment rows and graph invariants. Record package versions, snapshot, parameters, run ID and input hash. This example is raw RB Leiden, not the package's complete clustering pipeline; the multi-seed example was execution-tested on MotherDuck Flights on 2026-11-26.

The example was execution-tested on MotherDuck Flights with all 80 parameter combinations completing successfully. Research-specific results belong in a separate research project, not in this package. The full CLI workflow below is distinct from the raw Leiden example.

## Full package workflow

Export the selected works as JSON Lines with `id`, `references`, and optional metadata as documented in the README. In a Flight with a compatible pinned citation-topics installation, use subprocess.run(..., check=True) to execute `citation-topics run`, `describe`, `export --works`, `board`, and `agreement` across seeds. Use `names` only with evidence-based names. Persist results to an explicitly authorized destination; Flight scratch files are not durable downloads. Validate the full board before sharing. Never publish automatically.

## Historical precursors

For seed s and earlier candidate p, compute distinct citing sets C_s and C_p over the same full corpus. Rank by |C_p ∩ C_s| / |C_p|, report support and reverse coverage, test minimum co-citation thresholds 2,5,10,20,50,100, and inspect original papers. High overlap does not establish precedence or causal influence. Treat missing dates separately and avoid interpreting a retrospective test as prospective discovery.

## Example prompt

> Using my connected MotherDuck database, construct the citation neighborhood of INSPIRE record 709378. Rank earlier precursors without using their identity. Run Leiden sensitivity analysis remotely using Flights, retrieve terminal results, compare seeds, inspect citation contexts, and generate a private interactive board. Report all validation, assumptions and blockers. Do not modify source tables or publish anything without permission.
