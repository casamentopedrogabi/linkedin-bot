# Dashboard Guide

Complete reference for the Streamlit analytics dashboard that visualizes bot performance and LinkedIn metrics.

## Dashboard Overview

The dashboard provides real-time monitoring of:
- Social Selling Index (SSI) trends
- Connection success rates
- Engagement metrics
- Profile analytics

**Launch**: `streamlit run dashboard_app.py`
**Access**: http://localhost:8501

---

## Dashboard Architecture

### Data Sources

The dashboard pulls from multiple sources:

```
┌─────────────────────────────────────────────┐
│         Dashboard Data Pipeline             │
├─────────────────────────────────────────────┤
│                                             │
│  1. Load CSV (ssi_history.csv)              │
│     └─ Historical SSI trends                │
│                                             │
│  2. Query SQLite (bot_data.db)              │
│     ├─ interactions table                   │
│     └─ profile_analytics table              │
│                                             │
│  3. Calculate Derived Metrics               │
│     ├─ SSI change                           │
│     ├─ Success rates                        │
│     └─ Correlations                         │
│                                             │
│  4. Render Visualizations                   │
│     └─ 30+ plots with Heineken colors       │
│                                             │
└─────────────────────────────────────────────┘
```

### Implementation

```python
def load_data():
    # 1. SSI History from CSV
    ssi_df = pd.read_csv("ssi_history.csv")
    ssi_df['Date'] = pd.to_datetime(ssi_df['Date'])
    
    # 2. Interactions from SQLite
    conn = sqlite3.connect("bot_data.db")
    interactions_df = pd.read_sql_query("SELECT * FROM interactions", conn)
    
    # 3. Analytics from SQLite
    analytics_df = pd.read_sql_query("SELECT * FROM profile_analytics", conn)
    conn.close()
    
    return ssi_df, interactions_df, analytics_df

def main_dashboard():
    st.set_page_config(layout="wide", page_title="LinkedIn SSI Bot Analytics")
    
    ssi_df, interactions_df, analytics_df = load_data()
    
    # Render KPIs, charts, etc.
```

---

## Dashboard Sections

### 1. Key Performance Indicators (KPIs)

**Top Section**: 4-column layout with current session metrics.

| KPI | Source | Formula | Example |
|-----|--------|---------|---------|
| **Current SSI** | `ssi_df['Total_SSI'].iloc[-1]` | Latest SSI value | 38.5 |
| **SSI Change** | `ssi_df['SSI_Increase'].iloc[-1]` | SSI increase this period | +1.2 |
| **Total Connections** | `interactions_df[status='Connected']` | Count of connected profiles | 42 |
| **SSI Rank** | `ssi_df['Rank'].iloc[-1]` | Industry rank | #450 |

**Display Style**: Large metric cards with color coding (green for positive, red for negative)

---

### 2. SSI Trend Chart

**Type**: Line chart with date on X-axis, SSI on Y-axis

**Data**: `ssi_df` (all historical records)

**Features**:
- Shows SSI progression over time
- Identifies growth periods vs plateaus
- Heineken dark green color (#286529)

**SQL Query**:
```sql
SELECT date, total_ssi FROM ssi_history 
ORDER BY date
```

**Interpretation**:
- Steady upward slope → Effective automation
- Flat line → Stalled growth (check limits)
- Downward slope → Account cooling off (reduce SPEED_FACTOR)

---

### 3. Engagement by Source

**Type**: Bar chart showing interaction counts by source

**Categories**: "Group", "Feed", "QuickConnect"

**Data**:
```python
interactions_by_source = interactions_df.groupby('source').size()
# Group, Feed, QuickConnect (stacked bar)
```

**Insight**: Identifies which automation workflow is most effective

---

### 4. Interaction Status Distribution

**Type**: Pie chart or donut

**Categories**: "Visited", "Connected", "Followed"

**Example**:
```
Visited:    40%  (120 profiles)
Connected:  35%  (105 connections)
Followed:   25%  (75 follows)
```

**Metric**: `interactions_df.value_counts('status')`

---

### 5. Profile Views Trend

**Type**: Line chart with timeline

**Data**: `analytics_df['profile_views']`

**Expected Pattern**: Gradual increase as SSI grows

**Correlation**: Often correlates with connection activity

---

### 6. Post Impressions Over Time

**Type**: Area chart or line chart

**Data**: `analytics_df['post_impressions']`

**Insight**: Shows content reach

**Optimization**: Compare with engagement actions (likes/comments)

---

### 7. Search Appearances Trend

**Type**: Line chart

**Data**: `analytics_df['search_appearances']`

**Meaning**: How often profile appears in LinkedIn search results

**Correlation**: Grows with SSI increase and profile optimization

---

### 8. Follower Growth Chart

**Type**: Line chart with daily increments

**Data**: `analytics_df['followers']`

**Calculation**:
```python
daily_follower_increase = analytics_df['followers'].diff()
# Shows new followers per day
```

---

### 9. Connections vs SSI Correlation

**Type**: Scatter plot

**X-axis**: Total connections sent
**Y-axis**: SSI score

**Insight**: Validates correlation between activity and SSI growth

**Example SQL**:
```sql
SELECT 
    COUNT(*) as connections,
    (SELECT total_ssi FROM ssi_history ORDER BY date DESC LIMIT 1) as ssi
FROM interactions
WHERE status = 'Connected'
```

---

### 10. Daily Activity Heatmap

**Type**: Calendar heatmap or histogram

**Data**: Interactions grouped by date

**Colors**: 
- Light (few interactions) to dark (many interactions)
- Heineken color scale

**Query**:
```python
daily_activity = interactions_df.groupby(interactions_df['timestamp'].dt.date).size()
```

---

## Color Scheme (Heineken Branding)

**Global Heineken Colors**:

```python
HEINEKEN_COLORS = {
    "dark_green": "#286529",      # Primary (SSI, main metrics)
    "off_white": "#f2f2f1",       # Background
    "red": "#ca2819",             # Alerts, negative trends
    "medium_gray": "#95a49b",     # Secondary data
    "lime_green": "#8ebf48",      # Positive growth
    "black": "#000000"            # Text
}
```

**Usage**:
- **Dark Green**: Main KPI cards, primary line charts
- **Red**: Negative changes, alerts, error states
- **Lime Green**: Growth indicators, success metrics
- **Gray**: Secondary metrics, neutral data
- **Off-White**: Background of all plots

---

## Customizing Dashboard

### Add New KPI Card

```python
# In main_dashboard()
col1, col2, col3, col4, col5 = st.columns(5)  # Add 5th column

with col5:
    st.metric(
        "New Metric",
        value=some_calculated_value,
        delta=change_from_previous,
        delta_color="normal"  # or "inverse" for inverted logic
    )
```

### Add New Chart

```python
fig, ax = plt.subplots(figsize=(12, 6))

plot_line_chart(
    df=ssi_df,
    x_col='Date',
    y_col='Total_SSI',
    title='SSI Trend Over 30 Days',
    ax=ax,
    color_key="dark_green"
)

st.pyplot(fig)
```

### Export Dashboard Data

```python
# Download CSV
csv = interactions_df.to_csv(index=False)
st.download_button(
    label="Download Interactions CSV",
    data=csv,
    file_name="interactions_export.csv",
    mime="text/csv"
)
```

---

## Common Dashboard Issues

### Issue: "No data to display"

**Causes**:
1. Bot hasn't run yet
2. SQLite database not initialized
3. `ssi_history.csv` doesn't exist

**Solution**:
```bash
# Run bot first
python bot_v2.py

# Verify database
sqlite3 bot_data.db "SELECT COUNT(*) FROM interactions;"

# Check CSV
cat ssi_history.csv | head
```

---

### Issue: Charts show only one point

**Causes**: 
1. Only one day of data
2. All values are identical

**Solution**:
```python
# In load_data(), check for single-point data
if df[y_col].nunique() <= 1 and len(df) > 0:
    value = df[y_col].iloc[0]
    range_val = max(abs(value * 0.05), 0.1)
    ax.set_ylim(value - range_val, value + range_val)
```

---

### Issue: Dashboard crashes on large datasets

**Causes**: 
1. Too many interactions logged (> 100k)
2. Memory issues

**Solution**:
```python
# Filter to recent data
cutoff_date = datetime.now() - timedelta(days=30)
interactions_df = interactions_df[
    interactions_df['timestamp'] > cutoff_date
]
```

---

## Performance Optimization

### Cache Data Loading

```python
@st.cache_data
def load_data():
    # Only reloaded when data changes
    ssi_df = pd.read_csv("ssi_history.csv")
    conn = sqlite3.connect("bot_data.db")
    interactions_df = pd.read_sql_query("SELECT * FROM interactions", conn)
    conn.close()
    return ssi_df, interactions_df
```

### Limit Time Range

```python
# Show only last 90 days
cutoff = datetime.now() - timedelta(days=90)
ssi_df = ssi_df[ssi_df['Date'] >= cutoff]
```

---

## Advanced Features

### Anomaly Detection

Highlight unusual activity:

```python
# Flag days with unusually high connections
mean_connections = interactions_df.groupby('date').size().mean()
std_connections = interactions_df.groupby('date').size().std()

anomalies = interactions_df.groupby('date').size() > (mean_connections + 2*std_connections)
st.warning(f"⚠️ {anomalies.sum()} anomalous days detected")
```

### Predictive Analytics

Forecast SSI growth:

```python
from sklearn.linear_model import LinearRegression

X = np.arange(len(ssi_df)).reshape(-1, 1)
y = ssi_df['Total_SSI'].values

model = LinearRegression().fit(X, y)
future_days = np.array([len(ssi_df), len(ssi_df)+1, len(ssi_df)+2]).reshape(-1, 1)
forecast = model.predict(future_days)

st.line_chart(forecast)
```

### Engagement ROI

Calculate return on automation effort:

```python
total_interactions = len(interactions_df)
total_connections = len(interactions_df[interactions_df['status']=='Connected'])
ssi_increase = ssi_df['Total_SSI'].iloc[-1] - ssi_df['Total_SSI'].iloc[0]

roi = ssi_increase / total_interactions if total_interactions > 0 else 0
st.metric("SSI per Interaction", f"{roi:.4f}")
```

---

## Mobile View

Dashboard is responsive (Streamlit default), but for mobile optimization:

```python
st.set_page_config(layout="centered")  # Single column for mobile

# Or detect device
import streamlit as st
if st.session_state.get('mobile'):
    st.set_page_config(layout="centered")
else:
    st.set_page_config(layout="wide")
```

---

## Data Refresh

### Manual Refresh

```python
# Streamlit auto-refreshes every 5 seconds by default
# Force refresh with Rerun button
if st.button("🔄 Refresh Data"):
    st.rerun()
```

### Auto-Refresh

```python
import time
import streamlit as st

# Refresh every 60 seconds
placeholder = st.empty()

while True:
    with placeholder.container():
        load_and_render_dashboard()
    
    time.sleep(60)
    st.rerun()
```

---

## Troubleshooting Queries

### Debug: Check data quality

```sql
-- Interactions
SELECT COUNT(*) as total, 
       COUNT(DISTINCT status) as unique_statuses,
       COUNT(DISTINCT source) as unique_sources
FROM interactions;

-- Analytics
SELECT COUNT(*) as snapshots,
       MIN(timestamp) as first_snapshot,
       MAX(timestamp) as latest_snapshot
FROM profile_analytics;
```

---

## Next Steps

1. **Launch dashboard**: `streamlit run dashboard_app.py`
2. **Run bot**: `python bot_v2.py`
3. **Monitor KPIs**: Watch SSI, connections, engagement
4. **Adjust config**: If SSI plateaus, increase limits
5. **Export reports**: Use download buttons for analysis

See **[Configuration Guide](./04-CONFIGURATION.md)** to optimize bot behavior.

---

**Last Updated**: December 6, 2025 | **Dashboard Version**: 1.0
