# Repository Instructions

Read and follow [CLAUDE.md](CLAUDE.md) for all repository instructions.

## Branches and pull requests

- The fork's `master` branch (the "main" branch) only mirrors the upstream RomM `master`. It is used for upstream syncs and carries none of the fork's changes.
- Do not open pull requests unless the user explicitly asks for one. Push work to a feature or sync branch (for example `sync/upstream-backend`) and report it.
- When syncing from upstream, do not re-add features the fork deleted (streaming, netplay, emulator players, saves/states/screenshots, firmware, play sessions, memory cards, device save sync). Replay those removals on top of the upstream code and keep the fork-only additions listed in `ChangeFromUpstream.md`.

## Change documentation

- For every major change relative to the fork baseline, update `README.md` and `ChangeFromUpstream.md` in the same change.
- In `README.md`, keep a concise "Changes from the fork baseline" section with one short line per change category and identify the baseline commit.
- In `ChangeFromUpstream.md`, identify the baseline commit and document each change category, affected files, and the specific behavior added, changed, or removed.
- Treat feature or API additions and removals, configuration-default changes, persistence changes, and integration changes as major changes. Update both documents before considering the change complete.
- Compare the actual diff with the baseline; do not rely on commit titles alone.

## Never run the full backend test suite locally

A bare `uv run pytest` (or `pytest -vv`) over `backend/` takes 20+ minutes and burns a
huge number of tokens on output. Don't do it, even to "double check" at the end.

Instead, select the tests affected by the change and run only those:

```bash
cd backend
uv run pytest tests/path/to/test_file.py                # one file
uv run pytest tests/path/to/test_file.py::test_name     # one test
uv run pytest tests/handler/ tests/endpoints/           # affected areas
uv run pytest -k "scan or queue"                        # by name pattern
```

Pick the targets from the diff: the test file mirroring each changed module
(`backend/<area>/x.py` → `backend/tests/<area>/test_x.py`), plus the tests of the
callers of anything whose signature or behavior you changed (`grep` for the symbol).

CI runs the whole suite on the PR (`pytest.yml`, MariaDB + PostgreSQL). That is the
place for full-suite coverage; local runs stay scoped.
