# Spec-driven development

Lightweight spec-driven development for FrostWatch Altiplano. Each spec states WHAT and WHY,
the requirements, and numbered acceptance criteria. We do not run the full cycle (plan, tasks,
analyze, checklist): a coding agent (Claude Code) implements from a spec, and the result is
checked against its acceptance criteria before the builder commits.

## Specs

| # | Spec | Module | Implemented by |
|---|---|---|---|
| 01 | [Backend and serving](01-backend-serving.md) | `backend/` | Claude Code |
| 02 | [Muse alert explanations](02-muse-explanations.md) | `backend/` | Claude Code |
| 03 | [Mobile app and UX](03-mobile-app-ux.md) | `mobile/` | Claude Code |

Out of scope here: features, label, split, training, evaluation and the Muse dataset
experiment (A vs B). They are owned by the ml session. Its only interface with these specs is
`docs/artifacts_contract.md`.

## Rules for every spec

- `CLAUDE.md` wins on any conflict. Shared contracts live in `docs/api_contract.md` and
  `docs/artifacts_contract.md`; a spec never redefines them, it references them.
- A number that the code did not compute never appears in the app, an alert or the README.
- Every acceptance criterion is checked by an automated test where possible, otherwise by a
  manual check written down in `docs/status.md`.
- Agents never write to git. When a spec is done, list the changed files and suggest a commit
  message for the builder.

## Status values

`draft` -> `approved` -> `implemented` -> `verified` (all acceptance criteria pass).
