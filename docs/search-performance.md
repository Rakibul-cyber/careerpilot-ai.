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
