# Technical Issues

## Git and sandbox permissions

- Symptom: `git fetch origin master` failed with `error: cannot open '.git/FETCH_HEAD': Permission denied` inside the workspace sandbox.
- Root cause: the sandbox allowed reading the repository metadata but blocked writing Git's `FETCH_HEAD` file.
- Fix: rerun the fetch with the required elevated Git access; the fetch completed successfully.
- Future guidance: do not treat this sandbox permission failure as a remote Git failure. Use the approved Git access path for operations that must update `.git` or contact the remote.
- Symptom: `git add -- HANDOFF.md tech_issue.md` failed with `fatal: Unable to create '.../.git/index.lock': Permission denied` inside the workspace sandbox. The same occurred when staging the follow-up `HANDOFF.md` update.
- Root cause: the sandbox blocked writing Git's index lock, so Git could not update `.git/index`; this was a local sandbox permission issue, not a GitHub authentication or network failure.
- Fix: rerun the narrowly scoped `git add` with the approved elevated Git access, then run `git diff --cached --check`; staging and commits completed successfully.
- Future guidance: when a Git operation fails on `.git/FETCH_HEAD`, `.git/index.lock`, or another metadata path with `Permission denied`, classify it as a sandbox metadata-write restriction and use the approved Git access path. Stage only the intended files.

## PowerShell quoting

- Symptom: a `Select-String` command failed with a positional-parameter error.
- Root cause: a single-quoted PowerShell pattern contained an apostrophe, which ended the string early.
- Fix: use a pattern without the apostrophe or quote the pattern with a correctly escaped delimiter.
- Future guidance: check embedded apostrophes before using single-quoted PowerShell strings.

## GitHub connector arguments

- Symptom: a GitHub compare request using `...codex/local-updates-20261024` returned HTTP 400 from the connector allowlist.
- Root cause: the branch name contains a slash and was passed as a path segment in the compare URL.
- Fix: verify the local remote-tracking branch ancestry with `git merge-base --is-ancestor`; the check exited 0.
- Future guidance: use commit SHAs in GitHub compare URLs when a ref contains slashes, or use a local ancestry check after refreshing the remote refs.

## GitHub CLI authentication

- Symptom: `gh auth status` reported that the saved `xiaosagemisery` token was invalid.
- Root cause: the GitHub CLI's stored token is not currently valid; the exact expiration or revocation cause is unknown.
- Fix: verify SSH authentication with `ssh -o BatchMode=yes -T git@github.com`; it succeeded, so use SSH for the requested Git branch operations.
- Future guidance: check `gh auth status` before relying on GitHub CLI commands, and never print or commit token contents.

## Dependencies and environment

- Symptom: `uv lock` failed with "Required uv version `>=0.13.4, <0.14` does not match the running version `0.13.0`".
- Root cause: the only `uv` on `PATH` is an older copy in `~/.agent-reach-venv`, while `pyproject.toml` pins uv 0.13.4.
- Fix: run the pinned version without installing it globally: `uvx --from "uv==0.13.4" uv lock`. It wrote lock format `revision = 5`; setting it back to upstream's `revision = 3` still passes `uv lock --check`.
- Future guidance: never run the stray uv 0.13.0 against this repo. Use `uvx --from "uv==0.13.4" uv ...`, and keep the lock's `revision` line equal to upstream's to avoid needless churn.

- Symptom: uv's Python download failed with "Missing expected target directory for Python minor version link at `C:\Users\18521\AppData\Roaming\uv\python\cpython-3.14.8-windows-x86_64-none`".
- Root cause: commands run from the Claude desktop app are packaged-app processes, so Windows redirects their writes under `AppData\Roaming` into the app's private `LocalCache`. The junction uv creates then points at a real Roaming path that doesn't exist.
- Fix: set `UV_PYTHON_INSTALL_DIR` to a folder outside `AppData\Roaming` (the session scratchpad worked) before running uv.
- Future guidance: when uv or another tool fails on a path under `AppData\Roaming` from the agent shell, treat it as filesystem virtualization, not a broken install, and point the tool at a non-virtualized folder.

- Symptom: `uv sync --all-extras --dev` failed building `psycopg-c` (`pg_config` not found), and with that package skipped, `streaming-form-data` ("Microsoft Visual C++ 14.0 or greater is required").
- Root cause: these native dependencies are built for the Linux image; this Windows machine has neither PostgreSQL's dev files nor the MSVC build tools.
- Fix: run the backend and its tests in Docker, WSL or CI. Static checks (ruff, black, isort) run fine through `uvx`.
- Future guidance: don't try to build the backend environment natively on Windows.

- Symptom: `npm ci` and lockfile updates refused to run because of the engine check.
- Root cause: this machine has Node 25 with npm 11.6, while the project asks for Node 24 and npm 11.10 or newer, and `frontend/.npmrc` sets `engine-strict`.
- Fix: run the pinned npm without installing it: `npx npm@11.12.1 ci --engine-strict=false` (same for `install`).
- Future guidance: prefer installing Node 24 from `frontend/.nvmrc`; until then, use the `npx npm@...` form and check the lockfile diff stays limited to the intended packages.

- Symptom: `python3 src/locales/check_i18n_locales.py` did nothing, and `python` failed on emoji with a GBK encoding error.
- Root cause: `python3` here is the Windows Store placeholder, and the console code page is GBK.
- Fix: run `python` with `PYTHONIOENCODING=utf-8`.
- Future guidance: on this machine, never use `python3`; set `PYTHONIOENCODING=utf-8` for scripts that print non-ASCII.

## Formatting

- Symptom: running `isort` through `uvx` with `--settings-path .` rewrote imports into the default style, splitting first-party and third-party groups and wrapping lines with hanging indents.
- Root cause: the repo's isort settings live in `.trunk/configs/.isort.cfg`, which `--settings-path .` doesn't find.
- Fix: rerun with `--settings-path ../.trunk/configs/.isort.cfg` from `backend/`, which restored the expected layout.
- Future guidance: pass the Trunk config files explicitly (`.trunk/configs/.isort.cfg`, `.trunk/configs/ruff.toml`) when running a formatter outside Trunk, and use the versions pinned in `.trunk/trunk.yaml` (black 26.5.1, isort 8.0.1, ruff 0.15.22).

- Symptom: black 26.5.1 rewrote `except (TypeError, ValueError):` as `except TypeError, ValueError:`.
- Root cause: with `requires-python = ">=3.14"`, black applies the PEP 758 style that only Python 3.14 parses, while upstream's files keep the parentheses.
- Fix: put the parentheses back by hand in files copied from upstream.
- Future guidance: after running black outside Trunk, check the diff for `except A, B:` and keep upstream's form so syncs stay clean.

## Agent shell

- Symptom: after a Bash call that ran `cd backend/...`, later relative commands ran in the wrong folder.
- Root cause: the Bash tool keeps the working directory between calls.
- Fix: start each command with `cd /c/Users/18521/PycharmProjects/romm-cn` or use absolute paths.
- Future guidance: never rely on the previous call's working directory.
