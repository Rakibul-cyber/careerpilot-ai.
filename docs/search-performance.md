# Search Performance & Database Optimization

This document explains the database-level optimizations that back CareerPilot's
job search (`JobRepository.search`, exposed via `GET /api/v1/jobs`).

## Background

Job search matches free text with case-insensitive substring queries:

```sql
... WHERE normalized_title ILIKE '%flutter%'
     OR description ILIKE '%flutter%'
     OR requirements ILIKE '%flutter%'
```

A leading-wildcard pattern (`'%term%'`) **cannot** use a standard B-tree index —
B-trees only help with prefix matches (`'term%'`). Without help, every such
query is a **sequential scan** of the whole table, which degrades as the `jobs`
and `companies` tables grow.

## The optimization: `pg_trgm` + GIN trigram indexes

PostgreSQL's [`pg_trgm`](https://www.postgresql.org/docs/current/pgtrgm.html)
extension breaks text into three-character sequences (trigrams) and supports a
GIN index operator class, `gin_trgm_ops`, that indexes those trigrams. A GIN
trigram index **can** accelerate `ILIKE '%term%'` (and `LIKE`, similarity, and
regex) because the planner can look up candidate rows by trigram instead of
scanning every row.

### Migration `8c18594ccbc3_add_pg_trgm_and_gin_trigram_indexes_for_search`

```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE INDEX ix_jobs_normalized_title_trgm ON jobs        USING gin (normalized_title gin_trgm_ops);
CREATE INDEX ix_jobs_description_trgm      ON jobs        USING gin (description       gin_trgm_ops);
CREATE INDEX ix_jobs_requirements_trgm     ON jobs        USING gin (requirements      gin_trgm_ops);
CREATE INDEX ix_jobs_location_trgm         ON jobs        USING gin (location          gin_trgm_ops);
CREATE INDEX ix_companies_name_trgm            ON companies USING gin (name            gin_trgm_ops);
CREATE INDEX ix_companies_normalized_name_trgm ON companies USING gin (normalized_name gin_trgm_ops);
```

These six columns are exactly the ones `JobRepository.search` matches with
`ILIKE`. The migration is reversible: `downgrade()` drops the six indexes and
then the extension.

The same indexes are also declared on the `Job` / `Company` models
(`__table_args__` with `postgresql_using="gin"` + `postgresql_ops`) so that
`Base.metadata` matches the database and `alembic check` stays clean.

## What did NOT change

- **No schema changes** — no columns, tables, enums, or constraints added.
- **No B-tree indexes removed** — the existing `index=True` / unique indexes on
  `title`, `normalized_title`, `location`, `status`, `source`, `company_id`,
  `normalized_name`, etc. remain and still serve equality / ordering.
- **No API or search-behavior change** — results and ordering are identical to
  Milestone 24. These indexes only affect *how fast* the same query runs.

## Verifying the planner can use the indexes: `EXPLAIN ANALYZE`

```sql
EXPLAIN ANALYZE
SELECT * FROM jobs
WHERE deleted_at IS NULL
  AND status = 'active'
  AND normalized_title ILIKE '%flutter%';
```

On a **large** table you expect a `Bitmap Index Scan` on
`ix_jobs_normalized_title_trgm` feeding a `Bitmap Heap Scan`, instead of a
`Seq Scan`.

### Benchmark note (small datasets)

On a nearly empty development database the planner will usually still choose a
**sequential scan** — for a handful of rows a seq scan is genuinely cheaper than
consulting an index, so this is correct behavior, not a misconfiguration. The
GIN indexes start winning once the tables hold thousands of rows. To see the
planner switch, seed ~5,000–10,000 jobs and re-run `EXPLAIN ANALYZE` (optionally
`SET enable_seqscan = off;` to confirm the index is *usable*).

What matters for this milestone is that:

1. the `pg_trgm` extension installs,
2. the six GIN indexes are created with `gin_trgm_ops`,
3. the planner is *able* to use them (verifiable with `enable_seqscan = off`),
4. the migration is reversible, and
5. `alembic check` remains clean.

## Operational notes / future work

- **`CREATE INDEX CONCURRENTLY`**: this migration uses plain `CREATE INDEX`,
  which takes a lock and runs inside Alembic's transaction — fine for the
  current data size. For a large production table, build these
  `CONCURRENTLY` (outside a transaction) to avoid blocking writes.
- **Next milestone (26)**: PostgreSQL Full-Text Search (`tsvector` / `tsquery`
  with ranking) will build a relevance-ranked engine on top of this foundation;
  trigram search remains ideal for fuzzy / typo-tolerant substring matching.

---

## Full-Text Search Foundation

Milestone 26 adds PostgreSQL full-text search (FTS) alongside the trigram
substring search, so results can be **relevance-ranked** rather than only
filtered.

### What `search_vector` stores

`jobs.search_vector` is a `tsvector` — the tokenized, stemmed, weighted
representation of a job's searchable text. It combines five columns with
positional **weights**:

| Weight | Columns |
| --- | --- |
| `A` (highest) | `title`, `normalized_title` |
| `B` | `description`, `requirements` |
| `C` (lowest) | `location` |

It is built with the `english` text-search config (stemming, stop-word removal)
via:

```sql
setweight(to_tsvector('english', coalesce(title, '')), 'A') || ... || setweight(..., 'C')
```

#### Why a trigger (not a generated column)?

The column is kept up to date by a `BEFORE INSERT OR UPDATE` trigger
(`jobs_search_vector_trigger` → `jobs_search_vector_update()`), so application
code never sets it. A trigger was chosen over a `GENERATED ALWAYS AS ... STORED`
column because it is more portable across Postgres versions and plays nicely
with Alembic (plain column + explicit trigger, easy to audit and reverse). The
migration also backfills existing rows.

A GIN index (`ix_jobs_search_vector_gin`) over the vector makes `@@` matching and
ranking index-assisted.

### Why weights are used

Weights let ranking reflect *where* a term matched. A job whose **title** is
"Flutter Developer" is a stronger match for `flutter` than one that merely
mentions flutter in its **description**. `ts_rank_cd(search_vector, query)` uses
the A/B/C weights so title matches outrank description-only matches.

### Why FTS is added *alongside* trigram search

They solve different problems and complement each other:

- **FTS** — word-aware, stemmed, ranked. Great for natural queries
  (`python backend`, `senior flutter developer`) and relevance ordering. It does
  **not** match arbitrary substrings (searching `ackend` will not find
  `backend`).
- **Trigram / ILIKE** — literal substring matching, typo/partial friendly, but
  unranked.

`JobRepository.search` therefore **ORs an FTS branch with the existing ILIKE
branches**: `search_vector @@ websearch_to_tsquery('english', query)` OR
`normalized_title/description/requirements ILIKE '%query%'`. FTS supplies
relevance and word matching; ILIKE remains the substring fallback, so no query
that worked before stops working. `websearch_to_tsquery` is used because it
never raises on arbitrary user input (unlike `to_tsquery`), so special
characters can't break search.

### When relevance sorting is useful

Pass `sort_by=relevance` (with a `query`) to order by `ts_rank_cd` descending,
tie-broken by `created_at desc`. Use it for the main "search" experience where
the best textual match should come first. Without a query, `relevance` falls
back to `created_at desc`. All other sort fields (`created_at`, `posted_at`,
`salary_min`, `salary_max`) are unchanged, and the default remains
`created_at desc`.

### Benchmark

`EXPLAIN ANALYZE` on
`search_vector @@ websearch_to_tsquery('english', 'flutter developer')` over
~6,000 rows uses a `Bitmap Index Scan on ix_jobs_search_vector_gin` when the
planner is allowed to (e.g. with `enable_seqscan = off`). As with the trigram
indexes, on a small table the default planner still prefers a sequential scan —
that's expected; the index wins at scale.

### Future path

- **Ranking tuning** — custom weight vectors (`ts_rank_cd(weights, ...)`),
  `setweight` adjustments, cover-density vs. term-frequency ranking.
- **Headline snippets** — `ts_headline(...)` to return highlighted match
  fragments in API responses.
- **Language config** — per-job / per-user language instead of hard-coded
  `english`; a `regconfig` column feeding `to_tsvector`.
- **Hybrid FTS + embeddings** — combine lexical FTS ranking with semantic
  vector similarity (pgvector) for AI-powered job matching (later milestone).
