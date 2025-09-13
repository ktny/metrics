# SAR Viewer (Streamlit)

A simple, browser-based viewer for Linux sar files (sysstat). Supports v12 JSON (`sadf -j`) and v11-compatible CSV (`sadf -d`) with automatic detection.

## Features
- CPU, Memory, Disk, Network tabs with metric pickers and CSV export
- Auto-detects format: try JSON first, fallback to CSV
- Handles per-CPU, per-device, per-interface series
- Fast local conversion via `sadf`; cached in app

## Requirements
- Python 3.10+
- mise (task runner) and uv (Python package manager)
- sysstat (`sar`, `sadf`) for generating sample data

## Quick Start
- Install tools: `mise install` (installs uv from `.mise.toml`)
- Sync deps: `mise run setup`
- Generate samples: `mise run sample`
- Run app: `mise run run` and open http://localhost:8501

## Usage
- Input at the top: choose `samples/sar_v12.dat` or upload your own `.dat` file
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
- Lint/format: `mise run lint`, `mise run fmt`, auto-fix: `mise run lint-fix`
- Type-check: `mise run typecheck`, combined: `mise run qa`
- CI: GitHub Actions runs ruff + pyright using uv + mise

## Notes
- Samples are git-ignored. Add your own under `samples/`.
- For large files, consider resampling windows (future enhancement).
