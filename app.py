import json
import os
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
    samples = []
    if os.path.isdir("samples"):
        samples = [os.path.join("samples", f) for f in os.listdir("samples") if f.endswith(".dat")]
    selected = st.selectbox(
        "Sample .dat file", options=["(upload)"] + samples, index=1 if samples else 0
    )
    uploaded = (
        st.file_uploader("Or upload a sar .dat file", type=["dat", "bin", "sar", "data"])
        if selected == "(upload)"
        else None
    )

    path: str | None = None
    if selected != "(upload)":
        path = selected
    elif uploaded is not None:
        os.makedirs("samples", exist_ok=True)
        tmp_path = os.path.join("samples", "uploaded.dat")
        with open(tmp_path, "wb") as f:
            f.write(uploaded.getbuffer())
        path = tmp_path

    st.caption("Set env SAR_VERSION=auto|12|11 to force format handling.")

    # Charts area
    st.subheader("Charts")
    if not path:
        st.info("Select or upload a sar .dat file from the left.")
        return

    tabs = st.tabs(["CPU", "Memory", "Disk", "Network"])

    # CPU Tab
    with tabs[0]:
        from src.app.tabs import cpu as cpu_tab

        cpu_tab.render(path, prefer)

    # Memory Tab
    with tabs[1]:
        from src.app.tabs import memory as memory_tab
        memory_tab.render(path, prefer)

    # Disk Tab
    with tabs[2]:
        try:
            ddf, dfmt = load_disk_df(path, prefer)
            st.caption(f"Parsed as {dfmt}")
        except Exception as e:
            st.error(f"Disk read failed: {e}")
            ddf = None
        if ddf is not None and not ddf.empty:
            devs = (
                sorted(pd.Series(ddf["dev"]).dropna().astype(str).unique().tolist())
                if "dev" in ddf.columns
                else []
            )
            sel_devs = st.multiselect("Devices", devs, default=devs[:2])

            # Split into sub-tabs by unit to avoid mixing scales
            disk_tabs = st.tabs(["IOPS/Throughput", "Latency", "Utilization", "Capacity"])

            # IOPS/Throughput (tps, rkB_s, wkB_s)
            with disk_tabs[0]:
                g1 = [c for c in ["tps", "rkB_s", "wkB_s"] if c in ddf.columns]
                sel_g1 = st.multiselect("Metrics", g1, default=g1)
                if sel_devs and sel_g1:
                    series = {}
                    for m in sel_g1:
                        for dev in sel_devs:
                            key = f"{m}[{dev}]"
                            series[key] = ddf.loc[ddf["dev"] == dev].set_index("timestamp")[m]
                    if series:
                        st.line_chart(pd.concat(series, axis=1).sort_index())

            # Latency (await in ms)
            with disk_tabs[1]:
                g2 = [c for c in ["await"] if c in ddf.columns]
                sel_g2 = st.multiselect("Metrics", g2, default=g2)
                if sel_devs and sel_g2:
                    series = {}
                    for m in sel_g2:
                        for dev in sel_devs:
                            key = f"{m}[{dev}]"
                            series[key] = ddf.loc[ddf["dev"] == dev].set_index("timestamp")[m]
                    if series:
                        st.line_chart(pd.concat(series, axis=1).sort_index())

            # Utilization (% of time device was busy)
            with disk_tabs[2]:
                g3 = [c for c in ["util_pct"] if c in ddf.columns]
                sel_g3 = st.multiselect("Metrics", g3, default=g3)
                if sel_devs and sel_g3:
                    series = {}
                    for m in sel_g3:
                        for dev in sel_devs:
                            key = f"{m}[{dev}]"
                            series[key] = ddf.loc[ddf["dev"] == dev].set_index("timestamp")[m]
                    if series:
                        st.line_chart(pd.concat(series, axis=1).sort_index())

            # Capacity (filesystem-free/used, percent used)
            with disk_tabs[3]:
                try:
                    fsdf, fsfmt = load_fs_df(path, prefer)
                    st.caption(f"Parsed FS as {fsfmt}")
                except Exception as e:
                    st.error(f"Filesystem read failed: {e}")
                    fsdf = None
                if fsdf is not None and not fsdf.empty:
                    filesystems = (
                        sorted(pd.Series(fsdf["filesystem"]).dropna().astype(str).unique().tolist())
                        if "filesystem" in fsdf.columns
                        else []
                    )
                    sel_fs = st.multiselect("Filesystems", filesystems, default=filesystems[:2])
                    cap_metrics_all = [
                        c
                        for c in [
                            "mb_free",
                            "mb_used",
                            "fsused_pct",
                            "ufsused_pct",
                            "inodes_used_pct",
                        ]
                        if c in fsdf.columns
                    ]
                    sel_cap = st.multiselect(
                        "Metrics",
                        cap_metrics_all,
                        default=[m for m in ["mb_free", "fsused_pct"] if m in cap_metrics_all],
                    )
                    if sel_fs and sel_cap:
                        series = {}
                        for m in sel_cap:
                            for fs in sel_fs:
                                key = f"{m}[{fs}]"
                                series[key] = fsdf.loc[fsdf["filesystem"] == fs].set_index(
                                    "timestamp"
                                )[m]
                        if series:
                            st.line_chart(pd.concat(series, axis=1).sort_index())

            st.download_button(
                "Download Disk CSV",
                ddf.to_csv(index=False).encode("utf-8"),
                file_name="disk.csv",
                mime="text/csv",
            )

    # Network Tab
    with tabs[3]:
        from src.app.tabs import network as network_tab
        network_tab.render(path, prefer)


if __name__ == "__main__":
    main()
