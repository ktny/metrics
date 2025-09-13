from __future__ import annotations

import json
from datetime import datetime
from io import StringIO

import pandas as pd


def parse_net_json(text: str) -> pd.DataFrame:
    doc = json.loads(text)
    host = doc["sysstat"]["hosts"][0]
    rows: list[dict] = []
    for stat in host.get("statistics", []):
        ts = stat.get("timestamp", {})
        dt = datetime.strptime(f"{ts.get('date')} {ts.get('time')} UTC", "%Y-%m-%d %H:%M:%S UTC")
        net = stat.get("network", {})
        for e in net.get("net-dev", []) if isinstance(net, dict) else []:
            row: dict = {"timestamp": dt, "iface": e.get("iface")}
            for k, v in e.items():
                if k == "iface":
                    continue
                key = k.replace("-percent", "_pct").replace("-", "_")
                row[key] = v
            rows.append(row)
    return pd.DataFrame(rows)


def parse_net_csv(text: str) -> pd.DataFrame:
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
