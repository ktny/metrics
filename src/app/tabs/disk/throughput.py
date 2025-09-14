from __future__ import annotations

import pandas as pd
import streamlit as st


def render(ddf: pd.DataFrame, sel_devs: list[str]) -> None:
    metrics = [c for c in ["tps", "rkB_s", "wkB_s"] if c in ddf.columns]
    sel = st.multiselect("Metrics", metrics, default=metrics)
    if not sel_devs or not sel:
        return
    series: dict[str, pd.Series] = {}
    for m in sel:
        for dev in sel_devs:
            key = f"{m}[{dev}]"
            series[key] = ddf.loc[ddf["dev"] == dev].set_index("timestamp")[m]
    if series:
        st.line_chart(pd.concat(series, axis=1).sort_index())

