# MindOrbit: report definition for Earth

Contract version 5 · `models.Report` · built in `support/report.py` · packaged in `comms/package.py`

## Who sees what

| Who | What they see | Purpose |
| --- | --- | --- |
| Astronaut | Only a notice about the report, in a warm tone, with the shared categories and the sentence that the diary text is never sent. In red, the notice comes with the guidance to see the medical officer. About their own index, they see a plain-words explanation of what weighed most, with no weights or points. | Transparency about what is shared, and understanding of their own day, without clinical numbers about themselves. |
| Earth (health team) | The full clinical report, in the Earth panel, with the index breakdown in points. | Understand the situation and decide what to do. |

The astronaut neither sends nor receives the report: sending is always automatic.

## Notice to the astronaut

| Situation | Text (summary) |
| --- | --- |
| Nothing sent yet | "No report sent yet. The next one goes out automatically on mission day N." |
| Weekly sent | "The Earth health team received your weekly report today (day X). The next goes out on day N." |
| Immediate, red band | "The Earth health team was notified today (day X) and will be following up with you." |
| Held by blackout | "The report is in the queue and goes out as soon as the link returns. Your onboard support keeps working." |

In the red band, the immediate text takes priority over the weekly one. The final sentence is fixed: "What is shared: index band, themes, sensors and support provided. The text of your diary is never sent."

## Explaining the index (RNF06)

| For whom | Form | Example |
| --- | --- | --- |
| Astronaut | Up to two sentences in words: what weighed most today, plus a note when the day's text carries no complaints. No points, weights or percentages. | "What weighed most today: the theme tiredness and sleep appeared on 6 of the last 7 days and the tone of your diary is heavier than your usual." |
| Health team | Breakdown in points: diary tone (up to 35), theme persistence (up to 35) and sensors (up to 30), plus the notes that changed persistence. | Tone 33, persistence 35, sensors 20; total 88. |

The parts add up to the index (up to 0.5 difference from rounding).

## Decisions

| # | Decision | Choice |
| --- | --- | --- |
| 1 | Pseudonym | Fixed during the mission, so the team can follow the evolution. SHA-256 of a salt and the crew code, `A-` plus 6 characters. |
| 2 | Period | Mission days, never calendar dates. |
| 3 | Sensors | In words: within, below, well below, above, well above the usual. No raw values and no z-scores. |
| 4 | Mood of the day | Included only if the astronaut confirmed it. |
| 5 | Immediate report | Automatic, one only, when the index enters red. On the following days in red, the update goes in the weekly report. |
| 6 | Weekly report | Automatic on mission days 7, 14, 21…, complete for the health team. The astronaut has no send button. |
| 7 | Notice to the astronaut | Only the notice, with categories. No preview of the report. |
| 8 | Reply from Earth | The guidance goes back to the pseudonym; the ship maps it to the crew member. The map stays on board only. |
| 9 | Explaining the index | In words for the astronaut; in points inside the clinical report, for Earth. |

## What the health team needs to understand

| Question | Report field |
| --- | --- |
| How is the astronaut compared with themselves | `risk`, `band`, `sensor_dev` |
| Why the index has this value | `risk_breakdown`, `breakdown_notes`, `breakdown_why` |
| Since when it got worse | `onset_day` |
| Evolution | `trend`, `trend_days`, `trend_bands`, `week`, `prev_week` |
| Which themes and for how many days | `theme_days`, `alert_reasons`, `habitual_themes` |
| Do text and sensors agree | `discordance`, `sensor_days_off` |
| What phase of the mission | `period_end_day` of `mission_total_days`, `mission_context` |
| Days without writing | `missing_diary_days` |
| How much to trust the data | `data_days` |
| What was already tried | `support` |
| Did Earth speak and was it read | `last_directive_read` |
| How the astronaut sees themselves | `mood` (only if confirmed) |
| What repeats or is out of the ordinary | `contexts` |
| A plain-language overview | `summary` |

## `Report` contract (version 5)

| Field | Type | Content |
| --- | --- | --- |
| `pseudonym` | str | e.g. `A-70BB90` |
| `period_start_day`, `period_end_day` | int | Mission days; the end is the current day |
| `mission_total_days` | int | e.g. 180 |
| `kind` | str | `semanal` (weekly) or `imediato` (immediate) |
| `risk`, `band` | int, str | Index 0–100 and band |
| `risk_breakdown` | dict[str, float] | Points for `tone`, `persistence` and `sensors` (maximums 35, 35 and 30) |
| `breakdown_notes` | list[str] | Adjustments that changed persistence (reduced by a day without the theme, reinforced by a sensor) |
| `onset_day` | int or null | Day the current sequence outside green started; null if today is green |
| `trend` | list[int] | Index of the last 7 days |
| `theme_days` | dict[str, int] | Theme and days in the 7-day window |
| `alert_reasons` | list[str] | Which theme or sensor raised the alert (RNF06) |
| `sensor_dev` | dict[str, str] | `sleep`, `activity`, `hr`: within, below, well below, above or well above |
| `discordance` | list[str] | Text with no complaints, but a sensor far from the usual |
| `mood` | str or null | Only if confirmed by the astronaut |
| `support` | list[dict] | `title`, `days`, `answer` |
| `missing_diary_days` | list[int] | Days of the week with no entry |
| `data_days` | dict[str, int] | `janela`, `diario`, `sensores`: days with data in the week |
| `last_directive_read` | bool or null | Null if Earth has not yet sent a message |
| `immediate` | bool | True when `kind` is immediate |
| **v4** `summary` | str | Plain-language summary paragraph (no calendar dates) |
| `trend_days` | list[int] | Mission days matching `trend` |
| `trend_bands` | list[str] | Band of each day in `trend` |
| `week` | dict | `mean`, `worst`, `worst_day`, `bands` (green/yellow/red counts), `days` |
| `prev_week` | dict or null | The same for the previous week (null if none yet) |
| `breakdown_why` | dict[str, str] | `tone`, `persistence`, `sensors` → a sentence explaining the points |
| `sensor_days_off` | dict[str, int] | Sensor → days of the week outside the usual (in the bad direction) |
| `habitual_themes` | list[str] | Themes this week that are already usual for this crew member |
| `mission_context` | dict | `episodes` (start, end, peak, ongoing), `days_not_green`, `days_total` |
| **v5** `contexts` | dict | `recurring`, `out_of_norm` (kind, text), `combos` (text): contexts that repeat or fall outside the crew member's usual. Only catalog categories and day counts. |

## Never goes in the packet

The diary text, raw sensor values, z-scores, the personal wellbeing baseline, the real crew code and calendar dates.

## Declared limits

1. With 4 crew members and few days, a pattern of themes and sensors can identify a person. The anonymity protects the text and the raw data, not the identity.
2. The report supports the team and does not diagnose.
