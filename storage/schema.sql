-- MindOrbit: esquema do banco (data/mindorbit.db)
CREATE TABLE IF NOT EXISTS crew (
  crew_id   TEXT PRIMARY KEY,                 -- 'T1'..'T4'
  pseudonym TEXT NOT NULL UNIQUE              -- 'TRP-' + 8 caracteres do SHA-256
);

CREATE TABLE IF NOT EXISTS baselines (
  crew_id       TEXT PRIMARY KEY REFERENCES crew(crew_id),
  sleep_mean    REAL NOT NULL, sleep_std    REAL NOT NULL,
  activity_mean REAL NOT NULL, activity_std REAL NOT NULL,
  hr_mean       REAL NOT NULL, hr_std       REAL NOT NULL,
  polarity_mean REAL NOT NULL, polarity_std REAL NOT NULL,
  usual_themes  TEXT NOT NULL DEFAULT '[]',   -- lista JSON de ids de tema
  source        TEXT NOT NULL DEFAULT 'simulated',
  created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sensor_readings (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  crew_id      TEXT NOT NULL REFERENCES crew(crew_id),
  day          INTEGER NOT NULL,              -- 1..180
  date         TEXT NOT NULL,                 -- ISO, ex.: 2026-03-04
  sleep_h      REAL NOT NULL,
  activity_min REAL NOT NULL,
  hr_rest      REAL NOT NULL,
  source       TEXT NOT NULL DEFAULT 'simulated',
  received_at  TEXT NOT NULL,                 -- quando chegou ao banco
  UNIQUE (crew_id, date)
);
CREATE INDEX IF NOT EXISTS ix_sensor_crew_day ON sensor_readings(crew_id, day);

CREATE TABLE IF NOT EXISTS entries (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  crew_id    TEXT NOT NULL, day INTEGER NOT NULL, date TEXT NOT NULL,
  text       TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS analyses (
  entry_id       INTEGER PRIMARY KEY REFERENCES entries(id),
  crew_id        TEXT NOT NULL, day INTEGER NOT NULL,
  themes         TEXT NOT NULL,               -- JSON: lista de ids
  polarity       REAL NOT NULL,
  z              TEXT NOT NULL,               -- JSON: sleep, activity, hr, polarity
  persistence    TEXT NOT NULL,               -- JSON: tema -> dias
  alerts         TEXT NOT NULL,               -- JSON: lista de ids
  confirmed_by   TEXT NOT NULL,               -- JSON: tema -> sensor
  risk           INTEGER NOT NULL,
  band           TEXT NOT NULL,               -- verde | amarelo | vermelho
  main_theme     TEXT,
  mood           TEXT NOT NULL,
  mood_confirmed TEXT
);
CREATE INDEX IF NOT EXISTS ix_analyses_crew_day ON analyses(crew_id, day);

CREATE TABLE IF NOT EXISTS countermeasures (   -- RF18: sugestão e acompanhamento
  id INTEGER PRIMARY KEY AUTOINCREMENT, entry_id INTEGER NOT NULL, crew_id TEXT NOT NULL,
  day INTEGER NOT NULL, theme TEXT NOT NULL, title TEXT NOT NULL,
  done INTEGER, helped INTEGER                 -- NULL = ainda não respondeu
);
CREATE INDEX IF NOT EXISTS ix_cm_crew_day ON countermeasures(crew_id, day);

CREATE TABLE IF NOT EXISTS link_queue (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  direction TEXT NOT NULL CHECK (direction IN ('up','down')),
  payload BLOB NOT NULL, checksum TEXT NOT NULL,
  created_at REAL NOT NULL, deliver_at REAL NOT NULL,
  status TEXT NOT NULL DEFAULT 'queued'       -- queued | delivered
);

CREATE TABLE IF NOT EXISTS directives (        -- lado da nave: mensagens recebidas da Terra
  id INTEGER PRIMARY KEY AUTOINCREMENT, crew_id TEXT NOT NULL,
  text TEXT NOT NULL, sent_at TEXT NOT NULL, read INTEGER NOT NULL DEFAULT 0,
  ref INTEGER                                   -- número da mensagem em earth_messages
);

CREATE TABLE IF NOT EXISTS earth_messages (     -- lado da Terra: o que foi enviado e o que se sabe dele
  id INTEGER PRIMARY KEY AUTOINCREMENT, pseudonym TEXT NOT NULL,
  text TEXT NOT NULL, sent_day INTEGER NOT NULL,
  status TEXT NOT NULL DEFAULT 'enviada',       -- enviada | entregue | lida (só muda quando o aviso chega)
  delivered_day INTEGER, read_day INTEGER,      -- dia da missão, informado pela nave
  unseen INTEGER NOT NULL DEFAULT 0             -- 1 = leitura nova que a equipe ainda não viu
);

CREATE TABLE IF NOT EXISTS earth_reports (
  id INTEGER PRIMARY KEY AUTOINCREMENT, pseudonym TEXT NOT NULL,
  received_at TEXT NOT NULL, report TEXT NOT NULL -- JSON do Report
);

CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
