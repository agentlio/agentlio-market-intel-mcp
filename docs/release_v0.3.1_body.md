## Agentlio Market Intel v0.3.1

Initial clean public release of Agentlio Market Intel MCP.

### Highlights

- Production-ready MCP server for Google Play and App Store review intelligence
- Optimized response payload for AI context efficiency
- Incremental fetch support with since-date filtering
- Privacy-safe PII redaction for review text
- Competitive benchmark output with growth suggestions
- Claude menu router and prompt pack for repeatable workflows

### Core Reliability Features

- Input validation
- Retry with exponential backoff
- Timeout boundaries
- Rate limiting
- Hybrid cache (in-memory + optional Redis)

### Included MCP Tools

- get_google_play_reviews
- get_app_store_reviews
- get_market_reviews
- compare_google_play_apps

### Documentation

- README: project overview, setup, scenarios, examples
- Prompt Pack: reusable prompt library for common product workflows
- Menu Router Prompt: one-line and menu-based execution style

### Quality Status

- Ruff: passing
- Mypy: passing
- Pytest: passing

### Notes

Recommended runtime is Python 3.10-3.12 due to App Store dependency compatibility.
