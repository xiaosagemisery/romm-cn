# Handoff

## State

- `master` mirrors upstream RomM at `7eae2b8ff` and carries no fork changes.
- `sync/upstream-all` is the daily branch. It holds the upstream sync plus the fork's removals and the cleanup commits below. It is pushed over SSH up to `7e48d365b` plus this handoff update (remote tip verified with `git ls-remote`).
- `.git-credentials` sits untracked at the root and is now ignored. Never stage or print it.

## Completed

- Issues #1 and #2 (closed by `5a46a4939`): game titles are no longer machine translated (verified official title when `official_names_zh.json` has one, otherwise as provided), summaries are translated with the title protected, and the manual match dialog's posted provider values go through the same step as a scan. `search_titles_en.json` maps known Chinese filename titles to English for the provider name search (斑鸠, 路易的鬼屋, 星之卡比 三重彩).

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

- Official Chinese titles are looked up on Wikidata by IGDB slug (`wikidata_zh_title`); `backend/utils/official_names_zh.json` holds manual overrides for titles Wikidata lacks (Shining Soul, listed as 光明之魂 by MobyGames) or gets wrong. Traditional-only labels are converted with OpenCC (`opencc-python-reimplemented`, pure Python). Sources disagree on Majora's Mask (Wikidata zh-cn 魔吉拉的面具, zh-hans and zh-hk 姆吉拉的假面), so it has no override; the user suggested 玛祖拉的假面, which no source lists. Wikidata is only reachable from this sandbox after the user allowed `query.wikidata.org`.
- Manual matching of the six unmatched test games was paused after the first (Kirby: Triple Deluxe, stored in English) pending issue #1; it can resume now that titles are kept as provided.
- The summary title placeholder (`TITLE_PLACEHOLDER`) was only tested with a mocked translator; check it once against the live Google endpoint from a network that isn't rate limited.
- Not done by choice:
  - The translator stays as is (no switch, hard-coded zh-CN, re-translates on rescans, no Redis cache).
  - Orphaned i18n keys and small dead helpers in files shared with upstream stay, to keep syncs clean.

## Key files and commands

- Change docs: `README.md`, `ChangeFromUpstream.md`. Rules: `AGENTS.md`. Overview: `project.md`. Tests: `test_method.md`.
- Migration order check without a database: parse `revision`/`down_revision` in `backend/alembic/versions/` (see `test_troubleshooting.md`).
- uv on this machine: `UV_PYTHON_INSTALL_DIR=<non-Roaming dir> uvx --from "uv==0.13.4" uv lock`.
- Formatters outside Trunk: `uvx --python 3.14 black@26.5.1`, `isort@8.0.1 --settings-path ../.trunk/configs/.isort.cfg`, `ruff@0.15.22 check --config ../.trunk/configs/ruff.toml` (from `backend/`).
- Push over SSH: `git push git@github.com:xiaosagemisery/romm-cn.git sync/upstream-all`. `gh` has an invalid token.

- Local deploy test stack (`romm-cn-test`) was removed with `down -v`; the `romm-cn:local` image is kept. Rebuild it the same way (see `test_method.md`).
- The user's own RomM (`romm`, `romm-db`, upstream image, port 81) runs on the same Docker; never touch it.

## Blockers and risks

- No local MariaDB/Redis (Docker Desktop not running), and the backend dependencies don't build on Windows, so backend pytest only runs in CI, Docker or WSL.
- `0129_remove_emulator_data` revises `0128`, so a database coming from upstream RomM (at `0129_save_state_favorites_labels` or later) can't migrate onto the fork.

## First step next time

Nothing is blocking. Optional: a deploy test with ScreenScraper developer credentials of the fork's own, since builds from source have none.

## Pitfalls

- `tech_issue.md` has the details: the stray uv 0.13.0, the app's `AppData\Roaming` virtualization, native builds on Windows, isort's config path, black's PEP 758 `except` style, Node/npm engine checks, `python3` being a placeholder, and the Bash tool keeping its working directory.
- The repo-root `.venv` was deleted during this round without checking its contents first; recreate it with `uv sync` when needed.

## Verification

- Migration chain parses as linear with the single head `0150_roms_fs_name_lower_index`.
- `ruff`, `black` and `isort` (pinned versions, repo configs) pass on the changed backend files; `uv lock --check` passes.
- Frontend: `npm ci`, `npm run typecheck`, `npm run build`, ESLint, Prettier and both i18n checks pass. `npm run test` passed 2735 of 2743; the 8 failures come from this machine's Chinese locale (`RDateField`) and a parallel-run timeout (`useBrowserLocale`, which passes alone).
- The extended stats widget was checked in a temporary Storybook story with a mocked `/stats`, in both themes; not checked against a running backend.
- All 11 workflows parse as YAML; actionlint wasn't available.
- First CI run on `14ca67108`: Frontend Checks, Run Typescript Typecheck and Run E2E Tests passed; Run Pytest failed on both databases with only `test_the_upstream_revisions_follow_the_cross_user_smart_scopes_revision` failing (fixed in `40c883f1a`).
- CI on `40c883f1a`: Run Pytest (MariaDB and PostgreSQL) and Run E2E Tests passed. Frontend Checks and Typecheck didn't trigger, since that push changed no `frontend/` files; they passed on `14ca67108`.
- CI logs: the REST API needs admin auth, but signed in to github.com, `/<owner>/<repo>/commit/<sha>/checks/<job id>/logs` redirects to the raw log text.
- `docker compose -f examples/docker-compose.romm-cn.yml config` resolves (context = repo root, target `slim-image`, project `romm-cn`), and yamllint passes with the repo config. The image has not been built yet.
- Local Docker deploy test (2026-10-25), `romm-cn:local` built from `examples/docker-compose.romm-cn.yml` in about 2 minutes, fresh MariaDB:
  - Migrations ran to `0150_roms_fs_name_lower_index`; `notifications`, `audit_events` and `users.oidc_sub` exist, `saves` doesn't.
  - gunicorn, RQ workers, RQ cron, nginx and valkey running; no errors at startup.
  - Setup wizard (Chinese UI) detected the three mock platforms and created the admin.
  - The first scan failed every ROM with `KeyError: 'name'` (libretro-only matches carry no name; upstream bug). After the fix, a complete rescan identified all three with libretro covers.
  - The translator reached Google from the container (name and summary in 0.8 s). It wasn't exercised by the scan because no provider returned a name without keys.
  - Home stats widget in extended mode shows games, platforms, favorites and disk size with no errors; server stats shows three cards; the game page has no play button or save tab; light and dark themes checked.
- CI on `7e48d365b` (scan fix): Run Pytest (MariaDB and PostgreSQL) and Run E2E Tests passed.
- Deploy test with provider keys (2026-10-25): the user's own IGDB, MobyGames, SteamGridDB and ScreenScraper account keys, copied from their running `romm` container into a scratch override and deleted afterwards. The ScreenScraper developer credentials in that container come from the upstream image and were not used. A quick scan matched all three mock ROMs on IGDB and stored Chinese names and summaries (超级马里奥世界, 塞尔达传说：时之笛, 神奇宝贝翡翠版), and `/api/roms/<id>` serves them with covers. Stack removed with `down -v`.
- Real ROM test (2026-10-25), copies of 1 GBA and 9 N64 ROMs from the user's `E:\Roms
oms` (Chinese filenames), user's own provider keys, removed afterwards:
  - 7 of 10 matched on the first quick scan, almost all through Hasheous (file hash to IGDB); names and summaries came out in Chinese.
  - Not matched: `1.gba` (header: SHINING SOUL, code AHUJ, Japan), and the iQue China releases of Ocarina of Time and Star Fox 64 (region `C`). Their hashes are unknown to Hasheous, and Chinese filenames give IGDB's name search nothing to find.
  - After renaming the copies to English No-Intro style names, an UNMATCHED scan matched all three on IGDB (6593, 1029, 2591) with translated summaries; their names stayed as before because that scan keeps an existing name.
- `E:\Roms
oms\gba.gba` was renamed to `Shining Soul (Japan).gba` at the user's request (2026-10-26); it now matches IGDB 6593.
- Second real ROM test (2026-10-26), 20 more ROMs (6 N64, 7 GameCube, 7 3DS, Chinese filenames) bind-mounted read-only from `E:\Roms`, user's keys, removed afterwards:
  - Original names: 3 of 20 matched (all N64, by hash). Every file was hashed, but Hasheous knew none of the GameCube (`.iso`/`.rvz`/`.gcz`) or 3DS (`.cci`) images. Name search turns Chinese filenames into pinyin (`Chao Ji Ma Li Ao 64`), which finds nothing. MobyGames returns 401 for the user's key.
  - Same files mounted under English names on a fresh database: 19 of 20 matched, names and summaries in Chinese. Only `DK - Jungle Beat` missed (IGDB title: Donkey Kong Jungle Beat).
  - Takeaway: for this library, English filenames decide matching. This led to the search term translation below.
- Chinese filename search (2026-10-26): `translate_search_term` translates filename search terms with Chinese characters to English before the IGDB, MobyGames and ScreenScraper name searches. Rerun of the same 20 ROMs with their original Chinese names on a fresh database: 17 of 20 matched (was 3). Misses are literal translations of titles whose English names differ: 斑鸠 -> "turtledove" (Ikaruga), 路易的鬼屋 -> "louie's haunted house" (Luigi's Mansion), 星之卡比 三重彩 -> "Kirby Trifecta" (Kirby: Triple Deluxe). Stack and key-bearing override removed.
- Baidu Baike and Douban are blocked from the sandbox (tunnel refused); evaluate them as a second title source only after the user allows `baike.baidu.com` and the Douban hosts.
