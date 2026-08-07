# Phase 0 Research: Hymnal View History

Decisions taken before design, with the alternatives that were rejected. Every NEEDS CLARIFICATION
from Technical Context is resolved. R-11 and R-13 were settled later, once the church confirmed its
real service times.

---

## R-01: Where the code lives inside `songs`

**Decision**: add files to the existing packages with a `hymnal_history_` prefix. No new Django app,
no new subpackage, no restructuring of existing files.

```
models/hymnal_history.py          repositories/hymnal_history_repository.py
serializers/hymnal_history_serializers.py   services/hymnal_history_*.py
views/hymnal_history.py           hymnal_history_dtos.py   (feature root, beside dtos.py)
```

**Rationale**: `models/`, `services/`, `repositories/`, `views/` and `serializers/` are already
packages in this feature, so new files drop in without touching anything. `Hymn` lives here and the
constitution forbids features importing from each other, so a separate app is not an option.

**Alternatives rejected**:
- *New `features/hymnal_history` app* — would have to import `Hymn` from `features.songs`, a direct
  constitution violation.
- *`features/songs/hymnal_history/` subpackage* — cleaner grouping, but it splits the feature into
  two conflicting layouts and every import path stops matching the other five features.
- *Adding to the existing `dtos.py`* — that file is the Sunday-plays DTO module; mixing telemetry
  DTOs in would push it past its single responsibility. `hymnal_history_dtos.py` sits beside it
  instead (`dtos.py` is a flat module in this feature, not a package, so a sibling module is the
  minimal-change option).

---

## R-02: Ingest throttling — rate and key

**Decision**: `ScopedRateThrottle` with `throttle_scope = "hymnal_ingest"` at **`600/hour`**,
declared on the view so it *replaces* the global anon/user throttles for this endpoint.

```python
# settings/base.py — DEFAULT_THROTTLE_RATES
"hymnal_ingest": "600/hour",
```

**Rationale**:
- `ScopedRateThrottle` + `throttle_scope` is already the project's pattern
  (`features/accounts/views/auth.py:24` uses it for `login`).
- The throttle key is the client IP. **The whole congregation shares one IP** on church Wi-Fi, so
  the rate has to be sized for the building, not for a person: ~200 members syncing up to 3 times
  an hour ≈ 600 requests. The global `anon` rate of `500/hour` would start rejecting real syncs
  after a service, which is exactly the failure this endpoint must not have.
- Combined with `max_batch_size` (200), one IP is capped at 120k events/hour — an ample ceiling
  that still bounds abuse.

**Alternatives rejected**:
- *Throttle keyed on `device_id` from the payload* — the appealing option, since it is per-install
  rather than per-building. Rejected: `device_id` is attacker-controlled and trivially rotated, so
  it bounds honest clients and nothing else. It also forces the throttle to parse `request.data`
  before validation.
- *Leaving the default `anon` 500/hour* — too tight for a shared IP, as above.
- *No throttle* — unacceptable on an unauthenticated write endpoint.

**Two pre-existing gaps this exposes** (both affect the login throttle today, both worth fixing
alongside this feature):

1. **`NUM_PROXIES` is not set.** The app runs behind nginx, and DRF prefers `X-Forwarded-For` when
   present. Without `NUM_PROXIES = 1`, the throttle key can be read from a client-supplied XFF
   header, letting anyone bypass every rate limit by rotating that header. Set `NUM_PROXIES = 1`.
2. **No `CACHES` configured**, so DRF throttling counts live in per-process `LocMemCache`. Counters
   are not shared between gunicorn workers and reset on restart, making the effective rate
   *workers × rate*. Acceptable for this church-scale app; recorded so the number is understood as
   approximate.

---

## R-03: Idempotency and collapse without per-event queries

**Decision**: three bulk reads, one bulk write, all inside one transaction, with
`bulk_create(..., ignore_conflicts=True)` as the race guard.

1. One query for the batch's already-known `client_event_id`s (`__in` over the batch).
2. One query for existing collapse candidates: rows matching any `(hymn_id, device_id)` in the batch
   whose `viewed_at` falls in `[min(viewed_at) - window, max(viewed_at) + window]`.
3. One query resolving the batch's `hymn_id`s to existing hymns.
4. In-memory decision per event, then a single `bulk_create` of the survivors.

**Rationale**: constant query count regardless of batch size, satisfying the constitution's "no
queries inside loops". A 200-event batch costs 4 queries, not 600.

**Race guard**: two devices (or one device retrying) can pass step 1 concurrently and both insert.
`ignore_conflicts=True` on the `client_event_id` unique constraint makes the loser a silent no-op
instead of a 500, and the event is still reported `accepted` — which is correct, because the row
does exist.

**Intra-batch collapse**: the pre-fetch only sees the database. Two events in the *same* batch for
the same hymn and device 4 minutes apart must also collapse. The service sorts the batch by
`viewed_at` and carries a running `(hymn_id, device_id) -> last_kept_viewed_at` map, so
already-decided events in this batch participate in the window.

**Alternatives rejected**:
- *`get_or_create` per event* — 2 queries per event; 400 queries for a full batch.
- *`ignore_conflicts` alone with no pre-check* — cannot distinguish inserted from conflicted rows
  on PostgreSQL (`bulk_create` returns objects without PKs), so the response could not be built.
- *A database-level exclusion constraint for collapse* — would need a range type over
  `(hymn, device_id, viewed_at)` and makes the window non-configurable at runtime, which
  contradicts `collapse_window_minutes` being an editable setting.

---

## R-04: Computing occurrences — SQL vs Python

**Decision**: the repository returns raw rows for the range (`.values_list("hymn_id", "viewed_at",
"device_id")`), plus the active windows, plus a hymn id → (number, title) map. The **service**
collapses them in memory with a pure function.

**Rationale**:
- Window matching is "convert to local time, find the active window whose weekday and time range
  contain this instant, else fall back to the calendar day". Expressing that in the ORM means a
  correlated join against a small table with timezone conversion inside the predicate — hard to
  read, hard to test, and it drifts toward backend-specific SQL. This feature already inherits one
  PostgreSQL-only query (`DjangoHymnalRepository` uses `REGEXP_REPLACE`); adding more is a cost.
- The collapse rule *is* business logic, and the constitution puts business logic in services.
- A pure function over `(events, windows)` is unit-testable with no database at all, which is what
  "F.I.R.S.T tests" asks for.
- Volume is church-scale: a full year is on the order of tens of thousands of rows — a few MB of
  tuples, well within a request.

**Bounded by design**: the 366-day maximum range (FR-022) is what keeps this honest. Without it,
"fetch the range into memory" would be an unbounded promise.

**Alternatives rejected**:
- *Full ORM aggregation* — above.
- *A materialized `Occurrence` table maintained on write* — faster reads, but it freezes occurrences
  against the windows that existed at write time. FR-023 requires the opposite: editing a window
  must change future reports without touching stored events.

**Indexes** to keep the reads and the collapse pre-check cheap:
- `viewed_at` — range scans for reporting.
- `(hymn, device_id, viewed_at)` — the collapse candidate lookup.
- `client_event_id` is already indexed by its unique constraint.

---

## R-05: Time and timezone handling

**Decision**: `USE_TZ = True` and `TIME_ZONE = "America/Sao_Paulo"` are already set
(`settings/base.py:149`). Timestamps store as UTC; every piece of *reasoning* — window matching, day
and week and month boundaries — converts to the church's local time first via
`django.utils.timezone.localtime`.

**Decision**: wrap "now" behind a project-owned `Clock` protocol with a `now() -> datetime`, inject
it into the ingest service through the constructor, and register it in the DI container.

**Rationale**: clock validation (future tolerance, maximum age) is the one rule that cannot be
tested repeatably against a real clock. CLAUDE.md §7 already asks for third-party libs behind a thin
project-owned interface and for dependencies injected rather than imported; `timezone.now()` called
inline is exactly the global dependency that makes a test non-repeatable. A `FrozenClock` fake then
makes every boundary case deterministic.

**Alternatives rejected**:
- *`timezone.now()` inline plus `freezegun`* — adds a dependency to fix a design smell, and only
  works from the outside.

---

## R-06: Enforcing the settings singleton

**Decision**: a `CheckConstraint(condition=Q(id=1))` on the model, plus a repository method that
does `get_or_create(id=1, defaults=...)`.

**Rationale**: the constraint is enforced by the database, so a second row is impossible no matter
which code path tries — including the Django admin and a shell session. `get_or_create` in the
repository means the first read materializes the defaults, so no data migration is needed for the
settings row and a fresh database is immediately usable.

**Where it lives**: `get_or_create` is an ORM call, so it belongs to the repository, not to a
`Model.load()` classmethod. Models stay pure entities per the constitution.

**Alternatives rejected**:
- *`save()` override forcing `pk=1`* — no database guarantee; a `bulk_create` or raw insert slips
  past it. Can be added as a convenience on top, but not as the enforcement.
- *A data migration creating row 1* — still needs the constraint to stop a second row, and adds a
  migration that does nothing the `get_or_create` default does not.

---

## R-07: Rejection reasons as stable codes

**Decision**: `reason` is a stable `snake_case` code, not prose:
`unknown_hymn`, `viewed_at_in_future`, `viewed_at_too_old`, `invalid_event`.

**Rationale**: the spec says the app logs the reason and deletes the event. A code is greppable in
app logs and safe to switch on; free text is neither, and it would change whenever a message is
reworded. The human-readable explanation belongs in the contract document, where it can also be
translated app-side.

This refines FR-009 rather than contradicting it — the spec asks for "a reason", and the offending
value still appears alongside the code in the per-event entry.

---

## R-08: View style for the service-window CRUD

**Decision**: two `APIView`s — `ServiceWindowListCreateAPI` and `ServiceWindowDetailAPI` — not a
DRF `ViewSet` or router.

**Rationale**: the project uses plain `APIView` everywhere and registers explicit `path()` entries
in each feature's `urls.py`. `ChordChartListAPI` / `ChordChartDetailAPI` is the same shape as what
this feature needs. Introducing a router here would make this the only feature with two URL
conventions.

---

## R-09: Validation split between DRF serializers and Pydantic DTOs

**Decision**: DRF serializers validate at the HTTP boundary (shape, types, ranges, query params);
validated data is converted to Pydantic DTOs which are what services accept and return. Services
never see `request` or a serializer.

**Rationale**: this is the project's existing division — the constitution requires "all user input
validated via DRF serializer before reaching the database" *and* "DTOs between layers use Pydantic
models". `features/members` already does exactly this (`BirthdayQueryParamSerializer` validates,
`MemberService.list_birthdays_by_month_range` takes plain values and returns `BirthdayDTO`).

**Per-event validation is deliberately not serializer-level**: the batch must survive one bad
event, so the *envelope* (is it a list, is it within `max_batch_size`) is serializer-validated and
rejects the whole request, while each *event* is validated individually inside the service and
routed to `accepted` or `rejected`. A `ListSerializer` with `many=True` would fail the whole batch
on the first bad element, which is precisely the behaviour FR-007 forbids.

---

## R-10: Reporting query parameters

**Decision**: `from` and `to` are `DateField`s in the local timezone, interpreted as an inclusive
day range and converted to an aware `[start_of_day, end_of_next_day)` half-open interval before
querying. `group_by` is a `ChoiceField` defaulting to `service`. Missing dates default to the last
30 days; a span over 366 days or a `from` after `to` is a `400`.

**Rationale**: `from` is a Python keyword, so the serializer field is declared with
`source="from_date"` / read via `validated_data["from"]` — it stays `from` on the wire because the
spec and the app contract say so. Inclusive dates match how a person asks the question ("the 1st to
the 31st"); the half-open conversion is what makes the last day's evening service actually appear.

---

## R-11: Seed data for `ServiceWindow` — RESOLVED with the church's real schedule

**Decision**: seed the four real windows in a data migration (`0006_seed_service_windows.py`).
Times confirmed by the church on 2026-08-07. §5 permits hand-written *data* migrations provided the
reason sits at the top of the file, which it does.

**Why it was blocked before**: the times are not derivable from the codebase, and seeding wrong ones
fails *silently* — every occurrence lands in the wrong bucket while the dashboard looks perfectly
healthy. That risk is gone now that the values are confirmed rather than guessed.

**Idempotent by `get_or_create` on name**, so re-running is safe and an admin's own window with the
same name is never clobbered. The reverse deletes only those four.

**A grace period, not padded end times** — see R-13. Stored windows keep the scheduled times.

**Weekday convention — decide this first, it is the easiest silent bug here.** Three conventions are
in play: Python's `datetime.weekday()` (Monday = 0), `isoweekday()` (Monday = 1), and Django's ORM
`__week_day` lookup (Sunday = 1). **Decision: `0 = Monday … 6 = Sunday`, Python's `weekday()`**,
because the window matching runs in Python (R-04) and any other choice needs a conversion at every
comparison. Sunday is therefore `6`, not `0`.

Whoever creates the windows — through the API or the admin — has to use that convention, so
**Sunday is `6`**. This is the single easiest thing to get wrong here, and getting it wrong produces
no error at all: the window simply never matches, and the views quietly fall back to day-collapsing.

> **Known follow-up**: the `schedule` feature stores `ScheduleType.weekday` in a *different*
> convention — `1 = Sunday … 7 = Saturday`, visible in `WEEKDAYS_MAP` at
> `features/schedule/services/schedule_service.py:15`. Two conventions now coexist in one codebase.
> That, and the fact that `ScheduleType` already is the church's service catalogue, is what feature
> 007 addresses.

---

## R-12: Observability

**Decision**: one structured JSON log line per ingest request summarising the outcome
(`received`, `stored`, `deduplicated`, `collapsed`, `rejected` counts, plus rejection codes with
counts). No per-event logging.

**Rationale**: the project logs structured JSON (CLAUDE.md §11) and already has request-id context
(`core/logging/context.py`). A summary line makes "is the app syncing correctly?" answerable from
logs. Per-event lines would be up to 200 lines per request for no extra insight.

**Not doing**: a Prometheus counter per ingest outcome. The project has `django_prometheus` wired,
so it is available later, but nothing in the spec asks for alerting on this and unused metrics are
cost without a consumer.

---

## R-13: Services that run long — grace period at match time

**Decision**: window matching extends past `end_time` by `window_grace_minutes`, a new field on the
settings singleton (default 30). The **start** is never extended.

**Rationale**:
- Services run over. A hymn opened at 21:20 in a Culto Dominical scheduled to 21:00 is that
  service, and without a tolerance it would fall out to day-collapsing — quietly under-counting the
  services that ran long, which are exactly the memorable ones.
- The asymmetry is deliberate: someone opening a hymn *before* the service is preparing or
  browsing, not singing with the congregation. Extending the start backwards would fold personal
  weekday use into services.

**Why a setting and not padded `end_time` values**: an admin editing "Culto Dominical" should see
`21:00` — the time the church actually publishes — not `21:30`. Padding the stored data makes the
window rows lie about the schedule, and it spreads the tolerance across every row instead of one
tunable place. As a read-time value it also re-interprets past history the moment it changes,
without touching a stored event.

**Comparison on datetimes, not times**: `end_time + grace` on a bare `TimeField` wraps — 23:50 plus
30 minutes becomes 00:20, and `start <= t < 00:20` is false for everything. Building both bounds as
datetimes on the event's local date makes a late-night window behave correctly. Covered by a test.

**Alternatives rejected**:
- *Grace on both ends* — folds pre-service browsing into the service, above.
- *Per-window grace column* — more knobs than the church needs, and every window would carry the
  same 30 by default anyway.
