# Normalization – IT Assist

## Keys
| Table | Primary key | Candidate keys | Foreign keys |
|---|---|---|---|
| departments | department_id | department_name | – |
| employees | employee_id | email | department_id |
| asset_categories | category_id | category_name | – |
| vendors | vendor_id | – | – |
| assets | asset_id | asset_tag, serial_number | category_id, vendor_id |
| asset_assignments | assignment_id | – | asset_id, employee_id |
| maintenance | maintenance_id | – | asset_id |
| asset_usage | usage_id | (asset_id, usage_date) in practice | asset_id |

## Functional dependencies
* department_id → department_name, location
* employee_id → employee_name, email, phone, department_id, designation, joining_date, status  (email → employee_id)
* category_id → category_name, description
* vendor_id → vendor_name, contact_person, phone, email
* asset_id → asset_tag, asset_name, category_id, vendor_id, brand, model, serial_number, purchase_date, purchase_cost, warranty_expiry, status, location  (asset_tag → asset_id, serial_number → asset_id)
* assignment_id → asset_id, employee_id, assigned_date, returned_date, assignment_status, remarks
* maintenance_id → asset_id, issue, maintenance_date, cost, status, remarks
* usage_id → asset_id, usage_date, usage_hours, performance_score, downtime_hours

## 1NF
Every column holds one atomic value (no lists such as "laptop, mouse" in one cell), every row is uniquely identified by a primary key, and there are no repeating groups. Example: an employee's many assets are rows in `asset_assignments`, not columns `asset1, asset2, …`.

## 2NF
The design is in 1NF and every table has a single-column primary key, so no non-key attribute can depend on only part of a key. Hence there are no partial dependencies.

## 3NF
No non-key attribute depends on another non-key attribute (no transitive dependency).
* Department name/location are stored once in `departments`; `employees` holds only `department_id` (otherwise employee_id → department_id → location would be transitive).
* Category name and vendor details are stored once in `asset_categories` and `vendors`.
* Employee name is not copied into `asset_assignments`; the join gives it.
Derived values (utilization %, usage category, days left in warranty) are **calculated in queries**, not stored.

## Why separate tables?
* Removes redundancy (a department is written once, not for every employee).
* Prevents update, insert and delete anomalies (renaming a department is one UPDATE).
* Lets us enforce rules with keys and constraints.

## Why is assignment a separate table?
An employee can hold many assets and an asset can be held by many employees **over time** (many-to-many). The pair also has its own attributes – assigned_date, returned_date, status, remarks – that belong to neither the employee nor the asset. A separate junction table therefore keeps the full **history** and avoids NULL-filled columns in `assets` or `employees`.
