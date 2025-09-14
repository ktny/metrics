from __future__ import annotations

import pandas as pd
import streamlit as st


def render(fsdf: pd.DataFrame) -> None:
    filesystems = (
        sorted(pd.Series(fsdf.get("filesystem", pd.Series(dtype=str))).dropna().astype(str).unique().tolist())
        if "filesystem" in fsdf.columns
        else []
    )
    sel_fs = st.multiselect("Filesystems", filesystems, default=filesystems[:2])
    cap_metrics_all = [
        c
        for c in ["mb_free", "mb_used", "fsused_pct", "ufsused_pct", "inodes_used_pct"]
        if c in fsdf.columns
    ]
    sel_cap = st.multiselect(
        "Metrics",
        cap_metrics_all,
        default=[m for m in ["mb_free", "fsused_pct"] if m in cap_metrics_all],
    )
    if sel_fs and sel_cap:
        series: dict[str, pd.Series] = {}
        for m in sel_cap:
            for fs in sel_fs:
                key = f"{m}[{fs}]"
                series[key] = fsdf.loc[fsdf["filesystem"] == fs].set_index("timestamp")[m]
        if series:
            st.line_chart(pd.concat(series, axis=1).sort_index())

