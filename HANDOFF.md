# Handoff

## State

- `master` mirrors upstream RomM at `7eae2b8ff` and carries no fork changes.
- `sync/upstream-all` is the daily branch. It holds the upstream sync plus the fork's removals and the cleanup commits below. It was pushed over SSH at `14ca67108` (remote tip verified with `git ls-remote`); the compose example commit after it is local until pushed.
- `.git-credentials` sits untracked at the root and is now ignored. Never stage or print it.

## Completed

Cleanup after the upstream sync, one commit per area on `sync/upstream-all`:

1. `6dfceda16` Backend:
   - Migration chain re-ordered to `0129 → 0152 → 0130 … 0150` (head `0150_roms_fs_name_lower_index`), so databases stamped `0152` by the older fork chain get 0130 to 0150.
   - Restored the non-age parts of upstream #5081: gallery cache invalidation on permission changes and default-group followers.
   - `tools/generate_test_data.py` rebuilt from upstream.
   - Removed stale test config, `utils/openapi.py` and `asyncssh`.
2. `beaa5b01b` CI:
   - Workflows run on pushes to `sync/upstream-all`.
   - Playwright install for the Storybook tests; e2e builds before previewing and uploads from the right folder.
   - Upstream-only jobs guarded, `FUNDING.yml` removed, `.git-credentials` ignored.
3. `a88e1861a` Docs:
   - `AGENTS.md` is the single instruction file and `CLAUDE.md` only imports it.
   - Architecture docs and skills updated.
   - Added `project.md`, `test_method.md`, `test_troubleshooting.md`; `tech_issue.md` extended.
4. `ef988664d` Frontend:
   - Fixed the Home stats widget crash in extended mode; removed always-zero stats cards and two no-op settings.
   - Deleted player-only files, the console assets and four unused dependencies.
   - Fixed stale tests and the save/sync wording in en_US and zh_CN.
5. `14ca67108` Docs: `README.md`, `ChangeFromUpstream.md`, this file, and the troubleshooting notes.
6. Compose example: `examples/docker-compose.romm-cn.yml` builds `docker/Dockerfile` (`slim-image`) as `romm-cn:local` instead of pulling `rommapp/romm`; README's install section documents it with the fresh-database, ScreenScraper and translator caveats.

## Remaining

- **Pytest fails in CI** on both MariaDB and PostgreSQL (run `40196488927`, step "Run python tests", about 4m40s). The logs need a signed-in GitHub account (the API returns 403 without admin auth, and `gh`'s token is invalid), so the failing tests are not known yet. This was the fork's first CI run, so failures may predate the cleanup.
- Push the compose example commit after the Pytest failure is understood.
- A Docker deploy test with the new compose example (fresh database).
- Not done by choice:
  - The translator stays as is (no switch, hard-coded zh-CN, re-translates on rescans, no Redis cache).
  - Orphaned i18n keys and small dead helpers in files shared with upstream stay, to keep syncs clean.
- Manual GitHub step: the default branch is `master`, so scheduled workflows run upstream's files. Disable scheduled workflows in the fork's Actions settings, or make `sync/upstream-all` the default branch.

## Key files and commands

- Change docs: `README.md`, `ChangeFromUpstream.md`. Rules: `AGENTS.md`. Overview: `project.md`. Tests: `test_method.md`.
- Migration order check without a database: parse `revision`/`down_revision` in `backend/alembic/versions/` (see `test_troubleshooting.md`).
- uv on this machine: `UV_PYTHON_INSTALL_DIR=<non-Roaming dir> uvx --from "uv==0.13.4" uv lock`.
- Formatters outside Trunk: `uvx --python 3.14 black@26.5.1`, `isort@8.0.1 --settings-path ../.trunk/configs/.isort.cfg`, `ruff@0.15.22 check --config ../.trunk/configs/ruff.toml` (from `backend/`).
- Push over SSH: `git push git@github.com:xiaosagemisery/romm-cn.git sync/upstream-all`. `gh` has an invalid token.

## Blockers and risks

- No local MariaDB/Redis (Docker Desktop not running), and the backend dependencies don't build on Windows, so backend pytest only runs in CI, Docker or WSL.
- `0129_remove_emulator_data` revises `0128`, so a database coming from upstream RomM (at `0129_save_state_favorites_labels` or later) can't migrate onto the fork.
- The e2e workflow changes are untested until CI runs them.

## First step next time

Open https://github.com/xiaosagemisery/romm-cn/actions/runs/40196488927 signed in, read the "Run python tests" log of both jobs, and fix the failing tests.

## Pitfalls

- `tech_issue.md` has the details: the stray uv 0.13.0, the app's `AppData\Roaming` virtualization, native builds on Windows, isort's config path, black's PEP 758 `except` style, Node/npm engine checks, `python3` being a placeholder, and the Bash tool keeping its working directory.
- The repo-root `.venv` was deleted during this round without checking its contents first; recreate it with `uv sync` when needed.

## Verification

- Migration chain parses as linear with the single head `0150_roms_fs_name_lower_index`.
- `ruff`, `black` and `isort` (pinned versions, repo configs) pass on the changed backend files; `uv lock --check` passes.
- Frontend: `npm ci`, `npm run typecheck`, `npm run build`, ESLint, Prettier and both i18n checks pass. `npm run test` passed 2735 of 2743; the 8 failures come from this machine's Chinese locale (`RDateField`) and a parallel-run timeout (`useBrowserLocale`, which passes alone).
- The extended stats widget was checked in a temporary Storybook story with a mocked `/stats`, in both themes; not checked against a running backend.
- All 11 workflows parse as YAML; actionlint wasn't available.
- First CI run on `14ca67108`: Frontend Checks, Run Typescript Typecheck and Run E2E Tests passed; Run Pytest failed on both databases.
- `docker compose -f examples/docker-compose.romm-cn.yml config` resolves (context = repo root, target `slim-image`, project `romm-cn`), and yamllint passes with the repo config. The image has not been built yet.
