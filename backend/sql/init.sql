-- v0.1: empty tables only; no real or sample personal health data.
-- Idempotent initialization. Later schema changes need versioned migrations.
PRAGMA foreign_keys = ON;
BEGIN;

CREATE TABLE IF NOT EXISTS profiles (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    display_name TEXT NOT NULL CHECK (length(trim(display_name)) BETWEEN 1 AND 50),
    height_cm REAL CHECK (height_cm > 0),
    weight_kg REAL CHECK (weight_kg > 0),
    medical_history TEXT NOT NULL DEFAULT '',
    allergies TEXT NOT NULL DEFAULT '',
    medications TEXT NOT NULL DEFAULT '',
    preferences TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS health_goals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL DEFAULT 1 REFERENCES profiles(id) ON DELETE CASCADE,
    title TEXT NOT NULL CHECK (length(trim(title)) BETWEEN 1 AND 100),
    target_value REAL NOT NULL CHECK (target_value > 0),
    current_value REAL NOT NULL DEFAULT 0 CHECK (current_value >= 0),
    unit TEXT NOT NULL CHECK (length(trim(unit)) BETWEEN 1 AND 20),
    due_date TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS diet_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL DEFAULT 1 REFERENCES profiles(id) ON DELETE CASCADE,
    record_date TEXT NOT NULL,
    meal_type TEXT NOT NULL CHECK (meal_type IN ('breakfast', 'lunch', 'dinner', 'snack')),
    food_name TEXT NOT NULL CHECK (length(trim(food_name)) BETWEEN 1 AND 100),
    amount_g REAL NOT NULL CHECK (amount_g > 0),
    calories_kcal REAL CHECK (calories_kcal >= 0),
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS exercise_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL DEFAULT 1 REFERENCES profiles(id) ON DELETE CASCADE,
    record_date TEXT NOT NULL,
    exercise_type TEXT NOT NULL CHECK (length(trim(exercise_type)) BETWEEN 1 AND 50),
    duration_minutes INTEGER NOT NULL CHECK (duration_minutes > 0),
    intensity TEXT NOT NULL CHECK (intensity IN ('low', 'medium', 'high')),
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS sleep_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL DEFAULT 1 REFERENCES profiles(id) ON DELETE CASCADE,
    sleep_at TEXT NOT NULL,
    wake_at TEXT NOT NULL,
    quality INTEGER CHECK (quality BETWEEN 1 AND 5),
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    CHECK (julianday(wake_at) IS NOT NULL AND julianday(sleep_at) IS NOT NULL
           AND julianday(wake_at) > julianday(sleep_at))
);

CREATE TABLE IF NOT EXISTS cycle_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL DEFAULT 1 REFERENCES profiles(id) ON DELETE CASCADE,
    start_date TEXT NOT NULL,
    end_date TEXT,
    flow_level TEXT CHECK (flow_level IN ('light', 'medium', 'heavy')),
    symptoms TEXT NOT NULL DEFAULT '',
    mood TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    CHECK (end_date IS NULL OR end_date >= start_date)
);

CREATE INDEX IF NOT EXISTS idx_goals_profile ON health_goals(profile_id);
CREATE INDEX IF NOT EXISTS idx_diet_profile_date ON diet_records(profile_id, record_date);
CREATE INDEX IF NOT EXISTS idx_exercise_profile_date ON exercise_records(profile_id, record_date);
CREATE INDEX IF NOT EXISTS idx_sleep_profile_time ON sleep_records(profile_id, sleep_at);
CREATE INDEX IF NOT EXISTS idx_cycle_profile_date ON cycle_records(profile_id, start_date);

COMMIT;
