# syntax=docker/dockerfile:1
# Stages:
#   - python-runtime: Patch the Python image's libraries before they ship
#   - frontend-build: Build frontend
#   - backend-build: Build backend environment
#   - backend-dev-build: Similar to `backend-build`, but also compiles and installs development dependencies
#   - rahasher-build: Build RAHasher
#   - sigil-build: Build sigil Python bindings (title ID extraction)
#   - rom-converto-fetch: Fetch the rom-converto CLI (ROM conversion and metadata)
#   - nginx-build: Build nginx modules
#   - production-stage: Setup frontend and backend
#   - slim-image: Slim image with only the necessary files
#   - full-image: Same as slim-image
#   - dev-slim: Slim image with development dependencies
#   - dev-full: Full image with development dependencies


# ARGUMENT DECLARATIONS
ARG ALPINE_VERSION=3.24
ARG ALPINE_SHA256=294b683cb724975bec92580e1e685676bd4b50bda910ddb8c51d4cabeaec77e6
# Pins the base image tag, so it cannot read ../.python-version; keep the two in sync.
ARG PYTHON_VERSION=3.14
ARG PYTHON_ALPINE_SHA256=9e9fde4d32eedce0b661d9ab91e826b62dddf28e928c230ec55f1866cac66b01
# The image's pip comes from CPython's bundled ensurepip, which lags pip's security releases.
ARG PIP_VERSION=26.2.2
ARG NODE_VERSION=24.22
ARG NODE_ALPINE_SHA256=6a1c190e17215d844926b0677f4bf87273ff7d5e54db06d3b5b5863ab0b09a3d
ARG NGINX_VERSION=1.30.5
ARG NGINX_SHA256=a5f2157a0302eb0c5e300415effb63a9e70ed1eb9c107283819bf6d149ab607c
ARG UV_VERSION=0.13.4
ARG UV_SHA256=0cb69bb18ffcd57db04f045010b0234132a111da70dde5a393d26ad288d38e13


FROM python:${PYTHON_VERSION}-alpine${ALPINE_VERSION}@sha256:${PYTHON_ALPINE_SHA256} AS python-alias
ARG PIP_VERSION
RUN pip install --no-cache-dir --upgrade pip==${PIP_VERSION}


# PATCHED PYTHON RUNTIME
# production-stage copies /usr/lib from here over its own, so these libraries
# need the same patches, or the stale ones land in the final image. Kept apart
# from python-alias so that busting this layer's cache (see `no-cache-filters`
# in build.yml) does not also rebuild the venv and the sigil bindings.
FROM python-alias AS python-runtime
RUN apk upgrade --no-cache


# FRONTEND BUILD
# Built on the native build platform: the output (/front/dist) is static JS/CSS,
# fully architecture-independent, so there is no need to emulate the target arch.
FROM --platform=$BUILDPLATFORM node:${NODE_VERSION}-alpine${ALPINE_VERSION}@sha256:${NODE_ALPINE_SHA256} AS frontend-build
WORKDIR /front

COPY ./frontend/package*.json ./
RUN npm ci --ignore-scripts --no-audit --no-fund

COPY ./frontend ./
RUN npm run build


# BACKEND NODE HELPERS BUILD (server-side ROM patching via RomPatcher.js)
FROM node:${NODE_VERSION}-alpine${ALPINE_VERSION}@sha256:${NODE_ALPINE_SHA256} AS backend-node-build
WORKDIR /backend-node/rom_patcher
COPY ./backend/utils/rom_patcher/package*.json ./
RUN npm ci --ignore-scripts --no-audit --no-fund


# https://github.com/astral-sh/uv/pkgs/container/uv
FROM ghcr.io/astral-sh/uv:${UV_VERSION}-python${PYTHON_VERSION}-alpine@sha256:${UV_SHA256} AS uv-stage


# BACKEND PYTHON BUILD
FROM python-alias AS backend-build

# libpq-dev is needed to build psycopg-c
# mariadb-connector-c-dev is needed to build mariadb-connector
RUN apk add --no-cache \
    gcc \
    libpq-dev \
    mariadb-connector-c-dev \
    musl-dev

COPY --from=uv-stage /usr/local/bin/uv /usr/local/bin/uvx /bin/

WORKDIR /src

COPY ./pyproject.toml ./uv.lock /src/
RUN uv sync --frozen --no-cache

FROM backend-build AS backend-dev-build

# linux-headers is needed to install psutil
RUN apk add --no-cache \
    linux-headers

RUN uv sync --frozen --no-cache --all-extras


# CUSTOM RAHASHER FOR RETROACHIEVEMENTS
FROM alpine:${ALPINE_VERSION}@sha256:${ALPINE_SHA256} AS rahasher-build
RUN apk add --no-cache \
    g++ \
    git \
    linux-headers \
    make \
    zlib-dev \
    bash

# Tag 1.8.3. Pinned by commit because a tag can be moved.
# Keep this pin in sync with the dev image's RALIBRETRO_COMMIT in ../Dockerfile.
ARG RALIBRETRO_COMMIT=8ab61f745ab753a70b5482f2a0ccb6a4ced5193f

RUN git clone --filter=blob:none https://github.com/RetroAchievements/RALibretro.git && \
    cd ./RALibretro && \
    git checkout "${RALIBRETRO_COMMIT}" && \
    git submodule update --init --recursive && \
    sed -i '22a #include <ctime>' ./src/Util.h && \
    sed -i '6a #include <unistd.h>' \
        ./src/libchdr/deps/zlib-1.3.1/gzlib.c \
        ./src/libchdr/deps/zlib-1.3.1/gzread.c \
        ./src/libchdr/deps/zlib-1.3.1/gzwrite.c && \
    make HAVE_CHD=1 -f ./Makefile.RAHasher


# SIGIL TITLE ID EXTRACTION LIBRARY
# Built from python-alias (not plain alpine) so the cffi extension matches the
# CPython ABI of the venv produced in backend-build.
FROM python-alias AS sigil-build
RUN apk add --no-cache \
    cmake \
    g++ \
    git \
    make \
    musl-dev

# Keep this pin in sync with the dev image's SIGIL_VERSION in ../Dockerfile.
ARG SIGIL_VERSION=8a3b0089676e07f74da2d9ad08979dedf5cae7c0

RUN git clone --filter=blob:none https://github.com/rommapp/argosy-sigil.git && \
    cd ./argosy-sigil && \
    git checkout "${SIGIL_VERSION}" && \
    git submodule update --init --recursive && \
    cmake -B ./build-python -S . -DSIGIL_BUILD_CLI=OFF -DSIGIL_BUILD_TESTS=OFF && \
    cmake --build ./build-python --target sigil && \
    pip install --no-cache-dir cffi setuptools && \
    cd ./bindings/python && \
    python build_sigil.py && \
    mkdir /sigil-pkg && \
    cp ./sigil/*.py ./sigil/_sigil.*.so /sigil-pkg/


# ROM-CONVERTO CLI
# Keep the version and both sums in sync with the dev image's copy in ../Dockerfile.
FROM alpine:${ALPINE_VERSION}@sha256:${ALPINE_SHA256} AS rom-converto-fetch
ARG TARGETARCH
ARG ROM_CONVERTO_VERSION=v0.23.2
RUN case "${TARGETARCH}" in \
        amd64) rc="linux-x64-musl"; sum="734ecccfa77d425c01dc3ba621261389c1c23d23f0e5d6b8e3346fda1879d687" ;; \
        arm64) rc="linux-arm64-musl"; sum="e90cca392b08b859b79bab13fcd47300ffc613d5dca7da1b4d1e38e3a4bbc297" ;; \
        *) echo "unsupported TARGETARCH: ${TARGETARCH}" && exit 1 ;; \
    esac && \
    wget -qO /rom-converto \
        "https://github.com/DevYukine/rom-converto/releases/download/${ROM_CONVERTO_VERSION}/rom-converto-cli-${rc}" && \
    echo "${sum}  /rom-converto" | sha256sum -c - && \
    chmod 0755 /rom-converto


# BUILD NGINX MODULE WITH MOD_ZIP
FROM alpine:${ALPINE_VERSION}@sha256:${ALPINE_SHA256} AS nginx-build

RUN apk add --no-cache \
    gcc \
    git \
    libc-dev \
    make \
    pcre-dev \
    zlib-dev

ARG NGINX_VERSION
# The specified commit SHA is the latest commit on the `master` branch at the time of writing.
# It includes a fix to correctly calculate CRC-32 checksums when using upstream subrequests.
# TODO: Move to a tagged release of `mod_zip`, once a version newer than 1.3.0 is released.
ARG NGINX_MOD_ZIP_COMMIT=a9f9afa441117831cc712a832c98408b3f0416f6

# Clone both `nginx` and `ngx_http_zip_module` repositories, needed to compile the module from source.
# This is needed to be able to dinamically load it as a module in the final image. `nginx` Docker
# images do not have a simple way to include third-party modules.
RUN git clone https://github.com/evanmiller/mod_zip.git && \
    cd ./mod_zip && \
    git checkout "${NGINX_MOD_ZIP_COMMIT}" && \
    cd ../ && \
    git clone --branch "release-${NGINX_VERSION}" --depth 1 https://github.com/nginx/nginx.git && \
    cd ./nginx && \
    ./auto/configure --with-compat --add-dynamic-module=../mod_zip/ && \
    make -f ./objs/Makefile modules && \
    chmod 644 ./objs/ngx_http_zip_module.so


# PRODUCTION STAGE
FROM nginx:${NGINX_VERSION}-alpine${ALPINE_VERSION}@sha256:${NGINX_SHA256} AS production-stage
ARG WEBSERVER_FOLDER=/var/www/html

# Alpine backports security fixes to its repo faster than the base image is
# rebuilt, so the digest pin alone leaves known-vulnerable packages in the image.
RUN apk upgrade --no-cache && apk add --no-cache \
    bash \
    libarchive-tools \
    libmagic \
    mariadb-connector-c \
    libpq \
    nodejs \
    7zip \
    tzdata \
    valkey \
    valkey-cli

# Add Python by copying it from the official Docker image. This way, we don't rely on Alpine's
# Python version, which could not be the same as the one used in the backend build stage.
# TODO: Replace with a bundled installation of Python using `uv`, when it is supported.
#       Related issue: https://github.com/astral-sh/uv/issues/7865
ARG PYTHON_VERSION
COPY --from=python-runtime /usr/lib/* /usr/lib/
COPY --from=python-runtime /usr/local/bin/* /usr/local/bin/
COPY --from=python-runtime /usr/local/include/python${PYTHON_VERSION} /usr/local/include/python${PYTHON_VERSION}
COPY --from=python-runtime /usr/local/lib/libpython* /usr/local/lib/
COPY --from=python-runtime /usr/local/lib/python${PYTHON_VERSION} /usr/local/lib/python${PYTHON_VERSION}

COPY --from=rahasher-build /RALibretro/bin64/RAHasher /usr/bin/RAHasher
COPY --from=rom-converto-fetch /rom-converto /usr/bin/rom-converto
COPY --from=nginx-build ./nginx/objs/ngx_http_zip_module.so /usr/lib/nginx/modules/
COPY --from=frontend-build /front/dist ${WEBSERVER_FOLDER}
COPY --from=backend-node-build /backend-node/rom_patcher/node_modules/rom-patcher/rom-patcher-js /backend/utils/rom_patcher/rom-patcher-js

COPY ./frontend/assets ${WEBSERVER_FOLDER}/assets
RUN mkdir -p ${WEBSERVER_FOLDER}/assets/romm && \
    ln -sf /romm/resources ${WEBSERVER_FOLDER}/assets/romm/resources
COPY ./backend /backend

# Setup init script and config files
COPY ./docker/init_scripts/* /
COPY ./docker/nginx/js/ /etc/nginx/js/
COPY ./docker/nginx/templates/ /etc/nginx/templates/
COPY ./docker/nginx/default.conf /etc/nginx/nginx.conf
COPY ./docker/gunicorn/logging.conf /etc/gunicorn/logging.conf

# User permissions
# - Create default user `romm` (1000) and group `romm` (1000).
# - Create base directories and make default user/group the owner.
# - Make nginx configuration files writable by everyone for `envsubst` to work
RUN addgroup -g 1000 -S romm && adduser -u 1000 -D -S -G romm romm && \
    mkdir /romm /redis-data && \
    chown romm:romm /romm /redis-data && \
    chmod 755 /romm /redis-data && \
    chmod -R a+w /etc/nginx/conf.d && \
    chmod -R a+w /etc/gunicorn


# SLIM IMAGE
FROM scratch AS slim-image

COPY --from=production-stage / /

COPY --from=backend-build /src/.venv /src/.venv

# Optional sigil bindings for title ID extraction; the backend feature
# no-ops when the package is absent.
ARG PYTHON_VERSION
COPY --from=sigil-build /sigil-pkg /src/.venv/lib/python${PYTHON_VERSION}/site-packages/sigil

ENV PATH="/src/.venv/bin:${PATH}"

# ScreenScraper developer (application) credentials, injected at build time from
# CI secrets. Kept out of the source tree; empty when not supplied at build.
ARG SCREENSCRAPER_DEV_ID
ARG SCREENSCRAPER_DEV_PASSWORD
ENV SCREENSCRAPER_DEV_ID=${SCREENSCRAPER_DEV_ID}
ENV SCREENSCRAPER_DEV_PASSWORD=${SCREENSCRAPER_DEV_PASSWORD}

# Security: Set security-focused environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/backend

# Declare only the parent `/romm`, not its subdirs, so Docker keeps them 
# on one mount (`st_dev`) and cross-directory `os.link()` hardlinks don't fail.
VOLUME ["/romm", "/redis-data"]

# Expose non-privileged ports
EXPOSE 8080 6379/tcp
WORKDIR /romm

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["/init"]


# FULL IMAGE
FROM slim-image AS full-image


FROM slim-image AS dev-slim
COPY --from=backend-dev-build /src/.venv /src/.venv


FROM full-image AS dev-full
COPY --from=backend-dev-build /src/.venv /src/.venv
