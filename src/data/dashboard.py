from __future__ import annotations

from pathlib import Path
from typing import Any
import inspect
import math
import re

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st


st.set_page_config(page_title="GenPop", layout="wide")

st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1.15rem;
        padding-bottom: 1rem;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
    }

    .stTabs [data-baseweb="tab"] {
        padding-left: 0.75rem;
        padding-right: 0.75rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


WORKBOOK_NAME = "Full.xlsx"
ID_COLUMNS = ["Data", "Decile or Quintile", "Year", "Sex"]
CATEGORY_COLUMNS = ["Data", "Sex", "Decile or Quintile"]
AGGREGATIONS = ["mean", "sum", "median", "min", "max", "count"]
CHART_MODES = ["Combo", "Lines only", "Bars only"]
LINE_STYLES = ["Lines + Markers", "Lines", "Markers"]
SPLIT_ACTIONS = ["All values", "Keep selected", "Exclude selected"]
NO_SPLIT = "(none)"
SEX_PANELS = [("M", "Male"), ("F", "Female")]
TRACE_COLORS = [
    "#636EFA",
    "#EF553B",
    "#00CC96",
    "#AB63FA",
    "#FFA15A",
    "#19D3F3",
    "#FF6692",
    "#B6E880",
    "#FF97FF",
    "#FECB52",
]


def safe_key(value: Any) -> str:
    text = re.sub(r"[^a-zA-Z0-9_]+", "_", str(value))
    return re.sub(r"_+", "_", text).strip("_").lower() or "value"


def natural_sort_key(value: Any) -> tuple[Any, ...]:
    text = "" if pd.isna(value) else str(value)
    parts = re.split(r"(\d+(?:\.\d+)?)", text)
    key: list[Any] = []
    for part in parts:
        if not part:
            continue
        try:
            key.append((0, float(part)))
        except ValueError:
            key.append((1, part.lower()))
    return tuple(key)


def clean_category_value(value: Any) -> str:
    if pd.isna(value):
        return "(Missing)"
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    if isinstance(value, (float, np.floating)) and float(value).is_integer():
        return str(int(value))
    return str(value).strip()


def ordered_values(series: pd.Series) -> list[Any]:
    values = series.dropna().unique().tolist()
    return sorted(values, key=natural_sort_key)


def pretty_field(field: str) -> str:
    return {
        "Decile or Quintile": "Decile / Quintile",
        "Age": "Age",
        "Year": "Year",
        "Data": "Data",
        "Sex": "Sex",
    }.get(field, field)


def pretty_aggregation(aggregation: str) -> str:
    return "count" if aggregation == "count" else f"{aggregation} value"


def format_age_value(value: Any) -> str:
    try:
        age = int(value)
    except (TypeError, ValueError):
        return str(value)
    return "110+" if age >= 110 else str(age)


def format_split_value(field: str, value: Any) -> str:
    if field == "Age":
        return format_age_value(value)
    if field == "Year":
        try:
            return str(int(value))
        except (TypeError, ValueError):
            return str(value)
    return clean_category_value(value)


def parse_age_column(column: Any) -> int | None:
    text = str(column).strip()
    if re.fullmatch(r"\d+", text):
        return int(text)
    match = re.fullmatch(r"(\d+)\+", text)
    if match:
        return int(match.group(1))
    return None


def workbook_path() -> Path:
    source_dir = Path(__file__).resolve().parent
    candidate_dirs = [
        source_dir.parents[1] / "data" / "external",
        Path.cwd() / "data" / "external",
        source_dir,
    ]

    for folder in candidate_dirs:
        direct = folder / WORKBOOK_NAME
        if direct.exists():
            return direct

    for folder in candidate_dirs:
        if folder.exists():
            matches = [path for path in folder.glob("*.xlsx") if path.name.lower() == WORKBOOK_NAME.lower()]
            if matches:
                return matches[0]

    return candidate_dirs[0] / WORKBOOK_NAME


@st.cache_data(show_spinner="Reading Full.xlsx...")
def load_workbook(path_text: str) -> tuple[pd.DataFrame, dict[str, Any]]:
    raw = pd.read_excel(path_text, sheet_name=0, dtype=object, engine="openpyxl")
    raw.columns = [str(col).strip() for col in raw.columns]

    missing = [col for col in ID_COLUMNS if col not in raw.columns]
    if missing:
        raise ValueError(f"Missing required column(s): {', '.join(missing)}")

    age_lookup = {
        col: age
        for col in raw.columns
        if (age := parse_age_column(col)) is not None
    }
    if not age_lookup:
        raise ValueError("No age columns were found. Expected headers like 0, 1, 2, ..., 110+.")

    raw = raw.copy()
    raw["_source_row"] = np.arange(len(raw))

    long_df = raw.melt(
        id_vars=ID_COLUMNS + ["_source_row"],
        value_vars=list(age_lookup.keys()),
        var_name="Age Label",
        value_name="Value",
    )

    for col in CATEGORY_COLUMNS:
        long_df[col] = long_df[col].map(clean_category_value)

    long_df["Age"] = long_df["Age Label"].map(age_lookup)
    long_df["Age Label"] = long_df["Age"].map(format_age_value)
    long_df["Year"] = pd.to_numeric(long_df["Year"], errors="coerce")
    long_df["Value"] = pd.to_numeric(long_df["Value"], errors="coerce")
    long_df = long_df.dropna(subset=["Year", "Age", "Value"]).copy()
    long_df["Year"] = long_df["Year"].astype(int)
    long_df["Age"] = long_df["Age"].astype(int)

    long_df = long_df.sort_values(["Data", "Sex", "Decile or Quintile", "Year", "Age"]).reset_index(drop=True)

    metadata = {
        "source_rows": int(len(raw)),
        "value_rows": int(len(long_df)),
        "data_options": ordered_values(long_df["Data"]),
        "sex_options": ordered_values(long_df["Sex"]),
        "decile_options": ordered_values(long_df["Decile or Quintile"]),
        "year_min": int(long_df["Year"].min()),
        "year_max": int(long_df["Year"].max()),
        "age_min": int(long_df["Age"].min()),
        "age_max": int(long_df["Age"].max()),
    }
    return long_df, metadata


def ensure_list_state(key: str, options: list[Any], default_values: list[Any]) -> None:
    option_set = set(options)
    if key not in st.session_state:
        st.session_state[key] = [value for value in default_values if value in option_set]
        return
    st.session_state[key] = [value for value in st.session_state[key] if value in option_set]


def ensure_range_state(key: str, lo: int, hi: int) -> None:
    if key not in st.session_state:
        st.session_state[key] = (lo, hi)
        return

    current = st.session_state[key]
    if not isinstance(current, (tuple, list)) or len(current) != 2:
        st.session_state[key] = (lo, hi)
        return

    left = max(lo, min(int(current[0]), hi))
    right = max(lo, min(int(current[1]), hi))
    st.session_state[key] = (min(left, right), max(left, right))


def ensure_select_state(key: str, options: list[Any], default_value: Any) -> None:
    if not options:
        return
    if key not in st.session_state or st.session_state[key] not in options:
        st.session_state[key] = default_value if default_value in options else options[0]


def reset_filter_state(prefix: str, metadata: dict[str, Any]) -> None:
    st.session_state[f"{prefix}_filter_data"] = list(metadata["data_options"])
    st.session_state[f"{prefix}_filter_sex"] = list(metadata["sex_options"])
    st.session_state[f"{prefix}_filter_decile"] = list(metadata["decile_options"])
    st.session_state[f"{prefix}_filter_age"] = (metadata["age_min"], metadata["age_max"])
    st.session_state[f"{prefix}_filter_year"] = (metadata["year_min"], metadata["year_max"])


def render_filter_panel(df: pd.DataFrame, metadata: dict[str, Any], prefix: str) -> tuple[pd.DataFrame, dict[str, Any]]:
    with st.container(border=True):
        st.markdown("**Filters**")

        if st.button("Reset filters", key=f"{prefix}_reset_filters"):
            reset_filter_state(prefix, metadata)
            st.rerun()

        data_key = f"{prefix}_filter_data"
        sex_key = f"{prefix}_filter_sex"
        decile_key = f"{prefix}_filter_decile"
        age_key = f"{prefix}_filter_age"
        year_key = f"{prefix}_filter_year"

        ensure_list_state(data_key, metadata["data_options"], metadata["data_options"])
        ensure_list_state(sex_key, metadata["sex_options"], metadata["sex_options"])
        ensure_list_state(decile_key, metadata["decile_options"], metadata["decile_options"])
        ensure_range_state(age_key, metadata["age_min"], metadata["age_max"])
        ensure_range_state(year_key, metadata["year_min"], metadata["year_max"])

        selected_data = st.multiselect("Data", metadata["data_options"], key=data_key)
        selected_sex = st.multiselect("Sex", metadata["sex_options"], key=sex_key)
        selected_decile = st.multiselect(
            "Decile / Quintile",
            metadata["decile_options"],
            key=decile_key,
        )
        age_range = st.slider(
            "Age range",
            min_value=metadata["age_min"],
            max_value=metadata["age_max"],
            key=age_key,
            step=1,
        )
        year_range = st.slider(
            "Year range",
            min_value=metadata["year_min"],
            max_value=metadata["year_max"],
            key=year_key,
            step=1,
        )

    mask = (
        df["Data"].isin(selected_data)
        & df["Sex"].isin(selected_sex)
        & df["Decile or Quintile"].isin(selected_decile)
        & df["Age"].between(int(age_range[0]), int(age_range[1]), inclusive="both")
        & df["Year"].between(int(year_range[0]), int(year_range[1]), inclusive="both")
    )
    filtered = df.loc[mask].copy()

    st.caption(
        f"{filtered['_source_row'].nunique():,} workbook rows  |  "
        f"{len(filtered):,} plotted values"
    )

    return filtered, {
        "age_range": (int(age_range[0]), int(age_range[1])),
        "year_range": (int(year_range[0]), int(year_range[1])),
    }


def split_candidates_for_axis(axis_field: str) -> list[str]:
    if axis_field == "Age":
        return ["Data", "Decile or Quintile", "Year"]
    return ["Data", "Decile or Quintile", "Age"]


def split_value_options(df: pd.DataFrame, field: str) -> list[Any]:
    if field not in df.columns or df.empty:
        return []
    return ordered_values(df[field])


def render_split_controls(
    df: pd.DataFrame,
    prefix: str,
    split_number: int,
    split_field: str | None,
) -> dict[str, Any]:
    if not split_field:
        return {"field": None, "action": "All values", "values": []}

    action_key = f"{prefix}_split{split_number}_action_{safe_key(split_field)}"
    ensure_select_state(action_key, SPLIT_ACTIONS, "All values")
    action = st.selectbox(
        f"Split {split_number} filter",
        SPLIT_ACTIONS,
        key=action_key,
    )

    selected_values: list[Any] = []
    if action != "All values":
        options = split_value_options(df, split_field)
        value_key = f"{prefix}_split{split_number}_values_{safe_key(split_field)}"
        default_values = options[:12] if len(options) > 12 else options
        ensure_list_state(value_key, options, default_values)
        selected_values = st.multiselect(
            f"Split {split_number} values",
            options,
            key=value_key,
            format_func=lambda value, field=split_field: format_split_value(field, value),
        )

    return {"field": split_field, "action": action, "values": selected_values}


def render_settings_panel(
    filtered_df: pd.DataFrame,
    prefix: str,
    axis_field: str,
) -> dict[str, Any]:
    with st.container(border=True):
        st.markdown("**Plot settings**")

        max_bin = 10
        bin_size = st.select_slider(
            "Bin size",
            options=list(range(1, max_bin + 1)),
            value=1,
            key=f"{prefix}_bin_size",
        )

        chart_mode = st.selectbox(
            "Chart mode",
            CHART_MODES,
            key=f"{prefix}_chart_mode",
        )
        line_mode = st.selectbox(
            "Line style",
            LINE_STYLES,
            key=f"{prefix}_line_mode",
            disabled=chart_mode == "Bars only",
        )
        height = st.slider(
            "Chart height",
            360,
            900,
            540,
            10,
            key=f"{prefix}_height",
        )

        bar_aggregation = st.selectbox(
            "Bar aggregation",
            AGGREGATIONS,
            index=AGGREGATIONS.index("mean"),
            key=f"{prefix}_bar_aggregation",
            disabled=chart_mode == "Lines only",
        )
        line_aggregation = st.selectbox(
            "Line aggregation",
            AGGREGATIONS,
            index=AGGREGATIONS.index("mean"),
            key=f"{prefix}_line_aggregation",
            disabled=chart_mode == "Bars only",
        )

        split_candidates = split_candidates_for_axis(axis_field)
        split1_options = [NO_SPLIT] + split_candidates
        split1_key = f"{prefix}_split1"
        ensure_select_state(split1_key, split1_options, "Data")
        split1_raw = st.selectbox("Line split 1", split1_options, key=split1_key)
        split1 = None if split1_raw == NO_SPLIT else split1_raw

        split2_options = [NO_SPLIT] + [field for field in split_candidates if field != split1]
        split2_key = f"{prefix}_split2"
        ensure_select_state(split2_key, split2_options, NO_SPLIT)
        split2_raw = st.selectbox("Line split 2", split2_options, key=split2_key)
        split2 = None if split2_raw == NO_SPLIT else split2_raw

        split_rules = [
            render_split_controls(filtered_df, prefix, 1, split1),
            render_split_controls(filtered_df, prefix, 2, split2),
        ]

        top_n_traces = st.slider(
            "Max line traces",
            1,
            80,
            24,
            1,
            key=f"{prefix}_top_n_traces",
            disabled=chart_mode == "Bars only",
        )
        y_scale = st.selectbox(
            "Y scale",
            ["Linear", "Log"],
            key=f"{prefix}_y_scale",
        )

        apply_chart = st.button(
            "Apply chart",
            type="primary",
            key=f"{prefix}_apply_chart",
        )

    current_payload = {
        "axis_field": axis_field,
        "bin_size": int(bin_size),
        "chart_mode": chart_mode,
        "line_mode": line_mode,
        "height": int(height),
        "bar_aggregation": bar_aggregation,
        "line_aggregation": line_aggregation,
        "split_rules": split_rules,
        "top_n_traces": int(top_n_traces),
        "y_scale": y_scale,
    }
    state_key = f"{prefix}_chart_payload"
    if apply_chart or state_key not in st.session_state:
        st.session_state[state_key] = current_payload
    return st.session_state[state_key]


def bin_axis_label(start: int, end: int, axis_field: str) -> str:
    if start == end:
        return format_age_value(start) if axis_field == "Age" else str(start)
    if axis_field == "Age":
        return f"{format_age_value(start)}-{format_age_value(end)}"
    return f"{start}-{end}"


def add_axis_bins(
    df: pd.DataFrame,
    axis_field: str,
    bin_size: int,
    axis_range: tuple[int, int],
) -> pd.DataFrame:
    out = df.copy()
    source = out[axis_field].astype(int)
    lo, hi = axis_range
    width = max(int(bin_size), 1)

    if width <= 1:
        out["_axis_sort"] = source
        if axis_field == "Age":
            out["_axis_value"] = source.map(format_age_value)
        else:
            out["_axis_value"] = source.astype(str)
        return out

    starts = (np.floor((source - lo) / width).astype(int) * width) + lo
    ends = (starts + width - 1).clip(upper=hi)
    out["_axis_sort"] = starts
    out["_axis_value"] = [
        bin_axis_label(int(start), int(end), axis_field)
        for start, end in zip(starts, ends, strict=False)
    ]
    return out


def apply_split_rules(df: pd.DataFrame, split_rules: list[dict[str, Any]]) -> pd.DataFrame:
    out = df
    for rule in split_rules:
        field = rule.get("field")
        action = rule.get("action")
        values = rule.get("values") or []
        if not field or action == "All values" or field not in out.columns:
            continue
        if action == "Keep selected":
            out = out[out[field].isin(values)]
        elif action == "Exclude selected":
            out = out[~out[field].isin(values)]
    return out


def aggregate_values(df: pd.DataFrame, group_cols: list[str], aggregation: str) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=group_cols + ["_value"])
    grouped = df.groupby(group_cols, dropna=False, observed=True)
    if aggregation == "count":
        return grouped.size().reset_index(name="_value")
    return grouped["Value"].agg(aggregation).reset_index(name="_value")


def trace_label_from_row(row: pd.Series, split_fields: list[str]) -> str:
    if not split_fields:
        return "Line"
    pieces = [
        f"{pretty_field(field)}={format_split_value(field, row[field])}"
        for field in split_fields
    ]
    return " | ".join(pieces)


def summarize_for_plot(
    filtered_df: pd.DataFrame,
    payload: dict[str, Any],
    filter_payload: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    axis_field = payload["axis_field"]
    axis_range = filter_payload["age_range"] if axis_field == "Age" else filter_payload["year_range"]
    axis_df = add_axis_bins(filtered_df, axis_field, payload["bin_size"], axis_range)

    bar_group_cols = ["_axis_value", "_axis_sort"]
    bars = aggregate_values(axis_df, bar_group_cols, payload["bar_aggregation"])
    bars = bars.sort_values(["_axis_sort", "_axis_value"]).reset_index(drop=True)

    split_rules = payload["split_rules"]
    split_fields = [
        rule["field"]
        for rule in split_rules
        if rule.get("field") and rule["field"] in axis_df.columns
    ]
    line_base = apply_split_rules(axis_df, split_rules)
    line_group_cols = ["_axis_value", "_axis_sort"] + split_fields
    lines = aggregate_values(line_base, line_group_cols, payload["line_aggregation"])

    if not lines.empty:
        lines["_trace_label"] = lines.apply(lambda row: trace_label_from_row(row, split_fields), axis=1)
        support = lines.groupby("_trace_label", dropna=False)["_value"].apply(lambda col: col.abs().sum())
        keep_traces = support.sort_values(ascending=False).head(payload["top_n_traces"]).index
        lines = lines[lines["_trace_label"].isin(keep_traces)].copy()
        lines = lines.sort_values(["_axis_sort", "_axis_value", "_trace_label"]).reset_index(drop=True)
    else:
        lines["_trace_label"] = pd.Series(dtype=object)

    axis_frames = []
    if not bars.empty:
        axis_frames.append(bars[["_axis_value", "_axis_sort"]])
    if not lines.empty:
        axis_frames.append(lines[["_axis_value", "_axis_sort"]])
    if axis_frames:
        axis_order = (
            pd.concat(axis_frames, ignore_index=True)
            .drop_duplicates()
            .sort_values(["_axis_sort", "_axis_value"])["_axis_value"]
            .astype(str)
            .tolist()
        )
    else:
        axis_order = []

    return bars, lines, axis_order


def visible_output(payload: dict[str, Any], bars: pd.DataFrame, lines: pd.DataFrame) -> tuple[bool, bool]:
    chart_mode = payload["chart_mode"]
    show_bars = chart_mode in {"Combo", "Bars only"} and not bars.empty
    show_lines = chart_mode in {"Combo", "Lines only"} and not lines.empty
    return show_bars, show_lines


def combined_axis_order(panel_outputs: list[dict[str, Any]]) -> list[str]:
    axis_frames: list[pd.DataFrame] = []
    for panel in panel_outputs:
        for key in ("bars", "lines"):
            frame = panel[key]
            if not frame.empty:
                axis_frames.append(frame[["_axis_value", "_axis_sort"]])
    if not axis_frames:
        return []
    return (
        pd.concat(axis_frames, ignore_index=True)
        .drop_duplicates()
        .sort_values(["_axis_sort", "_axis_value"])["_axis_value"]
        .astype(str)
        .tolist()
    )


def trace_color_map(panel_outputs: list[dict[str, Any]], bar_label: str) -> dict[str, str]:
    names: list[str] = []
    for panel in panel_outputs:
        if panel["show_bars"]:
            names.append(f"Bars: {bar_label}")
        if panel["show_lines"]:
            names.extend(panel["lines"]["_trace_label"].dropna().astype(str).unique().tolist())

    unique_names = list(dict.fromkeys(names))
    return {
        name: TRACE_COLORS[index % len(TRACE_COLORS)]
        for index, name in enumerate(unique_names)
    }


def make_sex_split_figure(panel_outputs: list[dict[str, Any]], payload: dict[str, Any]) -> go.Figure:
    chart_mode = payload["chart_mode"]
    use_secondary = chart_mode == "Combo"
    axis_title = pretty_field(payload["axis_field"])
    bar_label = pretty_aggregation(payload["bar_aggregation"])
    line_label = pretty_aggregation(payload["line_aggregation"])
    axis_order = combined_axis_order(panel_outputs)
    colors = trace_color_map(panel_outputs, bar_label)

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=False,
        vertical_spacing=0.12,
        specs=[[{"secondary_y": use_secondary}], [{"secondary_y": use_secondary}]],
        subplot_titles=[panel["label"] for panel in panel_outputs],
    )

    legend_names: set[str] = set()

    def show_legend_once(name: str) -> bool:
        if name in legend_names:
            return False
        legend_names.add(name)
        return True

    for row, panel in enumerate(panel_outputs, start=1):
        bars = panel["bars"]
        lines = panel["lines"]
        show_bars, show_lines = panel["show_bars"], panel["show_lines"]

        if show_bars:
            name = f"Bars: {bar_label}"
            color = colors.get(name)
            fig.add_trace(
                go.Bar(
                    x=bars["_axis_value"].astype(str),
                    y=bars["_value"],
                    name=name,
                    legendgroup=name,
                    showlegend=show_legend_once(name),
                    marker_color=color,
                    hovertemplate=(
                        f"{panel['label']}<br>{axis_title}: %{{x}}<br>"
                        f"{bar_label}: %{{y:,.6g}}<extra></extra>"
                    ),
                ),
                row=row,
                col=1,
                secondary_y=False,
            )

        if show_lines:
            mode = {
                "Lines + Markers": "lines+markers",
                "Lines": "lines",
                "Markers": "markers",
            }.get(payload["line_mode"], "lines+markers")
            for trace_name in lines["_trace_label"].dropna().astype(str).unique().tolist():
                trace_df = lines[lines["_trace_label"].astype(str) == trace_name].sort_values(["_axis_sort", "_axis_value"])
                color = colors.get(trace_name)
                fig.add_trace(
                    go.Scatter(
                        x=trace_df["_axis_value"].astype(str),
                        y=trace_df["_value"],
                        mode=mode,
                        name=trace_name,
                        legendgroup=trace_name,
                        showlegend=show_legend_once(trace_name),
                        line=dict(color=color),
                        marker=dict(color=color),
                        hovertemplate=(
                            f"{panel['label']}<br>{axis_title}: %{{x}}<br>"
                            f"{trace_name}: %{{y:,.6g}}<extra></extra>"
                        ),
                    ),
                    row=row,
                    col=1,
                    secondary_y=use_secondary,
                )

        if not show_bars and not show_lines:
            fig.add_annotation(
                text=f"No {panel['label'].lower()} data after filters",
                x=0.5,
                y=0.76 if row == 1 else 0.24,
                xref="paper",
                yref="paper",
                showarrow=False,
                font=dict(color="#6b7280"),
            )

        fig.update_xaxes(
            title_text=axis_title,
            categoryorder="array",
            categoryarray=axis_order,
            tickangle=-35,
            row=row,
            col=1,
        )

        if use_secondary:
            fig.update_yaxes(title_text=f"Bars ({bar_label})", secondary_y=False, row=row, col=1, tickformat=",.5g")
            fig.update_yaxes(title_text=f"Lines ({line_label})", secondary_y=True, row=row, col=1, tickformat=",.5g")
        elif chart_mode == "Bars only":
            fig.update_yaxes(title_text=bar_label, row=row, col=1, tickformat=",.5g")
        else:
            fig.update_yaxes(title_text=line_label, row=row, col=1, tickformat=",.5g")

    if payload["y_scale"] == "Log":
        fig.update_yaxes(type="log")

    fig.update_layout(
        hovermode="x unified",
        barmode="group",
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0),
        height=max(int(payload["height"]) * 2, 620),
        margin=dict(l=20, r=20, t=65, b=25),
    )

    return fig


def csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def stretch_kwargs(streamlit_func: Any) -> dict[str, Any]:
    try:
        parameters = inspect.signature(streamlit_func).parameters
    except (TypeError, ValueError):
        return {"use_container_width": True}
    if "width" in parameters:
        return {"width": "stretch"}
    return {"use_container_width": True}


def render_plot_area(
    filtered_df: pd.DataFrame,
    payload: dict[str, Any],
    filter_payload: dict[str, Any],
    prefix: str,
) -> None:
    if filtered_df.empty:
        st.info("No values match the current filters.")
        return

    panel_outputs: list[dict[str, Any]] = []
    for sex_value, sex_label in SEX_PANELS:
        sex_df = filtered_df[filtered_df["Sex"] == sex_value]
        bars, lines, axis_order = summarize_for_plot(sex_df, payload, filter_payload)
        show_bars, show_lines = visible_output(payload, bars, lines)
        panel_outputs.append(
            {
                "sex": sex_value,
                "label": sex_label,
                "bars": bars,
                "lines": lines,
                "axis_order": axis_order,
                "show_bars": show_bars,
                "show_lines": show_lines,
            }
        )

    if not any(panel["show_bars"] or panel["show_lines"] for panel in panel_outputs):
        st.warning("The selected chart mode has no visible output for the current settings.")
        return

    fig = make_sex_split_figure(panel_outputs, payload)
    st.plotly_chart(fig, **stretch_kwargs(st.plotly_chart))

    with st.expander("Aggregated data", expanded=False):
        bar_frames = []
        line_frames = []
        for panel in panel_outputs:
            if panel["show_bars"]:
                bars = panel["bars"].copy()
                bars.insert(0, "Sex", panel["label"])
                bar_frames.append(bars)
            if panel["show_lines"]:
                lines = panel["lines"].copy()
                lines.insert(0, "Sex", panel["label"])
                line_frames.append(lines)

        if bar_frames:
            bars_out = pd.concat(bar_frames, ignore_index=True)
            st.markdown("**Bars**")
            st.dataframe(bars_out, hide_index=True, **stretch_kwargs(st.dataframe))
            st.download_button(
                "Download bars (.csv)",
                data=csv_bytes(bars_out),
                file_name=f"{prefix}_bars.csv",
                mime="text/csv",
                key=f"{prefix}_download_bars",
            )
        if line_frames:
            lines_out = pd.concat(line_frames, ignore_index=True)
            st.markdown("**Lines**")
            st.dataframe(lines_out, hide_index=True, **stretch_kwargs(st.dataframe))
            st.download_button(
                "Download lines (.csv)",
                data=csv_bytes(lines_out),
                file_name=f"{prefix}_lines.csv",
                mime="text/csv",
                key=f"{prefix}_download_lines",
            )


def render_plot_tab(
    df: pd.DataFrame,
    metadata: dict[str, Any],
    axis_field: str,
    prefix: str,
) -> None:
    filter_col, plot_col, settings_col = st.columns([1.35, 4.8, 1.8], gap="large")

    with filter_col:
        filtered_df, filter_payload = render_filter_panel(df, metadata, prefix)

    with settings_col:
        chart_payload = render_settings_panel(filtered_df, prefix, axis_field)

    with plot_col:
        render_plot_area(filtered_df, chart_payload, filter_payload, prefix)


def main() -> None:
    path = workbook_path()
    st.markdown("<h2 style='font-size:1.45rem; margin:0.5 0.5 0.15rem 0;'>Full.xlsx Plotter</h2>", unsafe_allow_html=True)

    if not path.exists():
        st.error(f"{WORKBOOK_NAME} was not found in {path.parent}.")
        return

    try:
        df, metadata = load_workbook(str(path))
    except Exception as exc:
        st.error(f"Could not read {path.name}: {exc}")
        return

    st.caption(
        f"{path.name}  |  {metadata['source_rows']:,} workbook rows  |  "
        f"{metadata['value_rows']:,} age values"
    )

    tab_age, tab_year = st.tabs(["By Age", "By Year"])

    with tab_age:
        render_plot_tab(df, metadata, axis_field="Age", prefix="age")

    with tab_year:
        render_plot_tab(df, metadata, axis_field="Year", prefix="year")


if __name__ == "__main__":
    main()
