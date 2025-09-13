from __future__ import annotations

import json
from datetime import datetime
from io import StringIO

import pandas as pd


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
