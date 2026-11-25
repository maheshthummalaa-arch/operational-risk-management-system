# Operational Risk Management System

A simple base project built with Python, Flask and SQLite.

## Features
- Dashboard: totals, rating breakdown, 5x5 heat map, top risks
- Risk register: add / edit / delete / filter by category
- Automatic risk score = Likelihood x Impact (Low <5, Medium 5-9, High 10-14, Critical 15+)
- Controls linked to each risk
- Incident log with loss amounts, linked to risks

## Run
```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000 (sample data is created on first run).

Reset the database: `python init_db.py` (or `python init_db.py --empty` for no sample data).

## Structure
```
app.py          routes, scoring, DB helpers
schema.sql      database tables
init_db.py      database reset script
templates/      HTML pages (Jinja2)
static/         CSS
```

## Ideas to extend
User login/roles, risk review dates, CSV export, charts, email alerts.
