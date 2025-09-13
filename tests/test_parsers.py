import json
import sys
from pathlib import Path
from textwrap import dedent

import pandas as pd

# Ensure the repository root is importable so we can import app.py directly
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import (  # noqa: E402
    parse_cpu_json,
    parse_cpu_csv,
    parse_mem_json,
    parse_mem_csv,
    parse_disk_json,
    parse_disk_csv,
    parse_net_json,
    parse_net_csv,
)


def test_parse_cpu_json_basic():
    doc = {
        "sysstat": {
            "hosts": [
                {
                    "statistics": [
                        {
                            "timestamp": {
                                "date": "2025-01-01",
                                "time": "00:00:01",
                                "utc": 1,
                                "interval": 1,
                            },
                            "cpu-load": [
                                {
                                    "cpu": "all",
                                    "user": 1.0,
                                    "system": 2.0,
                                    "iowait": 0.5,
                                    "idle": 96.5,
                                }
                            ],
                        }
                    ]
                }
            ]
        }
    }
    df = parse_cpu_json(json.dumps(doc))
    assert not df.empty and set(["timestamp", "cpu", "user", "system", "iowait", "idle"]).issubset(
        df.columns
    )


def test_parse_cpu_csv_basic():
    csv_text = dedent(
        """
        hostname;interval;timestamp;CPU;%user;%nice;%system;%iowait;%steal;%idle
        host;1;2025-01-01 00:00:01 UTC;all;1.0;0.0;2.0;0.5;0.0;96.5
        """
    ).strip()
    df = parse_cpu_csv(csv_text)
    assert list(df.columns) == ["timestamp", "cpu", "user", "system", "iowait", "idle"]


def test_parse_mem_json_basic():
    doc = {
        "sysstat": {
            "hosts": [
                {
                    "statistics": [
                        {
                            "timestamp": {
                                "date": "2025-01-01",
                                "time": "00:00:01",
                                "utc": 1,
                                "interval": 1,
                            },
                            "memory": {
                                "memfree": 100,
                                "memused": 900,
                                "memused-percent": 90.0,
                                "cached": 50,
                            },
                        }
                    ]
                }
            ]
        }
    }
    df = parse_mem_json(json.dumps(doc))
    assert set(["timestamp", "memfree", "memused", "memused_pct", "cached"]).issubset(df.columns)


def test_parse_mem_csv_basic():
    csv_text = dedent(
        """
        hostname;interval;timestamp;kbmemfree;kbavail;kbmemused;%memused;kbbuffers;kbcached;kbcommit;%commit;kbactive;kbinact;kbdirty
        host;1;2025-01-01 00:00:01 UTC;100;0;900;90.0;0;50;0;0;0;0;0
        """
    ).strip()
    df = parse_mem_csv(csv_text)
    assert set(["timestamp", "memfree", "memused", "memused_pct", "cached"]).issubset(df.columns)


def test_parse_disk_json_basic():
    doc = {
        "sysstat": {
            "hosts": [
                {
                    "statistics": [
                        {
                            "timestamp": {
                                "date": "2025-01-01",
                                "time": "00:00:01",
                                "utc": 1,
                                "interval": 1,
                            },
                            "disk": [
                                {
                                    "disk-device": "sda",
                                    "tps": 1.0,
                                    "await": 0.5,
                                    "util-percent": 10.0,
                                }
                            ],
                        }
                    ]
                }
            ]
        }
    }
    df = parse_disk_json(json.dumps(doc))
    assert set(["timestamp", "dev", "tps", "await", "util_pct"]).issubset(df.columns)


def test_parse_disk_csv_basic():
    csv_text = dedent(
        """
        hostname;interval;timestamp;DEV;tps;rkB/s;wkB/s;dkB/s;areq-sz;aqu-sz;await;%util
        host;1;2025-01-01 00:00:01 UTC;sda;1.0;0;0;0;0;0;0.5;10.0
        """
    ).strip()
    df = parse_disk_csv(csv_text)
    assert set(["timestamp", "dev", "tps", "await", "util_pct"]).issubset(df.columns)


def test_parse_net_json_basic():
    doc = {
        "sysstat": {
            "hosts": [
                {
                    "statistics": [
                        {
                            "timestamp": {
                                "date": "2025-01-01",
                                "time": "00:00:01",
                                "utc": 1,
                                "interval": 1,
                            },
                            "network": {
                                "net-dev": [
                                    {
                                        "iface": "eth0",
                                        "rxkB": 1.0,
                                        "txkB": 2.0,
                                        "ifutil-percent": 0.1,
                                    }
                                ]
                            },
                        }
                    ]
                }
            ]
        }
    }
    df = parse_net_json(json.dumps(doc))
    assert set(["timestamp", "iface", "rxkB", "txkB", "ifutil_pct"]).issubset(df.columns)


def test_parse_net_csv_basic():
    csv_text = dedent(
        """
        hostname;interval;timestamp;IFACE;rxpck/s;txpck/s;rxkB/s;txkB/s;rxcmp/s;txcmp/s;rxmcst/s;%ifutil
        host;1;2025-01-01 00:00:01 UTC;eth0;0;0;1.0;2.0;0;0;0;0.1
        """
    ).strip()
    df = parse_net_csv(csv_text)
    assert set(["timestamp", "iface", "rxkB_s", "txkB_s", "ifutil_pct"]).issubset(df.columns)
