# romm-cn

romm-cn is a fork of [RomM](https://github.com/rommapp/romm), a self-hosted ROM manager. It scans a game library off disk, matches every game against metadata providers, and serves the library through a web UI for browsing, searching, downloading, and organizing games into collections.

The fork targets Chinese-speaking users and a smaller feature set than upstream:

- It removes everything that runs or tracks games in the browser: the EmulatorJS, Ruffle, js-dos, PICO-8 and EasyRPG players, streaming, netplay, saves, states and user screenshots, firmware, play sessions, memory cards, device save sync and device push install. It also drops upstream's age limits.
- It translates each scanned game's name and summary to Simplified Chinese through Google Translate.
- It follows upstream otherwise. `master` mirrors upstream, `sync/upstream-all` carries the fork on top of it, and `ChangeFromUpstream.md` lists every difference.

## Components

| Component | Path | Role |
| --- | --- | --- |
| API server | `backend/main.py`, `backend/endpoints/` | FastAPI app serving `/api/*` (REST) and `/ws` (Socket.IO). Each router covers one resource: ROMs, platforms, collections, users, permissions, devices, client tokens, tasks, notifications, audit events, stats, feeds, export. |
| Handlers | `backend/handler/` | Business logic behind the endpoints: the scan pipeline (`scan_handler.py`), database access per model (`database/`), library and resource files (`filesystem/`), metadata providers (`metadata/`), auth and permissions (`auth/`), notifications, audit, Redis, the RQ worker. |
| Metadata adapters | `backend/adapters/services/` | HTTP clients for IGDB, ScreenScraper, MobyGames, RetroAchievements, Steam, SteamGridDB, libretro thumbnails and others. |
| Translator | `backend/utils/translator.py` | Translates a game's name and summary to zh-CN, and turns Chinese filenames into English search terms for the metadata providers. Results are cached per process, and a failed request keeps the original text. |
| Models and migrations | `backend/models/`, `backend/alembic/` | SQLAlchemy models for MariaDB, MySQL and PostgreSQL. Migrations run on startup. The fork's chain runs `0129_remove_emulator_data`, then `0152`, then upstream's `0130` to `0150`. |
| Background tasks | `backend/tasks/`, `backend/handler/rq_worker.py` | RQ jobs on Redis: scans, scheduled rescans, metadata store updates (Switch TitleDB, LaunchBox), cache cleanups. `watcher.py` rescans on filesystem changes. |
| Web UI | `frontend/src/` | Vue 3 + Vite single-page app with its own design system (tokens in `src/tokens/`, `R*` primitives in `src/lib/`), Pinia stores, a typed API client generated from the backend's OpenAPI schema (`src/__generated__/`), and 18 locales with `zh_CN` complete. |
| Container | `docker/`, `Dockerfile`, `docker-compose.yml` | One image running nginx, the API server, the RQ worker and the scheduler. nginx serves the built frontend and proxies `/api` and `/ws`. |

## Workflow

1. **Startup.** The container's init script applies the migrations, then starts the API server, the RQ worker, the scheduler and the filesystem watcher behind nginx.
2. **Scan.** A user starts a scan from the UI (or the scheduler or watcher queues one). The worker walks `LIBRARY_BASE_PATH`, maps each folder to a platform, hashes new or changed files, and queries the metadata providers in priority order. Hash matches (Hasheous) come first; for name searches, a Chinese filename is translated to English before it goes to IGDB, MobyGames or ScreenScraper.
3. **Translate and store.** After choosing the metadata, the scan translates the name and summary to zh-CN, downloads covers and screenshots into the resources folder, and saves the ROM. Progress reaches the UI over Socket.IO.
4. **Browse.** The UI loads galleries, filters and search through `/api/roms`, with per-user visibility from permission groups and hidden entities applied server-side and cached per user in Redis.
5. **Edit.** Editing a ROM's metadata in the UI also translates provider-supplied name and summary values, while explicitly typed values are kept as entered.
6. **Download and organize.** Users download files, manage collections and smart collections, rate and track their games, and export gamelists for other frontends.

## Where to read more

- `docs/BACKEND_ARCHITECTURE.md` and `docs/FRONTEND_ARCHITECTURE.md` for the detailed architecture.
- `DEVELOPER_SETUP.md` for running it locally.
- `test_method.md` for how each test suite runs.
- `HANDOFF.md` for the current state of the work.
