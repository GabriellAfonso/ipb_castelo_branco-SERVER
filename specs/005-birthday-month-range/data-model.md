# Data Model: Birthday Month Range Filter

## Existing Entities (No Changes)

### Member

No schema changes. Existing model used as-is.

| Field | Type | Notes |
|-------|------|-------|
| name | CharField(255) | Display name |
| gender | CharField ("M"/"F"/null) | Optional |
| birth_date | DateField (nullable) | Source field — month and day extracted |
| is_active | BooleanField | Filter: only active members |

## DTO Changes

### BirthdayDTO (updated)

| Field | Type | Before | After |
|-------|------|--------|-------|
| name | str | exists | unchanged |
| gender | str \| None | exists | unchanged |
| birth_day | int | exists | unchanged |
| birth_month | int | — | **added** |

No new entities. No migrations required.
