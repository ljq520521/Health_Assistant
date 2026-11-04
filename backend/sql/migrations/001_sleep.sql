ALTER TABLE sleep_records ADD COLUMN deep_minutes INTEGER CHECK (deep_minutes >= 0);
ALTER TABLE sleep_records ADD COLUMN light_minutes INTEGER CHECK (light_minutes >= 0);
ALTER TABLE sleep_records ADD COLUMN awakenings INTEGER NOT NULL DEFAULT 0 CHECK (awakenings BETWEEN 0 AND 50);
CREATE INDEX idx_sleep_profile_wake ON sleep_records(profile_id, wake_at);
CREATE TABLE sleep_settings (
    profile_id INTEGER PRIMARY KEY REFERENCES profiles(id) ON DELETE CASCADE,
    target_minutes INTEGER NOT NULL DEFAULT 480 CHECK (target_minutes BETWEEN 180 AND 720),
    bedtime TEXT NOT NULL DEFAULT '23:00',
    alarm_time TEXT NOT NULL DEFAULT '07:00',
    reminder_minutes INTEGER NOT NULL DEFAULT 30 CHECK (reminder_minutes BETWEEN 0 AND 120),
    bedtime_enabled INTEGER NOT NULL DEFAULT 0 CHECK (bedtime_enabled IN (0,1)),
    alarm_enabled INTEGER NOT NULL DEFAULT 0 CHECK (alarm_enabled IN (0,1)),
    smart_alarm INTEGER NOT NULL DEFAULT 0 CHECK (smart_alarm IN (0,1)),
    weekdays TEXT NOT NULL DEFAULT '[0,1,2,3,4,5,6]',
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
CREATE TABLE sleep_content (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL CHECK (length(trim(title)) BETWEEN 1 AND 100),
    category TEXT NOT NULL CHECK (category IN ('noise','meditation')),
    source_type TEXT NOT NULL CHECK (source_type IN ('generated','url','upload')),
    source TEXT NOT NULL,
    favorite INTEGER NOT NULL DEFAULT 0 CHECK (favorite IN (0,1)),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
INSERT INTO sleep_content(title, category, source_type, source) VALUES
    ('轻柔白噪音', 'noise', 'generated', 'white'),
    ('低频雨声', 'noise', 'generated', 'brown'),
    ('静心冥想音景', 'meditation', 'generated', 'meditation');
