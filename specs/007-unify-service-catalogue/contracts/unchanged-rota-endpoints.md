# Contract: Rota Endpoints — Frozen

The three rota endpoints **must not change**. This document exists to pin their current shapes so
the migration can be verified against them, not to describe new behaviour.

FR-004: the Android app requires no change and must not be able to detect that anything happened.

---

## `GET /api/schedule/current/`

- **Auth**: `IsMemberUser` · **View**: `CurrentMonthlyScheduleAPI` · ETag-enabled

### Response `200`

```json
{
  "year": 2026,
  "month": 8,
  "schedule": {
    "Domingo Liturgia de Adoração": {
      "time": "19:30",
      "items": [
        {
          "date": "2026-08-02",
          "day": 2,
          "member": { "id": 7, "name": "..." },
          "schedule_type": { "id": 3, "name": "Domingo Liturgia de Adoração" }
        }
      ]
    }
  }
}
```

Grouped by service **name** as the object key. `time` is `HH:MM` from the service's start time.

**What the migration must not disturb**: the key is the service name, so renaming a service would
change the response shape. This is why "Domingo Liturgia de Adoração" keeps its name rather than
adopting the hymnal seed's "Culto Dominical".

`schedule_type.id` values 1, 2, 3 must be identical afterwards. The app caches them.

---

## `POST /api/schedule/generate/`

- **Auth**: `IsAdminUser` · **View**: `MonthlySchedulePreviewAPI` · does not write

### Request

```json
{
  "year": 2026,
  "month": 9,
  "fixed": [{ "schedule_type_id": 3, "date": "2026-09-06", "member_id": 10 }]
}
```

`year`/`month` omitted defaults to next month. Malformed entries in `fixed` are skipped silently.

### Response `200`

```json
{
  "year": 2026,
  "month": 9,
  "items": [
    {
      "date": "2026-09-06",
      "day": 6,
      "schedule_type": { "id": 3, "name": "...", "time": "19:30" },
      "member": { "id": 10, "name": "..." },
      "fixed": true
    }
  ]
}
```

Sorted by service name then date.

### The two behaviour changes that **are** expected here

Both are intended and both are verifiable:

1. **Escola Bíblica Dominical must not appear.** It is `takes_rota=False`. Generating a month after
   the migration must yield exactly the same three services as before (SC-009).
2. **Services on any weekday now generate.** The `WEEKDAYS_MAP` skip is gone (research R-05). No
   current service is affected — all three fall on mapped days — so today's output is unchanged.

Everything else — weighted selection, the least-used tie-break, pinned assignments — is untouched.

---

## `POST /api/schedule/save/`

- **Auth**: `IsAdminUser` · **View**: `MonthlyScheduleSaveAPI`

### Request

```json
{
  "year": 2026,
  "month": 9,
  "items": [{ "date": "2026-09-06", "schedule_type_id": 3, "member_id": 10 }]
}
```

Also accepts the nested form the preview returns (`{"schedule_type": {"id": 3}, "member": {"id": 10}}`)
— `_parse_schedule_save_payload` normalises both. That tolerance must survive.

### Response `200`

```json
{ "ok": true }
```

### Errors

| Status | When |
|--------|------|
| `400` | `year`/`month` missing or not integers |
| `409` | The month was first saved more than 30 minutes ago (`ScheduleOverwriteError`) |

**Replaces the whole month** — deletes and recreates inside a transaction. Unchanged by this feature.

---

## Verification

The gate is a **full before/after diff**, not a spot check (research R-09):

```bash
# before migrating
curl -s .../api/schedule/current/ > before.json
# after migrating
curl -s .../api/schedule/current/ > after.json
diff before.json after.json   # must be empty
```

Repeat for a generated preview of the same month with the same pinned assignments. Random selection
makes unpinned output non-deterministic, so **pin every position** when comparing previews — that
makes the generator's output fully determined and the diff meaningful.
