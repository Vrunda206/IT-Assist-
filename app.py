"""IT Assist - Inventory Management System (Flask + MySQL + pandas)."""
import os
from datetime import date

import mysql.connector
import pandas as pd
from flask import (Flask, Response, flash, redirect, render_template,
                   request, session, url_for)
from mysql.connector import Error, IntegrityError

from config import Config

app = Flask(__name__)
app.secret_key = Config.SECRET_KEY
EXPECTED = Config.EXPECTED_HOURS

STATUSES = ["Available", "Assigned", "Under Maintenance", "Retired"]
MAINT_STATUSES = ["Pending", "In Progress", "Completed"]
USAGE_CLASSES = ["Low Usage", "Normal Usage", "High Usage"]


# ---------------------------------------------------------------- DB helpers
def get_conn():
    return mysql.connector.connect(**Config.DB)


def query(sql, params=None, one=False):
    """Run a SELECT and return a list of dicts (or one dict)."""
    conn = get_conn()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, params or ())
        rows = cur.fetchall()
        if one:
            return rows[0] if rows else None
        return rows
    finally:
        conn.close()


def execute(sql, params=None):
    """Run one INSERT/UPDATE/DELETE and commit."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(sql, params or ())
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def transaction(steps):
    """Run several statements as ONE transaction: all succeed or all roll back."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        for sql, params in steps:
            cur.execute(sql, params)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def nz(value):
    """Empty form field -> None (NULL in MySQL)."""
    value = (value or "").strip()
    return value or None


def pack(rows):
    return {"labels": [r["label"] for r in rows], "values": [int(r["value"]) for r in rows]}


@app.template_filter("money")
def money(v):
    return "₹{:,.0f}".format(float(v or 0))


# ---------------------------------------------------------- auth / errors
@app.before_request
def require_login():
    if request.endpoint in ("login", "static") or session.get("user"):
        return None
    return redirect(url_for("login"))


@app.errorhandler(Error)
def db_error(e):
    errno = getattr(e, "errno", None)
    if errno in (1451, 1217):
        msg = "Cannot delete: this record is used by other records (referential integrity)."
    elif errno == 1062:
        msg = "Duplicate value: a record with the same unique value already exists."
    elif errno in (3819, 4025):
        msg = "Invalid value: it breaks a CHECK constraint."
    else:
        msg = f"Database error: {getattr(e, 'msg', e)}"
    if request.method == "GET":
        return (f"<h3>Database error</h3><p>{msg}</p>"
                "<p>Check your .env file and make sure schema.sql and seed.sql were run.</p>"), 500
    flash(msg, "danger")
    return redirect(request.referrer or url_for("dashboard"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if (request.form["username"] == Config.ADMIN_USER
                and request.form["password"] == Config.ADMIN_PASS):
            session["user"] = Config.ADMIN_USER
            return redirect(url_for("dashboard"))
        flash("Invalid username or password.", "danger")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ------------------------------------------------------ usage analytics (pandas)
def usage_class(util):
    if util <= 40:
        return "Low Usage"
    if util <= 75:
        return "Normal Usage"
    return "High Usage"


def usage_df():
    """One row per asset that has usage data, with utilization + category."""
    cols = ["asset_id", "asset_tag", "asset_name", "category", "status",
            "records", "avg_hours", "avg_perf", "downtime"]
    rows = query("""
        SELECT a.asset_id, a.asset_tag, a.asset_name, c.category_name AS category, a.status,
               COUNT(u.usage_id) AS records, AVG(u.usage_hours) AS avg_hours,
               AVG(u.performance_score) AS avg_perf, SUM(u.downtime_hours) AS downtime
        FROM assets a
        JOIN asset_categories c ON c.category_id = a.category_id
        JOIN asset_usage u ON u.asset_id = a.asset_id
        GROUP BY a.asset_id, a.asset_tag, a.asset_name, c.category_name, a.status""")
    df = pd.DataFrame(rows, columns=cols)
    for c in ("avg_hours", "avg_perf", "downtime"):
        df[c] = pd.to_numeric(df[c]).astype(float)
    # utilization_rate = (usage_hours / expected_hours) x 100, capped at 100
    df["utilization"] = (df["avg_hours"] / EXPECTED * 100).clip(upper=100).round(1)
    df["usage_category"] = df["utilization"].apply(usage_class)
    df["avg_hours"] = df["avg_hours"].round(2)
    df["avg_perf"] = df["avg_perf"].round(1)
    df["downtime"] = df["downtime"].round(1)
    return df


def usage_stats(df):
    if df.empty:
        return {"avg_util": 0, "avg_perf": 0, "downtime": 0, "avg_hours": 0}
    return {"avg_util": round(float(df.utilization.mean()), 1),
            "avg_perf": round(float(df.avg_perf.mean()), 1),
            "downtime": round(float(df.downtime.sum()), 1),
            "avg_hours": round(float(df.avg_hours.mean()), 2)}


# ------------------------------------------------------------------ dashboard
@app.route("/")
def dashboard():
    cards = query("""SELECT
        (SELECT COUNT(*) FROM assets) AS total,
        (SELECT COUNT(*) FROM assets WHERE status='Available') AS available,
        (SELECT COUNT(*) FROM assets WHERE status='Assigned') AS assigned,
        (SELECT COUNT(*) FROM assets WHERE status='Under Maintenance') AS maintenance,
        (SELECT COUNT(*) FROM employees) AS employees,
        (SELECT COALESCE(SUM(purchase_cost),0) FROM assets) AS value""", one=True)
    by_cat = query("""SELECT c.category_name AS label, COUNT(a.asset_id) AS value
        FROM asset_categories c LEFT JOIN assets a ON a.category_id = c.category_id
        GROUP BY c.category_id, c.category_name ORDER BY c.category_id""")
    by_status = query("SELECT status AS label, COUNT(*) AS value FROM assets GROUP BY status")
    by_dept = query("""SELECT d.department_name AS label, COUNT(aa.asset_id) AS value
        FROM departments d
        LEFT JOIN employees e ON e.department_id = d.department_id
        LEFT JOIN asset_assignments aa ON aa.employee_id = e.employee_id
                                      AND aa.assignment_status = 'Active'
        GROUP BY d.department_id, d.department_name""")
    df = usage_df()
    counts = df.usage_category.value_counts()
    usage_chart = {"labels": USAGE_CLASSES, "values": [int(counts.get(k, 0)) for k in USAGE_CLASSES]}
    expiring = query("""SELECT asset_id, asset_tag, asset_name, warranty_expiry,
        DATEDIFF(warranty_expiry, CURDATE()) AS days_left FROM assets
        WHERE warranty_expiry BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 90 DAY)
        ORDER BY warranty_expiry LIMIT 6""")
    charts = {"cat": pack(by_cat), "status": pack(by_status), "dept": pack(by_dept), "usage": usage_chart}
    return render_template("dashboard.html", cards=cards, charts=charts, stats=usage_stats(df),
                           top=df.nlargest(5, "utilization").to_dict("records"), expiring=expiring)


# --------------------------------------------------------------------- assets
def categories():
    return query("SELECT * FROM asset_categories ORDER BY category_name")


def vendors():
    return query("SELECT * FROM vendors ORDER BY vendor_name")


@app.route("/assets")
def assets():
    q = request.args.get("q", "").strip()
    cat = request.args.get("category", "")
    status = request.args.get("status", "")
    sql = """SELECT a.*, c.category_name, e.employee_name
        FROM assets a
        JOIN asset_categories c ON c.category_id = a.category_id
        LEFT JOIN asset_assignments aa ON aa.asset_id = a.asset_id AND aa.assignment_status = 'Active'
        LEFT JOIN employees e ON e.employee_id = aa.employee_id
        WHERE 1=1"""
    p = []
    if q:
        sql += " AND (a.asset_tag LIKE %s OR a.asset_name LIKE %s OR a.serial_number LIKE %s)"
        p += [f"%{q}%"] * 3
    if cat:
        sql += " AND a.category_id = %s"
        p.append(cat)
    if status:
        sql += " AND a.status = %s"
        p.append(status)
    sql += " ORDER BY a.asset_id"
    return render_template("assets.html", assets=query(sql, p), categories=categories(),
                           statuses=STATUSES, q=q, cat=cat, status=status)


def asset_values(f):
    return (f["asset_tag"].strip(), f["asset_name"].strip(), f["category_id"], nz(f.get("vendor_id")),
            nz(f.get("brand")), nz(f.get("model")), f["serial_number"].strip(), f["purchase_date"],
            f["purchase_cost"], nz(f.get("warranty_expiry")), f["status"], nz(f.get("location")))


@app.route("/assets/add", methods=["GET", "POST"])
def asset_add():
    if request.method == "POST":
        execute("""INSERT INTO assets (asset_tag, asset_name, category_id, vendor_id, brand, model,
                   serial_number, purchase_date, purchase_cost, warranty_expiry, status, location)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""", asset_values(request.form))
        flash("Asset added successfully.", "success")
        return redirect(url_for("assets"))
    return render_template("asset_form.html", asset={}, categories=categories(),
                           vendors=vendors(), statuses=STATUSES)


@app.route("/assets/<int:aid>/edit", methods=["GET", "POST"])
def asset_edit(aid):
    if request.method == "POST":
        execute("""UPDATE assets SET asset_tag=%s, asset_name=%s, category_id=%s, vendor_id=%s, brand=%s,
                   model=%s, serial_number=%s, purchase_date=%s, purchase_cost=%s, warranty_expiry=%s,
                   status=%s, location=%s WHERE asset_id=%s""", asset_values(request.form) + (aid,))
        flash("Asset updated successfully.", "success")
        return redirect(url_for("assets"))
    asset = query("SELECT * FROM assets WHERE asset_id=%s", (aid,), one=True)
    if not asset:
        flash("Asset not found.", "danger")
        return redirect(url_for("assets"))
    return render_template("asset_form.html", asset=asset, categories=categories(),
                           vendors=vendors(), statuses=STATUSES)


@app.post("/assets/<int:aid>/delete")
def asset_delete(aid):
    execute("DELETE FROM assets WHERE asset_id=%s", (aid,))
    flash("Asset deleted successfully.", "success")
    return redirect(url_for("assets"))


@app.route("/assets/<int:aid>")
def asset_details(aid):
    a = query("""SELECT a.*, c.category_name, v.vendor_name FROM assets a
        JOIN asset_categories c ON c.category_id = a.category_id
        LEFT JOIN vendors v ON v.vendor_id = a.vendor_id WHERE a.asset_id=%s""", (aid,), one=True)
    if not a:
        flash("Asset not found.", "danger")
        return redirect(url_for("assets"))
    current = query("""SELECT e.employee_id, e.employee_name, d.department_name, aa.assigned_date
        FROM asset_assignments aa JOIN employees e ON e.employee_id = aa.employee_id
        JOIN departments d ON d.department_id = e.department_id
        WHERE aa.asset_id=%s AND aa.assignment_status='Active'""", (aid,), one=True)
    history = query("""SELECT aa.*, e.employee_name FROM asset_assignments aa
        JOIN employees e ON e.employee_id = aa.employee_id
        WHERE aa.asset_id=%s ORDER BY aa.assigned_date DESC""", (aid,))
    maint = query("SELECT * FROM maintenance WHERE asset_id=%s ORDER BY maintenance_date DESC", (aid,))
    usage = query("SELECT * FROM asset_usage WHERE asset_id=%s ORDER BY usage_date DESC LIMIT 10", (aid,))
    df = usage_df()
    row = df[df.asset_id == aid]
    summary = row.iloc[0].to_dict() if not row.empty else None
    days_left, w_state = None, None
    if a["warranty_expiry"]:
        days_left = (a["warranty_expiry"] - date.today()).days
        w_state = "Expired" if days_left < 0 else ("Expiring Soon" if days_left <= 90 else "Valid")
    return render_template("asset_details.html", a=a, current=current, history=history, maint=maint,
                           usage=usage, summary=summary, days_left=days_left, w_state=w_state)


# ------------------------------------------------------------------ employees
def departments_list():
    return query("SELECT * FROM departments ORDER BY department_name")


@app.route("/employees")
def employees():
    q = request.args.get("q", "").strip()
    dept = request.args.get("department", "")
    sql = """SELECT e.*, d.department_name,
        (SELECT COUNT(*) FROM asset_assignments aa
          WHERE aa.employee_id = e.employee_id AND aa.assignment_status='Active') AS active_assets
        FROM employees e JOIN departments d ON d.department_id = e.department_id WHERE 1=1"""
    p = []
    if q:
        sql += " AND e.employee_name LIKE %s"
        p.append(f"%{q}%")
    if dept:
        sql += " AND e.department_id = %s"
        p.append(dept)
    sql += " ORDER BY e.employee_id"
    return render_template("employees.html", employees=query(sql, p), departments=departments_list(), q=q, dept=dept)


@app.post("/employees/save")
def employee_save():
    f = request.form
    eid = f.get("employee_id")
    vals = (f["employee_name"].strip(), f["email"].strip(), nz(f.get("phone")), f["department_id"],
            nz(f.get("designation")), f["joining_date"], f["status"])
    if eid:
        execute("""UPDATE employees SET employee_name=%s, email=%s, phone=%s, department_id=%s,
                   designation=%s, joining_date=%s, status=%s WHERE employee_id=%s""", vals + (eid,))
        flash("Employee updated successfully.", "success")
    else:
        execute("""INSERT INTO employees (employee_name, email, phone, department_id, designation,
                   joining_date, status) VALUES (%s,%s,%s,%s,%s,%s,%s)""", vals)
        flash("Employee added successfully.", "success")
    return redirect(url_for("employees"))


@app.post("/employees/<int:eid>/delete")
def employee_delete(eid):
    execute("DELETE FROM employees WHERE employee_id=%s", (eid,))
    flash("Employee deleted successfully.", "success")
    return redirect(url_for("employees"))


@app.route("/employees/<int:eid>")
def employee_assets(eid):
    emp = query("""SELECT e.*, d.department_name FROM employees e
        JOIN departments d ON d.department_id = e.department_id WHERE e.employee_id=%s""", (eid,), one=True)
    if not emp:
        flash("Employee not found.", "danger")
        return redirect(url_for("employees"))
    rows = query("""SELECT aa.*, a.asset_id, a.asset_tag, a.asset_name, c.category_name
        FROM asset_assignments aa JOIN assets a ON a.asset_id = aa.asset_id
        JOIN asset_categories c ON c.category_id = a.category_id
        WHERE aa.employee_id=%s ORDER BY aa.assigned_date DESC""", (eid,))
    return render_template("employee_assets.html", emp=emp, rows=rows)


# ---------------------------------------------------------------- departments
@app.route("/departments")
def departments():
    rows = query("""SELECT d.*, COUNT(DISTINCT e.employee_id) AS employees,
        COUNT(DISTINCT aa.asset_id) AS assets, COALESCE(SUM(a.purchase_cost),0) AS asset_value
        FROM departments d
        LEFT JOIN employees e ON e.department_id = d.department_id
        LEFT JOIN asset_assignments aa ON aa.employee_id = e.employee_id AND aa.assignment_status='Active'
        LEFT JOIN assets a ON a.asset_id = aa.asset_id
        GROUP BY d.department_id, d.department_name, d.location ORDER BY d.department_id""")
    return render_template("departments.html", rows=rows)


@app.post("/departments/add")
def department_add():
    execute("INSERT INTO departments (department_name, location) VALUES (%s,%s)",
            (request.form["department_name"].strip(), nz(request.form.get("location"))))
    flash("Department added successfully.", "success")
    return redirect(url_for("departments"))


@app.post("/departments/<int:did>/delete")
def department_delete(did):
    execute("DELETE FROM departments WHERE department_id=%s", (did,))
    flash("Department deleted successfully.", "success")
    return redirect(url_for("departments"))


# ---------------------------------------------------------------- assignments
@app.route("/assignments")
def assignments():
    status = request.args.get("status", "")
    sql = """SELECT aa.*, a.asset_tag, a.asset_name, e.employee_name, d.department_name
        FROM asset_assignments aa JOIN assets a ON a.asset_id = aa.asset_id
        JOIN employees e ON e.employee_id = aa.employee_id
        JOIN departments d ON d.department_id = e.department_id"""
    p = []
    if status:
        sql += " WHERE aa.assignment_status = %s"
        p.append(status)
    sql += " ORDER BY aa.assignment_id DESC"
    return render_template("assignments.html", rows=query(sql, p), status=status,
                           free_assets=query("SELECT asset_id, asset_tag, asset_name FROM assets WHERE status='Available' ORDER BY asset_tag"),
                           active_emps=query("SELECT employee_id, employee_name FROM employees WHERE status='Active' ORDER BY employee_name"))


@app.post("/assignments/assign")
def assign_asset():
    aid, eid = request.form["asset_id"], request.form["employee_id"]
    asset = query("SELECT status FROM assets WHERE asset_id=%s", (aid,), one=True)
    if not asset or asset["status"] != "Available":
        flash("Only assets with status 'Available' can be assigned.", "danger")
        return redirect(url_for("assignments"))
    transaction([
        ("""INSERT INTO asset_assignments (asset_id, employee_id, assigned_date, assignment_status, remarks)
            VALUES (%s,%s,CURDATE(),'Active',%s)""", (aid, eid, nz(request.form.get("remarks")))),
        ("UPDATE assets SET status='Assigned' WHERE asset_id=%s", (aid,)),
    ])
    flash("Assignment successful.", "success")
    return redirect(url_for("assignments"))


@app.post("/assignments/<int:asid>/return")
def return_asset(asid):
    row = query("SELECT asset_id FROM asset_assignments WHERE assignment_id=%s AND assignment_status='Active'",
                (asid,), one=True)
    if not row:
        flash("This assignment is already returned.", "danger")
        return redirect(url_for("assignments"))
    transaction([
        ("UPDATE asset_assignments SET returned_date=CURDATE(), assignment_status='Returned' WHERE assignment_id=%s", (asid,)),
        ("UPDATE assets SET status='Available' WHERE asset_id=%s AND status='Assigned'", (row["asset_id"],)),
    ])
    flash("Asset returned successfully.", "success")
    return redirect(url_for("assignments"))


# ---------------------------------------------------------------- maintenance
@app.route("/maintenance")
def maintenance():
    status = request.args.get("status", "")
    sql = """SELECT m.*, a.asset_tag, a.asset_name FROM maintenance m
             JOIN assets a ON a.asset_id = m.asset_id"""
    p = []
    if status:
        sql += " WHERE m.status = %s"
        p.append(status)
    sql += " ORDER BY m.maintenance_date DESC, m.maintenance_id DESC"
    total = query("SELECT COALESCE(SUM(cost),0) AS total FROM maintenance", one=True)["total"]
    return render_template("maintenance.html", rows=query(sql, p), status=status, statuses=MAINT_STATUSES,
                           total=total, today=date.today().isoformat(),
                           asset_list=query("SELECT asset_id, asset_tag, asset_name FROM assets WHERE status <> 'Retired' ORDER BY asset_tag"))


@app.post("/maintenance/add")
def maintenance_add():
    f = request.form
    steps = [("""INSERT INTO maintenance (asset_id, issue, maintenance_date, cost, status, remarks)
                 VALUES (%s,%s,%s,%s,%s,%s)""",
              (f["asset_id"], f["issue"].strip(), f["maintenance_date"], f.get("cost") or 0,
               f["status"], nz(f.get("remarks"))))]
    if f["status"] != "Completed":
        steps.append(("UPDATE assets SET status='Under Maintenance' WHERE asset_id=%s AND status='Available'",
                      (f["asset_id"],)))
    transaction(steps)
    flash("Maintenance record added successfully.", "success")
    return redirect(url_for("maintenance"))


@app.post("/maintenance/<int:mid>/status")
def maintenance_status(mid):
    st = request.form["status"]
    row = query("SELECT asset_id FROM maintenance WHERE maintenance_id=%s", (mid,), one=True)
    aid = row["asset_id"]
    steps = [("UPDATE maintenance SET status=%s WHERE maintenance_id=%s", (st, mid))]
    if st == "Completed":   # back to Available if nothing else is still open
        steps.append(("""UPDATE assets SET status='Available' WHERE asset_id=%s AND status='Under Maintenance'
                         AND NOT EXISTS (SELECT 1 FROM maintenance WHERE asset_id=%s AND status <> 'Completed')""",
                      (aid, aid)))
    else:
        steps.append(("UPDATE assets SET status='Under Maintenance' WHERE asset_id=%s AND status='Available'", (aid,)))
    transaction(steps)
    flash("Maintenance status updated successfully.", "success")
    return redirect(url_for("maintenance"))


# ------------------------------------------------------------ usage analytics
@app.route("/analytics")
def analytics():
    cat = request.args.get("category", "")
    df = usage_df()
    view = df[df.usage_category == cat] if cat else df
    by_cat = df.groupby("category")["utilization"].mean().round(1)
    chart = {"labels": list(by_cat.index), "values": [float(v) for v in by_cat.values]}
    recent = query("""SELECT u.*, a.asset_tag, a.asset_name FROM asset_usage u
        JOIN assets a ON a.asset_id = u.asset_id ORDER BY u.usage_date DESC, u.usage_id DESC LIMIT 10""")
    return render_template("analytics.html", rows=view.sort_values("utilization", ascending=False).to_dict("records"),
                           most=df.nlargest(5, "utilization").to_dict("records"),
                           least=df.nsmallest(5, "utilization").to_dict("records"),
                           stats=usage_stats(df), chart=chart, recent=recent, cat=cat, classes=USAGE_CLASSES,
                           today=date.today().isoformat(),
                           asset_list=query("SELECT asset_id, asset_tag, asset_name FROM assets WHERE status <> 'Retired' ORDER BY asset_tag"))


@app.post("/usage/add")
def usage_add():
    f = request.form
    execute("""INSERT INTO asset_usage (asset_id, usage_date, usage_hours, performance_score, downtime_hours)
               VALUES (%s,%s,%s,%s,%s)""",
            (f["asset_id"], f["usage_date"], f["usage_hours"], f["performance_score"], f.get("downtime_hours") or 0))
    flash("Usage record added successfully.", "success")
    return redirect(url_for("analytics"))


# -------------------------------------------------------------------- reports
REPORTS = {
    "inventory": ("Asset Inventory Report", """SELECT a.asset_tag AS `Asset Tag`, a.asset_name AS `Asset`,
        c.category_name AS `Category`, a.brand AS `Brand`, a.status AS `Status`,
        a.purchase_cost AS `Purchase Cost`, a.warranty_expiry AS `Warranty Expiry`
        FROM assets a JOIN asset_categories c ON c.category_id = a.category_id ORDER BY a.asset_id"""),
    "assignments": ("Assigned Asset Report", """SELECT e.employee_name AS `Employee`, a.asset_tag AS `Asset Tag`,
        a.asset_name AS `Asset`, aa.assigned_date AS `Assigned Date`, aa.returned_date AS `Returned Date`,
        aa.assignment_status AS `Status`
        FROM asset_assignments aa JOIN employees e ON e.employee_id = aa.employee_id
        JOIN assets a ON a.asset_id = aa.asset_id ORDER BY aa.assigned_date DESC"""),
    "maintenance": ("Maintenance Report", """SELECT a.asset_tag AS `Asset Tag`, a.asset_name AS `Asset`,
        m.issue AS `Issue`, m.maintenance_date AS `Date`, m.cost AS `Cost`, m.status AS `Status`
        FROM maintenance m JOIN assets a ON a.asset_id = m.asset_id ORDER BY m.maintenance_date DESC"""),
    "warranty": ("Warranty Report", """SELECT a.asset_tag AS `Asset Tag`, a.asset_name AS `Asset`,
        c.category_name AS `Category`, a.warranty_expiry AS `Warranty Expiry`,
        DATEDIFF(a.warranty_expiry, CURDATE()) AS `Days Left`,
        CASE WHEN a.warranty_expiry < CURDATE() THEN 'Expired'
             WHEN a.warranty_expiry <= DATE_ADD(CURDATE(), INTERVAL 90 DAY) THEN 'Expiring Soon'
             ELSE 'Valid' END AS `Warranty Status`
        FROM assets a JOIN asset_categories c ON c.category_id = a.category_id
        WHERE a.warranty_expiry IS NOT NULL ORDER BY a.warranty_expiry"""),
    "usage": ("Usage Report", None),
}


def report_df(kind):
    if kind == "usage":
        df = usage_df()[["asset_tag", "asset_name", "category", "avg_hours", "utilization",
                         "avg_perf", "downtime", "usage_category"]].sort_values("utilization", ascending=False)
        return df.rename(columns={"asset_tag": "Asset Tag", "asset_name": "Asset", "category": "Category",
                                  "avg_hours": "Avg Usage Hours", "utilization": "Utilization %",
                                  "avg_perf": "Performance", "downtime": "Downtime (h)",
                                  "usage_category": "Usage Category"})
    return pd.DataFrame(query(REPORTS[kind][1]))


@app.route("/reports")
def reports():
    kind = request.args.get("type", "inventory")
    if kind not in REPORTS:
        kind = "inventory"
    df = report_df(kind)
    df = df.astype(object).where(df.notna(), None)
    return render_template("reports.html", kind=kind, reports=REPORTS, title=REPORTS[kind][0],
                           cols=list(df.columns), rows=df.to_dict("records"))


@app.route("/reports/<kind>/csv")
def report_csv(kind):
    if kind not in REPORTS:
        return redirect(url_for("reports"))
    return Response(report_df(kind).to_csv(index=False), mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment; filename={kind}_report.csv"})


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", 5000)),
        debug=False
    )