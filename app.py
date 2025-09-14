import json
import os
import re
import subprocess
from datetime import datetime
from typing import Literal

import pandas as pd
import streamlit as st

from src.app.services.sadf import convert_with_sadf as _svc_convert_with_sadf


def _run(cmd: list[str]) -> tuple[int, str, str]:
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


@st.cache_data(show_spinner=False)
def convert_with_sadf_cached(
    path: str, sar_args: tuple[str, ...], prefer: Literal["auto", "12", "11"] = "auto"
) -> tuple[Literal["json", "csv"], str]:
    return _svc_convert_with_sadf(path, sar_args, prefer)


def parse_cpu_json(text: str) -> pd.DataFrame:
    doc = json.loads(text)
    host = doc["sysstat"]["hosts"][0]
    rows: list[dict] = []
    for stat in host.get("statistics", []):
        ts = stat.get("timestamp", {})
        dt = datetime.strptime(f"{ts.get('date')} {ts.get('time')} UTC", "%Y-%m-%d %H:%M:%S UTC")
        for entry in stat.get("cpu-load", []):
            row = {
                "timestamp": dt,
                "cpu": str(entry.get("cpu")),
                "user": float(entry.get("user", 0.0)),
                "system": float(entry.get("system", 0.0)),
                "iowait": float(entry.get("iowait", 0.0)),
                "idle": float(entry.get("idle", 0.0)),
            }
            rows.append(row)
    df = pd.DataFrame(rows)
    # normalize 'all' label
    df.loc[df["cpu"] == "-1", "cpu"] = "all"
    return df


def parse_cpu_csv(text: str) -> pd.DataFrame:
    from io import StringIO

    df = pd.read_csv(StringIO(text), sep=";", comment="#")
    # Expected columns: hostname;interval;timestamp;CPU;%user;%nice;%system;%iowait;%steal;%idle
    keep = [
        "timestamp",
        "CPU",
        "%user",
        "%system",
        "%iowait",
        "%idle",
    ]
    existing = [c for c in keep if c in df.columns]
    df = df.loc[:, existing].copy()
    df = df.rename(
        columns={
            "CPU": "cpu",
            "%user": "user",
            "%system": "system",
            "%iowait": "iowait",
            "%idle": "idle",
        }
    )
    # Parse timestamp to datetime (timestamps from -d are in UTC by default)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce").dt.tz_convert(None)
    df["cpu"] = df["cpu"].astype(str)
    df.loc[df["cpu"] == "-1", "cpu"] = "all"
    return df


def parse_mem_json(text: str) -> pd.DataFrame:
    doc = json.loads(text)
    host = doc["sysstat"]["hosts"][0]
    rows: list[dict] = []
    for stat in host.get("statistics", []):
        ts = stat.get("timestamp", {})
        dt = datetime.strptime(f"{ts.get('date')} {ts.get('time')} UTC", "%Y-%m-%d %H:%M:%S UTC")
        mem = stat.get("memory", {})
        if not mem:
            continue
        row = {"timestamp": dt}
        for k, v in mem.items():
            key = k.replace("-percent", "_pct").replace("-", "_")
            row[key] = v
        rows.append(row)
    df = pd.DataFrame(rows)
    return df


def parse_mem_csv(text: str) -> pd.DataFrame:
    from io import StringIO

    df = pd.read_csv(StringIO(text), sep=";", comment="#")
    # Normalize names
    rename = {
        "kbmemfree": "memfree",
        "kbavail": "avail",
        "kbmemused": "memused",
        "%memused": "memused_pct",
        "kbbuffers": "buffers",
        "kbcached": "cached",
        "kbcommit": "commit",
        "%commit": "commit_pct",
        "kbactive": "active",
        "kbinact": "inactive",
        "kbdirty": "dirty",
    }
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce").dt.tz_convert(
            None
        )
    df = df.rename(columns=rename)
    keep = [
        c
        for c in [
            "timestamp",
            "memfree",
            "avail",
            "memused",
            "memused_pct",
            "buffers",
            "cached",
            "commit",
            "commit_pct",
            "active",
            "inactive",
            "dirty",
        ]
        if c in df.columns
    ]
    return df.loc[:, keep]


def parse_disk_json(text: str) -> pd.DataFrame:
    doc = json.loads(text)
    host = doc["sysstat"]["hosts"][0]
    rows: list[dict] = []
    for stat in host.get("statistics", []):
        ts = stat.get("timestamp", {})
        dt = datetime.strptime(f"{ts.get('date')} {ts.get('time')} UTC", "%Y-%m-%d %H:%M:%S UTC")
        for d in stat.get("disk", []):
            row = {"timestamp": dt, "dev": d.get("disk-device")}
            for k, v in d.items():
                if k == "disk-device":
                    continue
                key = k.replace("-percent", "_pct").replace("-", "_")
                row[key] = v
            rows.append(row)
    return pd.DataFrame(rows)


def parse_disk_csv(text: str) -> pd.DataFrame:
    from io import StringIO

    df = pd.read_csv(StringIO(text), sep=";", comment="#")
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce").dt.tz_convert(
            None
        )
    df = df.rename(
        columns={
            "DEV": "dev",
            "%util": "util_pct",
            "rkB/s": "rkB_s",
            "wkB/s": "wkB_s",
            "dkB/s": "dkB_s",
            "aqu-sz": "aqu_sz",
            "areq-sz": "areq_sz",
        }
    )
    return df


def parse_net_json(text: str) -> pd.DataFrame:
    doc = json.loads(text)
    host = doc["sysstat"]["hosts"][0]
    rows: list[dict] = []
    for stat in host.get("statistics", []):
        ts = stat.get("timestamp", {})
        dt = datetime.strptime(f"{ts.get('date')} {ts.get('time')} UTC", "%Y-%m-%d %H:%M:%S UTC")
        net = stat.get("network", {})
        for e in net.get("net-dev", []) if isinstance(net, dict) else []:
            row = {"timestamp": dt, "iface": e.get("iface")}
            for k, v in e.items():
                if k == "iface":
                    continue
                key = k.replace("-percent", "_pct").replace("-", "_")
                row[key] = v
            rows.append(row)
    return pd.DataFrame(rows)


def parse_net_csv(text: str) -> pd.DataFrame:
    from io import StringIO

    df = pd.read_csv(StringIO(text), sep=";", comment="#")
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce").dt.tz_convert(
            None
        )
    df = df.rename(
        columns={
            "IFACE": "iface",
            "%ifutil": "ifutil_pct",
            "rxkB/s": "rxkB_s",
            "txkB/s": "txkB_s",
            "rxpck/s": "rxpck_s",
            "txpck/s": "txpck_s",
            "rxcmp/s": "rxcmp_s",
            "txcmp/s": "txcmp_s",
            "rxmcst/s": "rxmcst_s",
        }
    )
    return df


def parse_fs_json(text: str) -> pd.DataFrame:
    doc = json.loads(text)
    host = doc["sysstat"]["hosts"][0]
    rows: list[dict] = []
    for stat in host.get("statistics", []):
        ts = stat.get("timestamp", {})
        dt = datetime.strptime(f"{ts.get('date')} {ts.get('time')} UTC", "%Y-%m-%d %H:%M:%S UTC")
        for fs in stat.get("filesystems", []) or []:
            row: dict = {"timestamp": dt, "filesystem": fs.get("filesystem")}
            for k, v in fs.items():
                if k == "filesystem":
                    continue
                key = (
                    k.replace("MBfs", "mb_")
                    .replace("%fsused", "fsused_pct")
                    .replace("%ufsused", "ufsused_pct")
                    .replace("%Iused", "inodes_used_pct")
                    .replace("Iused", "inodes_used")
                    .replace("Ifree", "inodes_free")
                )
                row[key] = v
            rows.append(row)
    return pd.DataFrame(rows)


def parse_fs_csv(text: str) -> pd.DataFrame:
    from io import StringIO

    df = pd.read_csv(StringIO(text), sep=";", comment="#")
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce").dt.tz_convert(
            None
        )
    df = df.rename(
        columns={
            "FILESYSTEM": "filesystem",
            "MBfsfree": "mb_free",
            "MBfsused": "mb_used",
            "%fsused": "fsused_pct",
            "%ufsused": "ufsused_pct",
            "Ifree": "inodes_free",
            "Iused": "inodes_used",
            "%Iused": "inodes_used_pct",
        }
    )
    return df


def load_cpu_df(path: str, prefer: Literal["auto", "12", "11"]) -> tuple[pd.DataFrame, str]:
    fmt, text = convert_with_sadf_cached(path, ("-u", "-P", "ALL"), prefer)
    if fmt == "json":
        return parse_cpu_json(text), "json"
    else:
        return parse_cpu_csv(text), "csv"


def load_mem_df(path: str, prefer: Literal["auto", "12", "11"]) -> tuple[pd.DataFrame, str]:
    fmt, text = convert_with_sadf_cached(path, ("-r",), prefer)
    if fmt == "json":
        return parse_mem_json(text), "json"
    else:
        return parse_mem_csv(text), "csv"


def load_disk_df(path: str, prefer: Literal["auto", "12", "11"]) -> tuple[pd.DataFrame, str]:
    fmt, text = convert_with_sadf_cached(path, ("-d",), prefer)
    if fmt == "json":
        return parse_disk_json(text), "json"
    else:
        return parse_disk_csv(text), "csv"


def load_net_df(path: str, prefer: Literal["auto", "12", "11"]) -> tuple[pd.DataFrame, str]:
    fmt, text = convert_with_sadf_cached(path, ("-n", "DEV"), prefer)
    if fmt == "json":
        return parse_net_json(text), "json"
    else:
        return parse_net_csv(text), "csv"


def load_fs_df(path: str, prefer: Literal["auto", "12", "11"]) -> tuple[pd.DataFrame, str]:
    fmt, text = convert_with_sadf_cached(path, ("-F",), prefer)
    if fmt == "json":
        return parse_fs_json(text), "json"
    else:
        return parse_fs_csv(text), "csv"


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

    tabs = st.tabs(["CPU", "Memory", "Disk", "Network"])

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


if __name__ == "__main__":
    main()
