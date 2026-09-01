---

description: "Task list for Login Brute-Force Lockout"
---

# Tasks: Login Brute-Force Lockout

**Input**: Design documents from `specs/008-login-brute-force-lockout/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md)

**Tests**: Not optional. CLAUDE.md §10 requires a test for every new function, and this feature is
a security control — an untested lockout is an assumed lockout.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel — different file, no dependency on an incomplete task
- **[Story]**: which user story the task serves (US1…US5)

## Path Conventions

Django project rooted at `server/`. Cross-cutting infrastructure in `server/core/`; settings in
`server/config/settings/`.

---

## Remaining work

### Known gaps this feature deliberately leaves open

- **T-901 — DRF throttle counters are still per-process.** No `CACHES` is configured, so the
  `login` scope at `10/min` is enforced separately by each of the four gunicorn workers (roughly
  `40/min` in aggregate) and resets on every deploy. Fixing it means adding Redis to
  `compose.prod.yml` and a `CACHES` block. Out of scope for 008 — see spec, Out of Scope. The
  lockout added here does not depend on it.

- **T-902 — `/ipbcb/admin/` is reachable from the public internet.** The lockout raises the cost of
  guessing the superuser password but does not remove the target. Restricting the location at nginx
  (allow-list, or moving it behind the church VPN) remains the strongest mitigation. The nginx
  configuration lives in the `nginx-deploy` repository, so this task is executed there.

- **T-903 — An attacker with many source addresses still gets five guesses per address against one
  username.** Accepted, with the reasoning in spec, Residual Risk. Revisit if the access-attempt
  table ever shows a distributed pattern; `AXES_LOCKOUT_PARAMETERS` is where it would change.

- **T-904 — No alert on lockout.** Attempts are recorded in `axes_accessattempt` and visible in the
  Django admin, but nobody is told. Sentry is already configured (`prod.py`); a hook on the
  `user_locked_out` signal would surface it. Not implemented — this project has no on-call.

- **T-906 — A successful API login does not reset the failure count.** `AXES_RESET_ON_SUCCESS`
  is driven by Django's `user_logged_in` signal, which only `django.contrib.auth.login()` sends;
  the JWT flow creates no session. The admin login does reset. Consequence: a member who mistyped
  four times and then logged in successfully is still one mistake away from a lockout for the rest
  of the 30-minute window. Fixing it means emitting `user_logged_in` from `LoginAPI`, which also
  starts writing `User.last_login` on every API login — a behaviour change worth deciding on
  separately. Reasoning in plan.md D-8.

### Deployment steps for this feature

- **T-905 — Run `manage.py migrate` on deploy.** The library ships its own migrations for
  `axes_accessattempt` and `axes_accesslog`. `compose.prod.yml` already runs `migrate --noinput`
  before gunicorn starts, so no deployment change is needed — this entry exists so the two new
  tables are not a surprise in the next schema review.
