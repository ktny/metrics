import json
import os
import re
from typing import Literal

import streamlit as st

from src.app.services.sadf import convert_with_sadf as _svc_convert_with_sadf

## Legacy helper removed


@st.cache_data(show_spinner=False)
def convert_with_sadf_cached(
    path: str, sar_args: tuple[str, ...], prefer: Literal["auto", "12", "11"] = "auto"
) -> tuple[Literal["json", "csv"], str]:
    return _svc_convert_with_sadf(path, sar_args, prefer)


## Unused legacy load_* helpers removed


def main():
    st.set_page_config(page_title="SAR Viewer", layout="wide")
    st.title("SAR Viewer (v11/v12 auto)")

    prefer = os.environ.get("SAR_VERSION", "auto").lower()
    if prefer not in ("auto", "11", "12"):
        prefer = "auto"

    # Input controls (top)
    st.subheader("Input")
    logs_root = "logs"
    dirs = (
        [
            d
            for d in sorted(os.listdir(logs_root))
            if os.path.isdir(os.path.join(logs_root, d)) and not d.startswith(".")
        ]
        if os.path.isdir(logs_root)
        else []
    )

    if not dirs:
        st.info("Place SAR files under logs/<dir>/ (e.g., logs/dir1/saXX)")
        return

    source = st.radio("Source", options=["sar", "csv"], index=0, horizontal=True)

    # Filter directories depending on source
    def _has_csv_bundle(dir_name: str) -> bool:
        root = os.path.join(logs_root, dir_name, "csv")
        if not os.path.isdir(root):
            return False
        for name in os.listdir(root):
            cdir = os.path.join(root, name)
            if os.path.isdir(cdir) and re.match(r"^\d{4}-\d{2}-\d{2}$", name):
                # require at least cpu.csv inside the date dir
                if os.path.isfile(os.path.join(cdir, "cpu.csv")):
                    return True
        return False

    filtered_dirs = [d for d in dirs if _has_csv_bundle(d)] if source == "csv" else dirs
    if not filtered_dirs:
        if source == "csv":
            st.info(
                "No CSV bundles found under logs/. "
                "Run `mise run sample:csv` or place files under "
                "logs/<dir>/csv/YYYY-MM-DD/cpu.csv"
            )
        else:
            st.info("Place SAR files under logs/<dir>/ (e.g., logs/dir1/saXX)")
        return

    sel_dir = st.selectbox("Logs directory", options=filtered_dirs, index=0)

    @st.cache_data(show_spinner=False)
    def index_sar_files(dir_path: str) -> list[tuple[str, str]]:
        # Return list of (date_str, path) for sar binaries
        items: list[tuple[str, str]] = []
        for name in sorted(os.listdir(dir_path)):
            path = os.path.join(dir_path, name)
            if not os.path.isfile(path):
                continue
            try:
                # Prefer filename pattern saYYYYMMDD if present
                m = re.match(r"^sa(\d{8})$", name)
                if m:
                    ymd = m.group(1)
                    date_str = f"{ymd[0:4]}-{ymd[4:6]}-{ymd[6:8]}"
                    items.append((date_str, path))
                    continue

                # Otherwise try sadf header (JSON) to read file-date
                fmt, text = convert_with_sadf_cached(path, ("-u",), "auto")
                if fmt == "json":
                    doc = json.loads(text)
                    host = doc.get("sysstat", {}).get("hosts", [{}])[0]
                    file_date = host.get("file-date")
                    if file_date:
                        items.append((file_date, path))
                        continue
                # Fallback to raw filename
                items.append((name, path))
            except Exception:
                continue
        return items

    @st.cache_data(show_spinner=False)
    def index_csv_dates(dir_path: str) -> list[tuple[str, str]]:
        # Return list of (date_str, csv_date_dir) for per-resource CSV bundles
        csv_root = os.path.join(dir_path, "csv")
        items: list[tuple[str, str]] = []
        if not os.path.isdir(csv_root):
            return items
        for name in sorted(os.listdir(csv_root)):
            cdir = os.path.join(csv_root, name)
            if os.path.isdir(cdir) and re.match(r"^\d{4}-\d{2}-\d{2}$", name):
                items.append((name, cdir))
        return items

    dir_path = os.path.join(logs_root, sel_dir)
    indexed = index_csv_dates(dir_path) if source == "csv" else index_sar_files(dir_path)
    dates = sorted({d for d, _ in indexed})
    if not dates:
        if source == "csv":
            st.warning(
                "No CSV date directories found. Expected logs/<dir>/csv/YYYY-MM-DD with cpu.csv"
            )
        else:
            st.warning("No SAR files found (saDD under logs/<dir>/)")
        return
    sel_date = st.selectbox("Date", options=dates, index=len(dates) - 1)
    # pick first item matching date
    if source == "csv":
        csv_date_dir = next((p for d, p in indexed if d == sel_date), None)
        path = None
    else:
        path = next((p for d, p in indexed if d == sel_date), None)
        csv_date_dir = None

    st.caption("Set env SAR_VERSION=auto|12|11 to force format handling.")

    # Charts area
    st.subheader("Charts")
    if source == "sar" and not path:
        st.info("Select a SAR file from logs.")
        return
    if source == "csv" and not csv_date_dir:
        st.info("Select a CSV date directory under logs/<dir>/csv.")
        return

    tabs = st.tabs(["CPU", "Memory", "Disk", "Network", "Filesystem"])

    # CPU Tab
    with tabs[0]:
        from src.app.tabs import cpu as cpu_tab

        cpu_tab.render(path, prefer, source if source in ("sar", "csv") else "sar", csv_date_dir)

    # Memory Tab
    with tabs[1]:
        from src.app.tabs import memory as memory_tab

        memory_tab.render(path, prefer, source if source in ("sar", "csv") else "sar", csv_date_dir)

    # Disk Tab
    with tabs[2]:
        from src.app.tabs import disk as disk_tab

        disk_tab.render(path, prefer, source if source in ("sar", "csv") else "sar", csv_date_dir)

    # Network Tab
    with tabs[3]:
        from src.app.tabs import network as network_tab

        network_tab.render(
            path, prefer, source if source in ("sar", "csv") else "sar", csv_date_dir
        )

    # Filesystem Tab
    with tabs[4]:
        from src.app.tabs import filesystem as fs_tab

        fs_tab.render(path, prefer, source if source in ("sar", "csv") else "sar", csv_date_dir)


if __name__ == "__main__":
    main()
