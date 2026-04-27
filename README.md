# Athena Invest (MVP Runtime)

Production-focused MVP for a Discord investing channel with two capabilities:

1. Users send a ticker as plain text and receive a technical analysis response.
2. Fear & Greed index updates are published on a schedule.

## MVP scope

In scope:
- Text ticker analysis in Discord
- Fear & Greed scheduled updates
- Stability controls (queue, cooldown, retry, timeout, cache, heartbeat)

Out of scope:
- Additional command systems and premium feature layers
- Multi-tenant permission models
- Microservice split

## Runtime architecture

- `src/app`: Discord bot lifecycle and background scheduler wiring
- `src/domain`: analysis and fear/greed orchestration logic
- `src/infrastructure`: clients, cache, Discord publishing adapters
- `src/presentation`: message parsing and output formatting
- `src/shared`: settings, logging, metrics, and shared errors

## Local run

```bash
pip install -r requirements.txt
cp .env.example .env
python discord_bot.py
```

One-shot Fear & Greed publish:

```bash
python fear_and_greed_monitor.py
```

## Oracle Cloud container run

Build:

```bash
docker build -t athena-invest:latest .
```

Run:

```bash
docker run -d --name athena-invest --restart always --env-file .env athena-invest:latest
```

Health probe:
- Container health is based on `python -m src.app.healthcheck`
- Bot heartbeat is written to `HEARTBEAT_FILE_PATH` every heartbeat cycle

## Observability baseline

The bot emits JSON logs with:
- request queue size
- total requests/success/errors
- p95 latency
- consecutive error alerts when error streak reaches 5

## Legacy components

The following modules are retained temporarily for migration/backward compatibility and should not be extended for new behavior:
- `main.py`
- `agents/technical_analyzer.py`
