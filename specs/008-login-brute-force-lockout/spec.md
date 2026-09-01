# Feature Specification: Login Brute-Force Lockout

**Feature Branch**: `008-login-brute-force-lockout`

**Created**: 2026-08-31

**Status**: Draft

**Input**: User description: "Nosso Django atualmente tem algo muito arriscado: dá pra quebrar a
senha do admin por bruteforce."

## Overview

Every credential-checking entry point in this project accepts unlimited guesses.

`config/urls.py` publishes `admin.site.urls` at the public `/ipbcb/admin/`. The Django admin login
is a plain Django view, so the DRF throttles configured in `config/settings/base.py` do not touch
it — those apply only to DRF views. There is no lockout, no `limit_req` for that location in the
nginx deployment, and the password policy deliberately allows any password of six characters or
more (`constitution.md`, Security). An attacker can guess the superuser password at the rate the
four gunicorn workers can answer.

The API login is only marginally better. `POST /ipbcb/accounts/api/auth/login/` carries the `login`
throttle scope at `10/min`, but no `CACHES` backend is configured anywhere, so DRF's throttle
counters live in the per-process `LocMemCache`. With `--workers 4` the effective ceiling is roughly
`40/min`, and every deploy resets it to zero.

This feature adds **failed-attempt lockout** shared across workers, covering the Django admin and
the API login with the same mechanism and the same counters.

**Scope**: backend only. The Android app is affected as a consumer — it gains one new error
response to handle — but app changes are out of scope for this spec.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The admin password stops being guessable (Priority: P1)

Someone finds `/ipbcb/admin/` and starts guessing the superuser password from a script.

**Acceptance:**

1. **Given** no previous failed attempts, **When** the script posts 4 wrong passwords for `admin`
   from the same address, **Then** each response reports a normal login failure.
2. **Given** those 4 failures, **When** the script posts a 5th wrong password, **Then** that
   response is already `429` and the pair is locked.
3. **Given** the pair is locked, **When** the script posts the *correct* password, **Then** the
   response is `429` and no session is created.
4. **Given** a lockout in place, **When** 30 minutes pass with no further attempt, **Then** the next
   attempt is evaluated normally again.

### User Story 2 - A locked-out attacker does not lock out the congregation (Priority: P1)

The whole church shares one NAT address on the building WiFi (the same fact already documented for
the `hymnal_ingest` throttle, `specs/006-hymnal-view-history/research.md` R-02). One member
mistyping their password five times must not lock every other member out of the app.

**Acceptance:**

1. **Given** member `ana` has hit the failure limit from the church address, **When** member `bruno`
   logs in correctly from that same address, **Then** `bruno` receives tokens normally.
2. **Given** member `ana` is locked out from the church address, **When** `ana` logs in correctly
   from a different address, **Then** `ana` receives tokens normally.

### User Story 3 - Nobody can lock the admin out on purpose (Priority: P2)

Locking purely by username would let anyone deny the administrator access from anywhere by failing
five times against `admin`. The lockout key is therefore the **pair** (username, address), never
username alone.

**Acceptance:**

1. **Given** an attacker has locked `(admin, attacker-address)`, **When** the real administrator
   logs in from the church address, **Then** the login succeeds.

### User Story 4 - The Android app can tell a lockout from a wrong password (Priority: P2)

The app's only client contract is the canonical error envelope from `core/http/exceptions.py`. A
lockout must arrive in that same shape, not as the HTML page django-axes renders by default.

**Acceptance:**

1. **Given** a locked-out client, **When** it posts to the login endpoint, **Then** the body is
   `{"error_code": "ACCOUNT_LOCKED", "detail": ..., "cooloff_seconds": ...}` with status `429`.

### User Story 5 - A successful admin login clears the record (Priority: P3)

**Acceptance:**

1. **Given** 3 failed admin attempts for a pair, **When** a correct password is accepted, **Then**
   the counter returns to zero and the next failure is counted as the first.
2. **Given** 3 failed API attempts for a pair, **When** a correct password is accepted, **Then** the
   count is *unchanged* — the JWT flow creates no session and therefore emits no reset. The count
   drains through the 30-minute window instead (FR-005).

---

## Functional Requirements

- **FR-001**: Failed credential attempts are counted per `(username, client address)` pair.
- **FR-002**: The 5th consecutive failure for a pair locks that pair, and that 5th request is
  already answered with the lockout response — the count and the refusal happen together. The 4
  preceding attempts are answered normally (`401` for the API, the admin's own error page for the
  admin). The lock is evaluated *before* the password is checked, so a correct password offered
  while the count still stands at 4 succeeds; from the 5th failure onward nothing does.
- **FR-003**: A lockout expires 30 minutes after the last attempt against the locked pair. The same
  window bounds the counter: attempts older than 30 minutes are purged, so the limit means five
  failures *within* 30 minutes, not five since the beginning of time.
- **FR-004**: An attempt made **during** a lockout restarts the 30-minute window. A script that
  keeps hammering never gets back in.
- **FR-005**: A successful authentication **through the Django admin** resets the counter for that
  pair to zero. It does **not** reset for the API login: the reset is driven by Django's
  `user_logged_in` signal, which `django.contrib.auth.login()` sends and the JWT flow never does —
  `LoginAPI` issues tokens without creating a session. For the API, FR-003's rolling window is what
  clears a partial count. See [tasks.md](tasks.md) T-906.
- **FR-006**: The username used as the lockout key is normalised (trimmed, lowercased) before it is
  counted. Without this, `admin`, `Admin` and `ADMIN` are three separate budgets of five.
- **FR-007**: The client address is taken from `X-Forwarded-For` as set by nginx, discounting
  exactly one proxy. A client-supplied `X-Forwarded-For` must not become the lockout key.
- **FR-008**: Attempt records survive process restarts and are shared by all four workers.
- **FR-009**: A lockout response uses the canonical error envelope with `error_code`
  `ACCOUNT_LOCKED` and HTTP `429`, for the admin and the API alike.
- **FR-010**: Lockouts are visible and clearable by an administrator without a shell.
- **FR-011**: The lockout mechanism is disabled by default in the test settings, and switched on
  explicitly by the tests that exercise it.

## Non-Functional Requirements

- **NFR-001**: The counter must not be a per-process in-memory structure. See the `LocMemCache`
  problem described in the Overview.
- **NFR-002**: No new infrastructure service. The existing Postgres holds the attempt records.

---

## Out of Scope

- Configuring a shared cache (Redis) for the DRF throttles. The per-process `LocMemCache` ceiling
  described in the Overview is **not fixed by this feature** — it is recorded in
  [tasks.md](tasks.md) as known remaining work.
- CAPTCHA, e-mail notification on lockout, or IP blacklisting.
- Restricting `/ipbcb/admin/` to an internal network. Considered and not chosen for this feature;
  it remains the strongest available mitigation and stays open.
- Password complexity rules. Forbidden by `constitution.md`.

---

## Errors

| Situation | Status | `error_code` | Message |
|-----------|--------|--------------|---------|
| Attempt while `(username, address)` is locked | 429 | `ACCOUNT_LOCKED` | "Muitas tentativas de login. Tente novamente em 30 minutos." |

The response carries `cooloff_seconds` so the app can show a countdown instead of a fixed string.

---

## Residual Risk (accepted)

Locking by the `(username, address)` pair means an attacker who controls many source addresses gets
five guesses per address against a single username. This is accepted:

- Locking by address alone is not available — it would lock the whole congregation behind the church
  NAT address (User Story 2).
- Locking by username alone hands anyone a remote denial of service against the administrator
  (User Story 3).
- For the API login the DRF `login` throttle remains as a second, per-address layer.
- The Django admin has no second layer. Removing it from the public internet is the mitigation, and
  it is listed in [tasks.md](tasks.md).
