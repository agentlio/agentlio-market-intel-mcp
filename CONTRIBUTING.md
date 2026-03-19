# Contributing to Agentlio Market Intel

Thanks for your interest in contributing.

## Development Setup

1. Clone the repository.
2. Create and activate a Python environment (recommended: Python 3.10-3.12).
3. Install dependencies:

```bash
pip install -e .[dev]
```

## Quality Checks

Run all checks before opening a PR:

```bash
ruff check .
mypy src
pytest -q
```

## Branch and Commit Style

- Create a feature branch from `main`.
- Use clear commit messages (Conventional Commits preferred):
  - `feat: ...`
  - `fix: ...`
  - `docs: ...`
  - `test: ...`

## Pull Request Guidelines

- Explain what changed and why.
- Add or update tests for behavior changes.
- Update `README.md` and release notes when relevant.
- Keep PRs focused; avoid unrelated refactors.

## Reporting Bugs

Please use the Bug Report issue template and include:

- Expected behavior
- Actual behavior
- Reproduction steps
- Environment (OS, Python version, MCP client)

## Security

For security vulnerabilities, do not open a public issue first.
Please follow `SECURITY.md`.
