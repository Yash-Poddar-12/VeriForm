FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

ENV PYTHONUNBUFFERED=1
ENV VERIFORM_ENV=production

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast python package management
RUN pip install uv

# Copy project files
COPY pyproject.toml .
COPY README.md .
COPY src/ src/
COPY alembic/ alembic/
COPY alembic.ini .
COPY start.sh .

RUN chmod +x start.sh

# Install python dependencies using uv
RUN uv pip install --system -e .

EXPOSE 8000

CMD ["./start.sh"]
