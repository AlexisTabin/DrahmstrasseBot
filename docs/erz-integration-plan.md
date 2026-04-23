# ERZ Integration Plan

Plan for integrating Stadt Zürich waste collection data (ERZ — *Entsorgung + Recycling Zürich*) into DrahmstrasseBot. Surface **irregular / non-weekly events** — Mobiler Recyclinghof stops, Sonderabfall-Mobil dates — that aren't already covered by the bot's existing Monday/Wednesday/Thursday reminders, plus expose calendar artefacts to the colocs.

**Status:** plan only, no code. One commit on branch `plan/erz-integration`.

**Target address:** Brahmsstrasse 21, 8003 Zürich. Postal code **8003** is the load-bearing parameter.

---

## 1. TL;DR

| Feature | Trigger | Purpose |
|---|---|---|
| `/semaine` | EventBridge, Monday ~08:00 UTC (after `/roles`) | Surface irregular events this week (Mobiler Recyclinghof, Sonderabfall-Mobil). Silent if nothing. |
| `/prochain [fraction]` | Manual | "When's the next Mobiler Recyclinghof / Sonderabfall?" |
| `/calendrier` | Manual | iCal subscribe URL + PDF download URL for 8003 |
| `/sammelstelle` *(optional, static data)* | Manual | Closest permanent drop-off points |

Data source: the [OpenERZ API](https://openerz.metaodi.ch/api) (third-party, volunteer-maintained wrapper around Stadt Zürich open data). Exposes both JSON and ICS. One endpoint, uniform shape, covers all fractions.

---

## 2. Key research findings

### 2.1 Cargo-Tram and E-Tram no longer exist (2026-01-03 breaking change)

The original ask mentioned "Cargo-Tram or stuff like this." **As of 1 January 2026** these services were renamed and merged: the Cargo-Tram and E-Tram became the **Mobiler Recyclinghof (MRH)** — a rail-independent, truck-based mobile recycling station that rotates through ~32 locations city-wide by end-2026.

Consequences for this plan:
- The OpenERZ API (v9.5.0, 2026-01-03) **removed** the `cargotram` and `etram` waste types and added `mobile` to replace them. Any query with `types=cargotram` or `types=etram` now returns HTTP 400.
- User-facing French wording should say *"Recyclinghof mobile"* or *"camion de recyclage"*, not *"Cargo-Tram"*.
- Some colocs may still say "Cargo-Tram" in daily speech — mention the new name in the first digest so they learn it.

Sources:
- [OpenERZ CHANGELOG v9.5.0](https://github.com/metaodi/openerz/blob/main/CHANGELOG.md) — *"Remove etram and cargotram waste types, since they no longer exist"*
- [Entsorgungstrams werden zum Mobilen Recyclinghof](https://www.stadt-zuerich.ch/de/aktuell/news/2025/entsorgungstrams-werden-mobiler-recyclinghof.html)
- [Mobiler Recyclinghof im Quartier — Stadt Zürich](https://www.stadt-zuerich.ch/de/umwelt-und-energie/entsorgung/wo-und-wann-entsorgen/mobiler-recyclinghof.html)

### 2.2 What 8003 has in 2026 (live data)

Query: `GET https://openerz.metaodi.ch/api/calendar.json?zip=8003&start=2026-01-01&end=2026-12-31&limit=500`
→ **227 entries total**, breakdown:

| waste_type | count | covered by existing bot? |
|---|---|---|
| `waste` (Hauskehricht) | 46 | no (Monday pickup, no bot reminder — poubelle is a subtask of DÉCHETS) |
| `organic` (Bioabfall) | 46 | no (Wednesday pickup — compost is a subtask of DÉCHETS) |
| `cardboard` (Karton) | 46 | **yes** — `/carton` every Wednesday |
| `paper` (Papier) | 23 | **yes** — `/papier` biweekly Monday |
| `mobile` (Mobiler Recyclinghof) | **31** | **no — new feature target** |
| `special` (Sonderabfall-Mobil) | **5** | **no — new feature target** |
| `bulky_goods` (Sperrgut) | 0 | Zurich uses on-demand pickup, not scheduled |

**Important observation**: all `mobile` and `special` stations for zip 8003 are physically in neighbouring zips (8002, 8004, 8045, 8047, 8055). The OpenERZ database maps "which MRH stops are *accessible* to residents of zip X" rather than "stops *inside* zip X." Useful — it means the API already gives us the relevant list, but the digest should say e.g. *"Recyclinghof mobile lundi à St. Jakobstrasse 29 (8004)"*, not just the location.

Nearest MRH stops to Brahmsstrasse 21 (rough geography, to verify with map):
- **8004 Hardbrücke: Gugolzstrasse (Hardplatz)** — ~10 min walk
- **8004 Hardau/Letzigrund: Bullingerstrasse 58** — ~10 min walk
- **8004 Stauffacher: St. Jakobstrasse 29** — ~15 min walk

Sonderabfall-Mobil for 8003 in 2026 (all five dates):

| Date | Station |
|---|---|
| 2026-03-27 | 8047 Albisrieden: Albisriederstrasse 385 (Alte evangelische Kirche) |
| 2026-04-15 | 8045 Friesenberg: Bachtobelstrasse (Wertstoff-Sammelstelle) |
| 2026-09-07 | 8004 Langstrasse: Helvetiaplatz |
| 2026-09-08 | 8002 Enge: Tessinerplatz |
| 2026-09-10 | 8055 Triemli: Wasserschöpfi/Küngenmatt (Bad Heuried) |

### 2.3 API shape (verified against live response)

```json
{
  "_metadata": { "total_count": 227, "row_count": 30 },
  "result": [
    {
      "date": "2026-01-05",
      "waste_type": "waste",
      "zip": 8003,
      "area": "8003",
      "station": "",
      "region": "zurich",
      "description": ""
    },
    {
      "date": "2026-01-06",
      "waste_type": "mobile",
      "zip": 8003,
      "area": "8003",
      "station": "8004, Stauffacher: St. Jakobstrasse 29",
      "region": "zurich",
      "description": ""
    }
  ]
}
```

Notes:
- `date` is ISO `YYYY-MM-DD`. **No time component** — the API does not expose start/end times. MRH stops typically last ~4 hours; Sonderabfall-Mobil usually 11:00–19:00. If we want times, we'd need a second data source (the official datasets on data.stadt-zuerich.ch) or hard-code "après-midi" / check the station page.
- `station` is populated only for `mobile` and `special` — empty string for routine collections.
- `description` is always empty in practice.
- `zip` is an int; `area` is the same value as a string. Treat them as duplicates.

### 2.4 Endpoints and query params

Base: `https://openerz.metaodi.ch/api`

| Endpoint | Returns |
|---|---|
| `/calendar.json` | JSON, paginated |
| `/calendar.ics` | iCalendar — **this IS the subscribable feed** (see §2.5) |

Query parameters (confirmed via live calls):
- `zip=8003` — postal code
- `types=<type>` — one of `waste, paper, organic, cardboard, mobile, special, incombustibles, chipping, metal, textile` for Zurich. Repeat or comma-separate for multiple. `cargotram` and `etram` return HTTP 400.
- `start=YYYY-MM-DD`, `end=YYYY-MM-DD` — date range filter
- `sort=date` (asc) or `sort=date:desc`
- `offset`, `limit` — pagination; default is 30 rows
- `lang=de` — affects only response headers/messages, not content (German is default)

No auth, no documented rate limit. Response times observed at <500 ms.

### 2.5 No direct stadt-zuerich.ch iCal subscribe URL

The [Entsorgungskalender page](https://www.stadt-zuerich.ch/de/umwelt-und-energie/entsorgung/entsorgungskalender.html) requires a form submission (street + house number + fractions) to generate a one-off `.ics` download. **There is no public `webcal://` feed on stadt-zuerich.ch.** Official alternatives:
- The "Entsorgung + Recycling Zürich"-App (iOS/Android)
- Manual PDF download

However, **OpenERZ's `/calendar.ics` endpoint IS a subscribable feed**:

```
webcal://openerz.metaodi.ch/api/calendar.ics?zip=8003
https://openerz.metaodi.ch/api/calendar.ics?zip=8003
```

Sample output (verified):
```
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//metaodi//openerz//EN
X-WR-CALNAME:OpenERZ
X-WR-CALDESC:Waste collection calendar
X-WR-TIMEZONE:Europe/Zurich
BEGIN:VEVENT
SUMMARY:Mobile\, ZIP: 8003
LOCATION:Station: 8004\, Stauffacher: St. Jakobstrasse 29
DTSTART;VALUE=DATE:20260106
DTEND;VALUE=DATE:20260107
END:VEVENT
…
```

Caveats:
- `SUMMARY` is English ("General waste collection", "Mobile", "Special") — not ideal for a French-speaking group. We can still offer it as *"abonne-toi à ce lien dans ton calendrier"* with a note.
- Events are all-day (`VALUE=DATE`) — no times.
- We could, later, generate our own French-localised `.ics` from the JSON response and serve it from S3 / Lambda, but that's out of scope for v1.

### 2.6 The PDF calendar

URL pattern: `https://www.stadt-zuerich.ch/content/dam/web/de/umwelt-energie/entsorgung/dokumente/entsorgungskalender-<year>-<zip>.pdf` — note: the *2026* files sit under an extra `entsorgungskalender-2026/` subfolder, so the true pattern for current year is:

```
https://www.stadt-zuerich.ch/content/dam/web/de/umwelt-energie/entsorgung/dokumente/entsorgungskalender-2026/entsorgungskalender-2026-8003.pdf
```

The 2026/8003 PDF contains **only** the four routine fractions:

| Fraction | Schedule | Holiday replacements (2026) |
|---|---|---|
| Hauskehricht | Every Monday | Mon 6 Apr skipped → Sat 4 Apr; Mon 25 May skipped → Sat 23 May |
| Bioabfall | Every Wednesday | — |
| Papier | Biweekly Tuesday (see dates in PDF) | — |
| Karton | Every Thursday | Thu 1 Jan skipped, no replacement; Thu 14 May skipped → Sat 16 May |

**Nothing in the PDF about Mobiler Recyclinghof, Sonderabfall-Mobil, Sammelstellen Kreis 3, Häckseldienst, or contact addresses beyond the phone +41 44 417 77 77.** The PDF is literally just the four-column table. So we get no bonus static data from it — the API is the only source.

Mildly interesting for the bot: it has holiday replacement dates that our current weekly cron fires ignore. E.g., `/papier` on Mon 6 April 2026 would be wrong (the real date is Tue 14 April 2026 per the PDF, since papier is biweekly Tuesday anyway) — but since the bot just reminds someone to *bring out* paper, not to collect it on a specific day, this is a non-issue for now. **But**: when we have ERZ data, we could tighten this — see §6.5.

---

## 3. Design: where things live

### 3.1 New module: `src/erz.py`

Single responsibility: talk to OpenERZ and format results. Exported surface (proposed):

```python
def fetch_events(zip_code: str, start: date, end: date, types: list[str] | None = None) -> list[Event]
def this_week_irregular(today: date, zip_code: str = "8003") -> list[Event]
def next_event(waste_type: str, today: date, zip_code: str = "8003") -> Event | None
def build_weekly_digest(events: list[Event], assignee: str | None = None) -> str | None
def build_calendar_links(zip_code: str = "8003", year: int | None = None) -> dict
```

An `Event` is a `@dataclass(frozen=True)`: `date: datetime.date, waste_type: str, station: str`. Small, no serialisation library, easy to pickle for unit tests.

HTTP client: **`urllib.request`** (stdlib) — `requests` is not a Lambda bundled dep and we'd have to add it to the package. The Lambda is already on 128 MB / 3 s — keep the layer thin. One `fetch_events()` helper using `urlopen` with a 2 s timeout.

Testability: inject the HTTP call via a callable param defaulting to the real one, so tests pass stub responses without mocking `urlopen`. Pattern already used elsewhere in the codebase would be preferable — none exists yet, so establish the convention here.

### 3.2 Caching (important — Lambda cold starts)

The calendar changes at most a few times a year. We can cache aggressively:
- **Level 1 — module global**: populate a module-level dict on first call within a warm container, TTL 24 h. Zero cost, survives across invocations of the same container.
- **Level 2 — S3 blob** *(optional, defer)*: write the yearly JSON to `s3://<bucket>/erz/8003/<year>.json` once per day. The Monday cron would hit S3, not OpenERZ, removing third-party dependency for the critical path. Add only if OpenERZ proves flaky — don't build it pre-emptively.
- **No DynamoDB caching.** The existing chores table is for write-heavy, per-week state. Caching the calendar in DynamoDB buys us nothing over module-global for our access pattern.

### 3.3 Graceful degradation

OpenERZ is volunteer-maintained. If it's down:
- `/prochain` and `/calendrier` return a short *"ERZ indispo, essaie plus tard"* and log the error to dev chat.
- `/semaine` scheduled digest: send **one** message per failure per week to the dev chat only, not the group. Silent failure in the group is strictly worse than "pas de digest cette semaine" — but a weekly "pas de digest" would also be noise. So: log to dev, silent in group. If we get repeated outages, revisit.

### 3.4 Localisation

Mapping to French for output:

| API `waste_type` | French |
|---|---|
| `waste` | ordures |
| `organic` | déchets organiques / compost |
| `paper` | papier |
| `cardboard` | carton |
| `mobile` | Recyclinghof mobile |
| `special` | déchets spéciaux |
| `metal` | métal |
| `textile` | textile |

Stations in the API come as e.g. `"8004, Stauffacher: St. Jakobstrasse 29"` — already human-readable, leave as-is (mixing German place names with French wording is fine, matches how the colocs speak).

---

## 4. Feature specs

### 4.1 `/semaine` — Monday weekly digest

**Trigger**: new EventBridge rule `semaine`, `cron(30 8 ? * MON *)` (30 min after `/roles` so they don't collide in the chat).

**Behaviour**:
1. Call `this_week_irregular(today)` → filter to `mobile` and `special` events with `monday <= date <= sunday`.
2. If empty: **send nothing** to the group (do send an INFO log).
3. If non-empty: build one message. Use `phrases.pick(...)` for varied intros (add new `WEEKLY_ERZ_INTRO` list to `phrases.py`).
4. Tag the DÉCHETS person via `menage.get_role_assignments(colocataires)["DÉCHETS"]` so they know it's theirs this week.

**Mockup** (Sonderabfall week):
```
🗑️ Cette semaine, Timon (DÉCHETS) :

• mar 27 mars — déchets spéciaux à Albisriederstrasse 385 (8047 Albisrieden)

Il n'y en a pas toutes les semaines, n'oublie pas.
```

**Mockup** (Recyclinghof week):
```
🚛 Cette semaine, Léa (DÉCHETS) :

• lun 6 jan — Recyclinghof mobile à St. Jakobstrasse 29 (8004 Stauffacher)

~10 min à pied de Brahmsstrasse.
```

**Mockup** (nothing irregular): no message sent.

### 4.2 `/prochain [fraction]` — on-demand next date

**Trigger**: manual, group chat.

**Syntax**:
- `/prochain` — defaults to the next Mobiler Recyclinghof stop
- `/prochain speciaux` — next Sonderabfall-Mobil
- `/prochain recyclinghof` — next MRH (same as default)
- Unknown fraction: reply with the list of valid arguments.

**Mockup**:
```
Prochain Recyclinghof mobile :
lun 6 jan (dans 3 jours) — St. Jakobstrasse 29 (8004 Stauffacher)
```

### 4.3 `/calendrier` — calendar links

**Trigger**: manual, group chat.

**Response** (copy-paste-able, no fancy buttons — keep MVP simple):
```
📅 Calendrier Entsorgung 2026 — 8003 Zürich

• S'abonner (auto-update) :
  webcal://openerz.metaodi.ch/api/calendar.ics?zip=8003
  (colle ce lien dans Apple Calendar / Google Calendar)

• PDF officiel (4 fractions routinières) :
  https://www.stadt-zuerich.ch/content/dam/web/de/umwelt-energie/entsorgung/dokumente/entsorgungskalender-2026/entsorgungskalender-2026-8003.pdf

Note : le flux iCal est en anglais et inclut toutes les fractions.
```

Year in the PDF URL: derive from `datetime.date.today().year` — will break when a new year arrives only if the URL pattern changes (it has been consistent since 2022 per our searches).

### 4.4 `/sammelstelle` — permanent drop-offs *(stretch, v2)*

The API has no permanent-Sammelstelle data. This would require a small hard-coded dict of Kreis 3 drop-off points with addresses and opening hours, scraped once from stadt-zuerich.ch and kept static. Not critical for v1. Defer.

---

## 5. Infrastructure changes

### 5.1 `infra/eventbridge.tf`

Add one rule to the `schedules` local:

```hcl
semaine = {
  schedule    = "cron(30 8 ? * MON *)"
  description = "ERZ weekly irregular-events digest (Monday 08:30 UTC)"
  command     = "/semaine@DrahmstrasseBot"
}
```

Plus the matching `aws_cloudwatch_event_rule.semaine` + `aws_cloudwatch_event_target.semaine` resources, following the existing pattern verbatim.

**No IAM changes needed** — the Lambda already has outbound HTTPS (it has to reach Telegram). No VPC attached.

**No SSM changes** — the API is public, no secret.

### 5.2 Lambda config

Stay at 128 MB / 3 s. Verify locally that `urllib.request` + JSON parse of a ~227-entry response stays well under 3 s (should be <500 ms in practice). If tight, bump to 256 MB — marginal cost increase.

---

## 6. Testing strategy

### 6.1 `tests/test_erz.py`

- Unit test `this_week_irregular(today)` with a hand-crafted list of events: mix of routine and irregular, various dates spanning the week boundary.
- Unit test `build_weekly_digest()` with three fixtures: nothing irregular → `None`; one mobile event; multiple events; covers the "silent if empty" rule.
- Unit test `next_event()` with a fixture where "next" is today, tomorrow, next month.
- **Do not hit the real API from CI.** Inject a fake HTTP callable returning canned JSON (committed to `tests/fixtures/erz_8003_2026.json`). Capture the real response once at plan time and commit the fixture.

### 6.2 Integration test — manual only

A `scripts/check_erz.py` one-off script that calls `fetch_events("8003", today, today + 30 days)` and prints a human-readable digest. Not run in CI. Useful when OpenERZ returns an unexpected shape — catches breakage early without polluting test runs.

### 6.3 What not to test
- Don't test the live API shape in CI — the point of the fixture is to pin it.
- Don't test EventBridge — Terraform plan-on-PR catches config errors.

---

## 7. Rollout plan (phased)

1. **M0 — this PR**: commit this plan doc on `plan/erz-integration`. No code.
2. **M1 — MVP**: `src/erz.py` + `/semaine` scheduled + `/calendrier` on-demand + tests with fixture. Feature-flag the EventBridge rule via a `var.erz_enabled` bool in Terraform so we can ship infra without firing yet.
3. **M2 — iterate**: `/prochain`, phrase variants, DÉCHETS tagging. Turn on the Monday cron after the colocs see M1 output for a week in dev chat.
4. **M3 — nice-to-haves**: S3 cache, `/sammelstelle` static data, custom French `.ics` feed.

---

## 8. Open questions (confirm before coding)

1. **Morning or evening digest?** `/roles` fires Monday 08:00 UTC. Having both at once is a lot of pings. Options: (a) 08:30 UTC same day — slot given above, (b) bundle into `/roles` message itself, (c) Sunday evening 19:00 UTC like `/recap`. Suggestion: **(a) 08:30 UTC Monday** — the DÉCHETS person is just named by `/roles`, perfect adjacency.
2. **Do we want `/prochain` at all, or is the Monday digest + calendar link enough?** Probably skip until someone asks.
3. **Should the digest mention distance to the stop?** *"~10 min à pied"* — nice but requires per-stop static data. Defer unless lightweight.
4. **Dev chat vs prod chat for early testing?** Suggest: flip the EventBridge target to `dev_chat_id` for one week before going live in the group. Add a `var.erz_target_chat` input to Terraform, default to prod.
5. **Silent-on-empty-week vs "rien cette semaine" message?** Leaning silent — the bot already posts a lot on Monday. The group can check `/prochain` if curious.

---

## 9. Out of scope

- Writing code (this PR is plan-only).
- Scraping the Stadt Zürich web UI.
- Building a custom-localised `.ics` (deferred to M3).
- Replacing or duplicating existing `/papier`, `/carton`, `/roles` behaviour. The ERZ module is purely additive.
- Home Assistant integration (mentioned in some search results) — not our use case.
- Supporting zip codes other than 8003 — hard-code and move on.

---

## 10. References

- [OpenERZ — API home](https://openerz.metaodi.ch/)
- [OpenERZ — API documentation](https://openerz.metaodi.ch/documentation) *(Swagger UI, best reference)*
- [OpenERZ — GitHub](https://github.com/metaodi/openerz)
- [OpenERZ — CHANGELOG](https://github.com/metaodi/openerz/blob/main/CHANGELOG.md)
- [Stadt Zürich — Mobiler Recyclinghof](https://www.stadt-zuerich.ch/de/umwelt-und-energie/entsorgung/wo-und-wann-entsorgen/mobiler-recyclinghof.html)
- [Stadt Zürich — Entsorgungskalender (landing page)](https://www.stadt-zuerich.ch/de/umwelt-und-energie/entsorgung/entsorgungskalender.html)
- [PDF — Entsorgungskalender 2026 für 8003](https://www.stadt-zuerich.ch/content/dam/web/de/umwelt-energie/entsorgung/dokumente/entsorgungskalender-2026/entsorgungskalender-2026-8003.pdf)
- [Open Data Zürich — dataset: erz_entsorgungskalender_mobiler_recyclinghof](https://data.stadt-zuerich.ch/dataset/erz_entsorgungskalender_mobiler_recyclinghof)
- [Open Data Zürich — dataset: cargo-und-e-tram](https://data.stadt-zuerich.ch/dataset/cargo-und-e-tram) *(legacy, superseded 2026-01-01)*
