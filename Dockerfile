# Stage 1: build wheels for the app and its dependencies.
FROM python:3.11-slim AS build
WORKDIR /src
COPY pyproject.toml ./
COPY api ./api
COPY core ./core
COPY adapters ./adapters
COPY pipelines ./pipelines
RUN pip wheel --no-cache-dir --wheel-dir /wheels .

# Stage 2: slim runtime with only the installed wheels, run as a non-root user.
FROM python:3.11-slim
RUN useradd --create-home --uid 10001 app
COPY --from=build /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels
USER app
EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
