import json
import os
import subprocess
from datetime import datetime
from typing import Dict, List, Literal, Optional, Tuple

import pandas as pd
import streamlit as st


def _run(cmd: List[str]) -> Tuple[int, str, str]:
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return p.returncode, p.stdout, p.stderr


@st.cache_data(show_spinner=False)
def convert_with_sadf(path: str, sar_args: Tuple[str, ...], prefer: Literal["auto", "12", "11"] = "auto") -> Tuple[Literal["json", "csv"], str]:
    """Convert a sar binary file to text using sadf.
    - sar_args: e.g., ("-u", "-P", "ALL") or ("-r",) or ("-d",) or ("-n", "DEV")
    Returns (format, text).
    """
    if prefer in ("auto", "12"):
        rc, out, err = _run(["sadf", "-j", path, "--", *sar_args])
        if rc == 0 and out.strip():
            return "json", out
        if prefer == "12":
            raise RuntimeError(f"sadf -j failed: {err}")
    # Fallback to CSV-like
    env = os.environ.copy()
    env.update({"LC_ALL": "C"})
    p = subprocess.run(["sadf", "-d", path, "--", *sar_args], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
    if p.returncode != 0:
        raise RuntimeError(f"sadf -d failed: {p.stderr}")
    return "csv", p.stdout


def parse_cpu_json(text: str) -> pd.DataFrame:
    doc = json.loads(text)
    host = doc["sysstat"]["hosts"][0]
    rows: List[Dict] = []
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
    df = df[existing].copy()
    df = df.rename(columns={
        "CPU": "cpu",
        "%user": "user",
        "%system": "system",
        "%iowait": "iowait",
        "%idle": "idle",
    })
    # Parse timestamp to datetime (timestamps from -d are in UTC by default)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce").dt.tz_convert(None)
    df["cpu"] = df["cpu"].astype(str)
    df.loc[df["cpu"] == "-1", "cpu"] = "all"
    return df


def parse_mem_json(text: str) -> pd.DataFrame:
    doc = json.loads(text)
    host = doc["sysstat"]["hosts"][0]
    rows: List[Dict] = []
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
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce").dt.tz_convert(None)
    df = df.rename(columns=rename)
    keep = [c for c in ["timestamp", "memfree", "avail", "memused", "memused_pct", "buffers", "cached", "commit", "commit_pct", "active", "inactive", "dirty"] if c in df.columns]
    return df[keep]


def parse_disk_json(text: str) -> pd.DataFrame:
    doc = json.loads(text)
    host = doc["sysstat"]["hosts"][0]
    rows: List[Dict] = []
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
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce").dt.tz_convert(None)
    df = df.rename(columns={
        "DEV": "dev",
        "%util": "util_pct",
        "rkB/s": "rkB_s",
        "wkB/s": "wkB_s",
        "dkB/s": "dkB_s",
        "aqu-sz": "aqu_sz",
        "areq-sz": "areq_sz",
    })
    return df


def parse_net_json(text: str) -> pd.DataFrame:
    doc = json.loads(text)
    host = doc["sysstat"]["hosts"][0]
    rows: List[Dict] = []
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
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce").dt.tz_convert(None)
    df = df.rename(columns={
        "IFACE": "iface",
        "%ifutil": "ifutil_pct",
        "rxkB/s": "rxkB_s",
        "txkB/s": "txkB_s",
        "rxpck/s": "rxpck_s",
        "txpck/s": "txpck_s",
        "rxcmp/s": "rxcmp_s",
        "txcmp/s": "txcmp_s",
        "rxmcst/s": "rxmcst_s",
    })
    return df


def load_cpu_df(path: str, prefer: Literal["auto", "12", "11"]) -> Tuple[pd.DataFrame, str]:
    fmt, text = convert_with_sadf(path, ("-u", "-P", "ALL"), prefer)
    if fmt == "json":
        return parse_cpu_json(text), "json"
    else:
        return parse_cpu_csv(text), "csv"


def load_mem_df(path: str, prefer: Literal["auto", "12", "11"]) -> Tuple[pd.DataFrame, str]:
    fmt, text = convert_with_sadf(path, ("-r",), prefer)
    if fmt == "json":
        return parse_mem_json(text), "json"
    else:
        return parse_mem_csv(text), "csv"


def load_disk_df(path: str, prefer: Literal["auto", "12", "11"]) -> Tuple[pd.DataFrame, str]:
    fmt, text = convert_with_sadf(path, ("-d",), prefer)
    if fmt == "json":
        return parse_disk_json(text), "json"
    else:
        return parse_disk_csv(text), "csv"


def load_net_df(path: str, prefer: Literal["auto", "12", "11"]) -> Tuple[pd.DataFrame, str]:
    fmt, text = convert_with_sadf(path, ("-n", "DEV"), prefer)
    if fmt == "json":
        return parse_net_json(text), "json"
    else:
        return parse_net_csv(text), "csv"


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
    selected = st.selectbox("Sample .dat file", options=["(upload)"] + samples, index=1 if samples else 0)
    uploaded = st.file_uploader("Or upload a sar .dat file", type=["dat", "bin", "sar", "data"]) if selected == "(upload)" else None

    path: Optional[str] = None
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
        try:
            df, fmt = load_cpu_df(path, prefer)
            st.caption(f"Parsed as {fmt}")
        except Exception as e:
            st.error(f"CPU load failed: {e}")
            df = None
        if df is not None and not df.empty:
            cpu_metrics = st.multiselect("Metrics", ["user", "system", "iowait", "idle"], default=["user", "system", "idle"])
            cpu_filter = st.text_input("CPU filter (e.g., all, 0, 1, 2)", value="all")
            wanted = [c.strip() for c in cpu_filter.split(',')] if cpu_filter else []
            if wanted and wanted != ['']:
                df = df[df["cpu"].isin(wanted)]
            series = {}
            for m in cpu_metrics:
                for cpu in sorted(df["cpu"].unique()):
                    key = f"{m}[{cpu}]"
                    series[key] = df[df["cpu"] == cpu].set_index("timestamp")[m]
            if series:
                chart_df = pd.concat(series, axis=1).sort_index()
                st.line_chart(chart_df)
            st.download_button("Download CPU CSV", df.to_csv(index=False).encode("utf-8"), file_name="cpu.csv", mime="text/csv")

    # Memory Tab
    with tabs[1]:
        try:
            mdf, mfmt = load_mem_df(path, prefer)
            st.caption(f"Parsed as {mfmt}")
        except Exception as e:
            st.error(f"Memory read failed: {e}")
            mdf = None
        if mdf is not None and not mdf.empty:
            # Default metrics for memory
            mem_metrics = st.multiselect("Metrics", [c for c in ["memused_pct", "memfree", "avail", "cached", "buffers", "commit_pct"] if c in mdf.columns], default=[mm for mm in ["memused_pct", "cached", "buffers"] if mm in mdf.columns])
            if mem_metrics:
                st.line_chart(mdf.set_index("timestamp")[mem_metrics])
            st.download_button("Download Memory CSV", mdf.to_csv(index=False).encode("utf-8"), file_name="memory.csv", mime="text/csv")

    # Disk Tab
    with tabs[2]:
        try:
            ddf, dfmt = load_disk_df(path, prefer)
            st.caption(f"Parsed as {dfmt}")
        except Exception as e:
            st.error(f"Disk read failed: {e}")
            ddf = None
        if ddf is not None and not ddf.empty:
            devs = sorted(ddf["dev"].dropna().astype(str).unique()) if "dev" in ddf.columns else []
            sel_devs = st.multiselect("Devices", devs, default=devs[:2])
            # Common disk metrics
            disk_metrics_all = [c for c in ["tps", "rkB_s", "wkB_s", "await", "util_pct"] if c in ddf.columns]
            disk_metrics = st.multiselect("Metrics", disk_metrics_all, default=disk_metrics_all[:3])
            if sel_devs and disk_metrics:
                series = {}
                for m in disk_metrics:
                    for dev in sel_devs:
                        key = f"{m}[{dev}]"
                        series[key] = ddf[ddf["dev"] == dev].set_index("timestamp")[m]
                if series:
                    chart_df = pd.concat(series, axis=1).sort_index()
                    st.line_chart(chart_df)
            st.download_button("Download Disk CSV", ddf.to_csv(index=False).encode("utf-8"), file_name="disk.csv", mime="text/csv")

    # Network Tab
    with tabs[3]:
        try:
            ndf, nfmt = load_net_df(path, prefer)
            st.caption(f"Parsed as {nfmt}")
        except Exception as e:
            st.error(f"Network read failed: {e}")
            ndf = None
        if ndf is not None and not ndf.empty:
            ifaces = sorted(ndf["iface"].dropna().astype(str).unique()) if "iface" in ndf.columns else []
            sel_ifaces = st.multiselect("Interfaces", ifaces, default=ifaces[:2])
            net_metrics_all = [c for c in ["rxkB_s", "txkB_s", "rxpck_s", "txpck_s", "ifutil_pct"] if c in ndf.columns]
            net_metrics = st.multiselect("Metrics", net_metrics_all, default=[m for m in ["rxkB_s", "txkB_s"] if m in net_metrics_all])
            if sel_ifaces and net_metrics:
                series = {}
                for m in net_metrics:
                    for iface in sel_ifaces:
                        key = f"{m}[{iface}]"
                        series[key] = ndf[ndf["iface"] == iface].set_index("timestamp")[m]
                if series:
                    chart_df = pd.concat(series, axis=1).sort_index()
                    st.line_chart(chart_df)
            st.download_button("Download Network CSV", ndf.to_csv(index=False).encode("utf-8"), file_name="network.csv", mime="text/csv")


if __name__ == "__main__":
    main()
