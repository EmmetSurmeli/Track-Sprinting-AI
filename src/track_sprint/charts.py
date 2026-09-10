"""Plots share exact decoded source-frame IDs with the video review."""
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .metrics import METRICS


def motion_figure(summary, series, sides, selected_frame, show_raw=False):
    names = list(METRICS)
    fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.08,
                        subplot_titles=[METRICS[n] + " (°)" for n in names])
    colors = {"left": "#2FCCE5", "right": "#FF9E5B"}
    for row, name in enumerate(names, 1):
        for side in sides:
            values = series[side][name]
            if show_raw:
                fig.add_trace(go.Scatter(x=summary["frames"], y=values["raw"], mode="lines",
                    line={"color": colors[side], "width": 1}, opacity=0.3, name=f"{side} raw",
                    legendgroup=side, showlegend=False, connectgaps=False), row=row, col=1)
            fig.add_trace(go.Scatter(x=summary["frames"], y=values["smoothed"], mode="lines",
                line={"color": colors[side], "width": 2}, name=side.title(), legendgroup=side,
                showlegend=row == 1, connectgaps=False,
                hovertemplate="Frame %{x}<br>%{y:.1f}°<extra>" + side.title() + "</extra>"), row=row, col=1)
        fig.add_vline(x=selected_frame, line_width=1, line_dash="dot", line_color="#B8F35A", row=row, col=1)
        fig.add_hline(y=0, line_width=1, line_color="#34414A", row=row, col=1)
    fig.update_layout(height=740, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#BBC8CB", "size": 12}, margin={"l": 12, "r": 12, "t": 40, "b": 30},
        hovermode="x unified", legend={"orientation": "h", "y": 1.08},
        uirevision=summary["analysis_id"])
    fig.update_xaxes(title_text="Decoded source frame", row=4, col=1)
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="#26323C", zeroline=False)
    return fig
