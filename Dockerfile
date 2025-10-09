# This container is intended to run with resource limits such as:
#   docker run --cpus=1 --memory=16g <image> ...
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

COPY pyproject.toml .

RUN poetry install --no-root --only main

COPY . .

ARG CPLEX_WHEEL=""
RUN if [ -z "${CPLEX_WHEEL}" ]; then \
        echo "CPLEX_WHEEL build argument is required. Set it to the path of the IBM CPLEX Python wheel inside the build context (see IBM docs)." >&2; \
        exit 1; \
    elif [ ! -f "${CPLEX_WHEEL}" ]; then \
        echo "CPLEX wheel '${CPLEX_WHEEL}' not found in build context. Ensure you extracted IBM ILOG CPLEX Optimization Studio and set CPLEX_WHEEL accordingly." >&2; \
        exit 1; \
    else \
        poetry run python -m pip install \"${CPLEX_WHEEL}\"; \
    fi \
    && rm -rf /root/.cache/pip

CMD ["poetry", "run", "python", "src/main.py"]
