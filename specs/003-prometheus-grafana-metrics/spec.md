# Feature Specification: Application Metrics with Prometheus & Grafana

**Feature Branch**: `003-prometheus-grafana-metrics`

**Created**: 2026-06-19

**Status**: Implemented

**Input**: User description: "Add application metrics to the Django API using Prometheus and Grafana for monitoring request performance, database queries, and business events."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Infrastructure Metrics Collection (Priority: P1)

As a DevOps engineer, I want the Django API to automatically expose RED metrics (Rate, Errors, Duration) so that I can monitor application health without modifying application code.

**Why this priority**: Without baseline request metrics, no other monitoring is possible. This is the foundation all other metrics build on.

**Independent Test**: Can be fully tested by sending requests to the API and verifying that `/metrics` returns Prometheus-formatted data containing request count, latency histograms, and error counts.

**Acceptance Scenarios**:

1. **Given** the Django API is running, **When** Prometheus scrapes the `/metrics` endpoint, **Then** it receives valid Prometheus exposition format data containing HTTP request metrics (count, duration, status code).
2. **Given** a request is made to any API endpoint, **When** the `/metrics` endpoint is queried, **Then** the request is reflected in the rate, latency histogram, and status code counters.
3. **Given** the `/metrics` endpoint is accessed, **When** no authentication token is provided, **Then** the endpoint still responds successfully (unauthenticated access).

---

### User Story 2 - Database Query Monitoring (Priority: P2)

As a DevOps engineer, I want database query metrics (count and duration) automatically collected so that I can identify slow queries and database bottlenecks.

**Why this priority**: Database performance is the most common bottleneck in Django applications. Visibility into query patterns is critical for troubleshooting.

**Independent Test**: Can be tested by triggering API endpoints that perform database queries and verifying that database operation metrics appear in the `/metrics` output.

**Acceptance Scenarios**:

1. **Given** the database engine is configured with the Prometheus wrapper, **When** any ORM query executes, **Then** the query count and duration are recorded in Prometheus metrics.
2. **Given** multiple database operations occur, **When** the `/metrics` endpoint is queried, **Then** metrics distinguish between different database operation types.

---

### User Story 3 - Business Event Tracking (Priority: P3)

As a product owner, I want key business events (logins, schedule operations, song interactions) tracked as metrics so that I can understand usage patterns and feature adoption.

**Why this priority**: Business metrics provide product insights beyond technical health, but depend on the metrics infrastructure from P1 being in place.

**Independent Test**: Can be tested by performing login, schedule, and song operations, then verifying corresponding counters increment in the `/metrics` output.

**Acceptance Scenarios**:

1. **Given** a user logs in with credentials, **When** login succeeds, **Then** a success counter increments with label `login_type=credentials`.
2. **Given** a user logs in via Google OAuth, **When** login fails, **Then** a failure counter increments with label `login_type=google`.
3. **Given** a schedule is generated, **When** the operation completes, **Then** a schedule generation counter increments.
4. **Given** a user registers song plays, **When** the registration completes, **Then** a play registration counter increments.

---

### User Story 4 - Metrics Visualization (Priority: P4)

As a DevOps engineer, I want a pre-configured Grafana dashboard so that I can visualize application metrics without manual dashboard setup.

**Why this priority**: Visualization makes metrics actionable. Without dashboards, raw Prometheus data is hard to interpret. Depends on all prior stories.

**Independent Test**: Can be tested by accessing Grafana, opening the provisioned dashboard, and verifying panels display data from Prometheus for request rate, latency percentiles, error rate, DB query duration, and business counters.

**Acceptance Scenarios**:

1. **Given** Grafana is running with provisioned datasource, **When** I open the default dashboard, **Then** I see panels for request rate, latency (p50/p95/p99), error rate, DB query duration, and business event counters.
2. **Given** Prometheus is scraping the Django API, **When** I view the Grafana dashboard after traffic, **Then** graphs show real-time data from the running application.

---

### Edge Cases

- What happens when the Prometheus container is down? The Django API must continue serving requests normally — metrics collection must not block request processing.
- What happens when the `/metrics` endpoint receives high traffic? It should not impact API performance for regular clients.
- What happens when a custom business metric label has an unexpected value? Prometheus client libraries handle this gracefully with default behavior.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST expose a `/metrics` endpoint that returns Prometheus exposition format data.
- **FR-002**: The `/metrics` endpoint MUST be accessible without authentication.
- **FR-003**: The `/metrics` endpoint MUST NOT be behind the `/ipbcb/` base path prefix — it must be accessible directly at the root level for container-internal scraping.
- **FR-004**: System MUST automatically collect RED metrics: request rate (by endpoint, method, status code), request latency histogram (by endpoint), and error rate (4xx, 5xx by endpoint).
- **FR-005**: System MUST automatically collect database metrics: query count and duration per database operation.
- **FR-006**: System MUST track business events via custom counters: login success/failure (by login type: credentials vs google), schedules generated, schedules saved, play registrations, chord chart views, lyrics views.
- **FR-007**: Business event metrics MUST be instrumented in the service layer, not in views, following clean architecture constraints.
- **FR-008**: System MUST include a Prometheus container configured to scrape the Django `/metrics` endpoint.
- **FR-009**: System MUST include a Grafana container with Prometheus pre-configured as the default datasource.
- **FR-010**: System MUST provision a Grafana dashboard displaying: request rate, latency p50/p95/p99, error rate, DB query duration, and business event counters.
- **FR-011**: Metrics collection MUST NOT impact existing logging or exception handling behavior.
- **FR-012**: Metrics collection failure MUST NOT block or degrade normal API request processing.

### Key Entities

- **Metric**: A named measurement exposed in Prometheus format (counter, histogram, gauge). Identified by name and label set.
- **Dashboard**: A collection of visualization panels in Grafana, pre-provisioned via configuration files.
- **Scrape Target**: The Django `/metrics` endpoint that Prometheus polls at regular intervals.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All API requests are automatically counted and timed — 100% of endpoints covered without per-endpoint instrumentation.
- **SC-002**: Database query volume and duration are visible — operators can identify the top slow queries within 5 minutes of accessing the dashboard.
- **SC-003**: Business events (logins, schedules, song plays) are tracked — product owners can see daily usage counts per feature.
- **SC-004**: A pre-built dashboard shows application health at a glance — no manual Grafana configuration needed after deployment.
- **SC-005**: Metrics collection adds no user-perceptible latency to API responses.

## Assumptions

- Prometheus and Grafana run as Docker containers alongside the Django API in the same Docker network.
- Prometheus scrape interval uses standard default (15 seconds).
- Grafana is accessible on a development port — no production-grade auth needed for Grafana itself.
- The existing `docker-compose.yml` is the deployment target for adding new containers.
- Business metrics cover the current domain services (accounts, songs, schedule) — new domains added later will follow the same pattern.
- Grafana dashboard is provisioned via YAML/JSON files, not manually created through the UI.
