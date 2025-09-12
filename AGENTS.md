# Repository Guidelines

## Project Structure & Module Organization
- App entry: `app.py`（Streamlit）。将来は `src/` に分割し、`tests/` にミラー配置。
- サンプルデータ: `samples/`（生成物は `.gitignore` 済み）。
- 設定: `pyproject.toml`（依存・ツール設定）、`.mise.toml`（タスク）、`.gitignore`。

## Build, Test, and Development Commands
- タスクランナーは mise、パッケージ管理は uv を使用。
  - `mise run setup` — 依存をインストール（`.venv` 作成、`uv sync`）。
  - `mise run run` — Streamlit を起動（`uv run streamlit run app.py`）。
  - `mise run sample` — sar 収集→`sadf -j/-d` で JSON/CSV 生成。
  - `mise run fmt` / `mise run lint` — ruff でフォーマット/静的解析。
  - `mise run typecheck` — pyright で型チェック。
- 互換目的で `make run` 等も mise にフォワードしています。

## Coding Style & Naming Conventions
- インデント4スペース、行長100。ファイル/関数は snake_case、クラスは PascalCase、定数は UPPER_CASE。
- ツール: ruff（formatter + linter）。`pyproject.toml` の `[tool.ruff]` に準拠。

## Testing Guidelines
- 将来テストは `tests/` に配置し、`src/` とミラー命名（例: `tests/metrics/test_foo.py`）。
- 変更箇所は 80% 以上のカバレッジを目安。CI で `mise run lint` / `typecheck` を通すこと。

## Commit & Pull Request Guidelines
- Conventional Commits 準拠: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`。
- 小さく意味のあるコミット。必要に応じてサンプルやドキュメントを更新。
- PR は概要、再現/確認手順、関連 Issue、UI 変更はスクショを添付。破壊的変更は明記。

## Security & Configuration Tips
- シークレットはコミット禁止（`.env.example` を共有し、実値は環境変数で）。
- ロケール依存を避けるため `sadf -d` は `LC_ALL=C` を推奨。
