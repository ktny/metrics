from __future__ import annotations

import os
import subprocess
from typing import Literal

import streamlit as st


def _run(cmd: list[str]) -> tuple[int, str, str]:
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


@st.cache_data(show_spinner=False)
def convert_with_sadf(
    path: str, sar_args: tuple[str, ...], prefer: Literal["auto", "12", "11"] = "auto"
) -> tuple[Literal["json", "csv"], str]:
    """Convert a sar binary file to text using sadf.
    Tries JSON first (v12+) then falls back to CSV-like (v11 compat) unless prefer is fixed.
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
    p = subprocess.run(
        ["sadf", "-d", path, "--", *sar_args], capture_output=True, text=True, env=env
    )
    if p.returncode != 0:
        raise RuntimeError(f"sadf -d failed: {p.stderr}")
    return "csv", p.stdout
