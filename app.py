import os
import json
import subprocess
from datetime import datetime
from typing import Literal, Tuple, List, Dict

import pandas as pd
import streamlit as st


def _run(cmd: List[str]) -> Tuple[int, str, str]:
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return p.returncode, p.stdout, p.stderr


def convert_with_sadf(path: str, prefer: Literal["auto", "12", "11"] = "auto") -> Tuple[Literal["json", "csv"], str]:
    """Convert a sar binary file to text using sadf.
    Tries JSON first (v12+) then falls back to CSV-like (v11 compat) unless prefer is fixed.
    Returns (format, text).
    """
    if prefer in ("auto", "12"):
        rc, out, err = _run(["sadf", "-j", path, "--", "-u", "-P", "ALL"])  # CPU only for speed
        if rc == 0 and out.strip():
            return "json", out
        if prefer == "12":
            raise RuntimeError(f"sadf -j failed: {err}")
    # Fallback to CSV-like
    env = os.environ.copy()
    env.update({"LC_ALL": "C"})
    p = subprocess.run(["sadf", "-d", path, "--", "-u", "-P", "ALL"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
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


def load_cpu_df(path: str, prefer: Literal["auto", "12", "11"]) -> Tuple[pd.DataFrame, str]:
    fmt, text = convert_with_sadf(path, prefer)
    if fmt == "json":
        return parse_cpu_json(text), "json"
    else:
        return parse_cpu_csv(text), "csv"


def main():
    st.set_page_config(page_title="SAR Viewer", layout="wide")
    st.title("SAR CPU Viewer (v11/v12 auto)")

    prefer = os.environ.get("SAR_VERSION", "auto").lower()
    if prefer not in ("auto", "11", "12"):
        prefer = "auto"

    left, right = st.columns([2, 3])
    with left:
        st.subheader("Input")
        samples = []
        if os.path.isdir("samples"):
            samples = [os.path.join("samples", f) for f in os.listdir("samples") if f.endswith(".dat")]
        default_path = samples[0] if samples else ""
        selected = st.selectbox("Sample .dat file", options=["(upload)"] + samples, index=1 if samples else 0)
        uploaded = st.file_uploader("Or upload a sar .dat file", type=["dat", "bin", "sar", "data"]) if selected == "(upload)" else None

        path = None
        if selected != "(upload)":
            path = selected
        elif uploaded is not None:
            tmp_path = os.path.join("samples", "uploaded.dat")
            with open(tmp_path, "wb") as f:
                f.write(uploaded.getbuffer())
            path = tmp_path

        metrics = st.multiselect("Metrics", ["user", "system", "iowait", "idle"], default=["user", "system", "idle"])
        cpu_filter = st.text_input("CPU filter (e.g., all, 0, 1, 2)", value="all")
        st.caption("Set env SAR_VERSION=auto|12|11 to force format handling.")

    with right:
        st.subheader("Chart")
        if not path:
            st.info("Select or upload a sar .dat file from the left.")
            return
        try:
            df, fmt = load_cpu_df(path, prefer)  # may raise
        except Exception as e:
            st.error(f"Failed to load: {e}")
            return
        st.write(f"Input: `{os.path.basename(path)}` parsed as `{fmt}`")

        # Filter CPU
        wanted = [c.strip() for c in cpu_filter.split(',')] if cpu_filter else []
        if wanted and wanted != ['']:
            df = df[df["cpu"].isin(wanted)]

        # Pivot for charting: one series per metric per CPU
        # Build a multiindex column like metric[cpu]
        series = {}
        for m in metrics:
            for cpu in sorted(df["cpu"].unique()):
                key = f"{m}[{cpu}]"
                series[key] = df[df["cpu"] == cpu].set_index("timestamp")[m]
        if not series:
            st.warning("No data after filtering.")
            return
        chart_df = pd.concat(series, axis=1).sort_index()
        st.line_chart(chart_df)


if __name__ == "__main__":
    main()

