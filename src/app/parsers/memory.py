from __future__ import annotations

import json
from datetime import datetime
from io import StringIO

import pandas as pd


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
        row: dict = {"timestamp": dt}
        for k, v in mem.items():
            key = k.replace("-percent", "_pct").replace("-", "_")
            row[key] = v
        rows.append(row)
    return pd.DataFrame(rows)


def parse_mem_csv(text: str) -> pd.DataFrame:
    df = pd.read_csv(StringIO(text), sep=";", comment="#")
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce").dt.tz_convert(
            None
        )
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
