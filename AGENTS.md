# RomM (romm-cn) - Repository Guide for Contributors & Agents

RomM is a self-hosted ROM manager: scan a game library off disk, enrich it with metadata from 10+ providers, and browse it in a web UI. This fork, romm-cn, removes the in-browser players and the features built on them, and translates scanned game names and summaries to Simplified Chinese. `README.md` and `ChangeFromUpstream.md` list every difference from upstream.

---

The frontend talks to the backend over `/api/*` (REST) and `/ws` (Socket.IO). TypeScript types are **generated** from the backend's OpenAPI schema into `frontend/src/__generated__/` - the backend is the single source of truth for API shapes.

## Deep-dive references

- **`project.md`** - what the fork is, its components and how they work together.
- **`docs/BACKEND_ARCHITECTURE.md`** - directory map, ER diagram, every endpoint, auth/scopes, tasks.
- **`docs/FRONTEND_ARCHITECTURE.md`** - routing, stores, services, theming, build tooling.
- **`DEVELOPER_SETUP.md`** - Docker and manual local setup (mock library, `.env`, services).
- **`CONTRIBUTING.md`** - contribution flow, **AI-assistance disclosure**, translations.
- **`HANDOFF.md`**, **`tech_issue.md`**, **`test_method.md`**, **`test_troubleshooting.md`** - the current state of the work, known tooling pitfalls, how to run each test, and test failures already solved.

---

## Stack-specific guidance

`frontend/AGENTS.md` (frontend layout and commands) and `backend/AGENTS.md` (backend commands) load when you work in those directories. The UI lives in `frontend/src/`.

---

## Skills - load the focused guide for your task

These live in `.claude/skills/` and carry the detailed rules. Invoke the one that matches what you're doing:

| Skill                 | When                                                                                                                                                      |
| --------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `frontend-components` | Building/editing any frontend component - tiers (lib/shared/feature), file & SFC conventions, barrels, anti-patterns.                                     |
| `frontend-theming`    | Colors, tokens, light/dark themes, visual language - and the **zero-hex-literal** policy.                                                                 |
| `frontend-input`      | Interactive components, focus/spatial navigation, gamepad/keyboard, breakpoints & responsive layout.                                                      |
| `frontend-patterns`   | Feature behavior - errors/snackbars, loading, sockets, state persistence, pagination, forms, permissions, destructive confirmations.                      |
| `frontend-i18n`       | Any user-visible string or change under `frontend/src/locales/**`.                                                                                        |
| `backend-development` | Endpoints, handlers, models, schemas, metadata adapters, tasks, migrations under `backend/`.                                                              |
| `review-polish`       | Before committing / opening a PR / declaring done - the self-review pass (comments, duplication, naming, test typing) plus the checks that keep CI green. |
| `security-audit`      | Vetting a diff (release tag range or PR) for anything malicious or a security regression - supply chain, egress, auth/injection, CI, provenance.          |

---

## Talking to the user

- Always answer the user in Simplified Chinese: replies, progress updates, summaries, questions and end-of-task reports. Keep code, commands, file names, identifiers and quoted error output as they are.
- This covers chat only. Files in the repo still follow the English-first rule below.

## Branches and pull requests

- The fork's `master` branch only mirrors the upstream RomM `master`. It is used for upstream syncs and carries none of the fork's changes. Never commit or push to it.
- `sync/upstream-all` is the fork's daily branch: it carries the fork's changes on top of upstream. Branch from it and push follow-up work there. CI runs on every push to it.
- Do not open pull requests unless the user explicitly asks for one. Push work to a feature or sync branch and report it.
- When syncing from upstream, do not re-add features the fork deleted: streaming, netplay, the in-browser players (EmulatorJS, Ruffle, js-dos, PICO-8, EasyRPG), saves, states and user screenshots, firmware, play sessions, memory cards, device save sync, device push install, and age limits. Replay those removals on top of the upstream code and keep the fork-only additions listed in `ChangeFromUpstream.md`.
- Upstream migrations that only touch removed tables or features are skipped. The rest are re-chained after the fork's head; `ChangeFromUpstream.md` records the current order.

## Change documentation

- For every major change relative to the fork baseline, update `README.md` and `ChangeFromUpstream.md` in the same change.
- In `README.md`, keep a concise "Changes from the fork baseline" section with one short line per change category and identify the baseline commit.
- In `ChangeFromUpstream.md`, identify the baseline commit and document each change category, affected files, and the specific behavior added, changed, or removed.
- Treat feature or API additions and removals, configuration-default changes, persistence changes, and integration changes as major changes. Update both documents before considering the change complete.
- Compare the actual diff with the baseline; do not rely on commit titles alone.
- `README.md` is written in Chinese for the fork's users. Every other `.md` file follows the English-first rule below.

---

## Repo-wide rules

**Disclose AI assistance in the PR.** RomM requires it (see `CONTRIBUTING.md`): state that AI was used and to what extent. This is mandatory and non-negotiable for agent-written contributions.
**Linting is via [Trunk](https://trunk.io)** (`trunk fmt && trunk check`), which wraps ruff, black, isort, ESLint, Prettier, and more, and runs in CI on every PR. **Never commit with `--no-verify`.**
**The backend owns the API contract.** Changed a response schema or route? Regenerate frontend types (`npm run generate`) and re-typecheck.
**Tests travel with code.** New logic gets a test; new endpoints get endpoint tests; new primitives get a Storybook story (+ `play()` if interactive).
**Verify before handoff.** Don't say "done" on UI work without testing it in the browser in both themes and all input modalities. See `review-polish`.
**English first.** Outside of language files and `README.md`, all code, comments, identifiers, `.md` files, and commit/PR messages are in English.
**No em-dashes.** Never use em-dashes (U+2014) when writing comments or text. Use commas, parentheses, or separate sentences instead. An em-dash string literal is code (an empty-value glyph) and stays allowed.
**Prefer a check to a model review.** A mechanical rule (an import, a character, a CSS pattern, an SFC shape) belongs in ESLint, `tsconfig`, or Trunk. When a review finding repeats, propose a check as a named follow-up; see `review-polish`.
**Keep comments short.** Comments should be concise, and focus on the "why" rather than the "what" (the code itself is the "what"). A comment is one or two lines; a docstring is one sentence plus `Args:`/`Returns:` when the signature needs it. Three or more lines of prose means you are explaining, not commenting. See `review-polish` for what to cut.
**Don't restate the code.** The code is self-documenting, so skip comments that narrate what a reader can already see (which button sits where, that something is disabled when empty, obvious ordering). Comment only non-obvious "why" that the code can't convey on its own.
**One home per value.** Before declaring a constant, type, limit, regex, or store getter, search for an existing one and import it. Validation limits live on the model and are imported by endpoints; a type lives in the component that owns it and is exported. Don't add a near-duplicate that differs only by sorting, and don't invent an identity scheme where a foreign key already exists.
**Never commit secrets.** Never commit secrets (API keys, passwords, tokens, etc.) to the repo. Use environment variables or secret management tools instead.
**Don't explain a change.** Avoid comments that explain why a change was made to the code, or that record what the code used to do. Focus instead on the current behaviour of the code and how it works. Reasons for a change go in the commit message and the PR body.
**Python tools live in `backend/tools/`.** Standalone dev/test utilities and scripts (not part of the app runtime) go in `backend/tools/`, not scattered across `backend/`.
**Link PRs to issues.** In the PR description, use `Fixes #XXXX` for issue/bug fixes and `Closes #XXXX` for feature implementations.
**Use the PR template.** Base every PR description on `.github/PULL_REQUEST_TEMPLATE.md`.
**Show UI changes in the PR.** A PR that touches anything visible ships with at least one screenshot under the template's `Screenshots` heading, captured from the running app during the `review-polish` browser pass. Save the files outside the repo and never commit them.
**Diagram architectural changes in the PR.** When a change moves a boundary (a new service, task, or provider in a path, a model relationship, a different call path across layers, an auth or socket flow), the PR description carries a `mermaid` block showing it. Draw what changed, not the whole system. See `review-polish`.

---

## Never run the full backend test suite locally

A bare `uv run pytest` (or `pytest -vv`) over `backend/` runs serially, takes 20+ minutes, and
burns a huge number of tokens on output. Don't do it, even to "double check" at the end.

Instead, select the tests affected by the change and run only those. Add `-n auto` when the
selection spans a directory or more: the suite is set up for `pytest-xdist` (one database per
worker).

```bash
cd backend
uv run pytest tests/path/to/test_file.py                # one file
uv run pytest tests/path/to/test_file.py::test_name     # one test
uv run pytest -n auto tests/handler/ tests/endpoints/   # affected areas, in parallel
uv run pytest -k "scan or queue"                        # by name pattern
```

It gains nothing on a single file or test, and `--pdb` and `-s` don't work under it, so drop it
when debugging.

Pick the targets from the diff: the test file mirroring each changed module
(`backend/<area>/x.py` → `backend/tests/<area>/test_x.py`), plus the tests of the
callers of anything whose signature or behavior you changed (`grep` for the symbol).

CI runs the whole suite on every push to `sync/upstream-all` and on PRs (`pytest.yml`,
MariaDB + PostgreSQL). That is the place for full-suite coverage; local runs stay scoped.

**In a git worktree, run tests against a temporary database.** Every checkout shares
`romm_test`, and one on another branch can migrate it to a revision yours lacks, so
every test errors in setup with `Can't locate revision`. Set `ROMM_TEST_DB_TAG` to a
tag unique to the worktree: the run creates and migrates `romm_test_tmp_<tag>` (one per
xdist worker), then drops it at the end. Never `stamp` or downgrade the shared `romm_test`.

```bash
ROMM_TEST_DB_TAG=my_worktree uv run pytest -n auto tests/handler/
```

---

## Environment setup

Each tool version is pinned in one file: Python in `.python-version`, uv as `ARG UV_VERSION` in `docker/Dockerfile`, and Node in `frontend/.nvmrc`. Don't install these by hand. Run `scripts/dev-setup.sh`, which installs the pinned toolchain, the backend and frontend dependencies, and the Trunk launcher, and skips anything already in place. Add `--db` to also install and start MariaDB with the pytest database (Debian/Ubuntu only). Rerun it whenever a version is wrong or a dependency is missing.

The backend's native dependencies (`psycopg-c`, `streaming-form-data`) do not build on Windows without the C build tools, so run the backend and its tests in Docker, WSL, or CI there. `tech_issue.md` has the details.

---

## Quick command reference

**Setup:** see `DEVELOPER_SETUP.md`. Docker path is `cp env.template .env` → `docker compose build` → `docker compose up -d` (app at `http://localhost:3000`).

**Lint (both stacks):** `trunk fmt && trunk check`.
