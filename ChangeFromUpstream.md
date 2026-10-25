# Changes from the Fork Baseline

Baseline: `6c3b32582594eb6f94bc858a05db78f33e84b882` (the fork's `master` before its own changes; `master` now mirrors upstream).

The changes live on `sync/upstream-all`. The first removal set was commit `36322f67ed5434df356f8332ccb25b4e72bf17de`; the sections from "Upstream sync" on cover the later commits.

## Streaming removal

| File | Specific change |
| --- | --- |
| `backend/endpoints/streaming.py` | Removed the `/streaming` FastAPI API, including configuration and capability reads, session claim/join/heartbeat/status, volume and mute controls, save/load/state-frame/disc-swap operations, session release, container/session administration, desktop sessions, and joinable-session listing. |
| `backend/handler/streaming/__init__.py` | Removed the streaming handler package marker. |
| `backend/handler/streaming/access.py` | Removed streaming-session access checks, owner checks, and platform/container resolution. |
| `backend/handler/streaming/background.py` | Removed the helper that retained fire-and-forget asynchronous sync tasks. |
| `backend/handler/streaming/broker.py` | Removed HTTP transport to emulator containers, including bounded broker reads and binary save transfers. |
| `backend/handler/streaming/capabilities.py` | Removed per-platform emulator capability tables for save slots, autosave, memory cards, and disc swapping. |
| `backend/handler/streaming/commands.py` | Removed broker command wrappers for launch, stop, save/load, disc swap, volume, and mute. |
| `backend/handler/streaming/config.py` | Removed parsing, validation, and resolution of streaming-container configuration and platform mappings. |
| `backend/handler/streaming/languages.py` | Removed conversion of ROM and user language values into broker-specific language codes. |
| `backend/handler/streaming/launch.py` | Removed asynchronous container launch, join, and launch-progress coordination. |
| `backend/handler/streaming/lifecycle.py` | Removed session teardown orchestration for stopping emulators, syncing saves/cards, recording play activity, and releasing containers. |
| `backend/handler/streaming/memory_cards.py` | Removed whole-memory-card upload, restore, and evacuation between user assets and emulator containers. |
| `backend/handler/streaming/protocol.py` | Removed route and response adapters for the Webstation and per-emulator broker protocols. |
| `backend/handler/streaming/saves.py` | Removed synchronization of in-game save archives between emulator containers and the library. |
| `backend/handler/streaming/session_store.py` | Removed Redis-backed streaming claims and atomic session state updates. |
| `backend/handler/streaming/states.py` | Removed emulator save-state synchronization between container slots and user assets. |
| `backend/handler/streaming/webstation.py` | Removed the Webstation broker adapter for session activation/exit and save-archive transfers. |
| `backend/tests/endpoints/test_streaming.py` | Removed the streaming endpoint test module (5,933 lines), including its coverage for the deleted API. |

## Netplay removal

| File | Specific change |
| --- | --- |
| `backend/endpoints/netplay.py` | Removed the protected `/netplay/list` endpoint that returned joinable rooms for a game with player counts, owner names, and password indicators. |
| `backend/endpoints/sockets/netplay.py` | Removed Socket.IO room open/join/leave and disconnect handling, including room capacity/password checks and participant updates. |
| `backend/handler/netplay_handler.py` | Removed Redis-backed netplay room records and their get/set/delete/list operations. |
| `backend/handler/socket_handler.py` | Removed the `/netplay/socket.io` Socket.IO handler instance; the regular `/ws/socket.io` handler remains. |

## In-browser player removal

| Area | Specific change |
| --- | --- |
| `frontend/src/` (then `src/v2/`, `src/views/`, `src/components/`, `src/console/`) | Removed the EmulatorJS, Ruffle, js-dos, and PICO-8 players, the Play routes and views, the play/launch buttons and menu entries on game cards and detail pages, the emulator settings, and the console-mode play flow. Game detail pages keep metadata, files, ROM screenshots, and downloads. |
| `frontend/assets/` | Removed the bundled EmulatorJS and Ruffle assets. The console theme assets went in the cleanup after the sync (below). |
| `frontend/src/__generated__/`, `frontend/src/services/`, `frontend/src/stores/`, `frontend/src/types/` | Regenerated the API client from the trimmed OpenAPI schema and removed the services, stores, and types that only served the players and save data. |
| `frontend/src/locales/` | Removed the `emulator` namespace and the keys for the deleted screens from every locale. |
| `frontend/vite.config.js` | Removed the PICO-8 audio-worklet inlining rule and the emulator asset watch ignores, and narrowed the `/ws` dev proxy to drop the `/netplay` socket. |

## Save data, firmware, and device sync removal

| Area | Specific change |
| --- | --- |
| `backend/endpoints/` | Removed the `saves`, `states`, `screenshots` (user/emulator screenshots; the ROM screenshot upload under `/roms/{id}/screenshots` remains), `firmware`, `play_sessions`, `memory_cards`, and `sync` routers and their socket handlers. |
| `backend/handler/`, `backend/models/` | Removed the asset store, play-session handler, sync handlers, the upload-size middleware, and the `Save`, `State`, `Screenshot`, `Firmware`, `PlaySession`, `MemoryCard`, `SyncSession`, `DeviceSaveSync`, and container-adoption models. `FSAssetsHandler` is trimmed to avatar storage. |
| `backend/tasks/`, `backend/sync_watcher.py`, `backend/utils/` | Removed the sync push/pull task, the manual firmware, save-hash, and sync-folder tasks, the netplay cleanup task, the sync watcher, and the upload and memory-card helpers. |
| `backend/models/device.py`, `backend/endpoints/device.py` | Devices and client tokens remain. The `sync_mode`, `sync_enabled`, and `sync_config` fields are gone. |
| `backend/config/config_manager.py` | Removed the `filesystem.structure.firmware` template and the EmulatorJS and streaming sections. A leftover `filesystem.structure.firmware` entry in an existing `config.yml` is ignored with a warning. |
| Permissions | Removed the `firmware` entity from the permission vocabulary. The `assets` entity stays because avatars use it. |
| `backend/alembic/versions/0129_remove_emulator_data.py` | Drops `saves`, `states`, `screenshots`, `firmware`, `play_sessions`, `sync_sessions`, `memory_cards`, `memory_card_versions`, `streaming_container_adoptions`, and `device_save_sync`, plus the `devices` sync columns and the `firmware` permission rows. The downgrade is not supported because the data is deleted. Migration 0050 no longer imports the removed `Firmware` model. |
| `backend/tests/` | Removed the test modules for the deleted code, the known-BIOS fixture, and the BIOS files in the mock library. |

## Infrastructure and configuration cleanup

| File | Specific change |
| --- | --- |
| `docker/nginx/templates/default.conf.template` | Removed the cross-origin isolation headers and the routes that only served the emulators. |
| `docker/Dockerfile`, `Dockerfile`, `entrypoint.sh`, `docker/init_scripts/init` | Removed the emulator asset and streaming setup steps. The `full` image target stays as an alias of `slim`. |
| `docker-compose.yml`, `docker-compose.streaming.yml` | Removed the streaming compose override and the emulator-related settings. |
| `env.template`, `DEVELOPER_SETUP.md`, `examples/config.example.yml`, `.gitignore` | Removed the emulator, streaming, and firmware settings and documentation. |
| `backend/tests/test_nginx_cache_headers.py` | Updated for the trimmed nginx template. |

## README cleanup

| File | Specific change |
| --- | --- |
| `README.md` | Removed the header badges and the contributing, official apps, community projects, project support, friendly projects, and sponsors sections, the official-apps feature bullet, and their link references. |
| `.github/resources/*-badge.svg` | Removed the Trendshift, Hacker News, selfh.st, Discord, Open Collective, Greptile, and Aikido badge images, which no longer have any reference. |

## Game metadata translation

| File | Specific change |
| --- | --- |
| `backend/utils/translator.py` | Added asynchronous translation through Google's public Translate endpoint. Results are cached in memory by trimmed text and target language; the default target is `zh-CN`, and failed requests return the original text. |
| `backend/handler/scan_handler.py` | Translates a scanned game's name and summary after metadata selection and before the attributes are persisted. |
| `backend/endpoints/roms/__init__.py` | Translates automatically supplied name/summary values during ROM updates while retaining explicitly submitted values; translated values are used when available. |
| `backend/tests/utils/test_translator.py` | Added tests for empty input, successful translation, cache hits, error fallback, paired metadata translation, and missing values. |
| `backend/utils/translator.py`, `backend/handler/metadata/base_handler.py` | `translate_search_term` turns a filename-derived search term that contains Chinese characters into English, after dropping release labels such as 英文版 and 汉化版. `_resolve_indexed_title` applies it, so the IGDB, MobyGames and ScreenScraper name searches use the English title instead of a pinyin transliteration. Terms without Chinese characters are untouched, and a failed translation searches the label-free Chinese title. |
| `backend/tests/utils/test_translator.py`, `backend/tests/handler/metadata/test_base_handler.py` | Cover the search term translation and its hook. |

## Configuration, startup, and database helpers

| File | Specific change |
| --- | --- |
| `backend/config/__init__.py` | Removed the `DISABLE_EMULATOR_JS`, `DISABLE_RUFFLE_RS`, `DISABLE_JSDOS`, and `DISABLE_PICO8` settings together with the emulator, streaming, and netplay settings; the in-browser players they controlled no longer exist. |
| `backend/main.py` | Removed streaming and netplay endpoint/socket imports, router registration and socket mounts; also removed `/netplay` from the CSRF middleware exclusions. |
| `backend/utils/database.py` | Rewrote exception handlers in `safe_str_to_bool`, `safe_float`, and `safe_int` as valid exception tuples. |

## Upstream sync (`7eae2b8ff`)

The backend, the migrations, the Docker and nginx files, `pyproject.toml` and `uv.lock` were brought up to the upstream `master` at `7eae2b8ff` (2026-10-23). The frontend follows upstream too, including #5309: the v1 UI and the console mode are gone and the former v2 UI lives in `frontend/src/`. The CI workflows stay at the fork's own state, apart from the removed v1 freeze check.

### Removed again after the sync

| Area | Specific change |
| --- | --- |
| Streaming, netplay, save sync | `endpoints/streaming.py`, `endpoints/netplay.py`, `endpoints/sync/`, `handler/streaming/`, `handler/sync/` (RetroArch Cloud Sync included), `handler/netplay_handler.py`, the sync watcher and the push-pull task stay deleted. The `STREAMING_*`, `SYNC_*` and `DISABLE_*` emulator settings, the streaming RQ queue and worker, and the `streaming`/`devices` notification topics are gone. |
| Device push install | `endpoints/device/install.py`, `handler/device_install/`, the `DEVICE_INSTALL_*` settings and the install notification kinds are removed. Devices keep registration and client tokens, without sync mode, sync config or capabilities. |
| Browser players | The EasyRPG endpoint, handler, RTP tooling, `Rom.is_easyrpg_game`, the `playable` filter and the emulator asset stages of both Dockerfiles are removed. The libgme WebAssembly stage stays, because the browser soundtrack player plays SPC, VGM and GYM files through it. |
| Age limits | Upstream's age-limit feature (#5081) is reverted: `utils/age_ratings.py`, `Rom.min_age` and its `roms_facets` mirror, `age_limit` and `hide_unrated_roms` on users and permission groups, the age clause of `RomVisibilityFilter`, the matching API fields and tests. Hidden platforms and ROMs still work. The age-ratings metadata itself is untouched. |
| Saves, states, screenshots, firmware | `has_saves` and `has_states` filters, the `saves`/`states`/`screenshots` relationships on `Rom`, the stats counters, the firmware pass of the scan, the `FIRMWARE` audit target and permission entities (`streaming`, `emulation`, `firmware`) are removed. |

### Frontend after the sync

| Area | Specific change |
| --- | --- |
| Structure | `frontend/` is upstream's tree at `7eae2b8ff`: the v1 views, components, layouts and console mode are removed and `frontend/src/v2/` moved to `frontend/src/`. The `frontend-v2-*` skills became `frontend-*`. |
| Removed again | The EmulatorJS, Ruffle, js-dos, PICO-8 and EasyRPG players and their routes, the save data and screenshot tabs, firmware and memory-card screens, streaming sessions and admin panel, device install and save sync, the desktop shell native launch, the play-mode badges and the `playable`, `has_saves` and `has_states` filters, and the age limit settings. |
| Kept small | `stores/playing.ts` stays as upstream has it. It is always false without a player, and the files that read it stay identical to upstream. |
| Generated types | `src/__generated__/` is regenerated from the fork's backend, so the removed endpoints and fields have no types. |
| Tooling | The player isolation headers plugin and the EasyRPG dev proxy are removed from `vite.config.js`. |

### Migrations

`0129_remove_emulator_data` keeps its revision id and still revises `0128_hltb_main_story_column`. `0152_cross_user_smart_scopes` follows it, then upstream's `0130` to `0147` and `0149`, `0150`, re-chained (`0130` revises `0152`, `0149` revises `0147`). The head is `0150_roms_fs_name_lower_index`. `0152` comes first because the fork's chain before the sync ran `0129` then `0152`, so databases stamped `0152` still get `0130` to `0150`, which all replay cleanly over a schema that already has them. Skipped because they only touch removed tables or add removed permissions: `0129_save_state_favorites_labels`, `0135`, `0136`, `0138`, `0140`, `0141`, `0142`, `0151` and `0153`. `0148_rom_age_limits` is skipped because the fork drops age limits.

### Docs and skills

`docs/BACKEND_ARCHITECTURE.md` was merged with upstream's version at `7eae2b8ff` and the sections for removed features (saves, states, screenshots, firmware, play sessions, netplay, device sync and install, EasyRPG, age limits) were dropped again. The `backend-development`, `review-polish` and `security-audit` skills follow upstream, with the references to tooling the fork does not have (the mypy workflow, the ruff `TID251` factory ban, the ESLint plugin) removed.

### Kept from the fork

The Google Translate step in `scan_handler.py` and `endpoints/roms/__init__.py`, and the trimmed `FSAssetsHandler` (avatars only), carry over unchanged.

## Cleanup after the sync

### Backend and infrastructure

| File | Specific change |
| --- | --- |
| `backend/alembic/versions/0130_notifications.py`, `0152_cross_user_smart_scopes.py` | Re-chained to `0129 → 0152 → 0130`, as described under Migrations. The `Revises:` docstring lines in `0130`, `0137`, `0139`, `0143` and `0152` are fixed. |
| `backend/tests/test_migrations.py` | Pins the chain order and head, and replays `0133`, `0134`, `0137`, `0149` and `0150` over the migrated schema. |
| `backend/endpoints/permissions.py`, `backend/handler/database/permissions_handler.py` | Restored the parts of upstream #5081 that are not about age limits: every permission change invalidates the cached gallery filter values, group edits and hides reach the users who follow the group (members, plus users without a group when it is the default), and creating a default group notifies them. |
| `backend/tests/endpoints/test_permissions_admin.py`, `test_permissions_visibility.py` | Cover default-group followers and a hide reaching the cached gallery. |
| `backend/handler/scan_handler.py`, `backend/tests/handler/test_scan_identified.py` | A ROM that only libretro artwork matches keeps its stored (filename-derived) name. Libretro results carry no name, so on new ROMs and complete rescans the scan raised `KeyError: 'name'` and the ROM was not scanned; upstream has the same bug. The fallback runs after the translation step, so the placeholder is not translated. |
| `backend/tools/generate_test_data.py` | Rebuilt from upstream's current version without the removed models, so it imports and inserts again. |
| `backend/utils/openapi.py`, `backend/tests/utils/test_openapi.py` | Removed; they only published the streaming socket payloads. |
| `pyproject.toml`, `uv.lock` | Removed `asyncssh`, which only the SSH push-pull sync used. |
| `backend/pytest.ini`, `backend/tests/config/fixtures/config/config.yml`, `backend/tests/tasks/test_task_func_paths.py`, `backend/tests/endpoints/roms/test_notes_loads.py` | Removed the netplay and sync-session cron settings, the `emulatorjs`/`netplay` config block, the sync push-pull module and the dropped asset tables. |
| `backend/utils/translator.py`, `backend/tests/utils/test_translator.py` | Formatting only; the test's response mock is a plain `MagicMock`. Behavior is unchanged. |
| `docker/Dockerfile.dockerignore`, `env.template`, `examples/docker-compose.example.yml` | Removed the emulator asset folders, the save version wording, and the sync volume. |
| `examples/docker-compose.romm-cn.yml` | Added: builds the `slim-image` target of `docker/Dockerfile` from the checkout as `romm-cn:local` instead of pulling `rommapp/romm`, which lacks the fork's changes. It passes optional ScreenScraper developer credentials as build args and notes the fresh-database requirement and the translator's network access. |

### Frontend

| Area | Specific change |
| --- | --- |
| `src/components/Home/Widgets/LibraryStatsWidget.vue` | Extended mode no longer reads saves, states and screenshots, which `/stats` doesn't return (it threw a TypeError). It shows disk size in a 2-column grid and uses the generated `StatsReturn` type. |
| `src/views/Settings/ServerStats.vue`, `src/components/Settings/SummaryStatsSection.vue` | Removed the always-zero saves, states and screenshots cards. |
| `src/views/Settings/UserInterface.vue`, `src/composables/useUISettings.ts` | Removed the play page style (`boxartStylePlayer`) and the protected launch confirmation (`confirmProtectedLaunch`), which nothing read. |
| Removed files | `composables/usePlayFocus/`, `usePlayerFullscreen/`, `useFullscreenFallback/`, `useGroupFold/`, `utils/playerFullscreen.ts`, `utils/idb.ts`, `test-utils/deviceSaveSync.ts`, `utils/saveStates.plays.ts`, and `assets/console/`. |
| `package.json`, `package-lock.json` | Removed `fflate`, `spark-md5`, `@types/spark-md5` and `fake-indexeddb`. |
| `eslint.config.js`, `vite.config.js`, `scripts/previewAssets.ts` | Removed the rules, watch ignores and comments for deleted player files. |
| Tests | The e2e media spec no longer expects a user screenshots section; `GameDetails.test.ts` drops the save data tab mock; the scan lifecycle test drops `new_firmware_count`. |
| `src/locales/en_US`, `src/locales/zh_CN` | The device, extended stats and rescan strings no longer mention saves or sync, and three Chinese strings that were still English are translated. Orphaned keys stay in every locale to keep upstream syncs clean. |

### CI

| File | Specific change |
| --- | --- |
| `pytest.yml`, `e2e.yml`, `frontend.yml`, `typecheck.yml` | Also run on pushes to `sync/upstream-all`. |
| `frontend.yml` | Installs the Chromium shell before the Storybook tests. |
| `e2e.yml` | Builds the frontend before `vite preview` serves it, and uploads the report from `frontend/e2e/.output/specs/`. |
| `build.yml`, `update-hltb-api-url.yml` | Only run on `rommapp/romm`. |
| `.github/FUNDING.yml` | Removed. |
| `.gitignore` | Ignores `.git-credentials`. |

### Docs and agent instructions

| File | Specific change |
| --- | --- |
| `AGENTS.md`, `CLAUDE.md` | `AGENTS.md` is upstream's guide plus the fork's branch, sync and documentation rules, and the only instruction file; `CLAUDE.md` imports it. |
| `project.md`, `test_method.md`, `test_troubleshooting.md` | Added: the project overview, how each test runs and what it should produce, and solved test problems. |
| `docs/FRONTEND_ARCHITECTURE.md`, `docs/BACKEND_ARCHITECTURE.md` | The frontend doc drops the player, firmware, save and netplay parts; the backend doc adds the translation step and the migration order. |
| `.claude/skills/frontend-*`, `review-polish`, `DEVELOPER_SETUP.md`, `frontend/AGENTS.md` | No longer describe the players, the `src/v2` path or a mypy CI job. |
