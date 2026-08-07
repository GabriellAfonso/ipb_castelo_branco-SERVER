# Feature Specification: Unified Church Service Catalogue

**Feature Branch**: `007-unify-service-catalogue`

**Created**: 2026-08-07

**Status**: Draft

**Input**: User description: "Unify the church service catalogue into a single shared model, owned by `core/`, and delete the duplicate."

## Overview

The church holds four recurring services a week. The system currently describes them **twice**, in two
tables that disagree with each other:

| | `schedule.ScheduleType` | `songs.ServiceWindow` |
|---|---|---|
| Fields | name, weekday, time | name, weekday, start_time, end_time, active |
| Used for | building the member rota | grouping hymn views into occurrences |
| Weekday convention | `1 = Sunday … 7 = Saturday` | `0 = Monday … 6 = Sunday` |
| Live data | **yes, in production** | seeded, never deployed |

Two rows describe "Culto Dominical". Change the service time and someone has to remember to edit it
in two places, in two different numbering systems. Sunday is `1` in one table and `6` in the other.

This feature collapses them into **one catalogue**, owned by `core/` so both features can point at it
without importing from each other. `songs.ServiceWindow` is deleted.

**The hard constraint**: every rota already generated must survive. `MonthlySchedule` holds months of
history keyed by `schedule_type_id`, and the Android app both receives and sends those ids. Nothing
may renumber.

**Scope**: backend only. No Android app change; the app must not be able to tell this happened.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Nothing breaks (Priority: P1)

The rota for last month still shows the same members on the same dates for the same services. The
app opens the rota screen and sees exactly what it saw yesterday. Nobody notices a migration
happened.

**Why this priority**: this is the whole risk of the feature. Every other story is a refinement;
this one is the reason the work is dangerous. If it fails, the church loses its rota history.

**Independent Test**: capture the full rota output before the change, apply it, capture again, and
diff. The two must be identical — same ids, same names, same dates, same members.

**Acceptance Scenarios**:

1. **Given** rotas generated over several past months, **When** the catalogue is unified, **Then**
   every stored rota row still exists, unchanged, pointing at the same service.
2. **Given** the app requests the current rota, **When** it reads the response, **Then** the service
   ids are the same values it received before the change.
3. **Given** the app sends a rota to be saved using service ids it cached earlier, **When** the
   server processes it, **Then** it resolves to the same services and saves correctly.
4. **Given** a member availability configuration, **When** the catalogue is unified, **Then** that
   configuration still points at the same service with the same weight and availability.
5. **Given** the rota generator runs, **When** it builds next month, **Then** it produces the same
   shape of result as before, for the same services.

---

### User Story 2 - One place to change a service time (Priority: P2)

The church moves the Sunday evening service from 19:30 to 18:30. An admin changes it **once**, and
both the rota and the hymn history dashboard follow.

**Why this priority**: this is the value the feature delivers. Without it the duplication stands.

**Independent Test**: change a service's time in the single catalogue, then confirm both the rota
generation and the hymn occurrence grouping use the new time.

**Acceptance Scenarios**:

1. **Given** a service in the catalogue, **When** an admin changes its start time, **Then** the rota
   generated afterwards uses the new time and the hymn dashboard groups by the new window.
2. **Given** a service is deactivated, **When** hymn views are grouped, **Then** it no longer claims
   them; they fall back to calendar-day grouping.
3. **Given** a new service that takes a rota is added to the catalogue, **When** the rota is
   generated, **Then** it is included — no code change and no second row anywhere.
4. **Given** Escola Bíblica Dominical, which is held but takes no member rota, **When** the rota is
   generated, **Then** it produces no rota rows, **and** hymn views on Sunday morning still group
   under it.

---

### User Story 3 - One weekday convention (Priority: P2)

A developer reading either feature finds the same answer to "what number is Sunday?".

**Why this priority**: the two conventions are a live trap. The failure mode is silent — a window
that simply never matches, or a rota that generates on the wrong day — and it costs an afternoon to
find every time.

**Independent Test**: assert the same weekday value resolves to the same real weekday in the rota
generator and in the hymn occurrence grouping.

**Acceptance Scenarios**:

1. **Given** a service stored on Sunday, **When** the rota generator picks dates, **Then** it picks
   Sundays.
2. **Given** the same service, **When** hymn views on that Sunday are grouped, **Then** they match
   that service.
3. **Given** any weekday, **When** either feature interprets it, **Then** both agree.

---

### User Story 4 - Services on any weekday work (Priority: P3)

The church adds a Saturday youth service. It appears in the rota like any other.

**Why this priority**: today it silently does not. This is a latent bug the unification exposes, and
fixing it is cheap once there is one catalogue — but the system is usable without it, because the
church's four current services all land on the three weekdays that happen to work.

**Independent Test**: add a service on a weekday the system has never used, generate a rota, and
confirm rows appear for it.

**Acceptance Scenarios**:

1. **Given** a service on a weekday not previously configured, **When** a rota is generated, **Then**
   rows are produced for that service on the correct dates.
2. **Given** a service that cannot be scheduled for a legitimate reason, **When** a rota is
   generated, **Then** the reason is visible — never a silent omission.

---

### Edge Cases

- **Ids must not renumber** — the app caches service ids between sessions. A renumbering would make
  it save rotas against the wrong services, silently.
- **Services with no end time** — every existing rota row has only a start time. The unified
  catalogue requires an end; the real values are confirmed and recorded below.
- **A service that is held but takes no rota** — Escola Bíblica Dominical. It must appear in hymn
  grouping and must not appear in rota generation. Marking it merely inactive would wrongly remove
  it from hymn grouping too.
- **A service marked as taking no rota that already has rota rows** — must not silently delete them;
  past rotas record what happened.
- **A rota exists for a service being edited** — changing a service's time must not retroactively
  alter rotas already saved; those record what happened.
- **Two services at the same time on different weekdays** — the two prayer meetings share 19:30.
  They must remain distinct.
- **Deleting a service that rotas reference** — must be prevented or handled explicitly; rota history
  must never be orphaned.
- **Rollback** — if the change goes wrong in production, the system must be restorable to its prior
  state with the data intact.
- **Partial deploy** — the migration must not leave a state where one feature sees the catalogue and
  the other does not.

---

## Requirements *(mandatory)*

### Functional Requirements

#### Preservation — the non-negotiable part

- **FR-001**: Every existing rota row MUST survive the unification unchanged: same service, same
  member, same date.
- **FR-002**: Service identifiers MUST NOT change. The value the app holds today must resolve to the
  same service afterwards.
- **FR-003**: Every member availability configuration MUST survive, pointing at the same service with
  the same availability and weight.
- **FR-004**: The rota endpoints MUST keep their exact request and response shapes. The Android app
  MUST require no change and MUST NOT be able to detect the difference.
- **FR-005**: The change MUST be reversible, restoring the prior structure with data intact, in case
  it has to be backed out in production.
- **FR-006**: The migration MUST be verified against a copy of real production data before it is
  applied to production. Verification against an empty database is explicitly insufficient.

#### The unified catalogue

- **FR-007**: The system MUST hold exactly one catalogue of recurring church services, shared by the
  rota and the hymn history rather than duplicated per feature.
- **FR-008**: Each service MUST record its name, the weekday it happens on, its start time, its end
  time, and whether it is currently active.
- **FR-009**: End times MUST be explicit per service — not derived from a fixed duration and not
  inferred from the next service. The three existing rota services MUST be backfilled with the end
  times already confirmed by the church (see Confirmed Production State), not with a guessed default.
- **FR-010**: Changing a service MUST affect both the rota and the hymn history, with no second edit
  anywhere.
- **FR-011**: Deactivating a service MUST remove it from future rota generation and from hymn
  occurrence grouping, without deleting it or its history.
- **FR-012**: The system MUST use a single weekday convention everywhere — `1 = Sunday … 7 = Saturday`,
  the one already carrying production data. Both features MUST resolve the same stored value to the
  same real weekday, and no second convention may remain in the codebase.
- **FR-020**: Each service MUST record whether it takes a **member rota**, separately from whether it
  is currently held. Only services marked as taking a rota may appear in rota generation.

  This is not a nicety: the catalogues being merged are not the same set. Escola Bíblica Dominical
  exists only on the hymn side and has no member rota. Without this distinction, unifying the two
  catalogues would silently start generating rota rows for it — a behaviour change nobody asked for,
  appearing in the next month's rota.
- **FR-013**: The catalogue MUST remain administrable through the interfaces that already manage
  these records, and the hymn history's service-window endpoints MUST continue to work against the
  unified catalogue.

#### Structural rules

- **FR-014**: Neither feature may import from the other. The catalogue MUST be reachable by both
  without a cross-feature dependency.
- **FR-015**: The duplicate service-window model in the songs feature MUST be removed, so no second
  source of truth can drift back into existence.
- **FR-016**: The project's shared layer MUST be permitted to hold data models, and that permission
  MUST be written down with an explicit boundary: only entities genuinely shared by two or more
  features belong there. Without the boundary the shared layer becomes a dumping ground.
- **FR-017**: The exception to the project's migration rule MUST be recorded with its reason, so a
  future reader knows it was a considered decision and not an oversight.

#### Correctness the unification exposes

- **FR-018**: Services on **any** weekday MUST be schedulable. A service the system cannot schedule
  MUST surface a visible reason rather than being silently skipped.

#### Documentation prerequisite

- **FR-019**: The rota domain MUST have a written specification of its current behaviour — the
  weighted member selection, the pinned assignments, the overwrite time limit — **before** its code
  is changed. It has none today.

### Key Entities

- **Church service**: one recurring service the church holds — its name, its weekday, when it starts
  and ends, whether it is currently held, and whether it takes a member rota. Shared by the rota and
  the hymn history. Replaces both of today's tables. The last two flags are independent: Escola
  Bíblica Dominical is held but takes no rota.
- **Member availability**: which members can serve at which service, and how heavily to favour them.
  Points at a church service. Unchanged by this feature except for what it points at.
- **Generated rota**: which member serves at which service on which date. Points at a church service.
  Its rows are the history that must survive untouched.
- **Hymn view occurrence** *(derived, from feature 006)*: consumes the catalogue to decide which
  service a hymn was sung in. Its rule does not change — only where its windows come from.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of rota rows that existed before the change exist afterwards, with identical
  service, member and date.
- **SC-002**: 100% of service identifiers are unchanged — verified by comparing full before/after
  listings, not sampled.
- **SC-003**: The Android app requires zero changes and zero re-releases.
- **SC-004**: Changing a service's time takes one edit instead of two, and both the rota and the hymn
  dashboard reflect it immediately.
- **SC-005**: One weekday convention exists in the codebase; a search finds no second one.
- **SC-006**: A service can be added on any of the seven weekdays and appears in the next generated
  rota.
- **SC-009**: Escola Bíblica Dominical groups hymn views on Sunday mornings and produces zero rota
  rows — verified by generating a rota after the unification and confirming it contains only the
  three services it contained before.
- **SC-007**: The entire existing test suite passes unchanged, and the change is demonstrated on a
  copy of production data before it reaches production.
- **SC-008**: The change can be reverted in production with no data loss.

---

## Assumptions

- **Ids are preserved by keeping the data in place**, not by copying it. Any approach that recreates
  rows risks renumbering, which FR-002 forbids.
- **The hymn history is not yet deployed**, so its side of the change carries no production data
  risk. Only the rota side does.
- **The seeded hymn-history windows are superseded** by the unified catalogue. Three of them map onto
  existing rota services and contribute only their end times; the fourth, Escola Bíblica Dominical,
  becomes a new catalogue row that takes no rota (FR-020).
- **The rota's weekday convention is the one kept** — `1 = Sunday … 7 = Saturday`, confirmed against
  production. It carries the live data, and migrating those values would risk breaking rota
  generation silently for no functional gain. The hymn side has zero rows, so converting *it* costs
  nothing.
- **The Sunday evening service keeps its production name.** "Domingo Liturgia de Adoração" is already
  displayed in the app's rota screen; renaming it to "Culto Dominical" would be a visible change for
  no benefit.
- **Admin management continues through the existing admin interface**, which already exposes these
  records. No new screens.
- **Deleting a service that rotas reference is prevented**, consistent with how the project protects
  other history-bearing relationships.
- **The latent weekday bug is in scope** as User Story 4, at the lowest priority. It can be dropped
  without affecting the rest, but it is cheap once there is one catalogue and it is the kind of
  silent failure worth closing while the code is open.
- **Verification uses a production dump restored locally.** The project has no staging environment.
  One is already restored, so the migration can be exercised against the real 91 rota rows before it
  goes anywhere near production.
- **The hymn history reaches production in the same deploy.** Its migrations are not applied there
  yet, so the duplicate window table will exist for the seconds between one migration and the next,
  and never carry data.

---

## Confirmed Production State

Read from a production backup restored locally on 2026-08-07. This resolves the weekday question and
fixes the merge mapping.

**Rota catalogue** (`schedule_scheduletype`) — the live data, convention **`1 = Sunday … 7 = Saturday`**:

| id | weekday | time | name |
|----|---------|------|------|
| 1 | 3 (Tue) | 19:30 | Terça de Oração |
| 2 | 5 (Thu) | 19:30 | Quinta de Oração |
| 3 | 1 (Sun) | 19:30 | Domingo Liturgia de Adoração |

**Hymn history windows** (`songs_servicewindow`) — seeded, never deployed, convention `0 = Monday … 6 = Sunday`:

| weekday | start | end | name |
|---------|-------|-----|------|
| 1 (Tue) | 19:30 | 20:30 | Terça de Oração |
| 3 (Thu) | 19:30 | 20:30 | Quinta de Oração |
| 6 (Sun) | 09:00 | 10:00 | Escola Bíblica Dominical |
| 6 (Sun) | 19:30 | 21:00 | Culto Dominical |

**Why the two conventions were dangerous**: "Terça de Oração" is `weekday=3` in one table and
`weekday=1` in the other, and **both values are valid in both conventions**. The number alone cannot
tell you which system it belongs to — only the name can. A migration written under the wrong
assumption would keep generating rotas, just on the wrong days.

**Scale of what must survive**: 91 rota rows spanning Feb–Aug 2026 across the three services, 24
member availability configurations, 18 members. **Zero** hymn view events — so all of the risk sits
on the rota side, none on the hymn side.

**Merge mapping**:

| Unified service | Weekday | Start | End | From |
|---|---|---|---|---|
| Terça de Oração | 3 (Tue) | 19:30 | 20:30 | rota id 1, end time from the hymn seed |
| Quinta de Oração | 5 (Thu) | 19:30 | 20:30 | rota id 2, end time from the hymn seed |
| Domingo Liturgia de Adoração | 1 (Sun) | 19:30 | 21:00 | rota id 3, end time from the hymn seed |
| Escola Bíblica Dominical | 1 (Sun) | 09:00 | 10:00 | hymn seed only — **new row, no rota** |

The Sunday evening service keeps its production name, "Domingo Liturgia de Adoração", not the
shorter "Culto Dominical" used in the hymn seed — that name is already on screen in the app.

---

## Dependencies

- The existing rota domain and its production data.
- The hymn view history from feature 006, whose windows come from the catalogue.
- The church's real end times for each service, which must be supplied.
- A restorable copy of production data for verification (FR-006).

## Out of Scope

- Any Android app change.
- Any change to hymn view collection, the occurrence rule, or the reporting endpoints beyond where
  their windows come from.
- Changing how the rota picks members — the weighting and randomisation stay exactly as they are.
- Adding new rota or catalogue features. This unifies what exists; it does not extend it.
- Moving any other model into the shared layer.
