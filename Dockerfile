# Extends the official Airflow image with the locked dependencies needed by ffguru workflows.

FROM ghcr.io/astral-sh/uv:0.12.9 AS uv

FROM apache/airflow:3.3.1-python3.12

COPY --from=uv /uv /bin/uv
COPY --chown=airflow:root pyproject.toml uv.lock /opt/airflow/project/

WORKDIR /opt/airflow/project

RUN uv export --frozen --no-dev --no-emit-project --prune apache-airflow \
        --output-file /tmp/requirements.txt \
    && pip install --no-cache-dir --requirement /tmp/requirements.txt

RUN mkdir -p /opt/airflow/data \
    && python -c "import duckdb; connection = duckdb.connect(); connection.install_extension('httpfs'); connection.close()"

COPY --chown=airflow:root README.md /opt/airflow/project/README.md
COPY --chown=airflow:root src /opt/airflow/project/src

RUN pip install --no-cache-dir --no-deps /opt/airflow/project

WORKDIR /opt/airflow
