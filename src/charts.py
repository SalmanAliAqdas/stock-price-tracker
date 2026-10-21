"""Plotly figures with explicit units and one consistent visual language."""

from __future__ import annotations

from html import escape

import pandas as pd
import plotly.graph_objects as go

COLORS = ["#5EE0B5", "#7DA9FF", "#BEA0FF", "#F5C77E", "#FF91B2",
          "#71DAEF", "#E0DC8D", "#C0CBE0", "#FFAD7D", "#BCDA92"]
GREEN = COLORS[0]
RED = "#FF7C91"


def _style(figure: go.Figure, ylabel: str, height: int = 400) -> go.Figure:
    figure.update_layout(
        template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)", height=height,
        font=dict(family="Arial, sans-serif", color="#B7C6DB", size=12),
        margin=dict(l=8, r=18, t=28, b=10), hovermode="x unified",
        autosize=True,
        legend=dict(orientation="h", y=-0.18, x=0, xanchor="left", yanchor="top"),
        xaxis=dict(showgrid=False, title=None, zeroline=False),
        yaxis=dict(title=ylabel, gridcolor="#1D2B40", zeroline=False, side="right"),
    )
    return figure


def price_chart(frame: pd.DataFrame, currency: str, averages: bool = False, adjusted: bool = True) -> go.Figure:
    figure = go.Figure()
    label = "Adjusted close" if adjusted else "Unadjusted close"
    figure.add_trace(go.Scatter(
        x=frame.index, y=frame["Adj Close" if adjusted else "Close"], name=label,
        mode="lines", line=dict(color=GREEN, width=2.6),
        fill="tozeroy", fillcolor="rgba(94,224,181,0.055)",
        hovertemplate="%{y:,.2f}<extra>" + label + "</extra>",
    ))
    if averages:
        for column, color in (("SMA 20", COLORS[1]), ("SMA 50", COLORS[3])):
            if column in frame and frame[column].notna().any():
                figure.add_trace(go.Scatter(x=frame.index, y=frame[column], name=column, mode="lines", line=dict(color=color, width=1.5)))
    return _style(figure, escape(currency))


def candlestick_chart(frame: pd.DataFrame, currency: str) -> go.Figure:
    figure = go.Figure(go.Candlestick(
        x=frame.index, open=frame["Open"], high=frame["High"],
        low=frame["Low"], close=frame["Close"], name="Daily OHLC",
        increasing_line_color=GREEN, decreasing_line_color=RED,
        increasing_fillcolor=GREEN, decreasing_fillcolor=RED,
    ))
    figure.update_layout(xaxis_rangeslider_visible=False)
    return _style(figure, f"Unadjusted · {escape(currency)}")


def volume_chart(frame: pd.DataFrame) -> go.Figure:
    colors = [GREEN if close >= opening else RED for close, opening in zip(frame["Close"], frame["Open"])]
    figure = go.Figure(go.Bar(x=frame.index, y=frame["Volume"], marker_color=colors, name="Volume", opacity=0.75))
    return _style(figure, "Shares traded", 230)


def rsi_chart(values: pd.Series) -> go.Figure:
    figure = go.Figure(go.Scatter(x=values.index, y=values, name="RSI 14", line=dict(color=COLORS[2], width=2)))
    figure.add_hrect(y0=30, y1=70, fillcolor="rgba(190,160,255,0.045)", line_width=0)
    for level in (30, 70):
        figure.add_hline(y=level, line_dash="dot", line_color="#60708B", annotation_text=str(level))
    _style(figure, "RSI · 0–100", 250)
    figure.update_yaxes(range=[0, 100])
    return figure


def comparison_chart(normalized: pd.DataFrame) -> go.Figure:
    figure = go.Figure()
    for index, symbol in enumerate(normalized.columns):
        figure.add_trace(go.Scatter(
            x=normalized.index, y=normalized[symbol], name=escape(symbol),
            mode="lines", line=dict(color=COLORS[index % len(COLORS)], width=2.4),
            hovertemplate="%{y:+.2f}%<extra>" + escape(symbol) + "</extra>",
        ))
    figure.add_hline(y=0, line_color="#46546B", line_dash="dot")
    return _style(figure, "Adjusted return (%)", 440)
