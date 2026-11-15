# MindOrbit: MVP scope

Team Elas · NASA Space Apps Challenge 2026 · Challenge: *Create Health Monitoring Software for Astronauts on Space Missions*

## Summary

MindOrbit is an onboard system that analyzes the astronaut's free-text diary, cross-checks it with sensor data the mission already provides, and gives the astronaut immediate feedback with something concrete to do, without depending on Earth. The feedback is a preventive intervention that helps self-awareness and self-regulation. The diary is what the team actually implements and is the project's differentiator. Each astronaut has a **wellbeing baseline**, created before the flight, that is the personal reference for all the analysis.

Earth enters a slower cycle: it receives summarized reports, the psychologist evaluates and sends guidance, and the guidance reaches the astronaut after the communication delay. Onboard support covers that interval.

The prototype is written in Python with Streamlit, with simulated data. **The diary text never leaves the spacecraft.**

## Rationale and gap

Current psychological support relies on real-time contact with Earth, which will not exist during the transit to Mars. MindOrbit brings that support inside the spacecraft.

- **The risk is official.** NASA identifies prolonged isolation and confinement as drivers of the risk of behavioral changes and psychiatric disorders, with anxiety and depression as main concerns and effects on sleep, morale and decision-making ([risk page](https://www.nasa.gov/reference/risk-of-behavioral-changes-and-psychiatric-disorders/)).
- **The risk grows with duration.** Adverse events are relatively rare on current missions of up to six months, but the probability increases a lot on longer ones ([2025 report](https://ntrs.nasa.gov/citations/20250001454), [2016 report](https://ntrs.nasa.gov/citations/20160004365)).
- **Communication changes everything.** On the ISS, the crew talks by video with family and medical staff. On the way to Mars the one-way delay reaches about 22 minutes.
- **The gap is recognized.** A 2023 NASA presentation lists semi-autonomous tools for behavioral health diagnosis, treatment and support as a capability gap for exploration ([Medical Capability Gaps and Roadmap](https://ntrs.nasa.gov/api/citations/20230007411/downloads/AsMA%202023%20Medical%20Capability%20Gaps%20and%20Roadmap.pdf)).

> Sensors tell how the body is, and the diary tells how the person is. NASA already collects the first kind of data. MindOrbit analyzes the second kind on board, in the moment, and gives support back to the astronaut.

## Inputs

| Input | Origin | Format in the MVP | Fields |
| --- | --- | --- | --- |
| Sensor data | Provided by the mission | CSV, one row per crew member per day | Date, crew member, sleep hours, activity minutes, resting heart rate (bpm) |
| Free diary | Written by the astronaut in the app | Free text, no fixed questions | Day, crew member, text |
| Wellbeing baseline | Created before the flight, for each astronaut | One file per crew member, simulated in the MVP | Usual mean and variation of sleep, activity and heart rate; usual diary tone; usual themes |

The sensor file is an input contract. Today it is simulated; in the future it would come from the spacecraft systems with no change to the rest of the system.

## Diary analysis

The analysis extracts the themes and the overall tone from the text and compares everything with the astronaut's own baseline.

- **Themes.** Word lists (in Portuguese) mark which of seven themes appear in each entry.
- **Tone.** Positive and negative word lists give a polarity from -1 to +1. A negation rule flips a word that comes up to two positions after "não", "nem" or "nunca".
- **Persistence.** The system counts on how many of the last 7 days each theme appeared. A negative theme on 4 or more days becomes an alert.
- **Wellbeing baseline.** The system measures, by z-score, the distance of each day from the baseline. It knows whether the astronaut is drifting away from or back toward their own normal, from the first mission day.
- **Cross-check.** A diary theme confirmed by a sensor weighs more (for example "tiredness" in the text together with below-usual sleep).
- **Risk index.** A score from 0 to 100 with three bands.
- **Mood of the day.** From the sentiment and the main theme, the system assigns a simple label ("well", "tired", "anxious", "sad", "irritated", "overloaded", "homesick", "bored", "neutral"). It is shown as a reading ("you seem tired today") and the astronaut can confirm or correct it.

| Theme | Sensor that confirms | Guided countermeasure |
| --- | --- | --- |
| Tiredness and sleep | Sleep hours | Sleep routine: fixed bedtime and less light before sleeping |
| Anxiety | Resting heart rate | Guided breathing with a 3-minute timer |
| Low mood | Activity minutes | Scheduled pleasant activity |
| Homesickness and isolation | None | Recorded message for family and a group activity |
| Crew conflict | None | Time alone and a conversation script |
| Overload | Sleep hours | Scheduled break and three priorities for the day |
| Monotony | Activity minutes | A new activity from the mission list |

| Index component | Weight |
| --- | --- |
| Diary tone (distance from the baseline) | 35% |
| Persistent negative themes | 35% |
| Sensors (sleep 15%, activity 10%, heart rate 5%) | 30% |

| Band | Index | What the system does on board |
| --- | --- | --- |
| Green | 0 to 33 | Positive feedback and logging |
| Yellow | 34 to 66 | Guided countermeasure for the main theme |
| Red | 67 to 100 | Countermeasure, guidance to see the medical officer and an immediate report to Earth |

Weights, bands and the 4-day limit are prototype assumptions.

## Cycle with Earth

Earth receives a summary, never the diary text, and answers with guidance that reaches the astronaut with a delay.

1. **Report.** One weekly report per crew member, and an immediate one when the index enters red.
2. **Packaging.** The report is pseudonymized, compressed with zlib, encrypted with Fernet and validated by a SHA-256 checksum.
3. **Sending.** The packet enters a queue with a simulated delay. During a blackout it is held and leaves when the link returns.
4. **Evaluation.** The psychologist sees the report in the Earth panel and writes guidance.
5. **Return.** The guidance goes back through the same queue and shows up on the astronaut's screen, who marks it as read.
6. **Read receipt.** The read receipt travels back to Earth, also with the delay.

See [report-definition.md](report-definition.md) for the report fields.

## Functional requirements

20 requirements: 17 essential (they form the demo), 2 desirable and 1 optional. The optional atypical-day detection (RF19) was not built.

| ID | Requirement | Description | Priority |
| --- | --- | --- | --- |
| RF01 | Read sensor data | Load the CSV with sleep, activity and heart rate per crew member and day. | Essential |
| RF02 | Free diary | Offer a free-text field with no fixed questions and save entries locally. | Essential |
| RF03 | Theme analysis | Mark the themes present in each entry. | Essential |
| RF04 | Tone analysis | Compute polarity from -1 to +1, with a negation rule. | Essential |
| RF05 | Wellbeing baseline | Load each astronaut's baseline and measure the daily distance from it. | Essential |
| RF06 | Theme persistence | Count the days each theme appeared in the 7-day window and alert from 4. | Essential |
| RF07 | Sensor cross-check | Increase a theme's weight when its related sensor also deviates. | Essential |
| RF08 | Risk index | Produce the 0–100 score and the green, yellow or red band. | Essential |
| RF09 | Immediate feedback | After each entry, show a sentence with what was noticed and why. | Essential |
| RF10 | Guided countermeasure | Offer the activity linked to the main theme, with a timer when it fits. | Essential |
| RF11 | Personal history | Show the index chart and theme frequency for the last 14 days. | Essential |
| RF12 | Local escalation | In red, guide the astronaut to the crew medical officer. | Essential |
| RF13 | Report to Earth | Produce the weekly summary, and the immediate one in red, with no diary text. | Essential |
| RF14 | Secure packaging | Pseudonymize, compress, encrypt and checksum the report. | Essential |
| RF15 | Delay queue and blackout | Simulate link delay and hold packets while a blackout is on. | Essential |
| RF16 | Earth panel and guidance | Show reports to the psychologist and let them send guidance that shows up on the astronaut's screen. | Essential |
| RF17 | Report notice | The astronaut sees a notice of what is shared with Earth (categories only, never the diary text). | Desirable |
| RF18 | Countermeasure follow-up | Ask the next day whether the activity helped and record the answer. | Desirable |
| RF19 | Atypical-day detection | Mark anomalous days on the chart with Isolation Forest, without changing the index. | Optional (not built) |
| RF20 | Mood of the day | Assign a mood label to the day and let the astronaut confirm or correct it. | Essential |

## Non-functional requirements

| ID | Requirement | Description | How to verify |
| --- | --- | --- | --- |
| RNF01 | Offline autonomy | All onboard functions work without internet. | Run the astronaut tab with the network off. |
| RNF02 | Delay tolerance | No onboard function waits for Earth. | Turn on the blackout and complete a support cycle. |
| RNF03 | Privacy | The diary text and raw sensor data are in no packet. | Decrypt a packet and inspect the fields (automated test). |
| RNF04 | Packet security | Every packet is encrypted with Fernet and validated by SHA-256. | Change one byte and see the rejection. |
| RNF05 | Lightness | Analyzing an entry takes under 1 second on an ordinary laptop, without GPU. | Time it in the demo. |
| RNF06 | Explainability | Every alert shows the theme or sensor that triggered it. | Check the feedback sentence of an alert. |
| RNF07 | Usability | The diary is a single free-text field with no minimum length. | Write a one-line entry and see the analysis. |
| RNF08 | Portability | Runs with Python, Streamlit and one command. | Follow the README on a clean machine. |
| RNF09 | Language | The interface is bilingual (English and Portuguese). The text analysis and the demo diaries are in Portuguese. | Switch the language and review the screens. |
| RNF10 | Supportive language | Every feedback uses a warm tone, no clinical labels, and always suggests something the astronaut can do. | Review the feedback texts for each theme and band. |

## Out of the MVP

| Item | Status in the MVP | Planned evolution |
| --- | --- | --- |
| Real sensor collection | The system reads a simulated CSV. | Integration with actigraphy and spacecraft systems. |
| Real astronaut data | Not public. Sensors and diaries are generated by simulation. | Data from space analogs, such as HERA. |
| Language understanding | Word lists with a negation rule. | A local language model, such as BERTimbau. |
| Attention test (PVT) | Not implemented. | A brief version integrated with the diary. |
| Slider check-in | Replaced by the free diary. | Reassess after user testing. |
| Real DTN network | A queue with a simulated delay. | A delay-tolerant networking protocol. |
| Login and profiles | Simple crew member selection, no authentication. | Authentication and role-based profiles. |
| Native app | A web application with two tabs. | Tablet app and psychologist station. |
| Other diary languages | Text analysis in Portuguese. | Word lists in English and other crew languages. |

## Known limits

| Limit | Consequence | How we handle it |
| --- | --- | --- |
| Word lists do not understand irony or context | Some themes will be flagged wrongly. | State it and point to a language model as the evolution. |
| Weights and bands are prototype assumptions | The index is illustrative. | Say that they are assumptions to calibrate. |
| The system supports, it does not diagnose | It does not replace the medical officer or the psychologist. | Show local escalation in red. |
| Pseudonym with 4 crew members | Re-identification is easy. | Promise only that the text and raw data stay on board. |
| It depends on the astronaut writing | With no entries, only sensors remain. | Free text imposes no format or length. |
| The baseline is created on Earth | Normal in flight may differ, for example in sleep. | State it and point to in-mission baseline adjustment as the evolution. |
