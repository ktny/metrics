# SAR Viewer (Streamlit)

A simple, browser-based viewer for Linux sar files (sysstat). Supports v12 JSON (`sadf -j`) and v11-compatible CSV (`sadf -d`) with automatic detection.

## Features
- CPU, Memory, Disk, Network tabs with metric pickers and CSV export
- Auto-detects format: try JSON first, fallback to CSV
- Handles per-CPU, per-device, per-interface series
- Fast local conversion via `sadf`; cached in app

## Requirements
- uv 0.8.17 (package manager) and mise (task runner)
- Python is pinned by uv to 3.10 (managed by `pyproject.toml`)
- sysstat (`sar`, `sadf`) for generating sample data

## Quick Start
- Install tools: `mise install` (installs uv as declared in `.mise.toml`)
- Sync deps: `mise run setup` (runs `uv sync --frozen` with Python 3.10)
- Generate samples (under logs/): `mise run sample` (creates `logs/dir1/saDD`)
- Run app: `mise run dev` and open http://localhost:8501

## Usage
- Input at the top: choose a logs subdir (e.g., `dir1`) and filter by Date
- Tabs:
  - CPU: select metrics (user/system/iowait/idle), filter CPUs (`all,0,1`)
  - Memory: typical series like `memused_pct`, `cached`, `buffers`
  - Disk: `tps`, `rkB_s`, `wkB_s`, `await`, `util_pct` by device
  - Network: `rxkB_s`, `txkB_s`, `rxpck_s`, `txpck_s`, `ifutil_pct` by iface
- Download buttons provide per-tab CSVs of the currently parsed data

## Version Handling
- Default is auto: the app runs `sadf -j` first and falls back to `-d` if needed
- Override via env: `SAR_VERSION=12` (force JSON) or `SAR_VERSION=11` (force CSV)
- CSV parsing uses `LC_ALL=C` semantics inside the app to avoid locale pitfalls

## Development
- Format/Lint: `mise run fmt`, `mise run lint`, auto-fix: `mise run fix`
- Type-check: `mise run type`, combined: `mise run check`
- Tests: `mise run test`
- CI: GitHub Actions runs `mise run check` and `mise run test`

## Notes
- Samples are git-ignored. Add your own under `samples/`.
- For large files, consider resampling windows (future enhancement).
