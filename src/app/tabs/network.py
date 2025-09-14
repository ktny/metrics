from __future__ import annotations

from typing import Literal

import pandas as pd
import streamlit as st

from src.app.parsers.network import parse_net_csv, parse_net_json
from src.app.services.sadf import convert_with_sadf


def load_net_df(path: str, prefer: Literal["auto", "12", "11"]) -> tuple[pd.DataFrame, str]:
    fmt, text = convert_with_sadf(path, ("-n", "DEV"), prefer)
    if fmt == "json":
        return parse_net_json(text), "json"
    else:
        return parse_net_csv(text), "csv"


def render(path: str, prefer: Literal["auto", "12", "11"]) -> None:
    try:
        ndf, nfmt = load_net_df(path, prefer)
        st.caption(f"Parsed as {nfmt}")
    except Exception as e:  # pragma: no cover - UI feedback
        st.error(f"Network read failed: {e}")
        return

    if ndf is not None and not ndf.empty:
        ifaces = (
            sorted(pd.Series(ndf["iface"]).dropna().astype(str).unique().tolist())
            if "iface" in ndf.columns
            else []
        )
        sel_ifaces = st.multiselect("Interfaces", ifaces, default=ifaces[:2])
        net_metrics_all = [
            c for c in ["rxkB_s", "txkB_s", "rxpck_s", "txpck_s", "ifutil_pct"] if c in ndf.columns
        ]
        net_metrics = st.multiselect(
            "Metrics", net_metrics_all, default=[m for m in ["rxkB_s", "txkB_s"] if m in net_metrics_all]
        )
        if sel_ifaces and net_metrics:
            series: dict[str, pd.Series] = {}
            for m in net_metrics:
                for iface in sel_ifaces:
                    key = f"{m}[{iface}]"
                    series[key] = ndf.loc[ndf["iface"] == iface].set_index("timestamp")[m]
            if series:
                chart_df = pd.concat(series, axis=1).sort_index()
                st.line_chart(chart_df)
        st.download_button(
            "Download Network CSV",
            ndf.to_csv(index=False).encode("utf-8"),
            file_name="network.csv",
            mime="text/csv",
        )

