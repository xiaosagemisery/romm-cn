# Test Troubleshooting

## Backend tests can't run on this Windows machine

- Symptom: `uv sync --all-extras --dev` fails building `psycopg-c` (`pg_config` not found), then `streaming-form-data` ("Microsoft Visual C++ 14.0 or greater is required").
- Cause: both are native builds the project only targets on Linux.
- Fix: run the backend tests in Docker, WSL or CI. CI's `pytest.yml` runs on every push to `sync/upstream-all`.

## No database for the backend tests

- Symptom: nothing listens on 3306, 5432 or 6379, and `docker version` can't reach `dockerDesktopLinuxEngine`.
- Cause: Docker Desktop isn't running, so neither MariaDB nor Redis is up.
- Fix: start Docker Desktop and the services from `DEVELOPER_SETUP.md`, or rely on CI.

## Migration chain checks without a database

- The chain order can be checked without the app's dependencies by parsing each revision's `revision` and `down_revision` with a short script. Expect one head (`0150_roms_fs_name_lower_index`) and no branch points.
- `tests/test_migrations.py::test_the_upstream_revisions_follow_the_cross_user_smart_scopes_revision` checks the same in CI.

## Storybook tests fail in CI with a missing browser

- Symptom: `npm test` fails in `frontend.yml` because Chromium isn't installed.
- Fix: `npx playwright install --only-shell chromium` before `npm test` (the workflow now does this).
