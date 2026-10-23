# Technical Issues

## Git and sandbox permissions

- Symptom: `git fetch origin master` failed with `error: cannot open '.git/FETCH_HEAD': Permission denied` inside the workspace sandbox.
- Root cause: the sandbox allowed reading the repository metadata but blocked writing Git's `FETCH_HEAD` file.
- Fix: rerun the fetch with the required elevated Git access; the fetch completed successfully.
- Future guidance: do not treat this sandbox permission failure as a remote Git failure. Use the approved Git access path for operations that must update `.git` or contact the remote.
