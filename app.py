import os
import io
import json
import pickle
from groq import Groq
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import date, timedelta
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    RunReportRequest, DateRange, Dimension, Metric,
    FilterExpression, Filter, OrderBy
)
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from googleapiclient.discovery import build

st.set_page_config(page_title="Customer Success Website Analytics Dashboard", layout="wide")

# ── PROPERTY REGISTRY ────────────────────────────────────────────────────────
# Name, GA4 ID, domain — GSC URL is auto-matched from your verified sites list
PORTFOLIO = [
    {"name": "The Serenite Collection", "ga4_id": "509737908", "domain": "theserenite.com",      "keywords": ["serenite","theserenite","the serenite","serenite collection","tallman hotel","tallman","narrow gauge inn","amador hotel","groveland hotel","blue wing saloon","shaver lake village hotel"]},
    {"name": "Shooting Star Lodge",     "ga4_id": "480184188", "domain": "shootingstarlodge.com","keywords": ["shooting star lodge","shooting star","shootingstarlodge"]},
    {"name": "Luffu Club",              "ga4_id": "513226281", "domain": "luffuclub.com",         "keywords": ["luffu","luffu club","luffuclub"]},
    {"name": "Yo1 Luxury Resorts",      "ga4_id": "342014736", "domain": "yo1.com",              "keywords": ["yo1","yo1 luxury","yo1 resorts","yo1.com"]},
]

# Active property — overridden by sidebar selection
PROPERTY_ID = PORTFOLIO[0]["ga4_id"]
SITE_URL    = ""
SCOPES = [
    "https://www.googleapis.com/auth/analytics.readonly",
    "https://www.googleapis.com/auth/webmasters.readonly"
]

MONTH_LABELS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
YEAR_COLORS  = ["#4C8BF5","#34A853","#FBBC04","#EA4335","#9C27B0"]
SEGMENT_COLORS = {
    "Direct":         "#4C8BF5",
    "Paid Search":    "#EA4335",
    "Paid Social":    "#FBBC04",
    "Organic Social": "#34A853",
    "Referral":       "#9C27B0",
    "Email":          "#00BCD4",
    "Display":        "#FF5722",
    "Unassigned":     "#9E9E9E",
    "Cross-network":  "#795548",
}

# ── AUTH ──────────────────────────────────────────────────────────────────────
def get_credentials():
    """
    Returns Google credentials using service account.
    Priority:
      1. Streamlit Cloud — reads service account JSON from st.secrets
      2. Local — reads from service account JSON file on disk
    Never expires. No browser login required.
    """
    import json

    sa_scopes = [
        "https://www.googleapis.com/auth/analytics.readonly",
        "https://www.googleapis.com/auth/webmasters.readonly",
    ]

    # ── Streamlit Cloud: load from secrets ───────────────────────────────────
    if hasattr(st, "secrets") and "service_account_json" in st.secrets:
        sa_info = json.loads(st.secrets["service_account_json"])
        return service_account.Credentials.from_service_account_info(
            sa_info, scopes=sa_scopes
        )

    # ── Local: load from service account JSON file ───────────────────────────
    sa_file = "cs-analytics-link-b5e07310a9fe.json"
    if os.path.exists(sa_file):
        return service_account.Credentials.from_service_account_file(
            sa_file, scopes=sa_scopes
        )

    # ── Fallback: original OAuth flow (local dev without service account) ────
    creds = None
    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as f:
            creds = pickle.load(f)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.pickle", "wb") as f:
            pickle.dump(creds, f)
    return creds

# ── DATA FUNCTIONS ────────────────────────────────────────────────────────────
def get_ga4_data(start, end):
    creds  = get_credentials()
    client = BetaAnalyticsDataClient(credentials=creds)
    req = RunReportRequest(
        property=f"properties/{PROPERTY_ID}",
        date_ranges=[DateRange(start_date=str(start), end_date=str(end))],
        dimensions=[Dimension(name="sessionDefaultChannelGroup")],
        metrics=[Metric(name="sessions"), Metric(name="engagementRate"), Metric(name="bounceRate")]
    )
    resp = client.run_report(req)
    rows = []
    for row in resp.rows:
        rows.append({
            "channel":    row.dimension_values[0].value,
            "sessions":   int(row.metric_values[0].value),
            "engagement": round(float(row.metric_values[1].value) * 100, 1),
            "bounce":     round(float(row.metric_values[2].value) * 100, 1),
        })
    return pd.DataFrame(rows).sort_values("sessions", ascending=False)

def get_ga4_monthly_yoy():
    creds  = get_credentials()
    client = BetaAnalyticsDataClient(credentials=creds)
    req = RunReportRequest(
        property=f"properties/{PROPERTY_ID}",
        date_ranges=[DateRange(start_date="2022-01-01", end_date="today")],
        dimensions=[Dimension(name="year"), Dimension(name="month")],
        metrics=[Metric(name="sessions")]
    )
    resp = client.run_report(req)
    rows = []
    for row in resp.rows:
        rows.append({
            "year":     int(row.dimension_values[0].value),
            "month":    int(row.dimension_values[1].value),
            "sessions": int(row.metric_values[0].value),
        })
    return pd.DataFrame(rows)

def get_ga4_monthly_yoy_organic():
    creds  = get_credentials()
    client = BetaAnalyticsDataClient(credentials=creds)
    req = RunReportRequest(
        property=f"properties/{PROPERTY_ID}",
        date_ranges=[DateRange(start_date="2022-01-01", end_date="today")],
        dimensions=[Dimension(name="year"), Dimension(name="month"), Dimension(name="sessionDefaultChannelGroup")],
        metrics=[Metric(name="sessions")]
    )
    resp = client.run_report(req)
    rows = []
    for row in resp.rows:
        if row.dimension_values[2].value == "Organic Search":
            rows.append({
                "year":     int(row.dimension_values[0].value),
                "month":    int(row.dimension_values[1].value),
                "sessions": int(row.metric_values[0].value),
            })
    return pd.DataFrame(rows)

def get_ga4_segmentation_monthly():
    creds    = get_credentials()
    client   = BetaAnalyticsDataClient(credentials=creds)
    seg_end   = date.today() - timedelta(days=1)
    seg_start = seg_end.replace(day=1) - timedelta(days=365 * 2)
    req = RunReportRequest(
        property=f"properties/{PROPERTY_ID}",
        date_ranges=[DateRange(start_date=str(seg_start), end_date=str(seg_end))],
        dimensions=[Dimension(name="year"), Dimension(name="month"), Dimension(name="sessionDefaultChannelGroup")],
        metrics=[Metric(name="sessions")]
    )
    resp = client.run_report(req)
    rows = []
    for row in resp.rows:
        channel = row.dimension_values[2].value
        if channel != "Organic Search":
            rows.append({
                "year":     int(row.dimension_values[0].value),
                "month":    int(row.dimension_values[1].value),
                "channel":  channel,
                "sessions": int(row.metric_values[0].value),
            })
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["month_label"] = df.apply(
        lambda r: f"{MONTH_LABELS[int(r['month'])-1]} '{str(int(r['year']))[2:]}", axis=1
    )
    df["sort_key"] = df["year"] * 100 + df["month"]
    return df.sort_values("sort_key")

def get_ga4_monthly_engagement(start, end):
    creds  = get_credentials()
    client = BetaAnalyticsDataClient(credentials=creds)
    req = RunReportRequest(
        property=f"properties/{PROPERTY_ID}",
        date_ranges=[DateRange(start_date=str(start), end_date=str(end))],
        dimensions=[Dimension(name="year"), Dimension(name="month")],
        metrics=[Metric(name="engagementRate")],
        dimension_filter=FilterExpression(
            filter=Filter(
                field_name="sessionDefaultChannelGroup",
                string_filter=Filter.StringFilter(value="Organic Search")
            )
        ),
    )
    resp = client.run_report(req)
    rows = []
    for row in resp.rows:
        rows.append({
            "year":            int(row.dimension_values[0].value),
            "month":           int(row.dimension_values[1].value),
            "engagement_rate": round(float(row.metric_values[0].value) * 100, 1),
        })
    df = pd.DataFrame(rows).sort_values(["year", "month"])
    df["label"] = df.apply(lambda r: f"{MONTH_LABELS[int(r['month'])-1]} {int(r['year'])}", axis=1)
    return df

def get_ga4_device(start, end):
    creds  = get_credentials()
    client = BetaAnalyticsDataClient(credentials=creds)
    req = RunReportRequest(
        property=f"properties/{PROPERTY_ID}",
        date_ranges=[DateRange(start_date=str(start), end_date=str(end))],
        dimensions=[Dimension(name="deviceCategory")],
        metrics=[Metric(name="sessions"), Metric(name="engagementRate"), Metric(name="averageSessionDuration")]
    )
    resp = client.run_report(req)
    rows = []
    for row in resp.rows:
        rows.append({
            "Device":                            row.dimension_values[0].value.title(),
            "Sessions":                          int(row.metric_values[0].value),
            "Engagement Rate (%)":               round(float(row.metric_values[1].value) * 100, 1),
            "Average Engagement Time (seconds)": round(float(row.metric_values[2].value), 1),
        })
    return pd.DataFrame(rows).sort_values("Sessions", ascending=False)

def get_ga4_top_cities():
    creds  = get_credentials()
    client = BetaAnalyticsDataClient(credentials=creds)
    start  = date.today() - timedelta(days=180)
    req = RunReportRequest(
        property=f"properties/{PROPERTY_ID}",
        date_ranges=[DateRange(start_date=str(start), end_date="today")],
        dimensions=[Dimension(name="city")],
        metrics=[Metric(name="sessions")],
        dimension_filter=FilterExpression(
            filter=Filter(
                field_name="sessionDefaultChannelGroup",
                string_filter=Filter.StringFilter(value="Organic Search")
            )
        ),
        limit=12,
        order_bys=[{"metric": {"metric_name": "sessions"}, "desc": True}]
    )
    resp = client.run_report(req)
    rows = []
    for row in resp.rows:
        city = row.dimension_values[0].value
        if city not in ("(not set)", ""):
            rows.append({"City": city, "Sessions": int(row.metric_values[0].value)})
    return pd.DataFrame(rows).head(10)

def get_ga4_top_countries():
    creds  = get_credentials()
    client = BetaAnalyticsDataClient(credentials=creds)
    start  = date.today() - timedelta(days=180)
    req = RunReportRequest(
        property=f"properties/{PROPERTY_ID}",
        date_ranges=[DateRange(start_date=str(start), end_date="today")],
        dimensions=[Dimension(name="country")],
        metrics=[Metric(name="sessions")],
        dimension_filter=FilterExpression(
            filter=Filter(
                field_name="sessionDefaultChannelGroup",
                string_filter=Filter.StringFilter(value="Organic Search")
            )
        ),
        limit=10,
        order_bys=[{"metric": {"metric_name": "sessions"}, "desc": True}]
    )
    resp = client.run_report(req)
    rows = []
    for row in resp.rows:
        rows.append({"Country": row.dimension_values[0].value, "Sessions": int(row.metric_values[0].value)})
    return pd.DataFrame(rows).head(10)

def get_gsc_data(start, end):
    creds   = get_credentials()
    service = build("searchconsole", "v1", credentials=creds)
    body = {
        "startDate":  str(start),
        "endDate":    str(end),
        "dimensions": ["query"],
        "rowLimit":   25,
        "orderBy":    [{"fieldName": "clicks", "sortOrder": "DESCENDING"}]
    }
    resp = service.searchanalytics().query(siteUrl=SITE_URL, body=body).execute()
    rows = []
    for row in resp.get("rows", []):
        rows.append({
            "Keyword":     row["keys"][0],
            "Clicks":      int(row["clicks"]),
            "Impressions": int(row["impressions"]),
            "CTR (%)":     round(row["ctr"] * 100, 1),
            "Position":    round(row["position"], 1),
        })
    return pd.DataFrame(rows)

def is_brand(keyword):
    kw = keyword.lower()
    return any(b in kw for b in BRAND_KEYWORDS)

def get_gsc_brand_nonbrand(start, end):
    creds   = get_credentials()
    service = build("searchconsole", "v1", credentials=creds)
    body = {
        "startDate":  str(start),
        "endDate":    str(end),
        "dimensions": ["date", "query"],
        "rowLimit":   25000,
    }
    resp = service.searchanalytics().query(siteUrl=SITE_URL, body=body).execute()
    rows = []
    for row in resp.get("rows", []):
        rows.append({
            "date":        row["keys"][0],
            "query":       row["keys"][1],
            "clicks":      int(row["clicks"]),
            "impressions": int(row["impressions"]),
            "ctr":         round(row["ctr"] * 100, 2),
        })
    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()
    df["date"]     = pd.to_datetime(df["date"])
    df["month"]    = df["date"].dt.to_period("M")
    df["is_brand"] = df["query"].apply(is_brand)
    brand    = df[df["is_brand"]].groupby("month").agg({"clicks": "sum", "impressions": "sum", "ctr": "mean"}).reset_index()
    nonbrand = df[~df["is_brand"]].groupby("month").agg({"clicks": "sum", "impressions": "sum", "ctr": "mean"}).reset_index()
    brand["ctr"]    = brand["ctr"].round(2)
    nonbrand["ctr"] = nonbrand["ctr"].round(2)
    return brand, nonbrand

# ── CHART HELPERS ─────────────────────────────────────────────────────────────

# Shared base layout for all charts — presentation-ready defaults
BASE = dict(
    plot_bgcolor="white",
    paper_bgcolor="white",
    font=dict(family="Arial", size=13),
)

def yoy_layout(y_title):
    """Layout for all YOY grouped bar charts."""
    return dict(
        **BASE,
        barmode="group", bargap=0.15, bargroupgap=0.05,
        yaxis=dict(title=y_title, gridcolor="#eeeeee", tickformat=",", rangemode="tozero", title_font=dict(size=13)),
        xaxis=dict(title="", tickfont=dict(size=12)),
        legend=dict(orientation="h", yanchor="bottom", y=1.04, xanchor="center", x=0.5, font=dict(size=12)),
        # Extra top + right margin: top for legend, right so outside labels aren't clipped
        margin=dict(t=80, b=60, l=70, r=40),
        height=460,
    )

def horiz_bar_layout(x_title, max_val):
    """Layout for horizontal bar charts — right margin scales with the largest label."""
    # Each digit in the label ~ 8px, plus padding
    label_width = max(len(f"{max_val:,}") * 9 + 30, 80)
    return dict(
        **BASE,
        xaxis=dict(
            title=x_title, gridcolor="#eeeeee", tickformat=",",
            title_font=dict(size=13), tickfont=dict(size=12),
            # Extend range so outside labels have room
            range=[0, max_val * 1.35],
        ),
        yaxis=dict(autorange="reversed", tickfont=dict(size=12)),
        margin=dict(t=30, b=60, l=160, r=label_width),
        height=420,
    )

def gsc_clean_chart(df_curr, df_prev, this_year, last_year, title, color_curr, color_prev):
    """Two-panel chart: Clicks + CTR line (top), Impressions (bottom). Fully labelled."""
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_heights=[0.55, 0.45],
        vertical_spacing=0.10,
        specs=[[{"secondary_y": True}], [{"secondary_y": False}]],
        subplot_titles=["Clicks & Click-Through Rate (%)", "Impressions"]
    )
    import datetime as _dt
    def _fmt(s):
        try:
            return _dt.datetime.strptime(str(s), "%Y-%m").strftime("%b %Y")
        except Exception:
            return str(s)

    for df, yr, color, dash in [
        (df_prev, last_year, color_prev, "dot"),
        (df_curr, this_year, color_curr, "solid"),
    ]:
        if df is not None and not df.empty:
            labels = [_fmt(m) for m in df["month"].astype(str).tolist()]
            fig.add_trace(go.Bar(
                name=f"Clicks {yr}", x=labels, y=df["clicks"],
                marker_color=color, legendgroup=yr,
                text=[f"{v:,}" for v in df["clicks"]],
                textposition="outside", textfont=dict(size=10),
                cliponaxis=False,
            ), row=1, col=1, secondary_y=False)
            fig.add_trace(go.Scatter(
                name=f"CTR {yr} (%)", x=labels, y=df["ctr"],
                mode="lines+markers",
                line=dict(color=color, width=2, dash=dash),
                marker=dict(size=5), legendgroup=yr,
            ), row=1, col=1, secondary_y=True)
            fig.add_trace(go.Bar(
                name=f"Impressions {yr}", x=labels, y=df["impressions"],
                marker_color=color, legendgroup=yr, showlegend=False,
                text=[f"{v:,}" for v in df["impressions"]],
                textposition="outside", textfont=dict(size=10),
                cliponaxis=False,
            ), row=2, col=1)

    # Build full sorted label list (already formatted as "Jan 2025" etc)
    all_fmt_labels = sorted(set(
        ([_fmt(m) for m in df_curr["month"].astype(str).tolist()] if df_curr is not None and not df_curr.empty else []) +
        ([_fmt(m) for m in df_prev["month"].astype(str).tolist()] if df_prev is not None and not df_prev.empty else [])
    ), key=lambda s: _dt.datetime.strptime(s, "%b %Y"))

    fig.update_layout(
        title=dict(text=title, font=dict(size=15, family="Arial")),
        barmode="group",
        **BASE,
        legend=dict(orientation="h", yanchor="bottom", y=1.06, xanchor="center", x=0.5, font=dict(size=11)),
        margin=dict(t=120, b=110, l=70, r=70),
        height=640,
    )
    # Force every month label on the shared x-axis
    fig.update_xaxes(
        tickmode="array",
        tickvals=all_fmt_labels,
        ticktext=all_fmt_labels,
        tickangle=-45,
        tickfont=dict(size=11),
        row=2, col=1,
    )
    fig.update_yaxes(title_text="Clicks", gridcolor="#eeeeee", tickformat=",",
                     title_font=dict(size=12), row=1, col=1, secondary_y=False)
    fig.update_yaxes(title_text="CTR (%)", showgrid=False,
                     title_font=dict(size=12), row=1, col=1, secondary_y=True)
    fig.update_yaxes(title_text="Impressions", gridcolor="#eeeeee", tickformat=",",
                     title_font=dict(size=12), row=2, col=1)
    return fig

# ── PROPERTY AUTO-DISCOVERY ──────────────────────────────────────────────────
from difflib import SequenceMatcher

@st.cache_data(ttl=3600, show_spinner=False)
def discover_properties():
    """
    Build PROPERTIES dict from PORTFOLIO registry.
    GSC URL is auto-matched from the verified sites list using the known domain.
    Returns dict keyed by property name for use in sidebar.
    """
    creds = get_credentials()

    # ── GSC: fetch all verified sites ────────────────────────────────────────
    gsc_sites = []
    try:
        gsc_service = build("searchconsole", "v1", credentials=creds)
        resp = gsc_service.sites().list().execute()
        gsc_sites = [s["siteUrl"] for s in resp.get("siteEntry", [])]
    except Exception:
        gsc_sites = []

    def clean_domain(url):
        return (url.replace("sc-domain:", "")
                   .replace("https://", "").replace("http://", "")
                   .replace("www.", "").rstrip("/").lower())

    def find_gsc_url(domain):
        """Find the GSC site URL that matches the given domain."""
        for site in gsc_sites:
            if domain in clean_domain(site) or clean_domain(site) in domain:
                return site
        return ""

    # ── Build PROPERTIES from registry ───────────────────────────────────────
    properties = {}
    for prop in PORTFOLIO:
        gsc_url = find_gsc_url(prop["domain"])
        properties[prop["name"]] = {
            "ga4_id":   prop["ga4_id"],
            "gsc_url":  gsc_url,
            "domain":   prop["domain"],
            "name":     prop["name"],
            "keywords": prop["keywords"],
        }
    return properties

def fuzzy_filter(query, properties):
    """Return property labels sorted by fuzzy match score to query."""
    if not query.strip():
        return list(properties.keys())
    q = query.lower().strip()
    scores = []
    for label, meta in properties.items():
        candidates = [
            label,
            meta.get("name", ""),
            meta.get("domain", ""),
            meta.get("ga4_id", ""),
        ]
        best = 0
        for c in candidates:
            c = c.lower()
            if q in c:
                best = 100
                break
            s = SequenceMatcher(None, q, c).ratio() * 100
            if s > best:
                best = s
        scores.append((label, best))
    scores.sort(key=lambda x: x[1], reverse=True)
    filtered = [lbl for lbl, sc in scores if sc > 30]
    return filtered if filtered else [scores[0][0]]

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
st.sidebar.title("Simplotel")
st.sidebar.markdown("**Select Property**")

# Auto-discover properties (cached for 1 hour)
with st.sidebar:
    with st.spinner("Loading properties..."):
        PROPERTIES = discover_properties()

if not PROPERTIES:
    st.sidebar.error("No portfolio properties found. Check credentials and PORTFOLIO_GA4_IDS.")
    st.stop()

# Search bar — fuzzy filtering
search_query = st.sidebar.text_input(
    "Search property",
    placeholder="Type name, domain, or GA4 ID...",
    label_visibility="collapsed",
)

matched = fuzzy_filter(search_query, PROPERTIES)

selected_label = st.sidebar.selectbox(
    "Property",
    options=matched,
    label_visibility="collapsed",
)

# Set active property config from discovered data
PROPERTY_ID    = PROPERTIES[selected_label]["ga4_id"]
SITE_URL       = PROPERTIES[selected_label]["gsc_url"]
BRAND_KEYWORDS = PROPERTIES[selected_label].get("keywords", [])

gsc_available = bool(SITE_URL)
st.sidebar.caption(f"GA4 ID: {PROPERTY_ID}")
if gsc_available:
    st.sidebar.caption(f"GSC: {SITE_URL}")
else:
    st.sidebar.caption("GSC: not matched — check domain")

st.sidebar.markdown("---")

preset = st.sidebar.selectbox("Date range", [
    "Last 30 days","Last 7 days","Last 28 days","Last 90 days",
    "This month","Last month","This year","Yesterday","Today","Custom"
])
today = date.today()
if   preset == "Last 7 days":   start_date, end_date = today-timedelta(days=7),  today-timedelta(days=1)
elif preset == "Last 28 days":  start_date, end_date = today-timedelta(days=28), today-timedelta(days=1)
elif preset == "Last 30 days":  start_date, end_date = today-timedelta(days=30), today-timedelta(days=1)
elif preset == "Last 90 days":  start_date, end_date = today-timedelta(days=90), today-timedelta(days=1)
elif preset == "This month":    start_date, end_date = today.replace(day=1),     today-timedelta(days=1)
elif preset == "Last month":
    first_this = today.replace(day=1)
    end_date   = first_this - timedelta(days=1)
    start_date = end_date.replace(day=1)
elif preset == "This year":     start_date, end_date = today.replace(month=1, day=1), today-timedelta(days=1)
elif preset == "Yesterday":     start_date, end_date = today-timedelta(days=1), today-timedelta(days=1)
elif preset == "Today":         start_date, end_date = today, today
else:
    start_date = st.sidebar.date_input("Start date", today-timedelta(days=30))
    end_date   = st.sidebar.date_input("End date",   today-timedelta(days=1))

st.sidebar.caption(f"{start_date.strftime('%d %b %Y')} – {end_date.strftime('%d %b %Y')}")
st.sidebar.markdown("---")
compare = st.sidebar.toggle("Compare to previous period", value=False)
if compare:
    period_days = (end_date - start_date).days + 1
    prev_end    = start_date - timedelta(days=1)
    prev_start  = prev_end - timedelta(days=period_days - 1)
    st.sidebar.caption(f"vs {prev_start.strftime('%d %b')} – {prev_end.strftime('%d %b %Y')}")

st.sidebar.markdown("---")
load = st.sidebar.button("Load / Refresh Data", type="primary", use_container_width=True)

# ── MAIN ──────────────────────────────────────────────────────────────────────
st.title("Customer Success Website Analytics Dashboard")
st.caption("Live data — Google Analytics 4 & Google Search Console")

if not load:
    st.info("Select a date range from the sidebar and click **Load / Refresh Data** to begin.")
st.markdown("---")

# ════════════════════════════════════════════════════════════════════
# WEBSITE + SEARCH CONSOLE ANALYTICS — DATA ON DEMAND
# ════════════════════════════════════════════════════════════════════
st.markdown("## Website + Search Console Analytics")
st.caption(
    "Ask any question about this property's data in plain English. "
    "The AI will fetch the exact numbers from Google Analytics 4 or Google Search Console "
    "and return a table, chart, and Excel download."
)

# ── Claude API key input ──────────────────────────────────────────────────
claude_key = st.text_input(
    "Groq API Key",
    type="password",
    placeholder="gsk_...",
    help="Get your free key from console.groq.com → API Keys. It is not stored anywhere.",
)

# ── GA4 dimension/metric schema for Claude ────────────────────────────────
GA4_SCHEMA = """
Available GA4 dimensions: sessionDefaultChannelGroup, deviceCategory, city, country,
landingPage, pagePath, year, month, date, sessionSourceMedium, browser, operatingSystem.

Available GA4 metrics: sessions, activeUsers, newUsers, engagementRate, bounceRate,
averageSessionDuration, screenPageViews, conversions, totalRevenue, eventCount.

Available GSC dimensions: query, page, country, device, date.
Available GSC metrics: clicks, impressions, ctr, position.
"""

# ── Query interpreter via Claude API ─────────────────────────────────────
def interpret_query(user_query, api_key, property_name, start_str, end_str):
    """
    Send the user query to Claude. Claude returns a JSON instruction:
    {
      "source": "ga4" | "gsc",
      "title": "Human-readable title for the result",
      "chart_type": "bar" | "line" | "table_only",
      "x_axis": "column name for x axis",
      "y_axis": "column name for y axis",
      "ga4": {
        "dimensions": [...],
        "metrics": [...],
        "order_by_metric": "metric_name",
        "limit": 25,
        "filter_channel": null | "Organic Search" | etc
      },
      "gsc": {
        "dimensions": ["query"|"page"|"country"|"device"],
        "row_limit": 25,
        "order_by": "clicks"|"impressions"|"position"
      }
    }
    """
    client = Groq(api_key=api_key)
    prompt = f"""You are a data fetching assistant for a hotel website analytics dashboard.
The active property is: {property_name}
Date range for the query: {start_str} to {end_str}

{GA4_SCHEMA}

Interpret the user request and return ONLY a valid JSON object — no markdown, no explanation:
{{
  "source": "ga4",
  "title": "short title",
  "chart_type": "bar",
  "x_axis": "column_name",
  "y_axis": "column_name",
  "ga4": {{"dimensions": ["sessionDefaultChannelGroup"], "metrics": ["sessions"], "order_by_metric": "sessions", "order_desc": true, "limit": 25, "filter_channel": null}},
  "gsc": {{"dimensions": ["query"], "row_limit": 25, "order_by": "clicks"}}
}}

Rules:
- source: "ga4" or "gsc"
- For trends/monthly: dimensions=["year","month"], chart_type="line"
- For breakdowns: chart_type="bar"
- For keywords: source="gsc"
- filter_channel maps to GA4 channel group e.g. "Organic Search", "Direct", "Paid Search"
- Return ONLY the JSON. No markdown fences.

User request: {user_query}"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=512,
    )
    raw = response.choices[0].message.content.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()
    return json.loads(raw)

# ── Execute GA4 query from instruction ────────────────────────────────────
def execute_ga4_query(instruction, start_str, end_str):
    creds   = get_credentials()
    client  = BetaAnalyticsDataClient(credentials=creds)
    g       = instruction.get("ga4", {})
    dims    = [Dimension(name=d) for d in g.get("dimensions", ["sessionDefaultChannelGroup"])]
    metrics = [Metric(name=m) for m in g.get("metrics", ["sessions"])]

    req_kwargs = dict(
        property=f"properties/{PROPERTY_ID}",
        date_ranges=[DateRange(start_date=start_str, end_date=end_str)],
        dimensions=dims,
        metrics=metrics,
        limit=g.get("limit", 25),
    )

    # Order by
    order_metric = g.get("order_by_metric")
    order_desc   = g.get("order_desc", True)
    if order_metric:
        req_kwargs["order_bys"] = [
            OrderBy(metric=OrderBy.MetricOrderBy(metric_name=order_metric), desc=order_desc)
        ]

    # Channel filter
    fc = g.get("filter_channel")
    if fc:
        req_kwargs["dimension_filter"] = FilterExpression(
            filter=Filter(
                field_name="sessionDefaultChannelGroup",
                string_filter=Filter.StringFilter(value=fc)
            )
        )

    resp = client.run_report(RunReportRequest(**req_kwargs))
    rows = []
    dim_names    = [d.name for d in dims]
    metric_names = [m.name for m in metrics]
    for row in resp.rows:
        r = {}
        for i, d in enumerate(dim_names):
            r[d] = row.dimension_values[i].value
        for i, m in enumerate(metric_names):
            try:
                r[m] = float(row.metric_values[i].value)
            except ValueError:
                r[m] = row.metric_values[i].value
        rows.append(r)
    df = pd.DataFrame(rows)
    # Round float columns sensibly
    for col in df.select_dtypes(include="float").columns:
        if "rate" in col.lower() or "ctr" in col.lower():
            df[col] = (df[col] * 100).round(1) if df[col].max() <= 1 else df[col].round(1)
        else:
            df[col] = df[col].round(0).astype(int)
    return df

# ── Execute GSC query from instruction ────────────────────────────────────
def execute_gsc_query(instruction, start_str, end_str):
    if not gsc_available:
        return pd.DataFrame()
    creds   = get_credentials()
    service = build("searchconsole", "v1", credentials=creds)
    g       = instruction.get("gsc", {})
    body = {
        "startDate":  start_str,
        "endDate":    end_str,
        "dimensions": g.get("dimensions", ["query"]),
        "rowLimit":   g.get("row_limit", 25),
        "orderBy":    [{"fieldName": g.get("order_by", "clicks"), "sortOrder": "DESCENDING"}],
    }
    resp = service.searchanalytics().query(siteUrl=SITE_URL, body=body).execute()
    rows = []
    for row in resp.get("rows", []):
        r = {d: row["keys"][i] for i, d in enumerate(g.get("dimensions", ["query"]))}
        r["clicks"]      = int(row.get("clicks", 0))
        r["impressions"] = int(row.get("impressions", 0))
        r["ctr"]         = round(row.get("ctr", 0) * 100, 1)
        r["position"]    = round(row.get("position", 0), 1)
        rows.append(r)
    return pd.DataFrame(rows)

# ── Render chart from instruction + dataframe ─────────────────────────────
def render_query_chart(df, instruction):
    chart_type = instruction.get("chart_type", "bar")
    x_col      = instruction.get("x_axis", df.columns[0])
    y_col      = instruction.get("y_axis", df.columns[1] if len(df.columns) > 1 else df.columns[0])
    title      = instruction.get("title", "Query Result")

    if x_col not in df.columns:
        x_col = df.columns[0]
    if y_col not in df.columns:
        y_col = df.select_dtypes(include="number").columns[0] if len(df.select_dtypes(include="number").columns) > 0 else df.columns[-1]

    if chart_type == "table_only" or len(df) == 0:
        return None

    fig = go.Figure()
    if chart_type == "line":
        fig.add_trace(go.Scatter(
            x=df[x_col].astype(str), y=df[y_col],
            mode="lines+markers+text",
            text=df[y_col].apply(lambda v: f"{v:,}" if isinstance(v, (int, float)) else str(v)),
            textposition="top center", textfont=dict(size=10),
            line=dict(color="#4C8BF5", width=2.5),
            marker=dict(size=7),
            fill="tozeroy", fillcolor="rgba(76,139,245,0.08)",
        ))
    else:
        fig.add_trace(go.Bar(
            x=df[x_col].astype(str), y=df[y_col],
            marker_color="#4C8BF5",
            text=df[y_col].apply(lambda v: f"{v:,}" if isinstance(v, (int, float)) else str(v)),
            textposition="outside", textfont=dict(size=11),
            cliponaxis=False,
        ))

    max_y = df[y_col].max() if pd.api.types.is_numeric_dtype(df[y_col]) else 1
    fig.update_layout(
        title=dict(text=title, font=dict(size=15, family="Arial")),
        plot_bgcolor="white", paper_bgcolor="white",
        font=dict(family="Arial", size=13),
        yaxis=dict(gridcolor="#eeeeee", tickformat=",", rangemode="tozero",
                   range=[0, max_y * 1.25] if pd.api.types.is_numeric_dtype(df[y_col]) else None),
        xaxis=dict(tickfont=dict(size=11), tickangle=-30 if len(df) > 6 else 0),
        margin=dict(t=70, b=80, l=60, r=40),
        height=420,
    )
    return fig

# ── Excel builder ─────────────────────────────────────────────────────────
def build_excel(query_results):
    """
    query_results: list of {"title": str, "df": DataFrame}
    Returns bytes of an Excel workbook with one sheet per result.
    """
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        for i, result in enumerate(query_results):
            sheet_name = result["title"][:28].strip() + f" ({i+1})" if len(result["title"]) > 28 else result["title"]
            sheet_name = sheet_name[:31]  # Excel sheet name limit
            result["df"].to_excel(writer, sheet_name=sheet_name, index=False)
    buf.seek(0)
    return buf.getvalue()

# ── Session state for accumulated query results ───────────────────────────
if "query_results" not in st.session_state:
    st.session_state["query_results"] = []

# ── Query input ───────────────────────────────────────────────────────────
with st.form("query_form", clear_on_submit=True):
    user_query = st.text_input(
        "What data do you need?",
        placeholder=(
            "e.g. Top 10 landing pages by sessions last 30 days  ·  "
            "Organic keyword clicks this month  ·  "
            "Device breakdown for last 90 days  ·  "
            "Monthly organic sessions trend this year"
        ),
    )
    run_query = st.form_submit_button("🔍 Run Query", use_container_width=True, type="primary")

if run_query:
    if not user_query.strip():
        st.warning("Please enter a query.")
    elif not claude_key.strip():
        st.warning("Please enter your Groq API key above.")
    else:
        # Date range inferred by AI from query text; fallback = last 90 days
        q_start = str(date.today() - timedelta(days=90))
        q_end   = str(date.today() - timedelta(days=1))
        with st.spinner("Thinking..."):
            try:
                instruction = interpret_query(
                    user_query, claude_key,
                    PROPERTIES[selected_label]["name"],
                    q_start, q_end
                )
                source = instruction.get("source", "ga4")
                if source == "gsc":
                    if not gsc_available:
                        st.error("Google Search Console is not configured for this property.")
                    else:
                        df_result = execute_gsc_query(instruction, q_start, q_end)
                else:
                    df_result = execute_ga4_query(instruction, q_start, q_end)

                if df_result.empty:
                    st.warning("No data returned for this query and date range.")
                else:
                    title = instruction.get("title", user_query[:60])
                    st.session_state["query_results"].append({
                        "title":       title,
                        "query":       user_query,
                        "df":          df_result,
                        "instruction": instruction,
                    })
            except json.JSONDecodeError:
                st.error("The AI returned an unexpected response. Try rephrasing your query.")
            except Exception as e:
                st.error(f"Error: {e}")

# ── Display accumulated results ───────────────────────────────────────────
if st.session_state["query_results"]:
    col_dl, col_clr = st.columns([3, 1])
    with col_dl:
        excel_bytes = build_excel(st.session_state["query_results"])
        st.download_button(
            label=f"📥 Download all {len(st.session_state['query_results'])} result(s) as Excel",
            data=excel_bytes,
            file_name=f"analytics_queries_{date.today()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    with col_clr:
        if st.button("🗑 Clear all results", use_container_width=True):
            st.session_state["query_results"] = []
            st.rerun()

    for i, result in enumerate(reversed(st.session_state["query_results"])):
        with st.expander(f"**{result['title']}**  ·  {result['query']}", expanded=(i == 0)):
            fig = render_query_chart(result["df"], result["instruction"])
            if fig:
                st.plotly_chart(fig, use_container_width=True, key=f"qchart_{i}")
            st.dataframe(result["df"], use_container_width=True, hide_index=True)
            # Individual download
            single_excel = build_excel([result])
            st.download_button(
                label="📥 Download this result as Excel",
                data=single_excel,
                file_name=f"{result['title'][:40]}_{date.today()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key=f"dl_{i}",
            )

st.markdown("---")

# ════════════════════════════════════════════════════════════════════
# DECK METRICS
# ════════════════════════════════════════════════════════════════════
st.markdown("## Deck Metrics")
st.caption(
    "Fixed date windows — independent of the date selector above. "
    "Year-on-Year charts: 2022 to present. "
    "Segmentation: last 24 months. "
    "Locations: last 6 months (Organic Search only). "
    "Google Search Console brand comparison: current year vs previous year, January to today."
)

# ── YOY ALL CHANNELS ──────────────────────────────────────────────────────
st.markdown("### Year-on-Year Traffic — Monthly Sessions (All Channels)")
with st.spinner("Loading overall year-on-year data..."):
    df_yoy = get_ga4_monthly_yoy()

if not df_yoy.empty:
    years   = sorted(df_yoy["year"].unique())
    fig_yoy = go.Figure()
    for i, year in enumerate(years):
        df_y   = df_yoy[df_yoy["year"] == year].set_index("month")
        y_vals = [int(df_y.loc[m, "sessions"]) if m in df_y.index else None for m in range(1, 13)]
        t_vals = [f"{v:,}" if v else "" for v in y_vals]
        fig_yoy.add_trace(go.Bar(
            name=str(year), x=MONTH_LABELS, y=y_vals,
            text=t_vals, textposition="outside", textfont=dict(size=10),
            marker_color=YEAR_COLORS[i % len(YEAR_COLORS)], cliponaxis=False,
        ))
    max_yoy = df_yoy["sessions"].max()
    layout  = yoy_layout("Overall Sessions")
    layout["yaxis"]["range"] = [0, max_yoy * 1.25]
    fig_yoy.update_layout(**layout)
    st.plotly_chart(fig_yoy, use_container_width=True)

# ── YOY ORGANIC ───────────────────────────────────────────────────────────
st.markdown("### Year-on-Year Traffic — Monthly Sessions (Organic Search Only)")
with st.spinner("Loading organic year-on-year data..."):
    df_yoy_org = get_ga4_monthly_yoy_organic()

if not df_yoy_org.empty:
    years_org   = sorted(df_yoy_org["year"].unique())
    fig_yoy_org = go.Figure()
    for i, year in enumerate(years_org):
        df_y   = df_yoy_org[df_yoy_org["year"] == year].set_index("month")
        y_vals = [int(df_y.loc[m, "sessions"]) if m in df_y.index else None for m in range(1, 13)]
        t_vals = [f"{v:,}" if v else "" for v in y_vals]
        fig_yoy_org.add_trace(go.Bar(
            name=str(year), x=MONTH_LABELS, y=y_vals,
            text=t_vals, textposition="outside", textfont=dict(size=10),
            marker_color=YEAR_COLORS[i % len(YEAR_COLORS)], cliponaxis=False,
        ))
    max_org = df_yoy_org["sessions"].max()
    layout  = yoy_layout("Organic Sessions")
    layout["yaxis"]["range"] = [0, max_org * 1.25]
    fig_yoy_org.update_layout(**layout)
    st.plotly_chart(fig_yoy_org, use_container_width=True)

st.markdown("---")

# ── TRAFFIC SEGMENTATION — MONTHLY STACKED ───────────────────────────────
st.markdown("### Traffic Segmentation — Month-wise (Excluding Organic Search)")
st.caption("Last 24 months · Stacked by channel · Organic Search has its own chart above.")
with st.spinner("Loading segmentation data..."):
    df_seg = get_ga4_segmentation_monthly()

if not df_seg.empty:
    month_order  = (df_seg[["sort_key","month_label"]]
                    .drop_duplicates()
                    .sort_values("sort_key")["month_label"]
                    .tolist())
    channels_seg = df_seg["channel"].unique().tolist()
    fig_seg      = go.Figure()
    for ch in channels_seg:
        df_ch  = df_seg[df_seg["channel"] == ch].set_index("month_label")
        y_vals = [int(df_ch.loc[m, "sessions"]) if m in df_ch.index else 0 for m in month_order]
        fig_seg.add_trace(go.Bar(
            name=ch,
            x=month_order,
            y=y_vals,
            marker_color=SEGMENT_COLORS.get(ch, "#BBBBBB"),
            text=[f"{v:,}" if v > 0 else "" for v in y_vals],
            textposition="inside",
            textfont=dict(size=9, color="white"),
        ))
    max_seg = df_seg.groupby(["sort_key","month_label"])["sessions"].sum().max()
    fig_seg.update_layout(
        **BASE,
        barmode="stack",
        yaxis=dict(
            title="Sessions", gridcolor="#eeeeee", tickformat=",",
            range=[0, max_seg * 1.15], title_font=dict(size=13)
        ),
        xaxis=dict(title="", tickangle=-45, tickfont=dict(size=11)),
        legend=dict(orientation="h", yanchor="bottom", y=1.03, xanchor="center", x=0.5, font=dict(size=12)),
        margin=dict(t=80, b=100, l=70, r=40),
        height=520,
    )
    st.plotly_chart(fig_seg, use_container_width=True)

st.markdown("---")

# ── ENGAGEMENT RATE — MONTHLY LINE ────────────────────────────────────────
st.markdown("### Engagement Rate — Month-wise (Organic Search Only)")
st.caption("Last 6 months · Fixed window · Organic Search only.")
_eng_end   = date.today() - timedelta(days=1)
_eng_start = date.today() - timedelta(days=180)
with st.spinner("Loading engagement rate data..."):
    df_eng = get_ga4_monthly_engagement(_eng_start, _eng_end)

if not df_eng.empty:
    fig_eng = go.Figure()
    fig_eng.add_trace(go.Scatter(
        x=df_eng["label"], y=df_eng["engagement_rate"],
        mode="lines+markers+text",
        text=[f"{v}%" for v in df_eng["engagement_rate"]],
        textposition="top center", textfont=dict(size=12),
        line=dict(color="#4C8BF5", width=2.5),
        marker=dict(size=8),
        fill="tozeroy", fillcolor="rgba(76,139,245,0.08)",
    ))
    fig_eng.update_layout(
        **BASE,
        yaxis=dict(
            title="Engagement Rate (%)", gridcolor="#eeeeee",
            range=[0, 110], title_font=dict(size=13)
        ),
        xaxis=dict(title="", tickfont=dict(size=12)),
        margin=dict(t=50, b=70, l=70, r=40),
        height=400,
    )
    st.plotly_chart(fig_eng, use_container_width=True)

st.markdown("---")

# ── DEVICE SPLIT ─────────────────────────────────────────────────────────
st.markdown("### Traffic Split — Device Wise")
with st.spinner("Loading device data..."):
    df_device = get_ga4_device(start_date, end_date)

if not df_device.empty:
    dev_colors = ["#4C8BF5", "#34A853", "#FBBC04", "#EA4335"]
    col_pie, col_table = st.columns([1, 1])

    with col_pie:
        fig_pie = go.Figure(go.Pie(
            labels=df_device["Device"],
            values=df_device["Sessions"],
            hole=0.45,
            marker=dict(colors=dev_colors[:len(df_device)]),
            textinfo="label+percent+value",
            textfont=dict(size=13),
            texttemplate="%{label}<br>%{value:,} (%{percent})",
            hovertemplate="<b>%{label}</b><br>Sessions: %{value:,}<br>Share: %{percent}<extra></extra>",
            insidetextorientation="radial",
        ))
        fig_pie.update_layout(
            **BASE,
            showlegend=False,
            margin=dict(t=30, b=30, l=30, r=30),
            height=380,
            annotations=[dict(text="Sessions", x=0.5, y=0.5, font=dict(size=15, family="Arial"), showarrow=False)]
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_table:
        st.markdown("&nbsp;")
        st.dataframe(df_device, use_container_width=True, hide_index=True)

st.markdown("---")

# ── TOP 10 CITIES & COUNTRIES ─────────────────────────────────────────────
st.markdown("### Organic Traffic — Top Locations (Past 6 Months)")
st.caption("Organic Search channel only · Last 180 days · Fixed window.")

col_cities, col_countries = st.columns(2)

with col_cities:
    st.markdown("#### Top 10 Cities")
    with st.spinner("Loading city data..."):
        df_cities = get_ga4_top_cities()
    if not df_cities.empty:
        max_city = df_cities["Sessions"].max()
        fig_cities = go.Figure(go.Bar(
            x=df_cities["Sessions"],
            y=df_cities["City"],
            orientation="h",
            marker_color="#4C8BF5",
            text=df_cities["Sessions"].apply(lambda x: f"{x:,}"),
            textposition="outside",
            textfont=dict(size=12),
            cliponaxis=False,
        ))
        fig_cities.update_layout(**horiz_bar_layout("Sessions", max_city))
        st.plotly_chart(fig_cities, use_container_width=True)

with col_countries:
    st.markdown("#### Top 10 Countries")
    with st.spinner("Loading country data..."):
        df_countries = get_ga4_top_countries()
    if not df_countries.empty:
        max_country = df_countries["Sessions"].max()
        fig_countries = go.Figure(go.Bar(
            x=df_countries["Sessions"],
            y=df_countries["Country"],
            orientation="h",
            marker_color="#34A853",
            text=df_countries["Sessions"].apply(lambda x: f"{x:,}"),
            textposition="outside",
            textfont=dict(size=12),
            cliponaxis=False,
        ))
        fig_countries.update_layout(**horiz_bar_layout("Sessions", max_country))
        st.plotly_chart(fig_countries, use_container_width=True)

st.markdown("---")

# ── GSC BRAND vs NON-BRAND ────────────────────────────────────────────────
st.markdown("### Google Search Console — Brand vs Non-Brand Queries")
if not gsc_available:
    st.info("Google Search Console is not configured for this property. Add the GSC URL to PROPERTIES in app.py.")
elif not BRAND_KEYWORDS:
    st.info("No brand keywords configured for this property. Add them to the PROPERTIES dict in app.py.")
else:
    st.caption(
        f"Current year ({today.year}) vs previous year ({today.year - 1}) · "
        "January 1 to today's date, both years."
    )

    ytd_end   = today
    ytd_start = date(today.year - 1, 1, 1)
    this_year = str(today.year)
    last_year = str(today.year - 1)

    with st.spinner("Loading brand and non-brand data (this may take a moment)..."):
        df_brand, df_nonbrand = get_gsc_brand_nonbrand(ytd_start, ytd_end)

    def filter_year(df, yr):
        if df.empty:
            return pd.DataFrame()
        return df[df["month"].astype(str).str.startswith(yr)].copy()

    col_brand, col_nb = st.columns(2)
    with col_brand:
        fig_b = gsc_clean_chart(
            filter_year(df_brand, this_year),
            filter_year(df_brand, last_year),
            this_year, last_year,
            "Brand Queries",
            "#4C8BF5", "#aac4f7"
        )
        st.plotly_chart(fig_b, use_container_width=True)

    with col_nb:
        fig_nb = gsc_clean_chart(
            filter_year(df_nonbrand, this_year),
            filter_year(df_nonbrand, last_year),
            this_year, last_year,
            "Non-Brand Queries",
            "#34A853", "#a8d9b5"
        )
        st.plotly_chart(fig_nb, use_container_width=True)

st.markdown("---")
# ── GA4 CHANNEL ───────────────────────────────────────────────────────────
st.markdown("### Google Analytics 4 — Traffic by Channel")
with st.spinner("Loading channel data..."):
    df_ga4 = get_ga4_data(start_date, end_date)

total_sessions = df_ga4["sessions"].sum()
top_channel    = df_ga4.iloc[0]["channel"] if not df_ga4.empty else "—"
org_eng        = df_ga4[df_ga4["channel"] == "Organic Search"]["engagement"].values
org_eng_val    = f"{org_eng[0]}%" if len(org_eng) else "—"

c1, c2, c3 = st.columns(3)
c1.metric("Total Sessions",          f"{total_sessions:,}")
c2.metric("Top Channel",              top_channel)
c3.metric("Organic Engagement Rate",  org_eng_val)

if compare:
    df_ga4_prev = get_ga4_data(prev_start, prev_end)
    fig_ga4 = go.Figure()
    fig_ga4.add_trace(go.Bar(
        name="Current Period",  x=df_ga4["channel"], y=df_ga4["sessions"],
        marker_color="#4C8BF5",
        text=df_ga4["sessions"].apply(lambda x: f"{x:,}"),
        textposition="outside", textfont=dict(size=11), cliponaxis=False,
    ))
    fig_ga4.add_trace(go.Bar(
        name="Previous Period", x=df_ga4_prev["channel"], y=df_ga4_prev["sessions"],
        marker_color="#cccccc",
        text=df_ga4_prev["sessions"].apply(lambda x: f"{x:,}"),
        textposition="outside", textfont=dict(size=11), cliponaxis=False,
    ))
else:
    fig_ga4 = go.Figure(go.Bar(
        x=df_ga4["channel"], y=df_ga4["sessions"],
        text=df_ga4["sessions"].apply(lambda x: f"{x:,}"),
        textposition="outside", textfont=dict(size=12),
        marker_color="#4C8BF5", cliponaxis=False,
    ))
max_ga4 = df_ga4["sessions"].max()
fig_ga4.update_layout(
    **BASE,
    barmode="group",
    yaxis=dict(gridcolor="#eeeeee", tickformat=",", range=[0, max_ga4 * 1.25]),
    xaxis=dict(tickfont=dict(size=12)),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(size=12)),
    height=420, margin=dict(t=60, b=60, l=70, r=40)
)
st.plotly_chart(fig_ga4, use_container_width=True)

# ── GSC TOP KEYWORDS ──────────────────────────────────────────────────────
st.markdown("### Google Search Console — Top Keywords")
if gsc_available:
    with st.spinner("Loading keyword data..."):
        df_gsc = get_gsc_data(start_date, end_date)
    if not df_gsc.empty:
        g1, g2, g3, g4 = st.columns(4)
        g1.metric("Total Clicks",      f"{df_gsc['Clicks'].sum():,}")
        g2.metric("Total Impressions",  f"{df_gsc['Impressions'].sum():,}")
        g3.metric("Average CTR",        f"{round(df_gsc['CTR (%)'].mean(), 1)}%")
        g4.metric("Average Position",   f"{round(df_gsc['Position'].mean(), 1)}")
        st.dataframe(df_gsc, use_container_width=True, hide_index=True)
else:
    st.info("Google Search Console is not configured for this property. Add the GSC URL to PROPERTIES in app.py to enable this section.")
