# CI runtime image (ADR-0009): threatwright CLI + LibreOffice Writer for PDF, no GUI.
# Base images pinned by digest (multi-arch index), looked up 2026-10-19; bump deliberately.

# --- 1: frontend bundle ------------------------------------------------------------
FROM node:24-slim@sha256:a5f4366e834695d5f363b920c104953a535d3a9864d1bdf74566a0ebe01daee5 AS frontend
WORKDIR /src/app
COPY app/package.json app/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY app/ ./
# vite writes to ../src/threatwright/web
RUN mkdir -p /src/src/threatwright && npm run build

# --- 2: wheel + locked requirements ----------------------------------------------
FROM python:3.13-slim@sha256:70729b46c69b4f1e97c4822c1af3df53a1476cf5ddc6c087c0c10bc3a5678c2f AS wheel
COPY --from=ghcr.io/astral-sh/uv:0.13.1@sha256:4a1f3666816dafadd20ceb71eac9a7d56d7ef30279f7d64048519ab901ada336 /uv /usr/local/bin/uv
WORKDIR /src
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src/ src/
COPY --from=frontend /src/src/threatwright/web src/threatwright/web
RUN uv build --wheel --out-dir /dist \
 && uv export --frozen --no-dev --no-emit-project --format requirements-txt -o /dist/requirements.txt

# --- 3: runtime --------------------------------------------------------------------
FROM python:3.13-slim@sha256:70729b46c69b4f1e97c4822c1af3df53a1476cf5ddc6c087c0c10bc3a5678c2f
# git: diff against tags in CI. LibreOffice Writer (headless) for PDF output.
RUN apt-get update \
 && apt-get install -y --no-install-recommends git libreoffice-writer-nogui fonts-dejavu-core \
 && rm -rf /var/lib/apt/lists/*
COPY --from=wheel /dist /tmp/dist
RUN pip install --no-cache-dir --require-hashes -r /tmp/dist/requirements.txt \
 && pip install --no-cache-dir --no-deps /tmp/dist/*.whl \
 && rm -rf /tmp/dist
RUN useradd --create-home --uid 10001 threatwright
USER threatwright
WORKDIR /work
ENTRYPOINT ["threatwright"]
CMD ["--help"]
