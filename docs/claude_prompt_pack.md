# Claude Prompt Pack - Agentlio Market Intel

This prompt pack helps you run Agentlio MCP workflows in Claude with consistent, professional output quality.

## Usage Guidelines

- Always provide clear app identity values.
- Ask for metrics, prioritized actions, and expected business impact.
- Use `since_date` whenever possible for incremental analysis.

---

## Prompt 1 - Executive Market Intel Report

Purpose:
Generate a concise, executive-level report focused on strategic actions.

Prompt:
Fetch the latest Google Play reviews for `com.spotify.music` with `since_date=2026-03-01`.
Produce an Executive Market Intel report with:
1. Sentiment summary
2. Top 5 issue themes with frequency and impact
3. 7 growth actions based on negative theme benchmark
4. ICE scoring (Impact, Confidence, Ease)
5. 14-day execution plan

---

## Prompt 2 - Churn Rescue Plan

Purpose:
Build a churn-reduction sprint plan from negative feedback.

Prompt:
Fetch App Store reviews for `app_name=spotify-music-and-podcasts`, `app_id=324684580`, `since_date=2026-03-01`.
Using only 1-2 star reviews:
1. Classify churn drivers by theme
2. Propose root-cause hypotheses
3. Build a 2-week churn-rescue sprint backlog
4. Add expected KPI impact per backlog item

---

## Prompt 3 - Competitive Benchmark Comparison

Purpose:
Compare competing products using score, themes, and growth opportunities.

Prompt:
Use `compare_google_play_apps` for:
- `com.spotify.music`
- `com.deezer.android.app`
- `com.apple.android.music`

Return:
1. Ranking by average score
2. Top negative theme per app
3. Theme-level differentiation opportunities
4. Top 3 growth experiments with expected upside

---

## Prompt 4 - Release Impact Radar

Purpose:
Monitor post-release sentiment and regression risk.

Prompt:
Fetch Google Play reviews for `com.spotify.music` with `since_date=2026-03-15`.
Answer:
1. Did sentiment improve or decline post-release?
2. Which themes are increasing or decreasing?
3. Are there regression signals?
4. What are the top 3 urgent hotfix priorities?

---

## Prompt 5 - PM Backlog Generator

Purpose:
Convert review signals directly into product backlog items.

Prompt:
Fetch the latest 200 reviews and generate backlog items with:
- Title
- Problem statement
- User segment
- Solution hypothesis
- Success metric
- Priority (P0/P1/P2)
- Effort (S/M/L)

Then rank by retention impact.

---

## Prompt 6 - Privacy-Safe Insight Mode

Purpose:
Produce compliance-friendly analysis using redacted data.

Prompt:
Analyze in privacy-safe mode using only anonymized findings.
1. Do not extract person-specific details.
2. Summarize only theme and behavior-level insights.
3. Flag any text that may carry policy risk.

---

## Prompt 7 - Weekly Growth Cadence

Purpose:
Prepare a weekly growth meeting brief.

Prompt:
Fetch the last 7 days of reviews with `since_date=2026-03-12` and generate:
1. Top 3 signals affecting the North Star metric
2. Top 5 user pain points
3. 5 growth experiments for next week
4. Success criteria and fail-fast conditions per experiment

---

## Reusable Prompt Template

Store: `[google_play|app_store]`
App: `[...]`
Since Date: `[...]`
Goal: `[sentiment|growth|churn|benchmark]`
Output: `[summary + table + action plan]`
Constraints: `[token limit, country, language, review count]`

Use this template to keep analysis quality consistent across runs.
