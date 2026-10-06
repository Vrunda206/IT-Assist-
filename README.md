# IT Assist – Inventory Management System

DBMS academic project: manage IT assets, employees, assignments, maintenance and asset-usage analytics.
**Stack:** Python Flask · MySQL · pandas · Bootstrap · Chart.js

## Quick start (easiest)
Install Python and MySQL, then **double-click `run.bat`** (Windows) or run `sh run.sh` (Mac/Linux).
It installs the packages, asks for your MySQL password once, creates the database, loads the sample data and opens the app.
Login: `admin` / `admin123`. The manual steps below are only needed if you prefer them.

## Requirements
* Python 3.9+
* MySQL 8.0.16+ (needed for CHECK constraints) and MySQL Workbench (optional)
* A web browser (internet needed once for Bootstrap / Chart.js CDN files)

## Installation
```
cd IT-Assist
pip install -r requirements.txt
```
Copy `.env.example` to `.env` and put your MySQL password in it:
```
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_mysql_password_here
DB_NAME=it_assist
```

## Database setup
1. Open **MySQL Workbench** and connect to your local server.
2. Open `database/schema.sql` → click the lightning ⚡ button (it creates the database `it_assist`, all tables, constraints and views).
3. Open `database/seed.sql` → run it (loads the sample data).

Command-line alternative:
```
mysql -u root -p < database/schema.sql
mysql -u root -p < database/seed.sql
```
`database/queries.sql` contains all demo queries for the viva (joins, GROUP BY, subqueries, views…).

## Run the application
```
python app.py
```
Open **http://127.0.0.1:5000**

**Demo login (academic demo only):** username `admin` · password `admin123`

## Troubleshooting
* *Can't connect to MySQL* → check `.env` (password) and that MySQL is running. If `localhost` fails try `DB_HOST=127.0.0.1`.
* *Unknown database / table doesn't exist* → run `schema.sql` then `seed.sql`.
* *CHECK constraint ignored / syntax error* → upgrade to MySQL 8.0.16 or newer.

## Project structure
```
app.py            Flask routes + SQL + pandas analytics
config.py         DB settings (read from .env)
database/         schema.sql, seed.sql, queries.sql
templates/        HTML pages (Jinja2)
static/           css/style.css, js/script.js
docs/             er_diagram.md, normalization.md, sql_queries.md, project_report.md
```

## Viva demo flow (5–10 min)
1. Show ER diagram (`docs/er_diagram.md`) and `schema.sql` (PK, FK, UNIQUE, CHECK).
2. Dashboard → numbers and charts come live from MySQL.
3. Assign an asset to an employee, then return it (see status change + history).
4. Add a maintenance record → asset becomes *Under Maintenance*; mark Completed → *Available*.
5. Usage Analytics → utilization = hours ÷ 8 × 100, Low/Normal/High.
6. Run a few queries from `queries.sql` in Workbench (JOIN, GROUP BY/HAVING, subquery, view).
7. Try deleting an employee who has assignments → foreign key blocks it.
