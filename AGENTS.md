# Repository Guidelines

## Project Structure & Module Organization
- Place production code in `src/`; tests in `tests/`; helper scripts in `scripts/`; documentation in `docs/`; static assets in `assets/`.
- Mirror module layout between `src/` and `tests/` (e.g., `src/metrics/aggregators.py` → `tests/metrics/test_aggregators.py`).
- Keep environment/config files in `config/` and provide a `./.env.example`. Generated artifacts belong in `build/` or `dist/` and should be git-ignored.

## Build, Test, and Development Commands
- Standardize through a Makefile (recommended):
  - `make setup` — install project dependencies and pre-commit hooks.
  - `make run` — run the app/demo locally (or a sample CLI).
  - `make test` — run the full test suite with coverage.
  - `make lint` — run static analysis and linters.
  - `make fmt` — auto-format the codebase.
  - `make clean` — remove caches and build artifacts.
Add these targets as the project grows so contributors have a single entry point.

## Coding Style & Naming Conventions
- Indentation: 4 spaces; max line length: 100.
- Naming: snake_case for files and functions, PascalCase for classes, UPPER_CASE for constants; directories are snake_case.
- Keep modules small and cohesive; avoid cyclic dependencies; prefer pure, testable functions.
- Use an auto-formatter and linter (e.g., Black/Ruff for Python or Prettier/ESLint for JavaScript) and commit their configs.

## Testing Guidelines
- Put unit and integration tests under `tests/`, mirroring `src/` structure; name tests like `test_<module>.py` (adapt for language/framework).
- Target 80%+ coverage for changed code; include negative and edge cases.
- Run `make test` locally before pushing; CI must be green to merge.

## Commit & Pull Request Guidelines
- Follow Conventional Commits: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`. Example: `feat(aggregators): add mean calculator`.
- Keep commits small and focused. Update docs and tests with code changes.
- PRs should include: clear description, linked issues, test plan/output, and screenshots when UI/UX changes. Note breaking changes in the title.

## Security & Configuration Tips
- Never commit secrets. Add required variables to `.env.example` and load via environment.
- Pin dependencies and update via PRs. Validate external input; avoid unsafe shelling-out.
