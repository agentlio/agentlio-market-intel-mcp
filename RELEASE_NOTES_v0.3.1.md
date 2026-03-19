# Agentlio Market Intel v0.3.1 Release Notes

Date: 2026-03-19
Status: Production Hardening + Insight Upgrade

## Summary

v0.3.1 evolves Agentlio Market Intel from a basic review fetch utility into a production-oriented MCP server focused on privacy, incremental analytics, cache performance, and action-ready growth insights.

## Added Features

### 1) Hybrid Cache (In-memory + Redis)

- Preserves in-memory TTL caching and adds an optional Redis layer.
- Activates Redis automatically when `REDIS_URL` is configured.
- Falls back to memory-only mode when Redis is unavailable.

Impact:
- Lower latency on repeated calls
- Reduced provider load and failure exposure

### 2) Incremental Fetch (`since_date`)

- Adds `since_date` support for Google Play and App Store fetch flows.
- Enables rolling analysis on newly collected reviews while skipping older data.

Impact:
- Lower token consumption
- Faster reporting cycles
- Clear time-window tracking for trend analysis

### 3) PII Redaction

- Masks email and phone-like patterns in review text.
- Enabled by default in the optimization pipeline.

Impact:
- Better alignment with privacy/compliance requirements
- Safer downstream use in agent responses

### 4) Advanced Compare Output

- Extends `compare_google_play_apps` with:
  - `themeMentions`
  - `negativeThemeMentions`
  - `growthSuggestions`
- Generates action-oriented suggestions based on negative theme concentration.

Impact:
- Upgrades comparison from raw scoring to decision-ready benchmarking

### 5) Claude Menu Router Prompt

- Adds a menu-router prompt for guided analysis in Claude.
- Supports both menu selection and one-line execution style.
- Documented at `docs/claude_menu_router_prompt.md`.

## API and Behavior Changes

- `get_google_play_reviews`
  - Added parameter: `since_date`
- `get_app_store_reviews`
  - Added parameter: `since_date`
- `get_market_reviews`
  - Added parameter: `since_date`
- `compare_google_play_apps`
  - Added output fields: `themeMentions`, `negativeThemeMentions`, `growthSuggestions`

## Quality Status

- Ruff lint: passing
- Mypy type-check: passing
- Pytest: 10 tests passing

## Backward Compatibility

- Existing tool calls remain valid.
- New parameters are optional.
- Redis configuration is optional.

## Known Constraints

- Due to dependency compatibility in App Store scraping stack, the recommended runtime is Python 3.10-3.12.
- Theme benchmarking is keyword-based and can be further improved with embedding-based clustering.

## Next Version Proposal (v0.4)

- Trend drift detection
- Tenant-level quota and auth controls
- Scheduled weekly report workflows
