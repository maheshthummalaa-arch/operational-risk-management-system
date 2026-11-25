"""Operational Risk Management System - simple base project (Flask + SQLite)."""
import os
import sqlite3
from datetime import date

from flask import Flask, g, redirect, render_template, request, url_for, flash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "orms.db")

CATEGORIES = ["Process", "People", "Systems", "External"]
STATUSES = ["Open", "Mitigating", "Closed"]
EFFECTIVENESS = ["Low", "Medium", "High"]
SEVERITIES = ["Low", "Medium", "High", "Critical"]

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-me-in-production")


# ---------- database helpers ----------
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(with_sample_data=True):
    db = sqlite3.connect(DATABASE)
    with open(os.path.join(BASE_DIR, "schema.sql")) as f:
        db.executescript(f.read())
    if with_sample_data:
        db.executemany(
            "INSERT INTO risks (title, description, category, owner, likelihood, impact, status) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                ("Payment processing outage", "Core payment system downtime", "Systems", "IT Ops", 3, 5, "Mitigating"),
                ("Manual data entry errors", "Errors in manual reconciliation", "Process", "Finance", 4, 3, "Open"),
                ("Key staff attrition", "Loss of critical knowledge holders", "People", "HR", 3, 3, "Open"),
                ("Third-party vendor failure", "Critical supplier becomes insolvent", "External", "Procurement", 2, 4, "Open"),
                ("Phishing attack", "Credential theft via email", "Systems", "Security", 4, 4, "Mitigating"),
            ],
        )
        db.executemany(
            "INSERT INTO controls (risk_id, name, effectiveness) VALUES (?, ?, ?)",
            [(1, "Redundant failover cluster", "High"), (2, "Four-eyes review", "Medium"), (5, "Security awareness training", "Medium")],
        )
        db.execute(
            "INSERT INTO incidents (risk_id, title, description, severity, occurred_on, loss_amount) "
            "VALUES (1, 'Payment gateway timeout', '45 min outage during peak hours', 'High', ?, 12500)",
            (date.today().isoformat(),),
        )
    db.commit()
    db.close()


# ---------- scoring ----------
def rating(score):
    if score >= 15:
        return "Critical"
    if score >= 10:
        return "High"
    if score >= 5:
        return "Medium"
    return "Low"


@app.template_filter("rating")
def rating_filter(score):
    return rating(score)


# ---------- dashboard ----------
@app.route("/")
def dashboard():
    db = get_db()
    risks = db.execute("SELECT *, likelihood * impact AS score FROM risks").fetchall()
    by_rating = {"Low": 0, "Medium": 0, "High": 0, "Critical": 0}
    for r in risks:
        by_rating[rating(r["score"])] += 1
    matrix = {}
    for r in risks:
        matrix.setdefault((r["likelihood"], r["impact"]), []).append(r["id"])
    totals = db.execute(
        "SELECT COUNT(*) AS n, COALESCE(SUM(loss_amount), 0) AS loss FROM incidents"
    ).fetchone()
    top = sorted(risks, key=lambda r: r["score"], reverse=True)[:5]
    return render_template(
        "dashboard.html",
        total_risks=len(risks),
        open_risks=sum(1 for r in risks if r["status"] != "Closed"),
        by_rating=by_rating,
        matrix=matrix,
        incidents=totals["n"],
        total_loss=totals["loss"],
        top=top,
    )


# ---------- risks ----------
@app.route("/risks")
def risks_list():
    db = get_db()
    category = request.args.get("category", "")
    query = "SELECT *, likelihood * impact AS score FROM risks"
    params = []
    if category in CATEGORIES:
        query += " WHERE category = ?"
        params.append(category)
    query += " ORDER BY score DESC"
    return render_template(
        "risks.html", risks=db.execute(query, params).fetchall(),
        categories=CATEGORIES, selected=category,
    )


def _risk_form_data():
    f = request.form
    return (
        f["title"].strip(), f.get("description", "").strip(), f["category"],
        f.get("owner", "").strip(), int(f["likelihood"]), int(f["impact"]), f["status"],
    )


@app.route("/risks/new", methods=["GET", "POST"])
def risk_new():
    if request.method == "POST":
        db = get_db()
        db.execute(
            "INSERT INTO risks (title, description, category, owner, likelihood, impact, status) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)", _risk_form_data())
        db.commit()
        flash("Risk added.")
        return redirect(url_for("risks_list"))
    return render_template("risk_form.html", risk=None, categories=CATEGORIES, statuses=STATUSES)


@app.route("/risks/<int:risk_id>")
def risk_detail(risk_id):
    db = get_db()
    risk = db.execute("SELECT *, likelihood * impact AS score FROM risks WHERE id = ?", (risk_id,)).fetchone()
    if risk is None:
        return "Risk not found", 404
    controls = db.execute("SELECT * FROM controls WHERE risk_id = ?", (risk_id,)).fetchall()
    incidents = db.execute("SELECT * FROM incidents WHERE risk_id = ? ORDER BY occurred_on DESC", (risk_id,)).fetchall()
    return render_template("risk_detail.html", risk=risk, controls=controls,
                           incidents=incidents, effectiveness=EFFECTIVENESS)


@app.route("/risks/<int:risk_id>/edit", methods=["GET", "POST"])
def risk_edit(risk_id):
    db = get_db()
    risk = db.execute("SELECT * FROM risks WHERE id = ?", (risk_id,)).fetchone()
    if risk is None:
        return "Risk not found", 404
    if request.method == "POST":
        db.execute(
            "UPDATE risks SET title=?, description=?, category=?, owner=?, likelihood=?, impact=?, status=? "
            "WHERE id=?", _risk_form_data() + (risk_id,))
        db.commit()
        flash("Risk updated.")
        return redirect(url_for("risk_detail", risk_id=risk_id))
    return render_template("risk_form.html", risk=risk, categories=CATEGORIES, statuses=STATUSES)


@app.route("/risks/<int:risk_id>/delete", methods=["POST"])
def risk_delete(risk_id):
    db = get_db()
    db.execute("DELETE FROM risks WHERE id = ?", (risk_id,))
    db.commit()
    flash("Risk deleted.")
    return redirect(url_for("risks_list"))


# ---------- controls ----------
@app.route("/risks/<int:risk_id>/controls", methods=["POST"])
def control_add(risk_id):
    db = get_db()
    db.execute("INSERT INTO controls (risk_id, name, effectiveness) VALUES (?, ?, ?)",
               (risk_id, request.form["name"].strip(), request.form["effectiveness"]))
    db.commit()
    return redirect(url_for("risk_detail", risk_id=risk_id))


@app.route("/controls/<int:control_id>/delete", methods=["POST"])
def control_delete(control_id):
    db = get_db()
    row = db.execute("SELECT risk_id FROM controls WHERE id = ?", (control_id,)).fetchone()
    db.execute("DELETE FROM controls WHERE id = ?", (control_id,))
    db.commit()
    return redirect(url_for("risk_detail", risk_id=row["risk_id"]) if row else url_for("risks_list"))


# ---------- incidents ----------
@app.route("/incidents")
def incidents_list():
    db = get_db()
    rows = db.execute(
        "SELECT i.*, r.title AS risk_title FROM incidents i "
        "LEFT JOIN risks r ON r.id = i.risk_id ORDER BY occurred_on DESC").fetchall()
    return render_template("incidents.html", incidents=rows)


@app.route("/incidents/new", methods=["GET", "POST"])
def incident_new():
    db = get_db()
    if request.method == "POST":
        f = request.form
        db.execute(
            "INSERT INTO incidents (risk_id, title, description, severity, occurred_on, loss_amount) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (f.get("risk_id") or None, f["title"].strip(), f.get("description", "").strip(),
             f["severity"], f["occurred_on"], float(f.get("loss_amount") or 0)))
        db.commit()
        flash("Incident logged.")
        return redirect(url_for("incidents_list"))
    risks = db.execute("SELECT id, title FROM risks ORDER BY title").fetchall()
    return render_template("incident_form.html", risks=risks, severities=SEVERITIES,
                           today=date.today().isoformat())


if __name__ == "__main__":
    if not os.path.exists(DATABASE):
        init_db()
    app.run(debug=True)
