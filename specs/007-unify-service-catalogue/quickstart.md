# Quickstart: Unified Church Service Catalogue

This is the **acceptance gate**, not a tour. The feature's entire risk is that 91 rota rows survive
unchanged, so the procedure is: capture, migrate, capture, diff.

Run every step against a **restored production dump**. Running it against an empty database proves
nothing (FR-006).

## Prerequisites

```bash
cd /c/Users/gabri/Projetos/Ipb_castelo_branco/backend
export PATH="$PWD/.venv_windows/Scripts:$PATH"
export DB="docker exec ipbcb-db-dev psql -U gabrielafonso -d ipbcb"
```

- A production dump restored into `ipbcb-db-dev`
- **A second copy of that dump kept outside the repository** — you will restore more than once
- `.venv_windows` active; `*.sql*` is git-ignored

---

## 0. Baseline — capture before touching anything

```bash
$DB -c "\copy (select id, weekday, time, name from schedule_scheduletype order by id) \
  to '/tmp/before_services.csv' csv header"
$DB -c "\copy (select id, date, schedule_type_id, member_id from schedule_monthlyschedule order by id) \
  to '/tmp/before_rota.csv' csv header"
$DB -c "\copy (select id, member_id, schedule_type_id, available, weight from schedule_memberscheduleconfig order by id) \
  to '/tmp/before_configs.csv' csv header"

curl -s -H "Authorization: Bearer $MEMBER_TOKEN" \
  "http://localhost:8000/api/schedule/current/" > /tmp/before_current.json
```

**Expected baseline**: 3 services (ids 1, 2, 3), 91 rota rows, 24 member configs.

```bash
$DB -tAc "select count(*) from schedule_monthlyschedule;"   # 91
```

---

## 1. Migrate

```bash
cd server && python manage.py migrate
```

**Expected**: `core.0001`, `core.0002`, `core.0003`, `schedule.0002`, `songs.0007` all applied, no
errors. `core.0001` and `schedule.0002` must report as applied without touching the table.

---

## 2. The diff that decides everything

```bash
$DB -c "\copy (select id, date, schedule_type_id, member_id from schedule_monthlyschedule order by id) \
  to '/tmp/after_rota.csv' csv header"
$DB -c "\copy (select id, member_id, schedule_type_id, available, weight from schedule_memberscheduleconfig order by id) \
  to '/tmp/after_configs.csv' csv header"

diff /tmp/before_rota.csv /tmp/after_rota.csv        # MUST be empty
diff /tmp/before_configs.csv /tmp/after_configs.csv  # MUST be empty
```

**Any output here fails the feature.** No renumbering, no lost rows, no repointed foreign keys.

Then the services, which *do* change — but only by gaining columns:

```bash
$DB -c "select id, weekday, start_time, end_time, active, takes_rota, name from core_churchservice order by id;"
```

**Expected**:

| id | weekday | start | end | active | takes_rota | name |
|----|---------|-------|-----|--------|------------|------|
| 1 | 3 | 19:30 | 20:30 | t | t | Terça de Oração |
| 2 | 5 | 19:30 | 20:30 | t | t | Quinta de Oração |
| 3 | 1 | 19:30 | 21:00 | t | t | Domingo Liturgia de Adoração |
| 4 | 1 | 09:00 | 10:00 | t | **f** | Escola Bíblica Dominical |

Ids 1–3 unchanged, names unchanged, weekdays unchanged. Row 4 is the only insert.

---

## 3. The app must not notice

```bash
curl -s -H "Authorization: Bearer $MEMBER_TOKEN" \
  "http://localhost:8000/api/schedule/current/" > /tmp/after_current.json
diff /tmp/before_current.json /tmp/after_current.json   # MUST be empty
```

Same service ids, same names as object keys, same members on the same dates.

---

## 4. Escola Bíblica Dominical must not enter the rota

```bash
curl -sX POST -H "Authorization: Bearer $ADMIN_TOKEN" -H "Content-Type: application/json" \
  -d '{"year":2026,"month":9}' "http://localhost:8000/api/schedule/generate/" \
  | python -c "import sys,json; print(sorted({i['schedule_type']['name'] for i in json.load(sys.stdin)['items']}))"
```

**Expected**: exactly the three rostered services. If "Escola Bíblica Dominical" appears, `takes_rota`
is not being honoured (SC-009).

---

## 5. Deleting a service can no longer destroy the rota

```bash
curl -sX DELETE -H "Authorization: Bearer $ADMIN_TOKEN" \
  "http://localhost:8000/api/hymnal-history/service-windows/3/"
```

**Expected**: `409` naming the service and the number of rota entries. Then confirm nothing was lost:

```bash
$DB -tAc "select count(*) from schedule_monthlyschedule;"   # still 91
```

This is the hazard the feature closes. Before it, this call would have returned `204` and left 60
rota rows behind out of 91.

Deactivating must work instead:

```bash
curl -sX PATCH -H "Authorization: Bearer $ADMIN_TOKEN" -H "Content-Type: application/json" \
  -d '{"active":false}' "http://localhost:8000/api/hymnal-history/service-windows/3/"
```

---

## 6. One weekday convention

```bash
grep -rn "WEEKDAYS_MAP\|calendar.SUNDAY\|calendar.TUESDAY" server/ ; echo "--- must be empty ---"
grep -rn "weekday" server/ --include="*.py" | grep -v tests | grep -v migrations
```

**Expected**: no `WEEKDAYS_MAP`, and every weekday translation going through
`core/domain/weekday.py` (SC-005).

Then prove both features agree:

```bash
pytest features/schedule/tests/ features/songs/tests/ -q
```

## 7. Services on any weekday generate

Create a Saturday service with `takes_rota: true`, generate a preview, confirm rows appear for it,
then delete it. Before this feature it would have produced nothing, silently (US4).

---

## 8. Rollback works

Non-negotiable (FR-005, SC-008). Restore the dump again, migrate forward, then back:

```bash
cd server
python manage.py migrate songs 0006
python manage.py migrate schedule 0001
python manage.py migrate core zero
$DB -tAc "select count(*) from schedule_monthlyschedule;"   # still 91
$DB -tAc "select count(*) from schedule_scheduletype;"      # 3 — table name restored
```

**Test this, do not assume it.** A reverse migration that has never been run is not a rollback plan.

---

## 9. Full regression

```bash
cd server
pytest                # every existing test, unchanged
mypy .
cd .. && ruff check server/ && ruff format --check server/
```

The rota tests in `features/schedule/tests/` are the ones that matter most — they exercise the
generator whose weekday handling changed.

---

## Order of work

Do **task 1 (the `PROTECT` change) first and on its own**. It is a small, independently shippable
fix that closes a live data-loss path, and it does not depend on any of the unification work.
