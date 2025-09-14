from __future__ import annotations

import json
from datetime import datetime
from io import StringIO

import pandas as pd


def parse_disk_json(text: str) -> pd.DataFrame:
    doc = json.loads(text)
    host = doc["sysstat"]["hosts"][0]
    rows: list[dict] = []
    for stat in host.get("statistics", []):
        ts = stat.get("timestamp", {})
        dt = datetime.strptime(f"{ts.get('date')} {ts.get('time')} UTC", "%Y-%m-%d %H:%M:%S UTC")
        for d in stat.get("disk", []) or []:
            row: dict = {"timestamp": dt, "dev": d.get("disk-device")}
            for k, v in d.items():
                if k == "disk-device":
                    continue
                key = k.replace("-percent", "_pct").replace("-", "_")
                row[key] = v
            rows.append(row)
    return pd.DataFrame(rows)


def parse_disk_csv(text: str) -> pd.DataFrame:
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
