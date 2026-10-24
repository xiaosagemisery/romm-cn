# Changes from the Fork Baseline

Baseline: `6c3b32582594eb6f94bc858a05db78f33e84b882` (the fork's `master` before this change set).

Change commit: `36322f67ed5434df356f8332ccb25b4e72bf17de`.

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
| `frontend/src/v2/` and `frontend/src/views/`, `frontend/src/components/`, `frontend/src/console/` | Removed the EmulatorJS, Ruffle, js-dos, and PICO-8 players, the Play routes and views, the play/launch buttons and menu entries on game cards and detail pages, the emulator settings, and the console-mode play flow. Game detail pages keep metadata, files, ROM screenshots, and downloads. |
| `frontend/assets/` | Removed the bundled EmulatorJS and Ruffle assets and the emulator-only console assets. |
| `frontend/src/__generated__/`, `frontend/src/services/`, `frontend/src/stores/`, `frontend/src/types/` | Regenerated the API client from the trimmed OpenAPI schema and removed the services, stores, and types that only served the players and save data. |
| `frontend/src/locales/` | Removed the `emulator` namespace and the keys for the deleted screens from every locale. |
| `frontend/vite.config.js` | Removed the PICO-8 audio-worklet inlining rule and the emulator asset watch ignores, and narrowed the `/ws` dev proxy to drop the `/netplay` socket. |

## Save data, firmware, and device sync removal

| Area | Specific change |
| --- | --- |
| `backend/endpoints/` | Removed the `saves`, `states`, `screenshots` (user/emulator screenshots; the ROM screenshot upload under `/roms/{id}/screenshots` remains), `firmware`, `play_sessions`, `memory_cards`, and `sync` routers and their socket handlers. |
| `backend/handler/`, `backend/models/` | Removed the asset store, play-session handler, sync handlers, the upload-size middleware, and the `Save`, `State`, `Screenshot`, `Firmware`, `PlaySession`, `MemoryCard`, `SyncSession`, `DeviceSaveSync`, and container-adoption models. `FSAssetsHandler` is trimmed to avatar storage. |
| `backend/tasks/`, `backend/sync_watcher.py`, `backend/utils/` | Removed the sync push/pull task, the manual firmware, save-hash, and sync-folder tasks, the netplay cleanup task, the sync watcher, and the upload and memory-card helpers. |
| `backend/models/device.py`, `backend/endpoints/device.py` | Devices and client tokens remain. The `sync_mode`, `sync_enabled`, and `sync_config` fields are gone, so save-sync clients such as Grout and Argosy can no longer sync saves with this server. |
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

## Configuration, startup, and database helpers

| File | Specific change |
| --- | --- |
| `backend/config/__init__.py` | Removed the `DISABLE_EMULATOR_JS`, `DISABLE_RUFFLE_RS`, `DISABLE_JSDOS`, and `DISABLE_PICO8` settings together with the emulator, streaming, and netplay settings; the in-browser players they controlled no longer exist. |
| `backend/main.py` | Removed streaming and netplay endpoint/socket imports, router registration and socket mounts; also removed `/netplay` from the CSRF middleware exclusions. |
| `backend/utils/database.py` | Rewrote exception handlers in `safe_str_to_bool`, `safe_float`, and `safe_int` as valid exception tuples. |
