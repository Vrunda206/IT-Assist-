# SQL Queries – IT Assist

All runnable queries are in `database/queries.sql`. Summary:

| Topic | Examples in queries.sql |
|---|---|
| DDL | CREATE DATABASE / TABLE / INDEX / VIEW in `schema.sql` |
| DML | INSERT, UPDATE, DELETE (inside START TRANSACTION … ROLLBACK, section A) |
| Constraints | PRIMARY KEY, FOREIGN KEY (RESTRICT / CASCADE / SET NULL), UNIQUE, NOT NULL, DEFAULT, CHECK |
| 16 required queries | Section B (all / available / assigned / maintenance assets, employees by department, warranty expiry, top cost, average cost, counts by category and department, total maintenance cost, high/low usage …) |
| INNER JOIN / LEFT JOIN | Section C (assets with maintenance; all employees even without assets; assets never used) |
| Aggregates | Section D – COUNT, SUM, AVG, MAX, MIN |
| GROUP BY / HAVING | Section E |
| Subqueries | Section F – scalar (`> AVG`), `IN`, `NOT EXISTS` |
| Views | `available_assets`, `assigned_assets`, `asset_usage_summary`, `maintenance_summary` |

## Key example – utilization in SQL
```sql
SELECT asset_tag, avg_usage_hours, utilization_rate, usage_category
FROM asset_usage_summary ORDER BY utilization_rate DESC;
```
`utilization_rate = LEAST(AVG(usage_hours) / 8 * 100, 100)`; Low ≤ 40, Normal ≤ 75, else High.

## Transactions used by the app
* **Assign asset:** INSERT into `asset_assignments` + UPDATE `assets.status='Assigned'` (one transaction).
* **Return asset:** UPDATE assignment (returned_date, status) + UPDATE asset to *Available*.
* **Maintenance:** INSERT record + set asset *Under Maintenance*; completing the last open record sets it back to *Available*.
