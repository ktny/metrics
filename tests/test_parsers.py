import json
import sys
from pathlib import Path
from textwrap import dedent

# Ensure the repository root is importable so we can import app.py directly
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import parse_cpu_csv, parse_cpu_json  # noqa: E402


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


    
