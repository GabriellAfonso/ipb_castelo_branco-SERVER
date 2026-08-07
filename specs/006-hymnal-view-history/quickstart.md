# Quickstart: Hymnal View History

Runnable checks that prove the feature works end to end. Contract details live in
[contracts/](contracts/); this file is how you exercise them.

## Prerequisites

- Python 3.14 (pyenv)
- PostgreSQL running, `.env` configured at project root
- Migrations applied: `python manage.py migrate`
- At least one `Hymn` in the database and one admin user
- `$ADMIN_TOKEN` — an access token for a user whose profile has `is_admin = True`

```bash
cd server
export BASE=http://localhost:8000/ipbcb
```

---

## 1. Ingest works without a login

```bash
curl -sX POST "$BASE/api/hymnal-history/events/" \
  -H "Content-Type: application/json" \
  -d '{"events":[{
        "client_event_id":"5b1f9a4e-1c2d-4f3a-9b8c-7d6e5f4a3b2c",
        "hymn_id":1,
        "device_id":"device-a",
        "viewed_at":"2026-08-09T19:32:11-03:00",
        "duration_seconds":47,
        "app_version":"1.4.2","platform":"android"}]}'
```

**Expected**: `201`, the id in `accepted`, `rejected` empty. No `Authorization` header was sent and
the event is stored with `user = null`.

## 2. Re-sending the same batch is idempotent

Run the exact command from step 1 again.

**Expected**: `201`, the same id in `accepted`. Then confirm nothing was duplicated:

```bash
python manage.py shell -c "
from features.songs.models.hymnal_history import HymnalViewEvent
print(HymnalViewEvent.objects.count())"
```

**Expected**: `1`. This is the property that lets the app delete its local copy after a timed-out
sync.

## 3. One bad event does not block the rest

```bash
curl -sX POST "$BASE/api/hymnal-history/events/" \
  -H "Content-Type: application/json" \
  -d '{"events":[
        {"client_event_id":"11111111-1111-4111-8111-111111111111","hymn_id":1,
         "device_id":"device-b","viewed_at":"2026-08-09T19:35:00-03:00","duration_seconds":40},
        {"client_event_id":"22222222-2222-4222-8222-222222222222","hymn_id":999999,
         "device_id":"device-b","viewed_at":"2026-08-09T19:36:00-03:00","duration_seconds":40}]}'
```

**Expected**: `201`. `accepted` contains `1111…`; `rejected` contains
`{"client_event_id":"2222…","reason":"unknown_hymn"}`. The good event is stored.

## 4. Write-time collapse

Send two events, same hymn, same device, 4 minutes apart (inside the default 10-minute window):

```bash
curl -sX POST "$BASE/api/hymnal-history/events/" \
  -H "Content-Type: application/json" \
  -d '{"events":[
        {"client_event_id":"33333333-3333-4333-8333-333333333333","hymn_id":1,
         "device_id":"device-c","viewed_at":"2026-08-09T19:40:00-03:00","duration_seconds":35},
        {"client_event_id":"44444444-4444-4444-8444-444444444444","hymn_id":1,
         "device_id":"device-c","viewed_at":"2026-08-09T19:44:00-03:00","duration_seconds":35}]}'
```

**Expected**: `201` with **both** ids in `accepted`, but only **one** row stored for `device-c`.
This is the "left the hymn and came back" case.

## 5. Clock validation

```bash
# viewed_at far in the future
curl -sX POST "$BASE/api/hymnal-history/events/" -H "Content-Type: application/json" \
  -d '{"events":[{"client_event_id":"55555555-5555-4555-8555-555555555555","hymn_id":1,
       "device_id":"device-d","viewed_at":"2030-01-01T12:00:00-03:00","duration_seconds":40}]}'
```

**Expected**: `201` with the id in `rejected`, reason `viewed_at_in_future`. Repeat with a date
older than `max_past_days` for `viewed_at_too_old`.

## 6. Batch too large fails as a whole

Send `max_batch_size + 1` events.

**Expected**: `400`, `error_code: "VALIDATION_ERROR"`, nothing stored. This is the only case where
one problem affects the other events in the request.

## 7. Occurrences collapse across devices

Ingest the same hymn from three different `device_id`s, all inside one service window, then:

```bash
curl -s -H "Authorization: Bearer $ADMIN_TOKEN" \
  "$BASE/api/hymnal-history/occurrences/?from=2026-08-01&to=2026-08-31&group_by=service"
```

**Expected**: `200` with **one** occurrence for that hymn, `device_count: 3`, and a non-null
`service_window_name`. Three people, one occurrence — the core rule of the feature.

Then ingest the same hymn on a weekday afternoon outside every window and request again:
**expected** a second occurrence with `service_window_id: null`, bucketed by calendar day.

## 8. Grouping does not change collapsing

```bash
for g in service day week month; do
  curl -s -H "Authorization: Bearer $ADMIN_TOKEN" \
    "$BASE/api/hymnal-history/occurrences/?from=2026-08-01&to=2026-08-31&group_by=$g" \
    | python -c "import sys,json; print('$g', len(json.load(sys.stdin)['occurrences']))"
done
```

**Expected**: the same count four times, with only the `bucket` labels differing.

## 9. Ranking counts occurrences, not events

```bash
curl -s -H "Authorization: Bearer $ADMIN_TOKEN" "$BASE/api/hymnal-history/top-hymns/"
```

**Expected**: `200`, ordered by `occurrence_count` descending. The hymn from step 7 shows
`occurrence_count: 1` for that service despite three devices. Hymns never viewed are absent.

## 10. Settings readable anonymously, writable only by an admin

```bash
curl -s "$BASE/api/hymnal-history/settings/"                       # 200, no auth
curl -sX PATCH "$BASE/api/hymnal-history/settings/" \
  -H "Content-Type: application/json" -d '{"min_seconds_to_count":45}'   # 401
curl -sX PATCH "$BASE/api/hymnal-history/settings/" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" -d '{"min_seconds_to_count":45}'   # 200
curl -sX PATCH "$BASE/api/hymnal-history/settings/" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" -d '{"min_seconds_to_count":0}'    # 400 with field_errors
```

**Then re-run step 9**: the counts must be **identical**. Changing a setting affects future
behaviour only and never rewrites history.

## 11. Service window CRUD, and history survives it

```bash
curl -sX POST "$BASE/api/hymnal-history/service-windows/" \
  -H "Authorization: Bearer $ADMIN_TOKEN" -H "Content-Type: application/json" \
  -d '{"name":"Culto de Teste","weekday":6,"start_time":"19:00","end_time":"21:00"}'

# invalid: end before start
curl -sX POST "$BASE/api/hymnal-history/service-windows/" \
  -H "Authorization: Bearer $ADMIN_TOKEN" -H "Content-Type: application/json" \
  -d '{"name":"Inválido","weekday":6,"start_time":"21:00","end_time":"19:00"}'   # 400
```

Delete the window created above, then check the event count from step 2 again: **unchanged**.
Re-run step 7: the occurrence regroups by calendar day. History intact, interpretation changed.

Remember `weekday` is `0 = Monday … 6 = Sunday` — Sunday is `6`.

## 12. The existing Sunday repertoire flow is untouched

```bash
curl -s "$BASE/api/songs-by-sunday/" | head -c 200
pytest features/songs/tests/integration/test_register_plays_api.py -v
```

**Expected**: unchanged output, all existing tests green. `Played`/`Song` and
`HymnalViewEvent`/`Hymn` share no code path.

---

## Running the tests

```bash
cd server
pytest features/songs/tests/ -v          # this feature plus the existing songs suite
pytest                                    # full suite — nothing else may regress
mypy .                                    # settings in mypy.ini
```

The unit tests for occurrence collapsing and clock validation run without a database — they operate
on the pure functions described in `research.md` R-04 and R-05, with a `FrozenClock` fake.

## Rollback

Nothing here is destructive to existing data. To back the feature out:

```bash
python manage.py migrate songs <previous_migration_number>
```

The three new tables drop; `Song`, `Played`, `Hymn`, `ChordChart` and `Lyrics` are untouched by
every migration this feature adds.
