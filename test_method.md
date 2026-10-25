# Test Methods

Run only the tests a change affects. CI runs the full suites on every push to `sync/upstream-all` and on PRs.

## Backend (`cd backend`)

The tests need MariaDB (or PostgreSQL) and the pinned Python. On Windows, run them in Docker, WSL or CI, because `psycopg-c` and `streaming-form-data` don't build there (see `tech_issue.md`).

| Scope | Command | Expected result |
| --- | --- | --- |
| One file | `uv run pytest tests/path/to/test_file.py` | All tests pass. |
| One test | `uv run pytest tests/path/to/test_file.py::test_name` | The test passes. |
| A directory | `uv run pytest -n auto tests/handler/` | All tests pass, one database per xdist worker. |
| By name | `uv run pytest -k "scan or queue"` | The matching tests pass. |
| Full suite | Never locally. CI's `pytest.yml` runs it on MariaDB and PostgreSQL. | Green on both databases. |

Pick the targets from the diff: `backend/<area>/x.py` maps to `backend/tests/<area>/test_x.py`, plus the tests of every caller whose behavior changed.

Key targets for the fork's own code:

| Area | Command | Expected result |
| --- | --- | --- |
| Translator | `uv run pytest tests/utils/test_translator.py` | Passes without network access (the HTTP client is mocked). |
| Migration chain | `uv run pytest tests/test_migrations.py` | One head, `0150_roms_fs_name_lower_index`; `0152` follows `0129_remove_emulator_data`; every listed revision replays as a no-op. |
| Permissions | `uv run pytest tests/endpoints/test_permissions_admin.py tests/endpoints/test_permissions_visibility.py` | Group changes reach default-group followers, and a hide shows up in the cached gallery. |
| Migrations on a real database | `uv run alembic upgrade head` | Applies cleanly on an empty database, and on one stamped `0152` by the older fork chain. |

## Frontend (`cd frontend`)

| Scope | Command | Expected result |
| --- | --- | --- |
| Install | `npm ci` | Installs from `package-lock.json` without changes. |
| Types | `npm run typecheck` | No vue-tsc errors. |
| Unit and Storybook | `npm run test` | All Vitest and Storybook `play()` tests pass. Needs `npx playwright install --only-shell chromium` once. |
| One test file | `npx vitest run src/path/to/file.test.ts` | The file's tests pass. |
| Lint | `npx eslint <files>` (or `trunk check`) | No ESLint errors. |
| Build | `npm run build` | `dist/` builds without errors. |
| i18n parity | `python3 src/locales/check_i18n_locales.py` | Every locale has the same keys as `en_US`. |
| i18n order | `python3 src/locales/check_i18n_sorted.py` | Every locale file is sorted (`--fix` sorts them). |
| End to end | `npm run test:e2e` (see `frontend/e2e/README.md`) | All Playwright specs pass against a running app with seeded e2e users. Reports land in `frontend/e2e/.output/`. |

## Docker deploy test

Run on a fresh database, isolated from any other RomM on the machine:

1. Write an override that renames the containers, maps another port and sets test secrets and the library path (see `HANDOFF.md`).
2. `docker compose -p romm-cn-test -f examples/docker-compose.romm-cn.yml -f <override> up -d --build`
3. Expected: `GET /api/heartbeat` returns 200, the log says "Database migrations succeeded", and `alembic_version` is `0150_roms_fs_name_lower_index`.
4. Finish the setup wizard, scan, and check the Home stats widget (extended mode), server stats, a game page and both themes.
5. `docker compose -p romm-cn-test ... down -v` when done.

## Lint (both stacks)

`trunk fmt && trunk check` from the repo root. Expected: no issues on the changed files.
