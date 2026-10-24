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
