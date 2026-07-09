# Use the official uv image with Python 3.14 (matches requires-python / .python-version)
FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim

# git is needed because the server shells out to git / clones protocol repos at runtime
# RUN apt-get update && apt-get install -y --no-install-recommends git \
#     && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies first (cached unless the lockfile changes)
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-install-project

# Copy the application code
COPY . .

# Install the project itself
RUN uv sync --locked

EXPOSE 8000

CMD ["uv", "run", "server.py"]
