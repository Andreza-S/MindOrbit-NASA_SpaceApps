# MindOrbit: data and sources

This page says which data MindOrbit uses, where each piece comes from, and which NASA sources shaped the project.

## 1. At a glance

| Data | Origin | Used for |
| --- | --- | --- |
| Earth–Mars signal delay, per mission day | **NASA JPL** orbital elements, computed by `simulator/light_delay.py` | **Inside the software**: link delay, "signal takes X min" notices, timing of reports, guidance and read receipts |
| Sensors (sleep, activity, resting heart rate), 4 crew × 180 days | Simulated (`simulator/generate.py`, `data/sensores.csv`) | Software input |
| Wellbeing baseline per crew member | Simulated (`data/baselines/T1..T4.json`) | Personal reference for the analysis |
| Diary entries, 720 (4 × 180) | Simulated from phrase templates (`data/diarios_demo.json`) | Demo diaries |
| Word lists (themes, tone, negation) | Written by the team (`data/lexicon/`) | Text analysis |
| NASA reports and pages | NASA and NASA-related publications (section 3) | **Design of the solution**: problem, themes, sensors, mission length, justification |

## 2. NASA data used inside the software

### Approximate Positions of the Planets (NASA JPL)

Source: [ssd.jpl.nasa.gov/planets/approx_pos.html](https://ssd.jpl.nasa.gov/planets/approx_pos.html), Table 1 (Keplerian elements and their rates, valid 1800–2050).

How we use it (`simulator/light_delay.py`):

1. For each mission day we compute the heliocentric position of the Earth (Earth–Moon barycenter) and of Mars from the JPL elements.
2. We take the distance between the two and divide it by the speed of light to get the one-way light time.
3. The result is stored in `data/atraso_terra_marte.csv` (`day, date, distance_au, one_way_delay_min`). On mission day 1 the delay is about 19.5 min; on day 65 it is about 18.6 min.
4. In the app, **Real Earth–Mars delay (NASA/JPL)** (on by default) uses that table. Messages, reports, guidance and read receipts are scheduled with this delay, shortened to seconds so a demo can be followed (1 real minute becomes 1 second on screen). A manual slider is available as an alternative.

Regenerate the table with `python -m simulator.light_delay`.

## 3. NASA sources behind the design

| Source | What it contributed |
| --- | --- |
| [Risk of Behavioral Changes and Psychiatric Disorders, NASA](https://www.nasa.gov/reference/risk-of-behavioral-changes-and-psychiatric-disorders/) | The definition of the problem: isolation and confinement as drivers of behavioral risk, with effects on sleep, morale and decision-making. It guided the themes (tiredness and sleep, anxiety, low mood, isolation, crew conflict, overload, monotony) and the sensors (sleep, activity, heart rate). |
| [Evidence Report 2025 (NTRS 20250001454)](https://ntrs.nasa.gov/citations/20250001454) | Risk is relatively low on today's missions of up to six months and grows with duration, which is why we simulate 180 days and follow changes over time. |
| [Evidence Report 2016 (NTRS 20160004365)](https://ntrs.nasa.gov/citations/20160004365) | The earlier evidence base on the same risk; it supports the same reasoning. |
| [Medical Capability Gaps and Roadmap, AsMA 2023 (NTRS)](https://ntrs.nasa.gov/api/citations/20230007411/downloads/AsMA%202023%20Medical%20Capability%20Gaps%20and%20Roadmap.pdf) | Lists semi-autonomous tools for behavioral health diagnosis, treatment and support as a capability gap for exploration: the gap MindOrbit addresses. |
| [Overview of NASA Behavioral Health and Performance Standard Measures (NTRS 20190000670)](https://ntrs.nasa.gov/citations/20190000670) | Background on how NASA measures behavioral health and performance. |
| [Reaction Self Test study on the ISS (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC8919197) | Background on a brief attention test used on the ISS; the reference for our planned attention-test feature. |
| [Behavioral health investigations in the one-year mission (Phys.org, 2015)](https://phys.org/news/2015-06-dont-stress-small-nasa-one-year.pdf) | Background on behavioral health research during a one-year mission. |

The last three are background research related to NASA's work, not data read by the software. The Reaction Self Test and Phys.org items are not hosted by NASA.

## 4. The simulated crew data

Real astronaut data is not public, so the crew data is simulated. The simulator (`simulator/generate.py`) uses a fixed random seed, so everyone sees the same demo.

- **Crew:** four crew members, T1 to T4, over a 180-day mission starting 2026-03-01.
- **Baselines:** each crew member has their own usual sleep, activity and heart rate (mean and variation), and may have a habitual theme (for example, T1 is often a bit overloaded and T3 a bit bored, which is normal for them and is not flagged as new).
- **Sensors:** daily readings around each baseline, within plausible ranges (sleep 3–10 h, activity 0–150 min, heart rate 40–100 bpm).
- **Diaries:** 720 short entries built from phrase templates. Normal days use neutral or positive phrases; theme phrases appear only in planted episodes and a few habitual days.
- **Three planted "wear-down" episodes**, so the demo has something to detect:

| Crew | Days | Themes | Sensor effect |
| --- | --- | --- | --- |
| T1 | 60–68 | Tiredness and sleep | Less sleep, higher heart rate, a little less activity |
| T2 | 110–118 | Low mood, homesickness | Much less activity |
| T3 | 140–148 | Overload | Less sleep, higher heart rate |

`python scripts/check_data.py` checks the generated data against the acceptance criteria.

## 5. Privacy of the data

The diary text and raw sensor values stay on the ship. Earth receives only the report (see [report-definition.md](report-definition.md)), and an automated test decrypts a packet and checks that no diary text is in it.
