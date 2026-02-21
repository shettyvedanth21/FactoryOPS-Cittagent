FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    default-libmysqlclient-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install poetry
RUN pip install poetry

COPY pyproject.toml ./

# Install dependencies (without creating a virtualenv)
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root

COPY . .

# Set PYTHONPATH
ENV PYTHONPATH=/app

# Run migrations and start app
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8003"]
