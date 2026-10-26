# RomM Backend Architecture

Comprehensive documentation of the RomM backend: a FastAPI-based server powering the self-hosted retro gaming platform.

---

## Table of Contents

1. [Overview](#1-overview)
2. [High-Level Architecture](#2-high-level-architecture)
3. [Directory Structure](#3-directory-structure)
4. [Application Lifecycle](#4-application-lifecycle)
5. [Database Layer](#5-database-layer)
6. [API Endpoints](#6-api-endpoints)
7. [Authentication & Authorization](#7-authentication--authorization)
8. [Business Logic (Handlers)](#8-business-logic-handlers)
9. [External Integrations (Adapters)](#9-external-integrations-adapters)
10. [Real-Time Communication (WebSockets)](#10-real-time-communication-websockets)
11. [Background Tasks & Scheduling](#11-background-tasks--scheduling)
12. [File System Management](#12-file-system-management)
13. [Caching (Redis)](#13-caching-redis)
14. [Configuration](#14-configuration)
15. [Error Handling](#15-error-handling)
16. [Logging](#16-logging)
17. [Testing](#17-testing)

---

## 1. Overview

| Property           | Value                            |
| ------------------ | -------------------------------- |
| **Framework**      | FastAPI 0.121.1                  |
| **Language**       | Python 3.14+                     |
| **ORM**            | SQLAlchemy 2.1                   |
| **Migrations**     | Alembic                          |
| **Databases**      | MariaDB, MySQL, PostgreSQL       |
| **Cache/Queue**    | Redis (via RQ)                   |
| **Real-time**      | Socket.IO (python-socketio)      |
| **Auth**           | OAuth2 + Basic + OIDC + Sessions |
| **ASGI Server**    | Uvicorn / Gunicorn               |
| **Error Tracking** | Sentry                           |

RomM's backend is responsible for:

- **Library scanning**: detecting platforms and ROMs from the filesystem
- **Metadata enrichment**: pulling game info from 10+ external providers
- **User management**: roles, authentication, per-user game tracking
- **Device management**: device registration and client tokens for companion apps
- **Feed generation**: Tinfoil, WebRcade, PKGi, and other custom formats

---

## 2. High-Level Architecture

```text
                                 +---------------------+
                                 |     Nginx / CDN     |
                                 |  (reverse proxy,    |
                                 |   X-Accel-Redirect) |
                                 +----------+----------+
                                            |
                                            v
                              +-------------+--------------+
                              |     FastAPI Application     |
                              |        (main.py)            |
                              +-------------+--------------+
                                            |
              +-----------------------------+------------------------------+
              |                             |                              |
     +--------v--------+         +---------v----------+         +---------v--------+
     |   Middleware     |         |   API Routers      |         |   WebSockets     |
     |  Stack (5 layers)|         |  (21 routers)      |         |       /ws        |
     +---------+--------+         +---------+----------+         +---------+--------+
               |                            |                              |
               v                            v                              v
     +-------------------+      +-----------+-----------+       +----------+---------+
     | CORS              |      |    Endpoint Layer     |       |  Socket.IO Server  |
     | CSRF              |      | (request validation,  |       |  (scan progress,   |
     | Authentication    |      |  response schemas)    |       |   activity, logs)  |
     | Session (Redis)   |      +-----------+-----------+       +----------+---------+
     | Context Vars      |                  |                              |
     +-------------------+                  v                              |
                              +-------------+--------------+               |
                              |     Handler Layer          |               |
                              | (business logic, CRUD,     |<--------------+
                              |  metadata, filesystem)     |
                              +------+-------+------+------+
                                     |       |      |
                  +------------------+       |      +------------------+
                  |                          |                         |
         +--------v--------+     +----------v----------+    +---------v---------+
         |   Database       |     |   External APIs     |    |   File System     |
         |  (SQLAlchemy)    |     |  (IGDB, MobyGames,  |    |  (ROM library,    |
         |                  |     |   ScreenScraper,     |    |   avatars, art)   |
         | MariaDB/MySQL/PG |     |   SteamGridDB, RA,   |    |                   |
         +---------+--------+     |   LaunchBox, HLTB,   |    +-------------------+
                   |              |   Hasheous, TGDB,    |
                   v              |   Flashpoint)        |
         +-------------------+    +---------------------+
         |     Redis          |
         | (sessions, cache,  |
         |  job queues)       |
         +-------------------+
```

### Layered Architecture

```text
+-----------------------------------------------------------------------+
|                         PRESENTATION LAYER                             |
|  endpoints/          API route handlers, request/response schemas      |
|  endpoints/sockets/  WebSocket event handlers                          |
+-----------------------------------------------------------------------+
|                         BUSINESS LOGIC LAYER                           |
|  handler/auth/       Authentication & authorization                    |
|  handler/database/   CRUD operations per entity                        |
|  handler/metadata/   Metadata fetching & normalization                 |
|  handler/filesystem/ File system operations                            |
|  handler/            Scan orchestration, socket management            |
+-----------------------------------------------------------------------+
|                         DATA ACCESS LAYER                              |
|  models/             SQLAlchemy ORM model definitions                  |
|  adapters/services/  External API client wrappers                      |
|  handler/redis_handler.py  Cache & queue operations                    |
+-----------------------------------------------------------------------+
|                         INFRASTRUCTURE LAYER                           |
|  config/             Environment variables & YAML config               |
|  decorators/         Auth & DB session decorators                      |
|  exceptions/         Custom exception hierarchy                        |
|  logger/             Structured logging                                |
|  utils/              Shared helpers (hashing, context, validation)     |
|  tasks/              Background job definitions & scheduling           |
+-----------------------------------------------------------------------+
```

---

## 3. Directory Structure

```text
backend/
├── main.py                    # FastAPI app creation, middleware, routers
├── startup.py                 # Pre-startup: cache init, scheduled tasks
├── watcher.py                 # Filesystem change detection (watchfiles)
├── __version__.py             # Version placeholder
├── alembic.ini                # Alembic migration configuration
├── pytest.ini                 # Test configuration
├── .coveragerc                # Code coverage settings
│
├── adapters/                  # External API client wrappers
│   └── services/
│       ├── igdb.py            # IGDB (Internet Game Database)
│       ├── mobygames.py       # MobyGames
│       ├── screenscraper.py   # ScreenScraper
│       ├── steamgriddb.py     # SteamGridDB
│       ├── retroachievements.py # RetroAchievements
│       ├── rahasher.py        # RA hash computation
│       ├── libretro_thumbnails.py # Libretro thumbnails (covers/screenshots)
│       └── *_types.py         # Type definitions per adapter
│
├── alembic/                   # Database migrations
│   ├── env.py                 # Migration environment setup
│   └── versions/              # 80+ migration scripts
│
├── config/                    # Configuration system
│   ├── __init__.py            # Env var loading (100+ variables)
│   └── config_manager.py      # YAML config manager (singleton)
│
├── decorators/                # Function decorators
│   ├── auth.py                # @protected_route, OAuth setup
│   └── database.py            # @begin_session (DB session injection)
│
├── endpoints/                 # API route handlers
│   ├── auth.py                # Login, logout, token, OIDC
│   ├── user.py                # User CRUD, invite links
│   ├── client_tokens.py       # API token management
│   ├── platform.py            # Platform CRUD
│   ├── collections.py         # Collection management
│   ├── configs.py             # App configuration
│   ├── device/                # Devices
│   │   ├── __init__.py        # Device registration
│   │   ├── auth.py            # Device pairing flow (RFC 8628)
│   ├── export.py              # ES-DE gamelist.xml + Pegasus exports
│   ├── feeds.py               # Tinfoil, WebRcade, PKGi feeds
│   ├── heartbeat.py           # Health check + setup wizard
│   ├── search.py              # Cross-provider metadata search
│   ├── stats.py               # Library statistics
│   ├── tasks.py               # Task monitoring & triggering
│   ├── roms/                  # ROM-specific endpoints
│   │   ├── __init__.py        # ROM CRUD, download, bulk ops
│   │   ├── upload.py          # Chunked upload system
│   │   ├── files.py           # File download (nginx redirect)
│   │   ├── manual.py          # Manual metadata entry
│   │   └── notes.py           # ROM notes/comments
│   ├── sockets/               # WebSocket handlers
│   │   ├── scan.py            # Scan progress events
│   ├── forms/                 # Request body models
│   │   └── identity.py        # Auth form schemas
│   └── responses/             # Pydantic response schemas
│       ├── base.py            # Base response classes
│       ├── rom.py             # SimpleRomSchema, DetailedRomSchema
│       ├── platform.py        # PlatformSchema
│       ├── identity.py        # UserSchema, TokenResponse
│       └── ...                # 15+ more response schemas
│
├── exceptions/                # Custom exception classes
│   ├── auth_exceptions.py     # AuthCredentialsException, etc.
│   ├── endpoint_exceptions.py # NotFound, Permission, Conflict
│   ├── fs_exceptions.py       # Filesystem errors
│   ├── config_exceptions.py   # Config write errors
│   ├── task_exceptions.py     # Scheduler errors
│   └── socket_exceptions.py   # Scan stopped or refused
│
├── handler/                   # Business logic layer
│   ├── scan_handler.py        # Library scan orchestration
│   ├── socket_handler.py      # Socket.IO server management
│   ├── redis_handler.py       # Redis clients & queues
│   ├── scan_jobs.py           # Finding & pruning in-flight scan jobs
│   ├── auth/                  # Authentication subsystem
│   │   ├── base_handler.py    # Auth, OAuth, OIDC handlers
│   │   ├── hybrid_auth.py     # Multi-method auth backend
│   │   ├── constants.py       # Scopes, role mappings
│   │   └── middleware/        # CSRF, session middleware
│   ├── database/              # Per-entity CRUD handlers
│   │   ├── base_handler.py    # Engine, session factory
│   │   ├── roms_handler.py    # ROM queries & mutations
│   │   ├── platforms_handler.py     # Platform CRUD, slug mapping
│   │   ├── users_handler.py         # User CRUD, role management
│   │   ├── collections_handler.py   # Regular/smart/virtual collections
│   │   ├── devices_handler.py       # Device registration, fingerprinting
│   │   ├── client_tokens_handler.py # API token hash lookup
│   │   └── stats_handler.py         # Library statistics
│   ├── filesystem/            # File I/O operations
│   │   ├── base_handler.py          # Path helpers, base class
│   │   ├── roms_handler.py          # ROM file reading, hashing
│   │   ├── assets_handler.py        # Avatar storage
│   │   ├── platforms_handler.py     # Platform folder detection
│   │   └── resources_handler.py     # Artwork caching
│   └── metadata/              # Metadata provider handlers
│       ├── base_handler.py          # Base metadata handler
│       ├── igdb_handler.py          # IGDB provider
│       ├── moby_handler.py          # MobyGames provider
│       ├── ss_handler.py            # ScreenScraper
│       ├── sgdb_handler.py          # SteamGridDB
│       ├── ra_handler.py            # RetroAchievements
│       ├── hltb_handler.py          # HowLongToBeat
│       ├── steam_handler.py         # Steam storefront (PC platforms)
│       ├── hasheous_handler.py      # Hasheous hash-based lookup
│       ├── tgdb_handler.py          # TheGamesDB
│       ├── flashpoint_handler.py    # Flashpoint archive
│       ├── gamelist_handler.py      # gamelist.xml parser
│       ├── libretro_handler.py      # Libretro thumbnails DB lookup
│       ├── playmatch_handler.py     # PlayMatch algorithm
│       ├── launchbox_handler/       # LaunchBox (local + remote)
│       └── fixtures/                # Static metadata indexes
│           ├── mame_index.json          # MAME ROM → game info
│           ├── scummvm_index.json       # ScummVM identification
│           ├── ps1_serial_index.json    # PS1 serial → game
│           ├── ps2_serial_index.json    # PS2 serial → game
│           ├── ps2_opl_index.json       # PS2 OPL serials
│           └── psp_serial_index.json    # PSP serial → game
│
├── logger/                    # Logging setup
│   ├── logger.py              # Logger instance ("romm")
│   └── formatter.py           # Colored formatter, LOGGING_CONFIG
│
├── models/                    # SQLAlchemy ORM models
│   ├── base.py                # BaseModel (created_at, updated_at)
│   ├── user.py                # User, Role enum
│   ├── platform.py            # Platform
│   ├── rom.py                 # Rom, RomFile, RomMetadata, RomUser, RomNote
│   ├── collection.py          # Collection, SmartCollection, VirtualCollection
│   ├── device.py              # Device
│   └── client_token.py        # ClientToken
│
├── tasks/                     # Background job system
│   ├── tasks.py               # TaskSpec, base Task, PeriodicTask, run_task_by_name
│   ├── registry.py            # Name -> TaskSpec catalog, the API and cron address
│   ├── cron_config.py         # Schedule the `rq cron` process loads
│   ├── scheduled/             # Cron-scheduled tasks
│   │   ├── scan_library.py                    # Nightly library rescan
│   │   ├── sync_retroachievements_progress.py # Pull RA user progress
│   │   ├── update_switch_titledb.py           # Refresh Switch TitleDB
│   │   ├── update_launchbox_metadata.py       # Refresh LaunchBox data
│   │   └── convert_images_to_webp.py          # Artwork WebP conversion
│   └── manual/                # On-demand tasks
│       ├── cleanup_missing_roms.py       # Drop DB entries for missing files
│       ├── convert_library.py            # Store matched ROMs in each platform's library format
│       └── cleanup_orphaned_resources.py # Remove unreferenced artwork
│
├── utils/                     # Shared helpers
│   ├── __init__.py            # get_version()
│   ├── cache.py               # Redis fixture loading
│   ├── hashing.py             # CRC32, file hashing
│   ├── context.py             # Async context vars (aiohttp, httpx2)
│   ├── database.py            # JSON/JSONB helpers, DB detection
│   ├── filesystem.py          # Path sanitization
│   ├── validation.py          # Input validation
│   ├── client_tokens.py       # Token generation
│   ├── datetime.py            # UTC helpers
│   ├── json_module.py         # Custom JSON encoder
│   ├── nginx.py               # X-Accel-Redirect responses
│   ├── router.py              # Custom APIRouter
│   ├── gamelist_exporter.py   # ES-DE gamelist.xml generation
│   ├── platform_aliases.py    # Batocera/RetroBat/ES-DE folder name → slug
│   ├── archives.py            # Archive handling (7-Zip, zip)
│   ├── platforms.py           # Platform management
│   └── emoji.py               # Emoji utilities
│
├── tools/                     # Development utilities
│   └── xml_diagnostics.py     # XML diagnostic tool
│
├── tests/                     # Test suite
│   ├── conftest.py            # Pytest fixtures
│   ├── factories.py           # make_* factories that persist test rows
│   └── ...                    # Mirrors backend structure
│
└── romm_test/                 # Test fixtures & data
    ├── assets/users/          # Test user avatars
    ├── config/                # Test configuration
    ├── library/               # Test ROM library
    └── resources/roms/        # Test ROM resources
```

---

## 4. Application Lifecycle

### Startup Sequence

```text
1. alembic upgrade head          # Run database migrations
2. startup.main()                # Async startup tasks
   ├── Clear stale delayed scans and legacy scheduler keys
   └── Load fixture caches into Redis
       ├── mame_index.json
       ├── scummvm_index.json
       ├── ps1/ps2/psp serial indexes
3. uvicorn.run("main:app")       # Start ASGI server
   └── FastAPI lifespan
       ├── Create aiohttp.ClientSession
       ├── Create httpx2.AsyncClient
       └── Store in app.state + context vars
```

### Middleware Stack (execution order, outside-in)

```text
Request →  CORS → CSRF → Authentication → Session (Redis) → Context Vars → Endpoint
Response ← CORS ← CSRF ← Authentication ← Session (Redis) ← Context Vars ← Endpoint
```

| Layer | Middleware                 | Purpose                                           |
| ----- | -------------------------- | ------------------------------------------------- |
| 1     | `CORSMiddleware`           | Allow cross-origin requests (all origins)         |
| 2     | `CSRFMiddleware`           | Token-based CSRF protection (cookie + header)     |
| 3     | `AuthenticationMiddleware` | `HybridAuthBackend`: Basic, Bearer, Session, OIDC |
| 4     | `RedisSessionMiddleware`   | Cookie-based sessions stored in Redis             |
| 5     | `set_context_middleware`   | Inject aiohttp/httpx2 clients into context vars   |

### Request Flow

```text
HTTP Request
    │
    ├─ Middleware processes request (auth, session, CSRF)
    │
    ├─ FastAPI routes to endpoint handler
    │   └─ @protected_route checks scopes
    │
    ├─ Endpoint calls handler layer
    │   ├─ handler/database/*   → SQLAlchemy queries
    │   ├─ handler/metadata/*   → External API calls
    │   ├─ handler/filesystem/* → File I/O
    │   └─ handler/auth/*       → Token operations
    │
    ├─ Response schema (Pydantic) serializes output
    │
    └─ HTTP Response
```

---

## 5. Database Layer

### Supported Databases

| Database       | Driver                     | Status    |
| -------------- | -------------------------- | --------- |
| MariaDB 10.11+ | `mariadb+mariadbconnector` | Default   |
| MySQL 8.0.17+  | `mysql+mysqlconnector`     | Supported |
| PostgreSQL     | `postgresql+psycopg`       | Supported |

MariaDB 10.5 and 10.6 reached upstream end of life in June 2025 and July 2026, so
10.11 is the oldest LTS still receiving fixes.

CI runs the test suite against MariaDB 13.0 and PostgreSQL 18, and the migration
suite additionally against MariaDB 10.11, which predates the 11.6 `uca1400`
collation default. MySQL has no CI coverage.

Query SQL that differs between engines lives in `utils/sql_dialect.py`
(`DialectCase` and the helpers built on it), which picks each engine's spelling
when the statement compiles. Handlers don't branch on `ROMM_DB_DRIVER`.

`utils/fulltext.py` reads InnoDB's full-text token sizes and stopwords from the
server and splits search words the way its parser does, so a search can require
the words a FULLTEXT index holds and check the rest with `LIKE`.

### Engine & Session Setup

**Location:** `handler/database/base_handler.py`

```python
sync_engine = create_engine(
    ConfigManager.get_db_engine(),
    pool_pre_ping=True,  # Connection health check
    echo=False,          # SQL logging (DEV_SQL_ECHO overrides)
)
sync_session = sessionmaker(bind=sync_engine, expire_on_commit=False)
```

Sessions are injected via the `@begin_session` decorator, which wraps handlers in a transaction context.

### Base Model

**Location:** `models/base.py`

All models inherit `BaseModel`, providing:

| Column       | Type                 | Behavior                     |
| ------------ | -------------------- | ---------------------------- |
| `created_at` | `TIMESTAMP(tz=True)` | Auto-set to UTC on creation  |
| `updated_at` | `TIMESTAMP(tz=True)` | Auto-updated on modification |

Constants: `FILE_NAME_MAX_LENGTH=450`, `FILE_PATH_MAX_LENGTH=1000`, `FILE_EXTENSION_MAX_LENGTH=100`

### Entity-Relationship Diagram

```text
                                    ┌──────────────┐
                          ┌────────>│  client_tokens│
                          │         └──────────────┘
                          │
                          │         ┌──────────────┐
                          ├────────>│   devices     │
┌──────────┐              │         └──────────────┘
│  users   │──────────────┤
└──────────┘              │
     │                    │
     │                    │         ┌──────────────┐
     │                    ├────────>│  rom_user     │
     │                    │         └──────────────┘
     │                    │              │
     │                    │              │
     │                    │         ┌──────────────┐      ┌──────────────┐
     │                    │    ┌───>│    roms       │<─────│  platforms   │
     │                    │    │    └──────────────┘      └──────────────┘
     │                    │    │         │                      │
     │                    │    │         ├────> rom_files
     │                    │    │         ├────> roms_metadata
     │                    │    │         ├────> rom_notes
     │                    │    │         └────> sibling_roms (self M:M)
     │                    │    │
     │         ┌──────────┴────┴──┐
     └────────>│   collections    │  (M:M via collections_roms)
               ├──────────────────┤
               │ smart_collections│  (filter-based, dynamic)
               ├──────────────────┤
               │virtual_collections│  (DB view over virtual_collection_roms)
               └──────────────────┘
```

### Model Definitions

#### Users

**Table:** `users`

| Column            | Type                              | Notes                                           |
| ----------------- | --------------------------------- | ----------------------------------------------- |
| `id`              | Integer                           | PK, autoincrement                               |
| `username`        | String(255)                       | Unique, indexed                                 |
| `hashed_password` | String(255)                       | Nullable (OIDC users)                           |
| `email`           | String(255)                       | Unique, indexed, nullable                       |
| `oidc_issuer`     | ExactString(255)                  | OIDC `iss`, nullable                            |
| `oidc_sub`        | ExactString(255)                  | OIDC `sub`, nullable; unique with `oidc_issuer` |
| `enabled`         | Boolean                           | Default `True`                                  |
| `role`            | Enum(`VIEWER`, `EDITOR`, `ADMIN`) | Default `VIEWER`                                |
| `avatar_path`     | String(255)                       | Default `""`                                    |
| `last_login`      | Timestamp                         | Nullable                                        |
| `last_active`     | Timestamp                         | Nullable                                        |
| `ra_username`     | String(255)                       | RetroAchievements username                      |
| `ra_progression`  | JSON                              | RetroAchievements data                          |
| `ui_settings`     | JSON                              | User preferences                                |

**Relationships:** rom_users (1:M), notes (1:M), collections (1:M), smart_collections (1:M), devices (1:M, cascade), client_tokens (1:M, cascade)

---

#### Platforms

**Table:** `platforms`

| Column                                                                                                       | Type         | Notes                         |
| ------------------------------------------------------------------------------------------------------------ | ------------ | ----------------------------- |
| `id`                                                                                                         | Integer      | PK                            |
| `slug`                                                                                                       | String(100)  | Indexed, canonical identifier |
| `fs_slug`                                                                                                    | String(100)  | Filesystem folder name        |
| `name`                                                                                                       | String(400)  | Display name                  |
| `custom_name`                                                                                                | String(400)  | User override                 |
| `igdb_id`, `sgdb_id`, `moby_id`, `ss_id`, `ra_id`, `launchbox_id`, `hasheous_id`, `tgdb_id`, `flashpoint_id` | Integer      | External provider IDs         |
| `category`                                                                                                   | String(100)  | Platform category             |
| `generation`                                                                                                 | Integer      | Console generation            |
| `family_name` / `family_slug`                                                                                | String(1000) | Platform family               |
| `aspect_ratio`                                                                                               | String(10)   | Default `"2 / 3"`             |
| `missing_from_fs`                                                                                            | Boolean      | Default `False`               |

**Computed properties:** `rom_count` (subquery), `fs_size_bytes` (sum of ROM sizes)

**Relationships:** roms (1:M)

---

#### ROMs

**Table:** `roms` (the central entity)

| Column Group          | Columns                                                                                                                                                                                                     | Notes                   |
| --------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------- |
| **Identity**          | `id`, `platform_id` (FK)                                                                                                                                                                                    | Core identifiers        |
| **External IDs**      | `igdb_id`, `sgdb_id`, `moby_id`, `ss_id`, `ra_id`, `launchbox_id`, `hasheous_id`, `tgdb_id`, `flashpoint_id`, `hltb_id`, `steam_id`, `gamelist_id`                                                          | All indexed             |
| **Filesystem**        | `fs_name`, `fs_name_no_tags`, `fs_name_no_ext`, `fs_extension`, `fs_path`, `fs_size_bytes`                                                                                                                  | File info               |
| **Display**           | `name`, `slug`, `summary`                                                                                                                                                                                   | Game metadata           |
| **Provider metadata** | `igdb_metadata`, `moby_metadata`, `ss_metadata`, `ra_metadata`, `launchbox_metadata`, `hasheous_metadata`, `flashpoint_metadata`, `hltb_metadata`, `steam_metadata`, `gamelist_metadata`, `manual_metadata` | JSON blobs per provider |
| **Media**             | `path_cover_s`, `path_cover_l`, `url_cover`, `path_manual`, `url_manual`, `path_screenshots`, `url_screenshots`                                                                                             | Cover art & screenshots |
| **Classification**    | `revision`, `version`, `regions`, `languages`, `tags`                                                                                                                                                       | Game attributes         |
| **Hashes**            | `crc_hash`, `md5_hash`, `sha1_hash`, `ra_hash`                                                                                                                                                              | File integrity          |
| **State**             | `missing_from_fs`                                                                                                                                                                                           | Filesystem sync         |

**Relationships:** platform (M:1), files (1:M), rom_users (1:M), notes (1:M), metadatum (1:1), sibling_roms (M:M self-referential), collections (M:M)

---

#### ROM Files (table)

**Table:** `rom_files`

Tracks individual files within a ROM (archives can contain multiple files).

| Column                                         | Type                    | Notes                                                                                                                              |
| ---------------------------------------------- | ----------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| `id`                                           | Integer                 | PK                                                                                                                                 |
| `rom_id`                                       | Integer                 | FK → roms                                                                                                                          |
| `file_name`, `file_path`                       | String                  | File identity                                                                                                                      |
| `file_size_bytes`                              | BigInteger              | Size                                                                                                                               |
| `crc_hash`, `md5_hash`, `sha1_hash`, `ra_hash` | String(100)             | Hashes                                                                                                                             |
| `category`                                     | Enum                    | `GAME`, `DLC`, `HACK`, `MANUAL`, `PATCH`, `UPDATE`, `MOD`, `DEMO`, `TRANSLATION`, `PROTOTYPE`, `CHEAT`, `SOUNDTRACK`, `SCREENSHOT` |
| `title_id`, `title_version`                    | String(100), BigInteger | Platform-native id and numeric version read from the binary (rom-converto or sigil)                                                |
| `converto_read_at`                             | Timestamp               | Last time rom-converto read the file; NULL queues it on the next scan                                                              |
| `missing_from_fs`                              | Boolean                 | Sync state                                                                                                                         |

**Relationships:** rom (M:1), track_meta (1:1, `SOUNDTRACK` files only)

---

#### Track Meta

**Table:** `track_meta`

Audio metadata for a `SOUNDTRACK` rom_file (1:1), indexed for the music API. Written from file tags at upload/scan.

| Column                     | Type         | Notes                            |
| -------------------------- | ------------ | -------------------------------- |
| `rom_file_id`              | Integer      | PK, FK → rom_files (cascade)     |
| `rom_id`                   | Integer      | FK → roms (cascade), indexed     |
| `title`, `artist`, `album` | String(512)  | Indexed: `artist`, `album`       |
| `genre`                    | String(255)  |                                  |
| `year`, `track`, `disc`    | SmallInteger | Parsed from tags; `year` indexed |
| `duration_seconds`         | Float        | Indexed                          |
| `has_embedded_cover`       | Boolean      |                                  |
| `cover_path`               | String(1024) | Extracted cover under resources  |

**Relationships:** rom_file (1:1)

---

#### ROM Metadata (Aggregated)

**Table:** `roms_metadata` (aggregated metadata from all providers)

| Column               | Type                        |
| -------------------- | --------------------------- |
| `rom_id`             | Integer (PK, FK → roms)     |
| `genres`             | JSON                        |
| `franchises`         | JSON                        |
| `collections`        | JSON                        |
| `companies`          | JSON                        |
| `game_modes`         | JSON                        |
| `age_ratings`        | JSON                        |
| `player_count`       | String(100)                 |
| `first_release_date` | BigInteger (UNIX timestamp) |
| `average_rating`     | Float                       |

---

#### ROM User Data

**Table:** `rom_user` (per-user, per-ROM tracking)

| Column               | Type         | Notes                                                                 |
| -------------------- | ------------ | --------------------------------------------------------------------- |
| `rom_id` + `user_id` | FK composite | Unique constraint                                                     |
| `is_main_sibling`    | Boolean      | Primary version flag                                                  |
| `last_played`        | Timestamp    |                                                                       |
| `backlogged`         | Boolean      |                                                                       |
| `now_playing`        | Boolean      |                                                                       |
| `hidden`             | Boolean      |                                                                       |
| `rating`             | Integer      | 0-5                                                                   |
| `difficulty`         | Integer      |                                                                       |
| `completion`         | Integer      | Percentage                                                            |
| `status`             | Enum         | `INCOMPLETE`, `FINISHED`, `COMPLETED_100`, `RETIRED`, `NEVER_PLAYING` |

---

#### ROM Notes

**Table:** `rom_notes`

| Column                         | Type        | Notes             |
| ------------------------------ | ----------- | ----------------- |
| `id`                           | Integer     | PK                |
| `rom_id` + `user_id` + `title` |             | Unique constraint |
| `title`                        | String(400) |                   |
| `content`                      | Text        |                   |
| `is_public`                    | Boolean     | Default `False`   |
| `tags`                         | JSON        |                   |

---

#### Collections

**Table:** `collections` (manually curated ROM lists)

| Column                        | Type        | Notes     |
| ----------------------------- | ----------- | --------- |
| `id`                          | Integer     | PK        |
| `user_id`                     | FK → users  |           |
| `name`                        | String(400) |           |
| `description`                 | Text        |           |
| `is_public`                   | Boolean     |           |
| `is_favorite`                 | Boolean     |           |
| `path_cover_s/l`, `url_cover` | Text        | Cover art |

Linked to ROMs via `collections_roms` join table (M:M).

**Table:** `smart_collections` (dynamic, filter-based)

| Column            | Type    | Notes                   |
| ----------------- | ------- | ----------------------- |
| `filter_criteria` | JSON    | Query definition        |
| `rom_ids`         | JSON    | Cached matching ROM IDs |
| `rom_count`       | Integer | Cached count            |

**View:** `virtual_collections` (database view, read-only, excluded from migrations).

It aggregates `virtual_collection_roms`, a real table holding one row per
(`type`, `name`, `rom_id`) plus that rom's cover paths. Membership is derived
from the `generated_*` columns on `roms` and maintained by triggers on that
table (`virtual_collection_roms_ai`/`_au` on MariaDB/MySQL,
`virtual_collection_roms_aiu` calling `romm_sync_virtual_collection_roms()` on
PostgreSQL); rom deletions are handled by the foreign key's cascade. Reads are
therefore indexed lookups instead of a full re-derivation of every rom's
metadata. Covers are not aggregated in the view: the collections handler
resolves at most `MAX_VIRTUAL_COLLECTION_COVERS` per collection.

---

#### Devices

**Table:** `devices`

| Column                                         | Type        | Notes       |
| ---------------------------------------------- | ----------- | ----------- |
| `id`                                           | String(255) | UUID, PK    |
| `user_id`                                      | FK → users  |             |
| `name`, `platform`, `client`, `client_version` | String      | Device info |
| `last_seen`                                    | Timestamp   |             |

---

#### Client Tokens

**Table:** `client_tokens` (long-lived API tokens)

| Column         | Type         | Notes                        |
| -------------- | ------------ | ---------------------------- |
| `id`           | Integer      | PK                           |
| `user_id`      | FK → users   |                              |
| `name`         | String(255)  | Display name                 |
| `hashed_token` | String(64)   | SHA-256 hash, unique         |
| `scopes`       | String(1000) | Space-separated OAuth scopes |
| `expires_at`   | Timestamp    | Nullable                     |
| `last_used_at` | Timestamp    |                              |

Token format: `rmm_` + 64 hex chars (32-byte random)

---

#### Audit Events

**Table:** `audit_events` (what users and background jobs did, kept `AUDIT_LOG_RETENTION_DAYS`)

| Column                                                  | Type       | Notes                                         |
| ------------------------------------------------------- | ---------- | --------------------------------------------- |
| `id`                                                    | Integer    | PK                                            |
| `occurred_at`                                           | Timestamp  | For a synced play, when it started            |
| `actor_kind`                                            | String(16) | `user`, `anonymous` or `system`               |
| `actor_id`                                              | FK → users | `SET NULL` on delete                          |
| `action`                                                | String(64) | `AuditAction`, e.g. `rom.download`            |
| `actor_name`, `target_type`, `target_id`, `target_name` | String     | Snapshots, so an event outlives what it names |
| `ip_address`, `device_id`                               | String     | No FK                                         |
| `data`                                                  | JSON       | What the client builds the sentence from      |

---

### Alembic Migrations

80+ migration scripts in `alembic/versions/`. Key milestones:

| Migration      | Description                                 |
| -------------- | ------------------------------------------- |
| `0009`         | Models refactor                             |
| `0014`, `0019` | Asset filesystem refactoring                |
| `0020`         | Added created_at/updated_at to all tables   |
| `0021`         | ROM user associations                       |
| `0022`         | Collection system                           |
| `0023`         | Column nullability constraints              |
| `0024`         | Sibling ROM database views                  |
| `0025`         | ROM hash tracking                           |
| `0064`         | Performance indexes on updated_at           |
| `0068`         | Device tables                               |
| `0072`         | Client tokens table                         |
| `0129`         | Drop emulator save data (irreversible)      |
| `0152`         | Cross-user smart collection scopes          |
| `0130`, `0131` | Notifications and notification channels     |
| `0132`         | Audit events                                |
| `0133`, `0134` | Indexed gallery sorts                       |
| `0137`         | System permission groups keyed, not flagged |
| `0139`         | Pinned media per ROM user                   |
| `0143`         | Sibling platform names                      |
| `0144`         | OIDC subject on users                       |
| `0145`         | Drop derivable columns                      |
| `0146`         | ROM search aliases                          |
| `0147`         | ROM file title ids                          |
| `0149`, `0150` | ROM file-name indexes                       |

The chain runs `0129`, `0152`, then `0130` to `0150`, so `0150` is the head. Upstream revisions for removed features are skipped.

Migrations support batch mode for SQLite and DB-specific SQL for MariaDB/MySQL/PostgreSQL.

---

## 6. API Endpoints

**Base URL:** `/api`
**Documentation:** Swagger UI at `/api/docs`, ReDoc at `/api/redoc`
**Pagination:** `PageParams` (`limit`, `offset`) via the `PAGE_QUERY` dependency, returning a `LimitOffsetPage` (`items`, `total`, `limit`, `offset`); both live in `endpoints/responses/base.py`. Routes with a smaller page cap subclass `PageParams` (`MusicPageParams`, `AuditPageParams`)

### 6.1 Authentication (`/api`)

| Method | Path               | Auth | Description                                    |
| ------ | ------------------ | ---- | ---------------------------------------------- |
| POST   | `/login`           | No   | Session login (HTTP Basic)                     |
| POST   | `/logout`          | No   | Logout (returns OIDC logout URL if configured) |
| POST   | `/token`           | No   | OAuth2 token (password, refresh_token grants)  |
| GET    | `/login/openid`    | No   | OIDC login redirect                            |
| GET    | `/oauth/openid`    | No   | OIDC callback                                  |
| POST   | `/forgot-password` | No   | Email a reset link, or log it without email    |
| POST   | `/reset-password`  | No   | Reset password with token                      |

A reset link is emailed when SMTP is set up, the user has an address and `ROMM_BASE_URL` is shareable, at most once a minute per user; otherwise it goes to the log for an admin to pass on. It is built from `ROMM_BASE_URL`, never the request's `Host`. The heartbeat's `NOTIFICATIONS.EMAILS_RESET_LINKS` says whether links are emailed.

### 6.2 Users (`/api/users`)

| Method | Path               | Scope                  | Description                      |
| ------ | ------------------ | ---------------------- | -------------------------------- |
| POST   | `/`                | ME_WRITE / USERS_WRITE | Create user (first user = admin) |
| POST   | `/invite-link`     | USERS_WRITE            | Generate invite token            |
| POST   | `/register`        | None                   | Register with invite token       |
| GET    | `/`                | USERS_READ             | List all users                   |
| GET    | `/identifiers`     | USERS_READ             | Get user IDs                     |
| GET    | `/me`              | ME_READ                | Current user profile             |
| GET    | `/{id}`            | USERS_READ             | Get user by ID                   |
| PUT    | `/{id}`            | ME_WRITE               | Update user                      |
| DELETE | `/{id}`            | USERS_WRITE            | Delete user                      |
| POST   | `/{id}/ra/refresh` | ME_WRITE               | Refresh RetroAchievements data   |

### 6.3 Client Tokens (`/api/client-tokens`)

| Method | Path                  | Scope       | Description                  |
| ------ | --------------------- | ----------- | ---------------------------- |
| POST   | `/`                   | ME_WRITE    | Create token                 |
| GET    | `/`                   | ME_READ     | List user's tokens           |
| DELETE | `/{id}`               | ME_WRITE    | Delete token                 |
| PUT    | `/{id}/regenerate`    | ME_WRITE    | Regenerate token             |
| POST   | `/{id}/pair`          | ME_WRITE    | Generate pair code           |
| GET    | `/pair/{code}/status` | None        | Check pair status            |
| POST   | `/exchange`           | None        | Exchange pair code for token |
| GET    | `/all`                | USERS_READ  | Admin: list all tokens       |
| DELETE | `/{id}/admin`         | USERS_WRITE | Admin: delete any token      |

### 6.4 Platforms (`/api/platforms`)

| Method | Path           | Scope           | Description                                  |
| ------ | -------------- | --------------- | -------------------------------------------- |
| POST   | `/`            | PLATFORMS_WRITE | Create platform                              |
| GET    | `/`            | PLATFORMS_READ  | List platforms (with `updated_after` filter) |
| GET    | `/identifiers` | PLATFORMS_READ  | Get platform IDs                             |
| GET    | `/supported`   | PLATFORMS_READ  | List supported platforms                     |
| GET    | `/{id}`        | PLATFORMS_READ  | Get platform                                 |
| PUT    | `/{id}`        | PLATFORMS_WRITE | Update platform                              |
| DELETE | `/{id}`        | PLATFORMS_WRITE | Delete platform                              |

### 6.5 ROMs (`/api/roms`)

| Method | Path                         | Scope      | Description                                      |
| ------ | ---------------------------- | ---------- | ------------------------------------------------ |
| GET    | `/`                          | ROMS_READ  | List ROMs (paginated, filterable)                |
| GET    | `/identifiers`               | ROMS_READ  | Get ROM IDs                                      |
| GET    | `/random`                    | ROMS_READ  | Get one ROM picked at random (optionally scoped) |
| GET    | `/{id}`                      | ROMS_READ  | Get ROM details                                  |
| PUT    | `/{id}`                      | ROMS_WRITE | Update ROM metadata                              |
| POST   | `/{id}/convert-to-folder`    | ROMS_WRITE | Promote single-file ROM to a folder ROM in place |
| PUT    | `/{id}/user`                 | ME_WRITE   | Update user-specific ROM data                    |
| DELETE | `/{id}`                      | ROMS_WRITE | Delete ROM                                       |
| POST   | `/delete`                    | ROMS_WRITE | Bulk delete                                      |
| POST   | `/download/{id}/{file_name}` | ROMS_READ  | Download ROM                                     |
| GET    | `/{id}/content/{file_name}`  | ROMS_READ  | Download ROM, in a listed `?format=` when asked  |
| POST   | `/unidentified`              | ROMS_READ  | Get unidentified ROMs                            |

With rom-converto enabled (`ROM_CONVERTO_ENABLED`, `converto.download_conversion_enabled`), `?format=zso,iso` lists the formats a client can read. A single-file download whose stored format is listed is served as-is. Otherwise the first listed format with a copy cached under `/tmp/romm/cache/converts` (`$ROMM_TMP_PATH/cache/converts` when set) is served, then the first one rom-converto can produce: answered by the same request if it converts within a few seconds, else `202` with `Retry-After` while it finishes. `406` means no listed format can be served, and `HEAD` reports the same without starting a conversion. Only signed-in, non-kiosk users start conversions. A rom's detail response lists the formats its single file can be converted to in `download_formats`, empty when the caller can't start a conversion.

#### ROM Upload (Chunked)

| Method | Path                    | Scope      | Description               |
| ------ | ----------------------- | ---------- | ------------------------- |
| POST   | `/upload/init`          | ROMS_WRITE | Initialize upload session |
| POST   | `/upload/{id}/chunk`    | ROMS_WRITE | Upload chunk (max 64MB)   |
| POST   | `/upload/{id}/complete` | ROMS_WRITE | Finalize upload           |
| GET    | `/upload/{id}/session`  | ROMS_WRITE | Check session status      |
| DELETE | `/upload/{id}`          | ROMS_WRITE | Cancel upload             |

#### ROM Files

| Method | Path                         | Scope     | Description                             |
| ------ | ---------------------------- | --------- | --------------------------------------- |
| GET    | `/{id}/files`                | ROMS_READ | Get ROM file metadata                   |
| GET    | `/{id}/files/content/{name}` | ROMS_READ | Download file (nginx X-Accel or direct) |

### 6.6 Music (`/api/music`)

Music-first read API over soundtrack `track_meta`, for external music-player clients. All routes are visibility-filtered (hidden platforms/ROMs excluded).

| Method | Path       | Scope     | Description                                                               |
| ------ | ---------- | --------- | ------------------------------------------------------------------------- |
| GET    | `/tracks`  | ROMS_READ | List tracks (search + artist/album/genre/year/duration filters, sortable) |
| GET    | `/artists` | ROMS_READ | Distinct artists + counts (searchable)                                    |
| GET    | `/albums`  | ROMS_READ | Distinct albums + counts (searchable)                                     |
| GET    | `/genres`  | ROMS_READ | Distinct genres + counts (searchable)                                     |
| GET    | `/years`   | ROMS_READ | Distinct years + counts                                                   |

Facet endpoints (`/artists`, `/albums`, `/genres`, `/years`) return `{value, count}` and accept the same filters as `/tracks`, for contextual typeahead browsing.

### 6.7 Search (`/api/search`)

| Method | Path     | Scope     | Description                          |
| ------ | -------- | --------- | ------------------------------------ |
| GET    | `/roms`  | ROMS_READ | Search metadata across all providers |
| GET    | `/cover` | ROMS_READ | Search SteamGridDB and Steam covers  |

### 6.8 Devices (`/api/devices`)

| Method | Path      | Scope         | Description                                                |
| ------ | --------- | ------------- | ---------------------------------------------------------- |
| POST   | `/`       | DEVICES_WRITE | Register device (fingerprint dedup)                        |
| GET    | `/`       | DEVICES_READ  | List devices                                               |
| GET    | `/online` | DEVICES_READ  | Ids of devices with a live device socket or a recent claim |
| GET    | `/{id}`   | DEVICES_READ  | Get device                                                 |
| PUT    | `/{id}`   | DEVICES_WRITE | Update device                                              |
| DELETE | `/{id}`   | DEVICES_WRITE | Delete device                                              |

### 6.9 Collections (`/api/collections`)

| Method | Path                     | Scope             | Description                       |
| ------ | ------------------------ | ----------------- | --------------------------------- |
| POST   | `/`                      | COLLECTIONS_WRITE | Create collection                 |
| GET    | `/`                      | COLLECTIONS_READ  | List collections                  |
| GET    | `/identifiers`           | COLLECTIONS_READ  | Get collection IDs                |
| GET    | `/{id}`                  | COLLECTIONS_READ  | Get collection                    |
| PUT    | `/{id}`                  | COLLECTIONS_WRITE | Update collection                 |
| PUT    | `/{id}/visibility`       | COLLECTIONS_WRITE | Share or unshare collection       |
| PUT    | `/smart/{id}/visibility` | COLLECTIONS_WRITE | Share or unshare smart collection |
| DELETE | `/{id}`                  | COLLECTIONS_WRITE | Delete collection                 |
| POST   | `/{id}/roms`             | COLLECTIONS_WRITE | Add ROM to collection             |
| DELETE | `/{id}/roms/{rom_id}`    | COLLECTIONS_WRITE | Remove ROM                        |

### 6.10 Feeds (`/api/feeds`)

| Method | Path                  | Description                   |
| ------ | --------------------- | ----------------------------- |
| GET    | `/webrcade`           | WebRcade feed format          |
| GET    | `/tinfoil`            | Tinfoil custom index (Switch) |
| GET    | `/pkgi/ps3/{type}`    | PKGi PS3 database             |
| GET    | `/pkgi/psvita/{type}` | PKGi PS Vita database         |
| GET    | `/pkgi/psp/{type}`    | PKGi PSP database             |
| GET    | `/fpkgi/{platform}`   | FPKGi (PS4/PS5) format        |
| GET    | `/kekatsu/{platform}` | Kekatsu DS format             |
| GET    | `/pkgj/psp/games`     | PKGj PSP games                |
| GET    | `/pkgj/psp/dlc`       | PKGj PSP DLC                  |
| GET    | `/pkgj/psvita/games`  | PKGj PS Vita games            |
| GET    | `/pkgj/psvita/dlc`    | PKGj PS Vita DLC              |
| GET    | `/pkgj/psx/games`     | PKGj PSX games                |

### 6.11 Configuration (`/api/config`)

| Method | Path                       | Scope           | Description              |
| ------ | -------------------------- | --------------- | ------------------------ |
| GET    | `/`                        | None            | Get RomM configuration   |
| POST   | `/system/platforms`        | PLATFORMS_WRITE | Add platform binding     |
| DELETE | `/system/platforms/{slug}` | PLATFORMS_WRITE | Remove platform binding  |
| POST   | `/system/versions`         | PLATFORMS_WRITE | Add version mapping      |
| DELETE | `/system/versions/{slug}`  | PLATFORMS_WRITE | Remove version mapping   |
| POST   | `/system/exclusions`       | PLATFORMS_WRITE | Add exclusion pattern    |
| DELETE | `/system/exclusions`       | PLATFORMS_WRITE | Remove exclusion pattern |

### 6.12 Tasks (`/api/tasks`)

| Method | Path          | Scope     | Description              |
| ------ | ------------- | --------- | ------------------------ |
| GET    | `/`           | TASKS_RUN | List all available tasks |
| GET    | `/status`     | TASKS_RUN | Status of all tasks      |
| GET    | `/{id}`       | TASKS_RUN | Status of specific task  |
| POST   | `/run/{name}` | TASKS_RUN | Trigger task execution   |
| POST   | `/scan`       | TASKS_RUN | Queue a scan             |

`POST /scan` takes the options of the `scan` socket event and answers 202 with the queued job.
`GET /{id}` follows it, with the counts so far in `meta.scan_stats`.
A missing body means a quick scan of the whole library, a missing `apis` every enabled metadata source, and an unknown key answers 422.
A scan of named `roms_ids` goes ahead of a queued library scan, any other scan answers 409 while a library scan is queued or running.
It answers 503 when no worker listens on the scan queue.

### 6.13 Notifications (`/api/notifications`)

| Method | Path    | Scope    | Description                                                 |
| ------ | ------- | -------- | ----------------------------------------------------------- |
| GET    | `/`     | ME_READ  | Caller's notifications, newest first                        |
| POST   | `/`     | ME_WRITE | Send one to yourself; admins also to users, `admins`, `all` |
| POST   | `/read` | ME_WRITE | Mark ids read (`ids: null` marks all)                       |
| DELETE | `/{id}` | ME_WRITE | Dismiss one for good                                        |
| DELETE | `/`     | ME_WRITE | Dismiss all                                                 |

A client's notification carries its own `title`, `body`, `icon` (`mdi-*`) and `link`, which must be a path inside RomM. RomM's own `kind`s are reserved; any other (`custom`, `argosy.sync_done`) is shown as sent.

```bash
curl -X POST "$ROMM/api/notifications" -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "Scan finished", "body": "12 ROMs added", "level": "success", "link": "/rom/12"}'
```

#### Notification channels (`/api/notification-channels`)

Each user forwards their own notifications to other services. A channel is one of three types:

- `apprise`: any of the 100+ services [Apprise](https://github.com/caronc/apprise#supported-notifications) reaches (Discord, Telegram, ntfy, Slack, Gotify…), set up through that service's own fields. **Admins only**, since Apprise opens its own connections, past the SSRF guard. The owner's role is checked again at every delivery, so a demoted admin's channel fails until it turns off.
- `webhook`: RomM's own JSON payload (below), POSTed to an http(s) URL.
- `email`: a plain-text email over the server's SMTP, to an address confirmed with a 6-digit code first.

A channel filters by minimum level and by topic (`scans`, `tasks`, `account`, `custom`); every stored notification that passes goes out in its own RQ job, retried at 30 s, 2 min and 10 min. A channel that fails 10 deliveries in a row turns itself off and tells its owner.

| Method | Path                      | Scope    | Description                                                                                    |
| ------ | ------------------------- | -------- | ---------------------------------------------------------------------------------------------- |
| GET    | `/`                       | ME_READ  | Caller's channels, secrets masked                                                              |
| GET    | `/apprise-services`       | ME_READ  | Every Apprise service and its fields (admins only, else 403)                                   |
| POST   | `/apprise-services/parse` | ME_READ  | Read a pasted URL (Discord's own, or an Apprise one) into its service and fields (admins only) |
| POST   | `/`                       | ME_WRITE | Add a channel; an email address gets a code                                                    |
| PATCH  | `/{id}`                   | ME_WRITE | Change it; an omitted URL or secret stays, an empty secret is dropped                          |
| DELETE | `/{id}`                   | ME_WRITE | Delete it                                                                                      |
| POST   | `/{id}/test`              | ME_WRITE | Send a sample notification now                                                                 |
| POST   | `/{id}/confirm`           | ME_WRITE | Confirm an email address with its code                                                         |
| POST   | `/{id}/resend-code`       | ME_WRITE | Email a new code (once a minute)                                                               |

The Apprise catalog comes from Apprise's own plugin details: URL tokens become fields, options become advanced fields, and a field is required only when every URL template of its service needs it. A token is a secret when Apprise marks it so or its name is a credential's (`token`, `key`, `webhook`…). A channel stores its service and fields, sealed, and each delivery builds the URL from the template those fields fill. Not offered: schemas that act on the host (`syslog`, `dbus`, `windows`…), FCM (it opens its key file itself), the options Apprise reads from a local file (`template`, `keyfile`, `subfile`, `pgp*`) and the ones RomM sets. Apprise follows no redirects and doesn't retry, its timeouts are capped at 10 s to connect and 15 s to read, a list takes at most 20 items, and `@everyone`, `@here` and `<@…>` ping nobody. A failure's error carries Apprise's warning and the start of the service's reply. Each service links its setup guide on Apprise's wiki. A pasted URL is read back into fields by matching the URL Apprise writes for it against the service's templates. The API returns the fields that aren't secret and names the secrets; on edit, a secret left out stays and an empty one goes, but a kept secret never follows the channel to another destination, as Apprise's `url_identifier` tells them apart. A test gets 60 s, like a queued delivery.

Only an admin's webhooks may reach private addresses; everyone else's go through the SSRF guard. A kept webhook secret doesn't follow the channel to another origin. A webhook delivery gets 15 s in all, and only the start of a refusal's body is read. Text for RomM's own kinds is English until outbound messages are translated. Links are absolute only when `ROMM_BASE_URL` is shareable.

```json
{
  "event": "notification",
  "id": 42,
  "kind": "scan_completed",
  "level": "success",
  "title": "Scan completed",
  "body": "3 new games",
  "url": "https://romm.example.com/scan",
  "data": { "new_roms": 3 },
  "actor": null,
  "created_at": "2026-09-23T12:00:00+00:00"
}
```

With a secret, a webhook adds `X-RomM-Signature: sha256=<hex HMAC-SHA256 of the body>`. Email needs `SMTP_HOST` and `SMTP_FROM` (see `env.template`); the heartbeat's `NOTIFICATIONS.EMAIL_ENABLED` says whether it's set up. Channel configs are sealed with a key derived from `ROMM_AUTH_SECRET_KEY`, so rotating it means entering their URLs and secrets again.

### 6.14 Audit Events (`/api/audit-events`)

| Method | Path | Scope   | Description                                                     |
| ------ | ---- | ------- | --------------------------------------------------------------- |
| GET    | `/`  | ME_READ | Events newest first: everyone's for an admin, else the caller's |

Filters: `actor_id`, `action`, `category`, `target_type`/`target_id`, `since`/`until`, `search` (names and IP). Pages carry `max_id`; pass it back so later pages skip events recorded meanwhile. An admin reads everyone's only with `users.read` in the token.

Events are written by `handler/audit_handler.record()` after an action succeeds, and a failure to write never fails the action. A ROM content fetch is a `rom.download`, or a `rom.player_load` when the in-browser player marks it `purpose=play`; a fetch whose Range starts past byte 0, or that the same caller made in the last 10 minutes, isn't recorded. A failed login keeps the attempted name only when an account has it. The client address comes from `X-Forwarded-For` only when the connection is from a proxy in `FORWARDED_ALLOW_IPS`.

### 6.15 Other Endpoints

| Router    | Path                                   | Description                            |
| --------- | -------------------------------------- | -------------------------------------- |
| Heartbeat | `GET /api/heartbeat`                   | System info, version, metadata sources |
| Heartbeat | `GET /api/heartbeat/metadata/{source}` | Check metadata provider health         |
| Heartbeat | `GET /api/setup/library`               | Library structure info (wizard)        |
| Heartbeat | `POST /api/setup/platforms`            | Create platform folders (wizard)       |
| Stats     | `GET /api/stats`                       | Library statistics                     |
| Export    | `POST /api/export/gamelist-xml`        | Export ES-DE gamelist.xml              |
| Export    | `POST /api/export/pegasus`             | Export Pegasus frontend metadata       |

The codebase exposes roughly **196 HTTP operations** and **7 WebSocket handlers** across 24 routers.

---

## 7. Authentication & Authorization

### Authentication Methods

```text
┌──────────────────────────────────────────────────────────────┐
│                    HybridAuthBackend                          │
│                                                              │
│  1. Check session cookie (romm_session)                      │
│     └─ Redis lookup → user from session["sub"]               │
│                                                              │
│  2. Check Authorization header                               │
│     ├─ "Basic ..." → bcrypt password verify                  │
│     ├─ "Bearer ..." → JWT validation (HS256)                 │
│     └─ "Bearer rmm_..." → Client API token (SHA-256 lookup)  │
│                                                              │
│  3. OIDC (if enabled)                                        │
│     └─ Token from OIDC provider → email match → user         │
│                                                              │
│  4. Kiosk mode (if enabled)                                  │
│     └─ Anonymous access with read-only scopes                │
│                                                              │
│  Falls through all methods → 401 Unauthorized                │
└──────────────────────────────────────────────────────────────┘
```

### Token Types

| Token            | Format                | Lifetime               | Storage                 |
| ---------------- | --------------------- | ---------------------- | ----------------------- |
| Access Token     | JWT (HS256)           | 30 min (configurable)  | Client-side             |
| Refresh Token    | JWT with JTI          | 7 days (configurable)  | JTI in Redis            |
| Session          | Cookie `romm_session` | 14 days (configurable) | Redis                   |
| Client API Token | `rmm_` + 64 hex chars | Configurable / never   | SHA-256 hash in DB      |
| CSRF Token       | Signed cookie         | Session lifetime       | Cookie + header         |
| Password Reset   | JWT with JTI          | 10 minutes             | JTI in Redis (one-time) |
| Invite Link      | JWT with JTI          | 10 minutes             | JTI in Redis (one-time) |

### Role-Based Access Control

| Role     | Scopes                                   | Description     |
| -------- | ---------------------------------------- | --------------- |
| `VIEWER` | Read all + write own profile             | Default role    |
| `EDITOR` | VIEWER + write ROMs, platforms, assets   | Content manager |
| `ADMIN`  | EDITOR + user management, task execution | Full access     |

### Scope Definitions

```text
me.read / me.write           : Own profile
roms.read / roms.write       : ROM data
platforms.read / platforms.write : Platform data
assets.read / assets.write   : User avatars
devices.read / devices.write : Device management
collections.read / collections.write : Collections
users.read / users.write     : User management (admin)
tasks.run                    : Task execution
```

### Permission Groups

Endpoints also check the caller's permission group (`handler/auth/permissions.py`), which holds entity and action grants plus per-user overrides. Most entities line up with a scope above.

### CSRF Protection

- Cookie: `romm_csrftoken` (signed with `itsdangerous`)
- Header: `x-csrftoken`
- Both must match and contain the authenticated user's ID
- Exempt: `/api/token`, `/api/client-tokens/exchange`, `/api/client-tokens/pair/*/status`, `/ws`
- Skipped for requests with `Authorization: Bearer` or `Authorization: Basic` headers

### Session Management

- Redis keys: `session:{session_id}`, `user_sessions:{username}`, `session_sockets:{channel}:{session_id}`
- Cookie: `romm_session` (httponly, samesite=lax/strict)
- `clear_user_sessions(user_id)` on password change clears all sessions
- Removing a session (logout, revoke) disconnects the sockets it opened on `/ws`, which would otherwise keep their `user:{id}` and `admin` rooms

---

## 8. Business Logic (Handlers)

### 8.1 Scan Handler (`handler/scan_handler.py`)

The core of RomM. Orchestrates library scanning and metadata enrichment.

**Scan Types:**

| Type            | Behavior                                                                                  |
| --------------- | ----------------------------------------------------------------------------------------- |
| `NEW_PLATFORMS` | Detect new platform folders only                                                          |
| `QUICK`         | Scan new ROMs and reconcile the files of existing ones, hashing only new or changed files |
| `UPDATE`        | Rescan already-identified ROMs                                                            |
| `UNMATCHED`     | Rescan ROMs without metadata                                                              |
| `COMPLETE`      | Full rescan of everything                                                                 |
| `HASHES`        | Recalculate all file hashes                                                               |

**Scan Flow:**

```text
1. Detect platform folders in LIBRARY_BASE_PATH
2. For each platform:
   ├── Map filesystem slug to canonical platform (via config bindings)
   ├── Query metadata providers for platform info
   └── Create/update platform in DB
3. For each ROM file in platform:
   ├── Parse filename (extract name, tags, region, version)
   ├── Calculate file hashes (CRC32, MD5, SHA1)
   ├── For a Chinese filename: English title from the header's product code (utils/product_codes.py), else a translation (utils/translator.py)
   ├── Search metadata providers (in priority order):
   │   ├── IGDB
   │   ├── MobyGames
   │   ├── ScreenScraper
   │   ├── LaunchBox
   │   ├── RetroAchievements
   │   ├── Hasheous (hash-based matching)
   │   ├── Flashpoint
   │   ├── HLTB
   │   ├── Steam (PC platforms)
   │   └── TheGamesDB
   ├── Download cover art and screenshots
   ├── Build aggregated metadata (RomMetadata)
   ├── Simplified Chinese title: official list, Bangumi, Wikidata, OpenCC, filename; summary to zh-CN (utils/translator.py)
   └── Create/update ROM in DB
4. Emit real-time progress via Socket.IO
5. Mark missing ROMs (files no longer on filesystem)
```

**Search Term Normalization:**

- Remove articles ("The", "A", "An")
- Strip punctuation and special characters
- Unicode normalization (NFKD)
- Jaro-Winkler similarity matching for fuzzy results

### 8.2 Database Handlers (`handler/database/`)

Each entity has a dedicated handler providing CRUD operations:

| Handler                    | Key Operations                                                                     |
| -------------------------- | ---------------------------------------------------------------------------------- |
| `db_roms_handler`          | Advanced filtering (platform, genre, region, status), pagination, file association |
| `db_platform_handler`      | Slug mapping, ROM count aggregation                                                |
| `db_users_handler`         | Role management, credential storage                                                |
| `db_collections_handler`   | ROM association, smart collection evaluation                                       |
| `db_stats_handler`         | Platform/ROM counts, storage usage, metadata coverage                              |
| `db_devices_handler`       | Fingerprint deduplication                                                          |
| `db_client_tokens_handler` | Hash-based lookup, scope management                                                |

### 8.3 Metadata Handlers (`handler/metadata/`)

Each external provider has a handler that normalizes data into a common format:

| Handler              | Provider          | Key Data                                   |
| -------------------- | ----------------- | ------------------------------------------ |
| `igdb_handler`       | IGDB              | Game info, covers, screenshots, franchises |
| `moby_handler`       | MobyGames         | Publisher, genre classification            |
| `ss_handler`         | ScreenScraper     | Regional metadata, box art, manuals        |
| `sgdb_handler`       | SteamGridDB       | Grid artwork, logos, icons                 |
| `ra_handler`         | RetroAchievements | Achievements, user progression             |
| `hltb_handler`       | HowLongToBeat     | Playtime estimates                         |
| `steam_handler`      | Steam             | PC store metadata, capsule art             |
| `hasheous_handler`   | Hasheous          | Hash-based ROM identification              |
| `tgdb_handler`       | TheGamesDB        | Alternative metadata                       |
| `flashpoint_handler` | Flashpoint        | Browser game archive                       |
| `gamelist_handler`   | gamelist.xml      | ES-DE format parser                        |
| `libretro_handler`   | Libretro          | Libretro thumbnails DB                     |
| `playmatch_handler`  | PlayMatch         | Game matching algorithm                    |
| `launchbox_handler/` | LaunchBox         | Local + remote database, media             |

**Priority system:** Metadata sources are queried in configurable priority order. First match wins for each field, with manual overrides taking highest priority.

### 8.4 Filesystem Handlers (`handler/filesystem/`)

| Handler             | Responsibility                                     |
| ------------------- | -------------------------------------------------- |
| `roms_handler`      | Read ROM files, calculate hashes, extract archives |
| `assets_handler`    | Store avatars and serve uploaded images            |
| `platforms_handler` | Platform folder creation and detection             |
| `resources_handler` | Download and cache artwork                         |

**Supported archive formats:** ZIP, 7Z, TAR, GZIP, BZ2, RAR

**Special hash handling:**

- CHD (Compressed Hunks of Data) v5: SHA1 extracted from header
- PICO-8 cartridges (.p8.png): special handling
- RetroAchievements hash (`ra_hash`): platform-specific algorithm via `rahasher.py`
- Non-hashable platforms (Switch, PS3/4/5): hashing skipped

### 8.5 Socket Handler (`handler/socket_handler.py`)

Manages the Socket.IO server mounted at `/ws` (scan progress, activity, logs). It uses Redis as the message queue backend for horizontal scaling.

**Scan Progress Events:**

```python
ScanStats:
    total_platforms, scanned_platforms, new_platforms
    identified_platforms
    total_roms, scanned_roms, new_roms, identified_roms
    updated_roms, new_files
```

### 8.6 Notifications (`handler/notification_handler.py`)

Persistent per-user notifications, kept until dismissed and pushed live to the user's `user:{id}` socket room. From backend code, web process or worker alike:

```python
await notify(user.id, NotificationKind.SCAN_COMPLETED, NotificationLevel.SUCCESS, stats)
await notify_admins("custom", NotificationLevel.WARNING, title="Disk almost full")
```

A `NotificationKind` is translated by the client from `data`; a new one needs a describer in `frontend/src/utils/notifications.ts` and locale keys. Until then, or for a one-off, pass any other kind with `title`/`body`/`link`/`icon`. Both helpers log and swallow failures, so a job never fails over reporting itself.

A task reports its success from `run_task_by_name`. Its failure is reported by `report_task_failure`, an exception handler `RomMWorker` installs, so a timeout, a killed work horse or a dead worker notifies too, for cron runs as well as manual ones. The handler can run in the worker parent, so it enqueues `notify_task_failure` on the default queue rather than loading the notification stack there.

---

## 9. External Integrations (Adapters)

**Location:** `adapters/services/`

Each adapter wraps an external API with authentication, retry logic, and type safety.

### IGDB (Internet Game Database)

| Property        | Value                                                                   |
| --------------- | ----------------------------------------------------------------------- |
| **Auth**        | Twitch OAuth2 (client_id + client_secret → bearer token)                |
| **Data**        | Game metadata, covers, screenshots, age ratings, franchises, game modes |
| **Rate limits** | Retry logic with backoff                                                |
| **Config vars** | `IGDB_CLIENT_ID`, `IGDB_CLIENT_SECRET`                                  |

### MobyGames

| Property       | Value                                               |
| -------------- | --------------------------------------------------- |
| **Auth**       | API key                                             |
| **Data**       | Game metadata, publisher info, genre classification |
| **Config var** | `MOBYGAMES_API_KEY`                                 |

### ScreenScraper

| Property        | Value                                                         |
| --------------- | ------------------------------------------------------------- |
| **Auth**        | Device ID + user credentials                                  |
| **Data**        | Regional game metadata, box art, screenshots, manuals, bezels |
| **Media types** | Box 2D/3D, screenshot, video, manual, marquee, bezel          |
| **Config vars** | `SCREENSCRAPER_USER`, `SCREENSCRAPER_PASSWORD`                |

### SteamGridDB

| Property       | Value                                                    |
| -------------- | -------------------------------------------------------- |
| **Auth**       | Bearer token                                             |
| **Data**       | Grid artwork, logos, icons in multiple dimensions/styles |
| **Filters**    | Style, dimension, MIME type                              |
| **Config var** | `STEAMGRIDDB_API_KEY`                                    |

### RetroAchievements

| Property       | Value                                             |
| -------------- | ------------------------------------------------- |
| **Auth**       | API key (query parameter)                         |
| **Data**       | Game achievements, user progression, award badges |
| **Hash**       | Platform-specific hash via `rahasher.py`          |
| **Config var** | `RETROACHIEVEMENTS_API_KEY`                       |

### Additional Providers

| Provider      | Handler              | Description                                       |
| ------------- | -------------------- | ------------------------------------------------- |
| LaunchBox     | `launchbox_handler/` | Local XML database + remote API, platform mapping |
| HowLongToBeat | `hltb_handler`       | Game playtime estimates                           |
| Steam         | `steam_handler`      | Storefront metadata (win/linux/mac) and cover art |
| Hasheous      | `hasheous_handler`   | Hash-based ROM identification                     |
| TheGamesDB    | `tgdb_handler`       | Alternative game metadata                         |
| Flashpoint    | `flashpoint_handler` | Browser game archive database                     |
| PlayMatch     | `playmatch_handler`  | Game matching algorithm                           |

### Static Fixture Data

Cached in Redis at startup from JSON files:

| Fixture                 | Location                     | Purpose                        |
| ----------------------- | ---------------------------- | ------------------------------ |
| `mame_index.json`       | `handler/metadata/fixtures/` | MAME ROM name → game info      |
| `scummvm_index.json`    | `handler/metadata/fixtures/` | ScummVM game identification    |
| `ps1_serial_index.json` | `handler/metadata/fixtures/` | PS1 serial code → game mapping |
| `ps2_serial_index.json` | `handler/metadata/fixtures/` | PS2 serial code → game mapping |
| `ps2_opl_index.json`    | `handler/metadata/fixtures/` | PS2 OPL serial codes           |
| `psp_serial_index.json` | `handler/metadata/fixtures/` | PSP serial code → game mapping |

---

## 10. Real-Time Communication (WebSockets)

### Socket Architecture

```text
Client  ←──Socket.IO──→  FastAPI (python-socketio)  ←──Redis PubSub──→  Workers
```

### Scan Progress (`/ws`)

**Events emitted to clients:**

| Event               | Payload            | When                        |
| ------------------- | ------------------ | --------------------------- |
| `scan:update_stats` | `ScanStats` object | Each ROM/platform processed |
| `scan:log`          | Log message        | Scan log entries            |
| `scan:stop`         |                    | Scan completed or cancelled |

### Notifications (`/ws`)

Sent to the user's own `user:{id}` room:

| Event                     | Payload                | When                         |
| ------------------------- | ---------------------- | ---------------------------- |
| `notifications:new`       | `NotificationSchema`   | One was stored for the user  |
| `notifications:read`      | `{ids: int[] \| null}` | Another tab marked some read |
| `notifications:dismissed` | `{ids: int[] \| null}` | Another tab dismissed some   |

## 11. Background Tasks & Scheduling

### Job Queue System

**Technology:** RQ (Redis Queue)

**Priority Queues:**

| Queue             | Use Case                                       |
| ----------------- | ---------------------------------------------- |
| `high_prio_queue` | Urgent operations                              |
| `default_queue`   | Standard background work                       |
| `low_prio_queue`  | Cleanups, conversions, metadata refreshes      |
| `scan_queue`      | Library scans, consumed by a worker of its own |

### Scheduled Tasks

Declared in `tasks/registry.py` and registered with RQ's cron scheduler by
`tasks/cron_config.py`, which the `rq cron` process loads at start. The registry
holds each task's `TaskSpec` (title, schedule, queue, timeout) and the dotted
path to the `Task` that runs it, which `get_task` imports only when a job runs.
The scheduler, the tasks API and the worker's failure reporting read specs
alone, so they never load task code. A task is
registered only when it is enabled and has a cron string, so turning one off is
a restart rather than an unschedule. Delayed jobs, which is how the filesystem
watcher defers a rescan, are released by the worker itself (`--with-scheduler`).

Everything is registered on `low_prio_queue`. A scan is registered as a dispatch
job that enqueues the real scan onto `scan_queue`, because cron can attach no
failure callback and a scan needs one to report a worker that died mid-scan.

Toggled via environment variables:

| Task                              | Env Toggle                                         | Default Cron       | Description                    |
| --------------------------------- | -------------------------------------------------- | ------------------ | ------------------------------ |
| `scan_library`                    | `ENABLE_SCHEDULED_RESCAN`                          | `0 3 * * *` (3 AM) | Full library rescan            |
| `update_switch_titledb`           | `ENABLE_SCHEDULED_UPDATE_SWITCH_TITLEDB`           | `0 4 * * *`        | Update Switch game DB          |
| `update_launchbox_metadata`       | `ENABLE_SCHEDULED_UPDATE_LAUNCHBOX_METADATA`       | `0 4 * * *`        | Refresh LaunchBox data         |
| `convert_images_to_webp`          | `ENABLE_SCHEDULED_CONVERT_IMAGES_TO_WEBP`          | `0 4 * * *`        | Image optimization             |
| `sync_retroachievements_progress` | `ENABLE_SCHEDULED_RETROACHIEVEMENTS_PROGRESS_SYNC` | `0 4 * * *`        | Sync RA user progress          |
| `cleanup_orphaned_resources`      | `ENABLE_SCHEDULED_CLEANUP_ORPHANED_RESOURCES`      | `0 5 * * *`        | Remove unused artwork          |
| `cleanup_upload_tmp`              | `ENABLE_SCHEDULED_CLEANUP_UPLOAD_TMP` (default on) | `0 * * * *`        | Drop stale uploads             |
| `cleanup_zip_cache`               | `ENABLE_SCHEDULED_CLEANUP_ZIP_CACHE` (default on)  | `0 4 * * *`        | Drop stale cached ZIPs         |
| `cleanup_conversion_cache`        | Always on                                          | `0 4 * * *`        | Drop stale converted downloads |
| `cleanup_audit_log`               | `AUDIT_LOG_RETENTION_DAYS` above 0 (default 90)    | `30 4 * * *`       | Prune old audit events         |

### Manual Tasks

Triggered via `POST /api/tasks/run/{task_name}`, which enqueues on `low_prio_queue` and answers 503 when no live worker is listening on it:

| Task                   | Description                                                                           |
| ---------------------- | ------------------------------------------------------------------------------------- |
| `cleanup_missing_roms` | Remove DB entries for files no longer on disk                                         |
| `convert_library`      | Convert matched ROMs to `converto.platform_formats` in place, replacing the originals |

A spec marked `destructive` asks for a typed confirmation before the UI runs it, and one marked `single_instance` answers 409 while a job of it is queued or running. `convert_library` is both, and runs only with `ROM_CONVERTO_ENABLED` set.

`convert_library` only converts losslessly (no xiso) and only identified ROMs, since a converted file no longer hash-matches a DAT. It stages each output under a `.romm_tmp_` directory beside the ROM, deletes the originals (and a cue's tracks) once the output is in place, rewrites `.m3u` entries in folder ROMs, and refreshes the ROM's files, so the ROM keeps its id, saves and collections.

`cleanup_orphaned_resources` is also runnable this way; it is listed under
Scheduled Tasks because it additionally supports an opt-in cron schedule. It
skips the cleanup when the database reports no platforms at all while artwork
is still on disk, since that usually means the database is unavailable rather
than the library being empty. Pass `{"force": true}` as the request body to
clean up a genuinely emptied library.

### Filesystem Watcher

**File:** `watcher.py`

Uses `watchfiles` to monitor the library directory for changes. When enabled (`ENABLE_RESCAN_ON_FILESYSTEM_CHANGE`), triggers a rescan after a configurable delay (`RESCAN_ON_FILESYSTEM_CHANGE_DELAY`, default 5 minutes).

---

## 12. File System Management

### Directory Layout

```text
{ROMM_BASE_PATH}/                    # Default: /romm
├── library/                         # ROM files, organized by platform
│   ├── n64/
│   │   └── roms/
│   │       ├── Game1.z64
│   │       └── Game2.z64
│   ├── psx/
│   │   └── roms/
│   │       └── Game.bin
│   └── {platform_slug}/
│       └── roms/                    # Configurable folder name
│
├── resources/                       # Cached metadata assets
│   └── roms/
│       └── {rom_id}/
│           ├── cover_s.webp         # Small cover
│           ├── cover_l.webp         # Large cover
│           └── screenshots/
│
├── assets/                          # User-uploaded assets
│   └── users/
│       └── {user_id}/               # Avatar
│
└── config/
    └── config.yml                   # YAML configuration
```

### File Serving

| Mode        | Mechanism                | When            |
| ----------- | ------------------------ | --------------- |
| Development | `FileResponse` (direct)  | `DEV_MODE=true` |
| Production  | Nginx `X-Accel-Redirect` | Default         |

Nginx receives an internal redirect header and efficiently serves the file from disk without passing bytes through the Python process.

### Hash Calculation

| Algorithm | Used For                                                       |
| --------- | -------------------------------------------------------------- |
| CRC32     | Quick integrity check, standard ROM identification             |
| MD5       | File integrity                                                 |
| SHA1      | ROM identification                                             |
| RA Hash   | RetroAchievements-specific hash (platform-dependent algorithm) |

Hashing can be disabled per-installation via `skip_hash_calculation` in config.yml.

Alongside hashing, scans extract platform-native title IDs from ROM binaries via
the optional `sigil` binding (Switch, PlayStation, Nintendo, Xbox and Dreamcast
families). The feature no-ops when the binding is absent, and can be turned off
with `skip_title_id_extraction`.

---

## 13. Caching (Redis)

### Cache Architecture

Two Redis client instances:

| Client         | Type                    | Purpose                        |
| -------------- | ----------------------- | ------------------------------ |
| `redis_client` | Sync (with auto-decode) | Cache queries, session lookups |
| `async_cache`  | Async                   | Async operations               |

Falls back to `FakeRedis` in test mode.

### Cache Key Patterns

| Pattern                           | TTL             | Content                             |
| --------------------------------- | --------------- | ----------------------------------- |
| `session:{id}`                    | 14 days         | Session JSON                        |
| `user_sessions:{username}`        | 14 days         | Set of session IDs                  |
| `session_sockets:{channel}:{id}`  | 14 days         | Socket IDs a session opened         |
| `notification-channel:{id}:code`  | 30 min          | Hash of an email confirmation code  |
| `notification-channel-cooldown:*` | 1 min           | A user's and an address's last code |
| `reset-email:{user_id}`           | 1 min           | A user's last emailed reset link    |
| `reset-jti:{jti}`                 | 10 min          | Password reset token (one-time)     |
| `invite-jti:{jti}`                | 10 min          | Invite token (one-time)             |
| `refresh-jti:{jti}`               | 7 days          | Refresh token validation            |
| `romm:mame_index`                 | Permanent       | MAME game index                     |
| `romm:scummvm_index`              | Permanent       | ScummVM game index                  |
| `romm:ps1_serials`                | Permanent       | PS1 serial codes                    |
| `romm:ps2_serials`                | Permanent       | PS2 serial codes                    |
| `romm:psp_serials`                | Permanent       | PSP serial codes                    |
| `romm:switch_titledb`             | Refreshed daily | Switch TitleDB                      |
| Upload sessions                   | 24 hours        | Chunked upload state                |

---

## 14. Configuration

### Environment Variables

#### Core

| Variable              | Default          | Description                                                |
| --------------------- | ---------------- | ---------------------------------------------------------- |
| `ROMM_BASE_PATH`      | `/romm`          | Base data directory                                        |
| `ROMM_BASE_URL`       | `http://0.0.0.0` | Application base URL                                       |
| `ROMM_PORT`           | `8080`           | Server port                                                |
| `DEV_MODE`            | `false`          | Development mode                                           |
| `LOGLEVEL`            | `INFO`           | Log level                                                  |
| `FORWARDED_ALLOW_IPS` | private ranges   | Proxies trusted to report the client address (`*` for any) |

#### Database

| Variable                  | Default   | Description                                                        |
| ------------------------- | --------- | ------------------------------------------------------------------ |
| `ROMM_DB_DRIVER`          | `mariadb` | `mariadb`, `mysql`, or `postgresql`                                |
| `DB_HOST`                 |           | Database host                                                      |
| `DB_PORT`                 | `3306`    | Database port                                                      |
| `DB_USER`                 |           | Database user                                                      |
| `DB_PASSWD`               |           | Database password                                                  |
| `DB_NAME`                 | `romm`    | Database name                                                      |
| `DB_QUERY_JSON`           |           | Extra connection parameters, as JSON                               |
| `DB_POOL_RECYCLE_SECONDS` | `300`     | Retire a pooled connection after this long (`-1` to never recycle) |

#### Redis

| Variable            | Default     | Description            |
| ------------------- | ----------- | ---------------------- |
| `REDIS_HOST`        | `127.0.0.1` | Redis host             |
| `REDIS_PORT`        | `6379`      | Redis port             |
| `REDIS_USERNAME`    |             | Redis username (ACL)   |
| `REDIS_PASSWORD`    |             | Redis password         |
| `REDIS_DB`          | `0`         | Redis database number  |
| `REDIS_SSL`         | `false`     | Enable SSL             |
| `REDIS_SAVE_POLICY` | `3600 1`    | Valkey snapshot policy |

#### Authentication

| Variable                             | Default   | Description                           |
| ------------------------------------ | --------- | ------------------------------------- |
| `ROMM_AUTH_SECRET_KEY`               |           | Session signing key (random if unset) |
| `OAUTH_ACCESS_TOKEN_EXPIRE_SECONDS`  | `1800`    | 30 minutes                            |
| `OAUTH_REFRESH_TOKEN_EXPIRE_SECONDS` | `604800`  | 7 days                                |
| `SESSION_MAX_AGE_SECONDS`            | `1209600` | 14 days                               |
| `DISABLE_CSRF_PROTECTION`            | `false`   | Disable CSRF                          |
| `DISABLE_DOWNLOAD_ENDPOINT_AUTH`     | `false`   | Allow unauthenticated downloads       |
| `DISABLE_USERPASS_LOGIN`             | `false`   | Disable password login                |
| `DISABLE_LOGS_VIEWER`                | `false`   | Disable backend log viewer + endpoint |
| `KIOSK_MODE`                         | `false`   | Read-only anonymous access            |

#### OIDC

| Variable                        | Default              | Description                     |
| ------------------------------- | -------------------- | ------------------------------- |
| `OIDC_ENABLED`                  | `false`              | Enable OpenID Connect           |
| `OIDC_ALLOW_REGISTRATION`       | `true`               | Auto-create accounts on login   |
| `OIDC_PROVIDER`                 |                      | Provider URL                    |
| `OIDC_CLIENT_ID`                |                      | Client ID                       |
| `OIDC_CLIENT_SECRET`            |                      | Client secret                   |
| `OIDC_REDIRECT_URI`             |                      | Redirect URI                    |
| `OIDC_USERNAME_ATTRIBUTE`       | `preferred_username` | Username claim                  |
| `OIDC_CLAIM_ROLES`              |                      | Roles claim name                |
| `OIDC_ROLE_VIEWER/EDITOR/ADMIN` |                      | Comma-separated role values     |
| `OIDC_TLS_CACERTFILE`           |                      | Custom CA bundle for OIDC calls |
| `OIDC_RP_INITIATED_LOGOUT`      | `false`              | Send logout to OIDC provider    |
| `OIDC_END_SESSION_ENDPOINT`     |                      | End-session URL override        |

#### API Keys

| Variable                                        | Description       |
| ----------------------------------------------- | ----------------- |
| `IGDB_CLIENT_ID` + `IGDB_CLIENT_SECRET`         | IGDB (via Twitch) |
| `MOBYGAMES_API_KEY`                             | MobyGames         |
| `SCREENSCRAPER_USER` + `SCREENSCRAPER_PASSWORD` | ScreenScraper     |
| `STEAMGRIDDB_API_KEY`                           | SteamGridDB       |
| `RETROACHIEVEMENTS_API_KEY`                     | RetroAchievements |

#### Feature Toggles

| Variable                 | Default | Description             |
| ------------------------ | ------- | ----------------------- |
| `LAUNCHBOX_API_ENABLED`  | `false` | LaunchBox metadata      |
| `PLAYMATCH_API_ENABLED`  | `false` | PlayMatch matching      |
| `HASHEOUS_API_ENABLED`   | `false` | Hasheous identification |
| `TGDB_API_ENABLED`       | `false` | TheGamesDB              |
| `FLASHPOINT_API_ENABLED` | `false` | Flashpoint archive      |
| `HLTB_API_ENABLED`       | `false` | HowLongToBeat           |
| `STEAM_API_ENABLED`      | `false` | Steam storefront        |

#### Task Scheduling

| Variable                               | Default     | Description                     |
| -------------------------------------- | ----------- | ------------------------------- |
| `SCAN_TIMEOUT`                         | `14400`     | 4-hour scan timeout             |
| `SCAN_WORKERS`                         | `4`         | Concurrent scan workers         |
| `TASK_TIMEOUT`                         |             | RQ job timeout for manual tasks |
| `TASK_RESULT_TTL`                      |             | How long to keep job results    |
| `ENABLE_SCHEDULED_RESCAN`              | `false`     | Auto library rescan             |
| `SCHEDULED_RESCAN_CRON`                | `0 3 * * *` | Rescan schedule                 |
| `ENABLE_RESCAN_ON_FILESYSTEM_CHANGE`   | `false`     | Watch for file changes          |
| `RESCAN_ON_FILESYSTEM_CHANGE_DELAY`    | `5`         | Debounce delay (minutes)        |
| `SEVEN_ZIP_TIMEOUT`                    | `180`       | Timeout for 7-Zip extraction    |
| `REFRESH_RETROACHIEVEMENTS_CACHE_DAYS` |             | RA cache TTL (days)             |

### YAML Configuration (`config.yml`)

```yaml
exclude:
  platforms: ["arcade"]
  roms:
    single_file:
      extensions: [".txt", ".nfo"]
      names: ["readme"]
    multi_file:
      names: ["__MACOSX"]

filesystem:
  structure: # Library layout; `{platform}` is the platform folder, `{game}` where a game begins
    default: "roms/{platform}/{game}"
    ps3: "roms/{platform}/{category}/{game}" # Per-platform override, by fs_slug
  skip_hash_calculation: false
  skip_title_id_extraction: false # Skip sigil title ID extraction
  embed_switch_title_ids: false # Rename Switch ROMs to embed their title ID

system:
  platforms: # fs_slug → slug overrides (Batocera/RetroBat/ES-DE folder names resolve automatically)
    snes: "snes"
  versions:
    snes: "pal" # Platform version overrides

scan:
  priority:
    metadata: ["igdb", "moby", "ss"] # Provider priority
    artwork: ["sgdb", "igdb", "ss"]
    region: ["us", "eu", "jp"]
    language: ["en", "es", "ja"]
  media: ["box2d", "screenshot", "manual"]
  export_gamelist: false
```

Managed by `ConfigManager` (singleton pattern) which reads, validates, and writes the YAML file.

---

## 15. Error Handling

### Exception Hierarchy

```text
Exception
├── AuthCredentialsException          # 401: Incorrect credentials
├── AuthenticationSchemeException      # 401: Invalid auth scheme
├── UserDisabledException             # 401: Account disabled
├── OAuthCredentialsException         # 401: Invalid OAuth token
├── OIDCDisabledException             # 500: OIDC not configured
├── OIDCNotConfiguredException        # 500: OIDC feature disabled
│
├── PlatformNotFoundInDatabaseException    # 404
├── RomNotFoundInDatabaseException         # 404
├── CollectionNotFoundInDatabaseException  # 404
├── CollectionPermissionError              # 403
├── CollectionAlreadyExistsException       # 500
├── SGDBInvalidAPIKeyException             # 401
│
├── FolderStructureNotMatchException  # Invalid library layout
├── PlatformAlreadyExistsException    # Duplicate platform
├── RomsNotFoundException             # No ROMs for platform
├── RomAlreadyExistsException         # Duplicate ROM
│
├── ConfigNotWritableException        # Config file not writable
├── SchedulerException                # Task scheduling error
└── ScanStoppedException              # Scan cancelled
```

### HTTP Status Codes

| Code | Meaning               |
| ---- | --------------------- |
| 200  | Success (GET, PUT)    |
| 201  | Created (POST)        |
| 204  | No Content (DELETE)   |
| 400  | Bad Request           |
| 401  | Unauthorized          |
| 403  | Forbidden             |
| 404  | Not Found             |
| 409  | Conflict (duplicate)  |
| 500  | Internal Server Error |

---

## 16. Logging

### Setup

**Logger name:** `"romm"`
**Level:** Configurable via `LOGLEVEL` env var (default `INFO`)

### Format

```text
[LEVEL]: [RomM][module] [timestamp] message
```

### Color Coding

| Level    | Color         |
| -------- | ------------- |
| DEBUG    | Light Magenta |
| INFO     | Green         |
| WARNING  | Yellow        |
| ERROR    | Light Red     |
| CRITICAL | Red           |

Color behavior:

- `FORCE_COLOR=true` → Always use colors
- `NO_COLOR=true` → Strip ANSI codes
- Default → Colors enabled

### Monitoring

- **Sentry** integration via `SENTRY_DSN` environment variable
- Release tagged as `romm@{version}`

---

## 17. Testing

### Configuration

**File:** `pytest.ini`

- Async mode enabled
- Test database: `romm_test`
- Mock API keys pre-configured
- OIDC disabled for tests
- Log level: DEBUG

### Test Structure

Tests mirror the backend directory structure under `tests/`:

```text
tests/
├── conftest.py                    # Shared fixtures
├── adapters/services/             # API adapter tests
│   └── cassettes/                 # VCR recorded API responses
├── config/                        # Configuration tests
├── endpoints/                     # Endpoint integration tests
│   ├── test_auth.py
│   ├── test_collections.py
│   ├── roms/
│   └── sockets/
├── handler/                       # Handler unit tests
│   ├── auth/
│   ├── database/
│   ├── filesystem/
│   └── metadata/
├── logger/                        # Logger tests
├── models/                        # Model tests
├── tasks/                         # Task tests
└── utils/                         # Utility tests
```

### Test Fixtures

Located in `romm_test/`:

- Test ROM library with real directory structure (n64, ps3, psp, psvita, psx)
- User asset fixtures
- Configuration fixtures
- VCR cassettes for external API responses (pre-recorded)

### Key Patterns

- **VCR cassettes** for external API tests (reproducible without network)
- **Test database** (separate `romm_test` DB)
- **FastAPI TestClient** for endpoint integration tests
- **Mock Redis** via FakeRedis

---

## Appendix: Key Design Patterns

| Pattern                     | Where                                | Purpose                           |
| --------------------------- | ------------------------------------ | --------------------------------- |
| **Three-tier architecture** | Endpoints → Handlers → Models        | Separation of concerns            |
| **Singleton**               | `ConfigManager`                      | Single config instance            |
| **Adapter pattern**         | `adapters/services/`                 | Normalize external APIs           |
| **Decorator pattern**       | `@protected_route`, `@begin_session` | Cross-cutting concerns            |
| **Context variables**       | `utils/context.py`                   | Request-scoped state (async-safe) |
| **Repository pattern**      | `handler/database/`                  | Encapsulate data access           |
| **Observer pattern**        | Socket.IO events                     | Real-time updates                 |
| **Priority queue**          | RQ with 3 priority levels            | Task scheduling                   |
| **Chunked upload**          | `endpoints/roms/upload.py`           | Large file handling               |
| **X-Accel-Redirect**        | `utils/nginx.py`                     | Efficient file serving            |
