FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md LICENSE requirements-dev.lock ./
COPY src ./src
COPY scenarios ./scenarios
RUN pip install --no-cache-dir -r requirements-dev.lock && pip install --no-deps .
RUN useradd --create-home bench && chown -R bench:bench /app
USER bench
ENTRYPOINT ["agentguard"]
CMD ["run", "--provider", "fake", "--output", "results/offline"]
