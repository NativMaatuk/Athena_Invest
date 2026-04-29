# Performance and Test Runbook

This runbook defines a repeatable process for performance hardening and safe rollout.
Use it for every runtime or message-handling change.

## 1) Scope and Guardrails

- Run all experiments only in a private dev Discord channel.
- Keep production secrets and channels isolated from dev.
- Apply one change at a time and compare against baseline.
- Do not promote changes that improve latency but worsen error rate.

## 2) Baseline Protocol

Run the current build with the current dev `.env` values.

Request matrix (10 requests total):

1. `AAPL`
2. `MSFT`
3. `NVDA`
4. `TSLA`
5. `AMZN`
6. `AAPL` (cache candidate)
7. `MSFT` (cache candidate)
8. `NVDA` (cache candidate)
9. invalid ticker candidate (`ZZZZ9999`)
10. another invalid ticker candidate (`1234`)

For each request, record:

- Time from message send to `processing` status message.
- Time from message send to final analysis/error message.
- Whether response included embed and chart.
- Whether response matched expected user-facing message.

Collect bot log metrics from `analysis_success` / `analysis_failed` lines:

- count of successes
- count of failures
- avg latency_ms
- p95 latency_ms

## 3) Tuning Experiment Matrix

Apply changes incrementally in dev only:

### Profile B (Timeout tuning)

- `REQUEST_TIMEOUT_SECONDS`: `15 -> 10`
- Keep `RETRY_ATTEMPTS=1`
- Re-run the 10-request matrix

### Profile C (Concurrency tuning)

- Keep Profile B
- `ANALYSIS_MAX_CONCURRENT`: `3 -> 4`
- Re-run the 10-request matrix

### Profile D (Aggressive timeout)

- Keep Profile C
- `REQUEST_TIMEOUT_SECONDS`: `10 -> 8`
- Re-run the 10-request matrix

Promotion rule:

- Accept profile only if p95 improves and error count is not higher than baseline.

Benchmark command:

```bash
python benchmarks/performance_profile_runner.py
```

### Latest benchmark snapshot (2026-04-28 local)

| profile | timeout | retry | max_concurrent | success | error | avg_ms | p95_ms |
|---|---:|---:|---:|---:|---:|---:|---:|
| A_baseline | 15 | 1 | 3 | 8 | 2 | 8160.47 | 13202.9 |
| B_timeout10 | 10 | 1 | 3 | 8 | 2 | 11114.45 | 15108.4 |
| C_timeout10_conc4 | 10 | 1 | 4 | 8 | 2 | 3530.09 | 5191.86 |
| D_timeout8_conc4 | 8 | 1 | 4 | 8 | 2 | 3911.37 | 5574.55 |

Current recommended runtime candidate from benchmark:

- `REQUEST_TIMEOUT_SECONDS=10`
- `ANALYSIS_MAX_CONCURRENT=4`
- `RETRY_ATTEMPTS=1`

## 4) Automated Test Suite

Run after each code/config change:

```bash
pytest -q
```

Recommended focused runs:

```bash
pytest tests/unit -q
pytest tests/integration -q
```

## 5) Manual Smoke Checklist

After automated tests pass:

1. Valid ticker returns a single analysis message.
2. Invalid ticker returns a short formal ticker-not-found message.
3. Generic service failure returns fallback temporary error message.
4. Cooldown message appears when user sends requests too quickly.
5. Queue overflow message appears when queue is intentionally saturated.
6. Fear & Greed scheduler can publish to dev webhook.
7. No duplicate bot responses in dev channel.

## 6) Rollback Criteria

Rollback immediately if one of these occurs:

- Error count increases materially versus baseline.
- p95 latency regresses for 2 consecutive runs.
- Users receive generic/unclear errors for invalid tickers.
- Duplicate responses reappear.

Rollback procedure:

1. Restore previous `.env` runtime values.
2. Re-deploy previous stable commit/runtime.
3. Verify smoke checklist items 1, 2, and 7.

## 7) Release Checklist (Dev -> Production)

Before production rollout:

- `pytest -q` passed on current branch.
- Baseline and candidate profile comparison documented.
- Dev smoke checklist fully passed.
- Production secrets/channel IDs verified.
- Plan for immediate rollback is prepared.

After rollout:

- Monitor first 30 minutes for `analysis_failed` spikes.
- Confirm no duplicate messages.
- Confirm p95 remains within expected band.
