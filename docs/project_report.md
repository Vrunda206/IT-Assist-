# IT Assist – Inventory Management System
**Subject:** DBMS  |  **Corporate relevance:** IT Infrastructure  |  **AI & DS integration:** Asset Usage Analytics

## 1. Project Introduction
IT Assist is a web-based system that lets an organization record and track its IT assets (laptops, desktops, monitors, mobiles, printers, servers, network devices), the employees who use them, maintenance work, and how heavily each asset is used. MySQL stores the data; Flask serves the web interface.

## 2. Problem Statement
Many organizations track IT equipment in scattered spreadsheets. This causes lost assets, unclear ownership, missed warranty dates, and no view of which devices are under-used or failing. A relational database with a simple interface solves these problems.

## 3. Objectives
* Store all asset, employee, department, vendor, assignment, maintenance and usage data in a normalized MySQL database.
* Provide CRUD, search, filters, assignment / return workflow and reports.
* Show live dashboard statistics and usage analytics.
* Demonstrate DBMS concepts: keys, constraints, joins, aggregates, subqueries, views, transactions, normalization.

## 4. Corporate Relevance
IT infrastructure is a costly and critical resource. Knowing who holds each asset, when warranty ends, how much is spent on repairs and which assets are idle supports budgeting, audit, and replacement planning.

## 5. AI & Data Science Integration – Asset Usage Analytics
Python **pandas** reads aggregated usage data from MySQL and computes, per asset:
* Utilization rate = (average daily usage hours ÷ 8 expected hours) × 100 (capped at 100)
* Category: Low ≤ 40 %, Normal 41–75 %, High > 75 %
* Average performance score and total downtime
The results feed the dashboard, the Usage Analytics page, asset details and the usage report. No machine-learning models are used; the analytics are simple descriptive statistics.

## 6. Technology Stack
HTML, CSS, JavaScript, Bootstrap 5 · Python 3, Flask · MySQL 8 (mysql-connector-python) · pandas · Chart.js.

## 7. System Architecture
Browser → Flask routes (`app.py`) → MySQL (`it_assist`). Flask renders Jinja2 templates; pandas performs the analytics step; Chart.js draws charts from JSON produced by the queries. Three layers: presentation (templates/static), application logic (Flask), data (MySQL).

## 8. ER Diagram
See `docs/er_diagram.md` (Mermaid source).

## 9. Relational Schema
departments(**department_id**, department_name, location)
employees(**employee_id**, employee_name, email, phone, *department_id*, designation, joining_date, status)
asset_categories(**category_id**, category_name, description)
vendors(**vendor_id**, vendor_name, contact_person, phone, email)
assets(**asset_id**, asset_tag, asset_name, *category_id*, *vendor_id*, brand, model, serial_number, purchase_date, purchase_cost, warranty_expiry, status, location, created_at)
asset_assignments(**assignment_id**, *asset_id*, *employee_id*, assigned_date, returned_date, assignment_status, remarks)
maintenance(**maintenance_id**, *asset_id*, issue, maintenance_date, cost, status, remarks)
asset_usage(**usage_id**, *asset_id*, usage_date, usage_hours, performance_score, downtime_hours)
(bold = primary key, italic = foreign key)

## 10. Normalization
The schema is in 3NF – details in `docs/normalization.md`.

## 11. Database Tables
Eight tables (above). Sample data: 4 departments, 16 employees, 7 categories, 5 vendors, 32 assets, 24 assignments, 16 maintenance records, 64 usage records (fictional).

## 12. SQL Queries
See `database/queries.sql` and `docs/sql_queries.md`.

## 13. Asset Usage Analytics
See section 5. Screens: Dashboard (usage chart, most-used assets, averages), Usage Analytics (per-asset table with filter, most/least used, average utilization by category, add usage record), Asset Details (per-asset summary).

## 14. Screenshots
Insert screenshots of: Login · Dashboard · Assets list · Asset details · Employees · Departments · Assignments · Maintenance · Usage Analytics · Reports · MySQL Workbench with tables.

## 15. Conclusion
The project shows how a well-designed relational database, SQL and a simple web layer can manage corporate IT infrastructure. Constraints and transactions keep data consistent, and basic analytics give useful information on asset usage.

## 16. Future Scope
* Role-based login (admin / employee), password hashing
* Email alerts for warranty expiry and long maintenance
* Barcode / QR scanning for assets
* Predictive maintenance using machine learning on usage history
* Purchase-order and depreciation tracking
