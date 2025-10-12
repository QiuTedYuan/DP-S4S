# This container is intended to run with resource limits such as:
#   docker run --cpus=1 --memory=32g <image> ...
FROM python:3.10-slim

ENV POETRY_VERSION=1.7.1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl build-essential libgomp1 \
    && rm -rf /var/lib/apt/lists/*

RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/root/.local/bin:${PATH}"

WORKDIR /app

COPY . .

RUN poetry install --no-root --only main

RUN poetry run python cplex/python/setup.py install

CMD ["poetry", "run", "python", "src/main.py"]
