# Agentlio Market Intel

Agentlio Market Intel is a production-grade MCP server that transforms mobile app reviews into actionable product intelligence for AI agents.

It connects Google Play and App Store review data to real decision workflows such as sentiment monitoring, growth strategy, churn reduction, competitor benchmarking, and post-release risk detection.

## What You Can Do With It

- Fetch review data from Google Play and App Store.
- Analyze only recent reviews using incremental windows (`since_date`).
- Keep AI context lightweight with a model-first optimized response schema.
- Detect theme-level pain points and benchmark competitors.
- Generate growth actions directly from negative sentiment clusters.
- Use privacy-safe output with built-in PII redaction.

## Why Teams Use Agentlio

- AI-efficient output: returns only high-value fields (`score`, `content`, `date`, `thumbsUp`).
- Production hardening: request validation, retries, timeouts, rate limiting, and caching.
- Reliability by design: request IDs, structured behavior, and safe fallbacks.
- MCP-native integration: plug into Claude Desktop and other MCP clients.
- Modular codebase: provider fetchers, utility logic, and server orchestration are separated.

## Project Structure

```text
agentlio/
├── pyproject.toml
├── README.md
├── RELEASE_NOTES_v0.3.1.md
├── docs/
│   ├── claude_prompt_pack.md
│   └── claude_menu_router_prompt.md
├── src/
│   ├── __init__.py
│   ├── fetchers.py
│   ├── server.py
│   └── utils.py
└── tests/
```

## Installation

Recommended Python version: 3.10-3.12

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
```

Start server:

```bash
agentlio-market-intel
```

Alternative:

```bash
python -m src.server
```

## Core MCP Tools

### `get_google_play_reviews`

Parameters:
- `app_id` (str): e.g. `com.spotify.music`
- `country` (str, default `us`)
- `lang` (str, default `en`)
- `count` (int, default `100`)
- `sort_by` (str, default `newest`; `newest`, `most_relevant`, `rating`)
- `since_date` (str, optional): `YYYY-MM-DD` or ISO-like lower bound

### `get_app_store_reviews`

Parameters:
- `app_name` (str): e.g. `spotify-music-and-podcasts`
- `app_id` (int): e.g. `324684580`
- `country` (str, default `us`)
- `count` (int, default `100`)
- `since_date` (str, optional): `YYYY-MM-DD` or ISO-like lower bound

### `get_market_reviews`

Unified tool for either provider:
- `provider`: `google_play` or `app_store`
- Google Play app identity: `app_id`
- App Store app identity: `ios_app_id`, `app_name`
- Optional: `since_date`

### `compare_google_play_apps`

Benchmark multiple apps (minimum 2):
- `app_ids`
- `country`, `lang`, `count`

Extended output includes:
- `themeMentions`
- `negativeThemeMentions`
- `growthSuggestions`

## Optimized Response Format

```json
{
  "score": 5,
  "content": "Great app!",
  "date": "2026-03-17T10:20:30",
  "thumbsUp": 12
}
```

Additional metadata fields:
- `requestId`
- `cached`
- `summary` (average score + distribution)

## Real-World Scenarios

### 1) Release Impact Monitoring
Goal: detect quality regressions within 24-72 hours after release.

Typical flow:
1. Fetch reviews with `since_date` set to release date.
2. Compare rising themes (`stability`, `performance`, `ux`).
3. Build urgent hotfix list from negative clusters.

### 2) Churn Rescue Sprint
Goal: convert 1-2 star feedback into a 2-week execution plan.

Typical flow:
1. Pull low-rating reviews.
2. Group root causes by theme.
3. Generate backlog with KPI impact and priority.

### 3) Competitive Positioning
Goal: understand where your app wins/loses vs competitors.

Typical flow:
1. Run `compare_google_play_apps` for top competitors.
2. Compare average scores and negative theme density.
3. Turn gaps into growth experiments.

### 4) Weekly Growth Cadence
Goal: run an objective weekly review cycle.

Typical flow:
1. Analyze the last 7 days with `since_date`.
2. Extract top user pain points.
3. Propose next-week experiments with success criteria.

## Prompt Examples

### Example A: Executive Report

```text
Analyze Google Play reviews for com.spotify.music since 2026-03-10.
Return: sentiment summary, top 5 issue themes, 7 growth actions, ICE prioritization,
and a 14-day execution plan.
```

### Example B: Churn Recovery

```text
Fetch App Store reviews for app_name=spotify-music-and-podcasts, ios_app_id=324684580,
since_date=2026-03-01. Use only 1-2 star reviews to build a churn rescue sprint backlog
with expected KPI impact.
```

### Example C: Competitor Benchmark

```text
Compare Google Play apps: com.spotify.music, com.deezer.android.app,
com.apple.android.music. Return score ranking, top negative themes per app,
and top 3 growth experiments.
```

### Example D: One-Line Menu Command

```text
menu:1 provider=google_play app_id=com.spotify.music country=us lang=en count=200 since_date=2026-03-12
```

### Example E: One-Line Benchmark Alias

```text
run:bench app_ids=com.spotify.music,com.deezer.android.app,com.apple.android.music country=us lang=en count=120 since_date=2026-03-10
```

## Claude Desktop Setup

1. Resolve the Python executable path in your virtual environment.
2. Open Claude config file:

```text
~/Library/Application Support/Claude/claude_desktop_config.json
```

3. Register MCP server:

```json
{
  "mcpServers": {
    "agentlio-market-intel": {
      "command": "/ABSOLUTE/PATH/TO/python",
      "args": ["-m", "src.server"],
      "cwd": "/ABSOLUTE/PATH/TO/agentlio"
    }
  }
}
```

4. Fully restart Claude Desktop.

## Performance and Reliability Defaults

- Rate limit: 60 calls/minute (in-memory window)
- Timeout: 25 seconds
- Retry: 3 attempts (exponential backoff)
- Cache TTL: 5 minutes
- Cache mode: in-memory + optional Redis

Enable Redis layer:

```bash
export REDIS_URL=redis://localhost:6379/0
```

## Troubleshooting

### MCP server not showing in Claude
- Confirm config path is correct (`claude_desktop_config.json`).
- Ensure command path points to the correct Python environment.
- Restart Claude completely (not just window refresh).

### App Store fetch fails on Python 3.13
- Use Python 3.10-3.12 for compatibility with App Store scraping dependencies.

### Rate limit errors
- Reduce burst calls or wait for the next window.
- Add Redis for more stable repeated workloads.

### Empty results with `since_date`
- Verify date format and ensure there are reviews in that interval.

## Documentation

- Release notes: `RELEASE_NOTES_v0.3.1.md`
- Prompt pack: `docs/claude_prompt_pack.md`
- Menu router prompt: `docs/claude_menu_router_prompt.md`
- Contribution guide: `CONTRIBUTING.md`
- Security policy: `SECURITY.md`

## Compliance Note

Respect each platform's terms of service and your organization's data governance requirements.
Always review storage and processing policies before persisting review-derived insights.
