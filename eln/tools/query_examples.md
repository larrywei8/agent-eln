# DuckDB Query Examples

Prerequisite: first run `python tools/index.py` to generate `index/data.duckdb`. Run:

```
python tools/query.py "SELECT ..."
python tools/query.py --file tools/queries/<name>.sql
```

## Table schema

| Table | Columns |
|---|---|
| `records` | `id, type, name, status, project, path, who, created_date, tags[]` |
| `edges` | `src, dst, rel` |
| `backlinks` | `id, backlink, value` |

`created_date` is a string (YYYY-MM-DD); when doing time filtering use `CAST(... AS DATE)`.

---

## 1. Experiment count by project (this month)

```sql
SELECT project, count(*) AS n_exps
FROM records
WHERE type = 'experiment'
  AND CAST(created_date AS DATE) >= date_trunc('month', current_date)
GROUP BY project
ORDER BY n_exps DESC;
```

## 2. Failure rate per protocol

```sql
SELECT e.dst AS protocol_id,
       count(*) AS total,
       sum(CASE WHEN r.status = 'failed' THEN 1 ELSE 0 END) AS failed,
       round(100.0 * sum(CASE WHEN r.status = 'failed' THEN 1 ELSE 0 END) / count(*), 1) AS pct
FROM edges e
JOIN records r ON r.id = e.src
WHERE e.rel = 'protocols' AND r.type = 'experiment'
GROUP BY e.dst
ORDER BY pct DESC;
```

## 3. Resource hotness Top 20 (by reference count)

```sql
SELECT dst AS resource_id, count(*) AS refs
FROM edges
WHERE dst LIKE 'PLA-%' OR dst LIKE 'AB-%' OR dst LIKE 'CL-%'
   OR dst LIKE 'OLI-%' OR dst LIKE 'RGT-%' OR dst LIKE 'VIR-%'
   OR dst LIKE 'MUS-%' OR dst LIKE 'INS-%'
GROUP BY dst
ORDER BY refs DESC
LIMIT 20;
```

## 4. Experiments stuck in-progress for more than 14 days

```sql
SELECT id, project, who, created_date,
       current_date - CAST(created_date AS DATE) AS days_open
FROM records
WHERE type = 'experiment'
  AND status = 'in-progress'
  AND CAST(created_date AS DATE) < current_date - INTERVAL 14 DAY
ORDER BY days_open DESC;
```

## 5. Antibody usage census (each antibody × related project)

```sql
SELECT e.dst AS antibody_id,
       r.project,
       count(DISTINCT r.id) AS used_in_n_exps
FROM edges e
JOIN records r ON r.id = e.src
WHERE e.dst LIKE 'AB-%' AND r.type = 'experiment'
GROUP BY e.dst, r.project
ORDER BY antibody_id, used_in_n_exps DESC;
```

---

## More patterns

- Reverse lookup "who produced this dataset": `SELECT src FROM edges WHERE dst = 'DAT-2026-0003' AND rel LIKE 'produced_%';`
- Who recently modified experiments: `SELECT who, count(*) FROM records WHERE type='experiment' AND CAST(created_date AS DATE) >= current_date - 7 GROUP BY who;`
- Two-hop neighbors in the graph: recursive CTE (`WITH RECURSIVE ...`), natively supported by DuckDB.
