# MUSE.md

Instructions for Muse Code in this repo. Project context lives in `docs/project-context.md` (single source of truth). Read it before starting any task.

## Hard rules

- **Commits are forbidden.** Never run `git commit`, `git push`, `git merge`, `git rebase`, `git tag` or any command that creates or rewrites history. Only the builder commits.
- You may edit files and run read-only git commands (`git status`, `git diff`, `git log`). When a change is ready, stop and suggest a commit message in English, prefixed with `[muse-code]`, for the builder to use.
- Work only on the bounded module you were given (agent tools, evaluation harness). Do not touch other parts of the repo.
- Never read, print or commit secrets. Do not open `.env`.
- Code, comments and docs in English. No em dashes.
