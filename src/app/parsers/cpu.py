from __future__ import annotations

import json
from datetime import datetime

import pandas as pd


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
    df.loc[df["cpu"] == "-1", "cpu"] = "all"
    return df


def parse_cpu_csv(text: str) -> pd.DataFrame:
    from io import StringIO

    df = pd.read_csv(StringIO(text), sep=";", comment="#")
    keep = ["timestamp", "CPU", "%user", "%system", "%iowait", "%idle"]
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
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce").dt.tz_convert(None)
    df["cpu"] = df["cpu"].astype(str)
    df.loc[df["cpu"] == "-1", "cpu"] = "all"
    return df
