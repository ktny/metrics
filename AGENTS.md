# Repository Guidelines

## Project Structure & Module Organization
- App entry: `app.py`（Streamlit）。将来は `src/` に分割し、`tests/` にミラー配置。
- サンプルデータ: `samples/`（生成物は `.gitignore` 済み）。
- 設定: `pyproject.toml`（依存・ツール設定。uv で Python 3.10 を固定）、`.mise.toml`（タスク）、`.gitignore`。
 - CI: `.github/workflows/ci.yml`（ruff/pyright を uv + mise で実行）。

## Build, Test, and Development Commands
- タスクランナーは mise、パッケージ管理は uv を使用（uv が Python 3.10 を管理）。
  - `mise install` — `.mise.toml` の [tools]（uv など）をインストール。
  - `mise run setup` — 依存同期（`uv sync --frozen`）＋ pre-commit フック導入。
  - `mise run run` — Streamlit 起動。
  - `mise run sample` — sar 収集→`sadf -j/-d` で JSON/CSV 生成。
  - `mise run fmt` / `mise run lint` — ruff フォーマット/静的解析。
  - `mise run fix` — ruff 自動修正。
  - `mise run type` / `mise run check` — 型チェック単体 / まとめ（format-check + lint + type）。
  - `mise run test` — pytest を実行。

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
- バージョン切替: `SAR_VERSION=11` で CSV 経路を強制、未指定は自動判定。

## Architecture Overview（要点）
- 変換: `sadf -j`（v12+ JSON）→ 失敗時 `sadf -d`（v11 互換 CSV）に自動フォールバック。
- タブ別 sar 引数: CPU `-u -P ALL` / Memory `-r` / Disk `-d` / Net `-n DEV`。
- 正規化: 列名や単位を正規化（例: `%util`→`util_pct`, `rxkB/s`→`rxkB_s`）。
- キャッシュ: `@st.cache_data` で `sadf` 実行結果をキャッシュ。

## Local Samples
- ダミーデータ生成: `mise run sample`
- 生成物: `samples/sar_v12.dat` と `sar_v12.json` / `sar_v12.csv`
