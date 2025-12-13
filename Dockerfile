FROM python:3.11-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy project files
COPY pyproject.toml .
COPY src ./src
COPY .env .env

# Install dependencies and the app package
RUN uv sync && uv pip install -e .

# Run scraper
CMD ["uv", "run", "python", "-m", "app"]
