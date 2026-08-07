# Phase 1 Data Model: Unified Church Service Catalogue

One new model in `core/`, two models repointed, one deleted. **Not a single row moves.**

**Weekday convention: `1 = Sunday … 7 = Saturday`** — the one already in production. Sunday is `1`.
Converted to and from Python's `weekday()` in exactly one place (`core/domain/weekday.py`).

---

## ChurchService — `core/models/church_service.py`

The single catalogue of recurring church services. Replaces `schedule.ScheduleType` (by taking over
its table) and `songs.ServiceWindow` (which is deleted).

| Field | Type | Constraints | Origin |
|-------|------|-------------|--------|
| `id` | `BigAutoField` | unchanged — **ids must not renumber** | existing values 1, 2, 3 |
| `name` | `CharField(max_length=100)` | required | existing |
| `weekday` | `PositiveSmallIntegerField` | `1..7`, Sunday = 1 | existing |
| `start_time` | `TimeField` | required | existing `time`, renamed |
| `end_time` | `TimeField` | required, strictly after `start_time` | **new**, backfilled |
| `active` | `BooleanField` | `default=True` | **new** |
| `takes_rota` | `BooleanField` | `default=True` | **new** — see below |

**Meta**
- `db_table = "core_churchservice"` (renamed from `schedule_scheduletype`)
- `ordering = ["weekday", "start_time"]`
- `verbose_name = "church service"`, `verbose_name_plural = "church services"`
- `constraints`:
  - `CheckConstraint(condition=Q(end_time__gt=F("start_time")), name="church_service_end_after_start")`
  - `CheckConstraint(condition=Q(weekday__gte=1) & Q(weekday__lte=7), name="church_service_weekday_range")`
- `__str__` → `f"{self.name} ({self.weekday} {self.start_time}-{self.end_time})"`

### `active` and `takes_rota` are independent

This is the distinction that reading production forced (FR-020), and the two flags answer different
questions:

| | `active` | `takes_rota` |
|---|---|---|
| Question | Is this service currently held? | Do members get scheduled for it? |
| False means | Stop grouping hymn views under it; stop generating rota | Still group hymn views; never generate rota |

**Escola Bíblica Dominical is `active=True, takes_rota=False`.** It is a real service that groups
hymn views, and nobody is rostered for it. Marking it inactive instead would wrongly remove it from
the hymnal dashboard — the one place it matters.

Collapsing these into one flag was the tempting simplification and it is wrong: the two states
"happens, no rota" and "does not happen" are genuinely different.

---

## Seed state after migration

| id | name | weekday | start | end | active | takes_rota |
|----|------|---------|-------|-----|--------|------------|
| 1 | Terça de Oração | 3 (Tue) | 19:30 | 20:30 | ✓ | ✓ |
| 2 | Quinta de Oração | 5 (Thu) | 19:30 | 20:30 | ✓ | ✓ |
| 3 | Domingo Liturgia de Adoração | 1 (Sun) | 19:30 | 21:00 | ✓ | ✓ |
| *new* | Escola Bíblica Dominical | 1 (Sun) | 09:00 | 10:00 | ✓ | **✗** |

Rows 1–3 keep their existing ids and names — including "Domingo Liturgia de Adoração" rather than
the hymnal seed's "Culto Dominical", because that name is already on screen in the app. End times
come from the hymnal seed the church confirmed.

The EBD row is the only `INSERT` in the whole feature.

---

## Repointed — `features/schedule/models/schedule.py`

### MemberScheduleConfig

| Field | Change |
|-------|--------|
| `schedule_type` | FK target `ScheduleType` → `core.ChurchService`. **Field name unchanged.** `on_delete` `CASCADE` → **`PROTECT`** |
| `member`, `available`, `weight` | unchanged |

### MonthlySchedule

| Field | Change |
|-------|--------|
| `schedule_type` | FK target `ScheduleType` → `core.ChurchService`. **Field name unchanged.** `on_delete` `CASCADE` → **`PROTECT`** |
| everything else | unchanged |

**The `PROTECT` change is the most important line in this document.** Today `MonthlySchedule`
cascades: deleting a service deletes every rota row that ever referenced it. Feature 006 exposed a
`DELETE` endpoint for service windows, so once the catalogue is unified, an admin deleting what
looks like a hymnal setting would destroy the rota history — 91 rows and growing, silently. See
research R-01.

**Field names stay `schedule_type`** deliberately. They surface as `schedule_type_id` in the rota
API payloads that the Android app sends and receives; renaming them would change the wire format,
which FR-004 forbids. Each declaration carries a comment saying so.

`unique_together` on both models references the field name, so both are unaffected.

---

## Deleted — `features/songs/models/hymnal_history.py`

`ServiceWindow` is removed entirely: model, table, admin registration, DTO, repository methods and
the constants `MIN_WEEKDAY` / `MAX_WEEKDAY`.

Safe to drop outright — it holds four seeded rows and nothing references it. `HymnalViewEvent` has
**no** foreign key to it, because occurrences are derived at read time. That design choice from
feature 006 is what makes this side of the unification nearly free.

`HymnalHistorySettings` is untouched; `window_grace_minutes` stays in `songs`, since the grace period
is a hymnal reading rule and means nothing to the rota.

---

## New — `core/domain/weekday.py`

Not a model — the single conversion between the stored convention and Python's.

```python
def to_python_weekday(stored: int) -> int:   # 1 (Sun) -> 6, 3 (Tue) -> 1
    return (stored + 5) % 7

def from_python_weekday(python_weekday: int) -> int:   # 6 (Sun) -> 1, 1 (Tue) -> 3
    return (python_weekday + 1) % 7 + 1
```

Lives in `core/domain/` rather than `core/models/` because it is framework-free. It replaces
`schedule_service.WEEKDAYS_MAP` and the direct `moment.weekday()` comparison in
`hymnal_history_occurrences.match_window`.

After this feature, a search for weekday arithmetic must find exactly these two functions (SC-005).

---

## Relationship map

```
                    ┌──────────────────────┐
                    │ core.ChurchService   │   ← the single catalogue
                    └──────────┬───────────┘
                   PROTECT     │     PROTECT
              ┌───────────────┴────────────────┐
              │                                │
  schedule.MemberScheduleConfig    schedule.MonthlySchedule
                                            (91 rows — must survive)

  songs.HymnalViewEvent  ──reads at query time──▶  core.ChurchService
      (no foreign key — occurrences are derived)
```

`songs` and `schedule` both depend on `core`. Neither depends on the other — the constitution rule
that made this feature necessary is satisfied by construction.

---

## What must be identical afterwards

The acceptance gate, stated as data (FR-001, FR-002, SC-001, SC-002):

| Check | Before | After |
|-------|--------|-------|
| Rota rows | 91 | 91, same ids, dates, members, services |
| Member configs | 24 | 24, same services, weights, availability |
| Service ids | 1, 2, 3 | 1, 2, 3 — **not** renumbered |
| Service names | as listed above | unchanged |
| Hymn view events | 0 | 0 |
