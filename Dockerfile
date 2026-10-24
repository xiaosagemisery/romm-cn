# syntax=docker/dockerfile:1
# trunk-ignore-all(trivy)
# trunk-ignore-all(checkov)
# trunk-ignore-all(hadolint/DL4006)

# Keep the pins in sync with the gme-build stage of docker/Dockerfile.
# trunk-ignore(hadolint/DL3029)
FROM --platform=linux/amd64 emscripten/emsdk:4.0.12@sha256:744fb6a68941970951bacf9d6632041a0398260492232691ef22bbf54b0585c6 AS emsdk-amd64
# trunk-ignore(hadolint/DL3029)
FROM --platform=linux/arm64 emscripten/emsdk:4.0.12-arm64@sha256:369a4cb655aa1066e6e450dde774243c502d999b1d93fb4890a9d1428daa9280 AS emsdk-arm64
# trunk-ignore(hadolint/DL3006)
FROM emsdk-${BUILDARCH} AS gme-build
ARG GME_VERSION=0.6.5
ARG GME_COMMIT=9e23d10f9fd2a6a2f33b10912dd8dc7153258995
ADD --checksum=${GME_COMMIT} "https://github.com/libgme/game-music-emu.git#${GME_VERSION}" /libgme
COPY docker/gme /romm-gme
RUN /romm-gme/build.sh /libgme /gme

FROM ubuntu:22.04

# Prevent interactive prompts during installation
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
# trunk-ignore(hadolint/DL3008)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    make \
    cmake \
    gcc \
    g++ \
    libmariadb3 \
    libmariadb-dev \
    libpq-dev \
    libffi-dev \
    musl-dev \
    curl \
    ca-certificates \
    libmagic-dev \
    7zip \
    libarchive-tools \
    tzdata \
    libbz2-dev \
    libssl-dev \
    libreadline-dev \
    libsqlite3-dev \
    zlib1g-dev \
    liblzma-dev \
    libncurses5-dev \
    libncursesw5-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install nvm
ENV NVM_DIR="/root/.nvm"
RUN curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash \
    && . "$NVM_DIR/nvm.sh" \
    && nvm install 24.22.1 \
    && nvm use 24.22.1 \
    && nvm alias default 24.22.1
ENV PATH="$NVM_DIR/versions/node/v24.22.1/bin:$PATH"

# Build and install RAHasher (optional for RA hashes)
# Tag 1.8.3. Keep the pin in sync with docker/Dockerfile.
ARG RALIBRETRO_COMMIT=8ab61f745ab753a70b5482f2a0ccb6a4ced5193f
RUN git clone --filter=blob:none https://github.com/RetroAchievements/RALibretro.git /tmp/RALibretro \
    && git -C /tmp/RALibretro checkout "${RALIBRETRO_COMMIT}" \
    && git -C /tmp/RALibretro submodule update --init --recursive
WORKDIR /tmp/RALibretro
RUN make HAVE_CHD=1 -f ./Makefile.RAHasher \
    && cp ./bin64/RAHasher /usr/bin/RAHasher
RUN rm -rf /tmp/RALibretro

# Install rom-converto (optional); its static musl build runs on this glibc image.
# Keep the version and both sums in sync with docker/Dockerfile.
ARG TARGETARCH
RUN ROM_CONVERTO_VERSION=v0.23.2 \
    && arch="${TARGETARCH:-$(dpkg --print-architecture)}" \
    && case "${arch}" in \
        amd64) rc="linux-x64-musl"; sum="734ecccfa77d425c01dc3ba621261389c1c23d23f0e5d6b8e3346fda1879d687" ;; \
        arm64) rc="linux-arm64-musl"; sum="e90cca392b08b859b79bab13fcd47300ffc613d5dca7da1b4d1e38e3a4bbc297" ;; \
        *) echo "unsupported architecture: ${arch}" && exit 1 ;; \
    esac \
    && curl -fsSL -o "/tmp/rom-converto-cli-${rc}" \
        "https://github.com/DevYukine/rom-converto/releases/download/${ROM_CONVERTO_VERSION}/rom-converto-cli-${rc}" \
    && echo "${sum}  /tmp/rom-converto-cli-${rc}" | sha256sum -c --status \
    && install -m 0755 "/tmp/rom-converto-cli-${rc}" /usr/bin/rom-converto \
    && rm -f "/tmp/rom-converto-cli-${rc}"

# Install frontend dependencies
COPY frontend/package.json /app/frontend/
WORKDIR /app/frontend
RUN npm install

# Install backend Node helpers (server-side ROM patching)
COPY backend/utils/rom_patcher/package.json /app/backend/utils/rom_patcher/
WORKDIR /app/backend/utils/rom_patcher
RUN npm install

# Set working directory
WORKDIR /app

# Install uv for the non-root user
COPY --from=ghcr.io/astral-sh/uv:0.13.4 /uv /uvx /usr/local/bin/

# Copy project files (including pyproject.toml and uv.lock)
COPY pyproject.toml uv.lock* .python-version /app/

# Install Python (pinned by .python-version) and the project dependencies
RUN uv python install \
    && uv sync --all-extras

ENV PATH="/app/.venv/bin:${PATH}"

# Build and install sigil (optional, for title ID extraction)
# Placed after `uv sync` because the extension is compiled with the venv's
# Python so the ABI matches. Keep the pin in sync with docker/Dockerfile.
ARG SIGIL_VERSION=8a3b0089676e07f74da2d9ad08979dedf5cae7c0
# One layer, so the clone and the cmake tree never reach the image.
# trunk-ignore(hadolint/DL3003)
RUN git clone --filter=blob:none https://github.com/rommapp/argosy-sigil.git /tmp/argosy-sigil \
    && cd /tmp/argosy-sigil \
    && git checkout "${SIGIL_VERSION}" \
    && git submodule update --init --recursive \
    && cmake -B ./build-python -S . -DSIGIL_BUILD_CLI=OFF -DSIGIL_BUILD_TESTS=OFF \
    && cmake --build ./build-python --target sigil \
    && uv pip install --python /app/.venv/bin/python cffi setuptools \
    && cd ./bindings/python \
    && /app/.venv/bin/python build_sigil.py \
    && SITE_PACKAGES="$(/app/.venv/bin/python -c 'import site; print(site.getsitepackages()[0])')" \
    && mkdir -p "${SITE_PACKAGES}/sigil" \
    && cp ./sigil/*.py ./sigil/_sigil.*.so "${SITE_PACKAGES}/sigil/" \
    && rm -rf /tmp/argosy-sigil
# Kept outside /app/frontend because the ./frontend bind mount hides it;
# entrypoint.sh links it into the assets tree at startup.
ENV GME_ASSETS_DIR="/opt/romm/gme"
COPY --from=gme-build /gme "${GME_ASSETS_DIR}"
WORKDIR /app

# Copy entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
