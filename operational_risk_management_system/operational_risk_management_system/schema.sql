DROP TABLE IF EXISTS risks;
DROP TABLE IF EXISTS controls;
DROP TABLE IF EXISTS incidents;

CREATE TABLE risks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    category TEXT NOT NULL,          -- Process, People, Systems, External
    owner TEXT,
    likelihood INTEGER NOT NULL,     -- 1 (rare) .. 5 (almost certain)
    impact INTEGER NOT NULL,         -- 1 (minor) .. 5 (severe)
    status TEXT NOT NULL DEFAULT 'Open',  -- Open, Mitigating, Closed
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE controls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    risk_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    effectiveness TEXT NOT NULL DEFAULT 'Medium',  -- Low, Medium, High
    FOREIGN KEY (risk_id) REFERENCES risks (id) ON DELETE CASCADE
);

CREATE TABLE incidents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    risk_id INTEGER,
    title TEXT NOT NULL,
    description TEXT,
    severity TEXT NOT NULL DEFAULT 'Low',  -- Low, Medium, High, Critical
    occurred_on TEXT NOT NULL,
    loss_amount REAL DEFAULT 0,
    FOREIGN KEY (risk_id) REFERENCES risks (id) ON DELETE SET NULL
);
