# Database Schema Documentation

Complete reference for all SQLite databases and data structures used in the LinkedIn Bot.

## Database Files Overview

| Database | Purpose | Location | Tables |
|----------|---------|----------|--------|
| `bot_data.db` | Primary data store | Project root | interactions, profile_analytics, ssi_history |
| `linkedin_data.db` | Alternative store | Project root | interactions, profile_analytics, ssi_history |

**Note**: Most operations use `bot_data.db`. The `linkedin_data.db` is available for fallback or alternative implementations.

---

## Table: `interactions`

Stores every profile visit, connection, and follow action.

### Schema

```sql
CREATE TABLE interactions (
    profile_url TEXT PRIMARY KEY,
    name TEXT,
    headline TEXT,
    source TEXT,
    status TEXT,
    timestamp DATETIME
)
```

### Column Details

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `profile_url` | TEXT (PRIMARY KEY) | LinkedIn profile URL | `"https://linkedin.com/in/johndoe"` |
| `name` | TEXT | User's display name | `"John Doe"` |
| `headline` | TEXT | User's headline/role | `"Senior Data Scientist at Tech Corp"` |
| `source` | TEXT | Where profile came from | `"Group"`, `"Feed"`, `"QuickConnect"` |
| `status` | TEXT | Action taken | `"Visited"`, `"Connected"`, `"Followed"` |
| `timestamp` | DATETIME | When action occurred | `"2025-12-06 14:47:30"` |

### Queries

**Get all connections this session**:
```sql
SELECT * FROM interactions 
WHERE status = 'Connected' 
ORDER BY timestamp DESC;
```

**Count interactions by source**:
```sql
SELECT source, COUNT(*) as count 
FROM interactions 
GROUP BY source;
```

**Get today's activity**:
```sql
SELECT * FROM interactions 
WHERE DATE(timestamp) = DATE('now') 
ORDER BY timestamp DESC;
```

**Find all followed profiles**:
```sql
SELECT name, headline 
FROM interactions 
WHERE status = 'Followed' 
LIMIT 10;
```

**Get statistics for dashboard**:
```sql
SELECT 
    COUNT(DISTINCT profile_url) as total_profiles,
    SUM(CASE WHEN status='Connected' THEN 1 ELSE 0 END) as connections,
    SUM(CASE WHEN status='Followed' THEN 1 ELSE 0 END) as follows,
    COUNT(DISTINCT source) as engagement_sources
FROM interactions;
```

### Indexes

**Primary Key Index** (auto-created):
```sql
-- Ensures profile_url uniqueness, enables fast lookups
CREATE INDEX idx_profile_url ON interactions(profile_url);
```

**Recommended Additional Indexes**:
```sql
-- Speed up queries by status
CREATE INDEX idx_status ON interactions(status);

-- Speed up queries by source
CREATE INDEX idx_source ON interactions(source);

-- Speed up time-range queries
CREATE INDEX idx_timestamp ON interactions(timestamp);
```

---

## Table: `profile_analytics`

Snapshots of LinkedIn profile metrics at point-in-time moments.

### Schema

```sql
CREATE TABLE profile_analytics (
    timestamp DATETIME,
    profile_views INT,
    post_impressions INT,
    search_appearances INT,
    followers INT
)
```

### Column Details

| Column | Type | Description | Source |
|--------|------|-------------|--------|
| `timestamp` | DATETIME | When metrics were captured | `datetime.now()` |
| `profile_views` | INT | Profile views this month | LinkedIn Dashboard |
| `post_impressions` | INT | Total post impressions | LinkedIn Dashboard |
| `search_appearances` | INT | Times profile appeared in search | LinkedIn Dashboard |
| `followers` | INT | Current follower count | LinkedIn Profile |

### Example Rows

```
timestamp                | profile_views | post_impressions | search_appearances | followers
2025-12-01 09:00:00     | 145          | 1200            | 45                | 5000
2025-12-01 18:00:00     | 148          | 1250            | 46                | 5005
2025-12-02 09:00:00     | 155          | 1350            | 48                | 5010
```

### Queries

**Track profile view growth**:
```sql
SELECT 
    DATE(timestamp) as date,
    MAX(profile_views) as daily_max_views,
    MIN(profile_views) as daily_min_views,
    (MAX(profile_views) - MIN(profile_views)) as daily_growth
FROM profile_analytics
GROUP BY DATE(timestamp)
ORDER BY date DESC
LIMIT 7;
```

**Correlation: Views vs Impressions**:
```sql
SELECT 
    ROUND(
        (COUNT(*) * SUM(profile_views * post_impressions) 
         - SUM(profile_views) * SUM(post_impressions))
        / 
        SQRT((COUNT(*) * SUM(profile_views*profile_views) 
              - SUM(profile_views)*SUM(profile_views))
             * 
             (COUNT(*) * SUM(post_impressions*post_impressions) 
              - SUM(post_impressions)*SUM(post_impressions)))
        , 3
    ) as correlation
FROM profile_analytics;
```

**Average daily metrics**:
```sql
SELECT 
    AVG(profile_views) as avg_views,
    AVG(post_impressions) as avg_impressions,
    AVG(search_appearances) as avg_searches,
    AVG(followers) as avg_followers
FROM profile_analytics;
```

---

## Table: `ssi_history`

LinkedIn Social Selling Index (SSI) scores and component breakdowns over time.

### Schema

```sql
CREATE TABLE ssi_history (
    date DATE PRIMARY KEY,
    total_ssi REAL,
    people_score REAL,
    insight_score REAL,
    brand_score REAL,
    relationship_score REAL,
    ssi_rank_industry INT,
    ssi_rank_network INT
)
```

### Column Details

| Column | Type | Description | Range |
|--------|------|-------------|-------|
| `date` | DATE (PRIMARY KEY) | Date of SSI measurement | `2025-12-01` |
| `total_ssi` | REAL | Composite SSI score | 0-100 |
| `people_score` | REAL | "Establish Your Professional Brand" | 0-100 |
| `insight_score` | REAL | "Find the Right People" | 0-100 |
| `brand_score` | REAL | "Engage with Insights" | 0-100 |
| `relationship_score` | REAL | "Build Relationships" | 0-100 |
| `ssi_rank_industry` | INT | Rank within industry | 1-100000+ |
| `ssi_rank_network` | INT | Rank within network | 1-100000+ |

### Example Rows

```
date       | total_ssi | people | insight | brand | relationship | industry_rank | network_rank
2025-12-01 | 35.5     | 45    | 30     | 25    | 40          | 500          | 1200
2025-12-02 | 36.2     | 46    | 31     | 26    | 41          | 480          | 1180
2025-12-03 | 37.1     | 47    | 32     | 27    | 42          | 460          | 1150
```

### Queries

**SSI Growth Trajectory**:
```sql
SELECT 
    date,
    total_ssi,
    LAG(total_ssi) OVER (ORDER BY date) as prev_ssi,
    (total_ssi - LAG(total_ssi) OVER (ORDER BY date)) as daily_change
FROM ssi_history
ORDER BY date DESC
LIMIT 30;
```

**Identify strongest component**:
```sql
SELECT 
    'people' as component,
    AVG(people_score) as avg_score
FROM ssi_history
UNION ALL
SELECT 'insight', AVG(insight_score) FROM ssi_history
UNION ALL
SELECT 'brand', AVG(brand_score) FROM ssi_history
UNION ALL
SELECT 'relationship', AVG(relationship_score) FROM ssi_history
ORDER BY avg_score DESC;
```

**Rank improvement over time**:
```sql
SELECT 
    date,
    ssi_rank_industry,
    LAG(ssi_rank_industry) OVER (ORDER BY date) as prev_rank,
    (LAG(ssi_rank_industry) OVER (ORDER BY date) - ssi_rank_industry) as improvement
FROM ssi_history
WHERE date >= DATE('now', '-30 days')
ORDER BY date DESC;
```

---

## CSV Data Formats

### Primary CSV: `ssi_history.csv`

Historical SSI tracking for dashboard charting.

**Format**:
```
Date,Total_SSI,People,Insights,Brand,Relationships,Industry_Rank,Network_Rank
2025-12-01,35.5,45,30,25,40,500,1200
2025-12-02,36.2,46,31,26,41,480,1180
2025-12-03,37.1,47,32,27,42,460,1150
```

**Usage**:
```python
import pandas as pd

df = pd.read_csv("ssi_history.csv")
df['Date'] = pd.to_datetime(df['Date'])
print(df.tail())  # Last 5 entries
```

### Session Logs: `CSV/GroupBot-{timestamp}.csv`

Per-session engagement logs (created each run).

**Naming**: `GroupBot-HH-MM-SS-MICROSECONDS.csv`

**Format**:
```
Name,URL,Status,Timestamp,ConnectionLimit,FollowLimit,FeedLikeProbability,FeedCommentProbability,ProfilesScanned
John Doe,https://linkedin.com/in/johndoe,Connected,14:47:30,10,15,0.25,0.10,20
Jane Smith,https://linkedin.com/in/janesmith,Followed,14:52:45,10,15,0.25,0.10,20
```

**Columns**:
- `Name` - Profile name
- `URL` - LinkedIn profile URL
- `Status` - Action taken (Connected, Followed, Visited)
- `Timestamp` - Time of interaction
- `ConnectionLimit` - Connection limit for that session
- `FollowLimit` - Follow limit for that session
- `FeedLikeProbability` - Probability used for that session
- `FeedCommentProbability` - Comment probability
- `ProfilesScanned` - Total profiles scanned

---

## Text-Based Tracking Files

### `visitedUsers.txt`

Fallback session tracking (one URL per line).

```
https://linkedin.com/in/johndoe
https://linkedin.com/in/janesmith
https://linkedin.com/in/bobsmith
```

**Usage**:
```python
with open('visitedUsers.txt', 'r') as f:
    visited = set(line.strip() for line in f)
```

### `commentedPosts.txt`

Tracks posts already commented on (one URN per line).

```
urn:li:share:7123456789
urn:li:share:7123456790
urn:li:share:7123456791
```

**Usage**:
```python
commented_posts = get_commented_posts()  # Returns set of URNs
if urn not in commented_posts:
    perform_comment(browser, post, text)
```

---

## Data Migration & Backup

### Backup Strategy

**Daily Backup**:
```bash
# Backup main database
cp bot_data.db backups/bot_data_$(date +%Y-%m-%d).db

# Backup CSVs
cp ssi_history.csv backups/ssi_history_$(date +%Y-%m-%d).csv
cp -r CSV/ backups/CSV_$(date +%Y-%m-%d)/
```

### Archive Old Sessions

**Clean up monthly** (keep last 3 months):
```bash
# List all session CSVs
ls -la CSV/

# Archive old ones
mkdir -p archives/
mv CSV/GroupBot-* archives/  # Older than 90 days
```

### Export for Analysis

**Export interactions to CSV**:
```python
import pandas as pd
import sqlite3

conn = sqlite3.connect('bot_data.db')
df = pd.read_sql_query("SELECT * FROM interactions", conn)
df.to_csv('export_interactions.csv', index=False)
conn.close()
```

**Export analytics to Excel**:
```python
import pandas as pd
import sqlite3

conn = sqlite3.connect('bot_data.db')
analytics = pd.read_sql_query("SELECT * FROM profile_analytics", conn)
ssi = pd.read_csv('ssi_history.csv')

with pd.ExcelWriter('full_report.xlsx') as writer:
    analytics.to_excel(writer, sheet_name='Analytics', index=False)
    ssi.to_excel(writer, sheet_name='SSI History', index=False)
```

---

## Performance Optimization

### Index Creation

```sql
-- Execute these to improve query performance
CREATE INDEX IF NOT EXISTS idx_interactions_status 
    ON interactions(status);

CREATE INDEX IF NOT EXISTS idx_interactions_source 
    ON interactions(source);

CREATE INDEX IF NOT EXISTS idx_interactions_timestamp 
    ON interactions(timestamp);

CREATE INDEX IF NOT EXISTS idx_analytics_timestamp 
    ON profile_analytics(timestamp);
```

### Vacuum & Optimize

```python
import sqlite3

conn = sqlite3.connect('bot_data.db')
conn.execute("VACUUM")  # Reclaim space
conn.execute("PRAGMA optimize")  # Optimize indexes
conn.close()
```

### Query Performance Tips

| Slow ❌ | Fast ✓ |
|---------|--------|
| `SELECT * FROM interactions` | `SELECT profile_url, status FROM interactions WHERE status='Connected'` |
| Join without indexes | Use indexed columns in WHERE clauses |
| Large LIKE patterns | Use exact matches when possible |
| No LIMIT | `LIMIT 1000` for reports |

---

## Troubleshooting

### "Table Already Exists"
```python
# init_db() uses "CREATE TABLE IF NOT EXISTS"
# Safe to call multiple times
init_db()
```

### Database Locked Error
```python
# Close other connections
# Only one writer at a time
# Retry with exponential backoff
```

### Missing Data in Dashboard
```python
# Verify tables exist:
sqlite3 bot_data.db ".tables"

# Check row counts:
sqlite3 bot_data.db "SELECT COUNT(*) FROM interactions;"
```

---

**Last Updated**: December 6, 2025 | **Schema Version**: 1.0
