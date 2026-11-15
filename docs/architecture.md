# MindOrbit: architecture

## 1. Principles

1. **Onboard first.** All the analysis and the astronaut support run locally, with no network and without waiting for Earth (RNF01, RNF02).
2. **A hard border between ship and Earth.** Earth only sees what goes through the link, and the link only carries aggregated, encrypted reports (RNF03, RNF04).
3. **A pure, testable core.** The analysis is a set of functions with no side effects: text, sensors and baseline go in, a result comes out. This gives RNF05 (under 1 s) and lets us test without the interface.
4. **Contracts first.** Data types (`models.py`) were defined first so the two of us could work in parallel.
5. **Rules in configuration files.** Word lists, weights, bands and limits live outside the code, because they are assumptions to calibrate (`config.py`, `data/lexicon/`).

## 2. Overview

```
                    ┌──────────────────────── SHIP (ONBOARD) ───────────────────────┐
 Sensors CSV ────►  │  Ingest ─► Analysis core ─► Astronaut support ─► UI           │
 Baseline ───────►  │            (themes, tone,    (feedback,                       │
 Diary (UI) ─────►  │             z-score,          countermeasure,                 │
                    │             persistence,      mood, history,                  │
                    │             cross-check,      escalation)                     │
                    │             index)                                            │
                    │                  │                                            │
                    │                  ▼                                            │
                    │       Report ─► Packaging (pseudonym→zlib→Fernet→SHA-256)     │
                    └──────────────────┬────────────────────────────────────────────┘
                                       ▼
                      SIMULATED LINK (queue with delay + blackout)
                                       ▲
                    ┌──────────────────┴────────────────────────────────────────────┐
                    │  EARTH: unpack ─► clinical panel ─► guidance ─────────────────►│ back through the queue
                    └───────────────────────────────────────────────────────────────┘
```

## 3. Components

### 3.1 Onboard

| Module | Responsibility | Requirements |
| --- | --- | --- |
| `ingest/sensors.py`, `ingest/source.py` | Read the sensor CSV and deliver each day only when mission time reaches it (the astronaut tab never sees future days) | RF01 |
| `ingest/baseline.py` | Load each crew member's wellbeing baseline (JSON) | RF05 |
| `core/lexicon.py`, `core/themes.py` | Load the word lists and mark themes per entry | RF03 |
| `core/sentiment.py` | Polarity from -1 to +1 with a negation rule (2-word window) | RF04 |
| `core/baseline_distance.py` | The day's z-score against the personal baseline (sensors and tone) | RF05 |
| `core/persistence.py` | Days per theme in the 7-day window; alert from 4 | RF06 |
| `core/crossing.py` | A diary theme confirmed by a sensor weighs more | RF07 |
| `core/risk.py` | Index 0–100 (35% tone, 35% persistence, 30% sensors) and band | RF08 |
| `core/mood.py` | Mood label of the day from sentiment and main theme | RF20 |
| `core/pipeline.py` | `analyze_entry(...) -> Analysis` orchestrates the core | all of `core/` |
| `support/feedback.py` | Feedback sentence with its reason, warm tone, always with an action | RF09, RNF06, RNF10 |
| `support/countermeasures.py` | Theme → activity catalog, with a timer when it fits | RF10 |
| `support/escalation.py` | In red, guide the astronaut to the medical officer and trigger the immediate report | RF12 |
| `support/explain.py` | Plain-words and in-points explanations of the index | RNF06 |

### 3.2 Link and Earth

| Module | Responsibility | Requirements |
| --- | --- | --- |
| `support/report.py` | Build the report (weekly or immediate) from aggregates only | RF13, RNF03 |
| `support/contexts.py` | Contexts that repeat or fall outside the crew member's ordinary (categories and day counts only) | RF13 |
| `comms/package.py` | Pseudonymize → JSON → zlib → Fernet → SHA-256, and the way back | RF14, RNF04 |
| `comms/link.py` | Queue with `deliver_at` (simulated delay) and a blackout flag; packets held until the link returns; read receipts | RF15, RF16, RNF02 |
| `simulator/light_delay.py` | Real Earth–Mars one-way light delay per mission day, from NASA/JPL orbital elements | RF15 |
| `support/link_status.py` | Link status messages, including the expected return from a blackout | RF15 |
| `ui/earth_data.py` | Reads only what arrived through the link and prepares the clinical report | RF16 |

### 3.3 Interface (Streamlit)

One app with two tabs that stand for two separate sides. The tabs do not call each other's code: the Earth tab only reads what arrived through the link.

- **Astronaut tab** (`ui/astronaut_tab.py`): crew member selector, single-field diary, feedback, mood (confirm or correct), countermeasure with a timer, 14-day chart, escalation notice, box of guidance received.
- **Earth tab** (`ui/earth_tab.py`): clinical report, index breakdown, contexts, period selector, link queue, form to send guidance.
- **Demo sidebar** (`ui/sidebar.py`): advance the simulated day, go to a day, blackout, link delay, restart the demo.
- **Language** (`support/i18n.py`, `support/i18n_en.py`): Portuguese is the source text; the English catalog is looked up when the English interface is on. Stored values stay in Portuguese and are translated only at display.

## 4. Main flows

**Flow A, immediate support (onboard):**
`Diary (text)` → `analyze_entry` (themes, tone, z-score, persistence, cross-check, index, mood) → `feedback` + `countermeasure` → UI → saves the `Analysis`.

**Flow B, cycle with Earth:**
`Red index` or `end of week` → `report` → `package` → `link.enqueue(up)` → (delay / blackout) → Earth reads the packet and checks the checksum → panel → the psychologist writes → `package` → `link.enqueue(down)` → (delay) → the astronaut's box → marked as read → the read receipt goes up.

Flow A never depends on Flow B.

## 5. Data model

Contracts in `models.py` (dataclasses): `SensorDay`, `Baseline`, `Entry`, `Analysis`, `Report`, `Directive`, `CountermeasureLog`.

Local storage uses **SQLite** (standard library, no server, works offline), in `storage/db.py`. An in-memory backend (`storage/memory_db.py`) is used for tests. When hosted, `storage/session_db.py` gives **each visitor a private temporary database** that starts at day 1.

| Data | Main fields |
| --- | --- |
| Entries | crew, day, text, created time |
| Analyses | themes, polarity, mood, z-scores, persistence, risk, band, main theme |
| Countermeasures | theme, title, done, helped (RF18) |
| Link queue | direction (up/down), payload, checksum, `deliver_at`, status |
| Directives | crew, text, sent time, read |
| Settings | simulated day, blackout, delay mode and seconds |

**Why the queue is in SQLite and not just in memory:** Streamlit re-runs the script on every interaction, and in-memory state is lost. Persisting the queue and the simulated day avoids surprises in the demo. It is a simulated queue, not a DTN network.

**Simulated clock:** the mission day is a counter (`sim_day`) that the demo controls advance. The link delay is a few real seconds in the demo; the real Earth–Mars delay in minutes is shown on screen.

## 6. Repository layout

```
app.py               Streamlit entry point (two tabs + demo sidebar)
config.py            weights, bands, thresholds, labels
models.py            data contracts
demo_seed.py         loads the simulated diaries up to a mission day
core/                pure analysis functions
support/             feedback, countermeasures, report, contexts, explanations, link status, i18n
comms/               report packaging (Fernet), simulated link, read receipts
ingest/              sensor CSV and baseline loading
simulator/           simulated data generator and the Earth–Mars light delay
storage/             SQLite, in-memory backend, per-visitor databases
ui/                  astronaut tab, Earth tab, sidebar, day navigation
data/                word lists, baselines, sensors.csv, simulated diaries, light-delay table
scripts/             data checks, seeding, CLI demo
tests/               automated tests
```

## 7. Technology

| Item | Choice | Reason |
| --- | --- | --- |
| Language | Python 3.11 | One language for the whole prototype |
| Interface | Streamlit | Two tabs, no separate front end |
| Data | pandas, numpy | CSV reading and z-scores |
| Charts | Altair (ships with Streamlit) | History charts, no CDN |
| Encryption | `cryptography` (Fernet) | RF14, RNF04 |
| Compression and checksum | `zlib`, `hashlib` (standard library) | RF14 |
| Storage | `sqlite3` (standard library) | Local and offline |
| Tests | pytest | Core, privacy, link, interface smoke tests |

No dependency reaches the internet at runtime (RNF01).

## 8. Architecture decisions

| # | Decision | Discarded alternative | Reason |
| --- | --- | --- | --- |
| 1 | One app with two tabs | Two services (ship and Earth) with an API | One command (RNF08) and less risk. The border is kept by the `comms` module, not by the network |
| 2 | Core as pure functions | Classes with state | Testable and fast (RNF05) |
| 3 | Word lists and rules in JSON | Constants in code | The team can calibrate without touching code; easy to swap for a language model later |
| 4 | SQLite | Loose JSON files | Queries over 7- and 14-day windows and a persistent queue, no server |
| 5 | Fernet key as a shared file | Key exchange | A simulation; in production it would be pre-distributed before flight. Declared in the docs |
| 6 | The packet enters the queue already encrypted and Earth decrypts | Passing the object in memory | Shows RNF03 and RNF04 for real (decrypt and inspect; change a byte and see the rejection) |
| 7 | The simulator generates everything (sensors, baselines, diaries) | Public data | There is no public real astronaut data; HERA analog data is future work |
| 8 | One database per visitor when hosted | A shared database | Nobody changes another visitor's demo |

## 9. How the architecture meets the non-functional requirements

| RNF | How | Test |
| --- | --- | --- |
| RNF01 Offline | No external calls; everything local | Run the astronaut tab with no network |
| RNF02 Delay | Flow A does not touch the `link` | Blackout on and a full support cycle |
| RNF03 Privacy | `report.py` only receives the `Analysis`, never the text or raw CSV | Automated test: decrypt the packet and check there is no diary text |
| RNF04 Security | Fernet + SHA-256 in `package` and on arrival | Change one byte and see the rejection |
| RNF05 Lightness | Word lists in memory, no heavy model | Time `analyze_entry` |
| RNF06 Explainability | `Analysis` keeps the theme and sensor of each alert; `feedback` cites them | See the alert sentence |
| RNF07 Usability | One text field, no minimum | A one-line entry |
| RNF08 Portability | `requirements.txt` and `streamlit run app.py` | README on a clean machine |
| RNF09 Language | Bilingual interface; Portuguese text analysis | Switch the language and review the screens |
| RNF10 Supportive language | Feedback texts in a catalog by theme and band, reviewable | Review the catalog |
