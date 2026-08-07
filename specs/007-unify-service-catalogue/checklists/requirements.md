# Specification Quality Checklist: Unified Church Service Catalogue

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-08-07
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

- **Deliberate deviation from "no implementation details"**: the spec names no framework, table or
  migration operation — those live in the plan. It does state *that* ids must be preserved by
  keeping data in place rather than copying it (Assumptions), because that constraint is the
  difference between a safe and an unsafe feature, not an implementation preference.

- **The open question is resolved.** A production backup was restored locally on 2026-08-07 and read
  directly. The convention is confirmed as `1 = Sunday … 7 = Saturday` (Terça=3, Quinta=5,
  Domingo=1). Nothing about this feature is now blocked on outside information.

- **Reading production changed the spec in one material way.** The two catalogues turned out not to
  be the same set: Escola Bíblica Dominical exists only on the hymn side and has no member rota.
  Merging without accounting for that would have silently started generating rota rows for Sunday
  mornings. FR-020 was added to separate "is held" from "takes a rota", and SC-009 verifies it.

- **The weekday trap was worse than described.** "Terça de Oração" is `weekday=3` in the rota table
  and `weekday=1` in the hymn table, and both numbers are valid in both conventions. Nothing about
  the value reveals which system it belongs to. A migration written under the wrong assumption would
  have kept generating rotas, on the wrong days, with no error.

- **Two guideline exceptions carried in from the conversation**, both already granted by the user and
  both requiring a written record during planning (FR-016, FR-017):
  1. `CLAUDE.md` §5 forbids hand-written schema migrations. A cross-app model move cannot be
     generated — the generator would emit a drop-and-recreate that destroys the rota history. The
     compensating control is FR-006: verification against real data.
  2. The shared layer has never held models and has never been an installed app. There is no written
     rationale for that anywhere — it simply never needed one.

- **FR-019 is a hard prerequisite, not a nicety.** `specs/schedule/` contains only a `.gitkeep`.
  Per §6.5 the rota domain's current behaviour must be documented before its code changes. That
  work is substantial: weighted random selection, pinned assignments, a 30-minute overwrite window,
  and a silently-skipped weekday map.

- **Risk concentration**: User Story 1 carries essentially all of the feature's risk. It is worth
  treating its verification (FR-006, SC-001, SC-002) as the acceptance gate for the whole feature.
