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
| `backend/config/__init__.py` | Defaults `DISABLE_EMULATOR_JS`, `DISABLE_RUFFLE_RS`, `DISABLE_JSDOS`, and `DISABLE_PICO8` to `true` when the corresponding environment variables are unset. |
| `backend/main.py` | Removed streaming and netplay endpoint/socket imports, router registration and socket mounts; also removed `/netplay` from the CSRF middleware exclusions. |
| `backend/utils/database.py` | Rewrote exception handlers in `safe_str_to_bool`, `safe_float`, and `safe_int` as valid exception tuples. |
