 # SQL Query Recipes

 Reusable query patterns for the portfolio environment. Replace `?` placeholders with values from the task prompt.

 ## Portfolio mix — closed work items by scope

 ```sql
 SELECT id, title, team, portfolio_category, category, status,
        closed_at, mirror_of, duplicate_of
 FROM work_items
 WHERE team IN (?, ?)
   AND closed_at BETWEEN ? AND ?
   AND (mirror_of IS NULL OR mirror_of = '')
   AND (duplicate_of IS NULL OR duplicate_of = '')
   AND status != 'Cancelled'
   AND portfolio_category IN ('NewFeature', 'TechDebt', 'Reliability', 'Security')
 ORDER BY closed_at ASC, id ASC
 ```

 ## Portfolio mix — find excluded duplicates and cancelled

 ```sql
 SELECT id, status, duplicate_of, mirror_of
 FROM work_items
 WHERE team IN (?, ?)
   AND closed_at BETWEEN ? AND ?
   AND (
     status = 'Cancelled'
     OR duplicate_of IS NOT NULL
     OR mirror_of IS NOT NULL
   )
 ORDER BY closed_at ASC, id ASC
 ```

 ## SLA aging — primary in-scope items

 ```sql
 SELECT id, title, team, owner, category, portfolio_category,
        severity, sla_target_date, status, closed_at,
        duplicate_of, mirror_of
 FROM work_items
 WHERE team IN (?, ?)
   AND portfolio_category IN ('Reliability', 'Security')
   AND (mirror_of IS NULL OR mirror_of = '')
   AND (duplicate_of IS NULL OR duplicate_of = '')
   AND status != 'Cancelled'
 ORDER BY id ASC
 ```

 ## SLA aging — duplicate clusters

 ```sql
 SELECT id, duplicate_of, mirror_of
 FROM work_items
 WHERE team IN (?, ?)
   AND portfolio_category IN ('Reliability', 'Security')
   AND (duplicate_of IS NOT NULL OR mirror_of IS NOT NULL)
 ORDER BY id ASC
 ```

 ## Release readiness — work items by release

 ```sql
 SELECT wi.id, wi.title, wi.status, wi.milestone_id,
        wi.duplicate_of, wi.mirror_of, wi.owner
 FROM work_items wi
 JOIN milestones m ON wi.milestone_id = m.milestone_id
 WHERE m.release_id = ?
   AND (wi.mirror_of IS NULL OR wi.mirror_of = '')
   AND (wi.duplicate_of IS NULL OR wi.duplicate_of = '')
   AND wi.status != 'Cancelled'
 ORDER BY wi.id ASC
 ```

 ## Work items by product area

 ```sql
 SELECT id, title, team, product_area, portfolio_category, status, closed_at
 FROM work_items
 WHERE product_area = ?
   AND closed_at BETWEEN ? AND ?
 ORDER BY closed_at ASC, id ASC
 ```

 ## General tips

 - Always parameterize values; never concatenate user input into SQL.
 - Use `LIMIT` during exploration, then remove for final queries.
 - If a field name is uncertain, fetch a single item by ID and inspect the JSON keys.
 - The query endpoint returns at most 1000 rows.
