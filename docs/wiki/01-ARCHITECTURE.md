# Architecture Guide

## System Overview

The LinkedIn Bot is a multi-layered automation system designed with three core principles:

1. **Stealth**: Anti-detection mechanisms prevent LinkedIn's security systems from flagging the account
2. **Intelligence**: Adaptive behavior scales based on SSI score and account age
3. **Monitoring**: Real-time analytics track engagement effectiveness

## High-Level Data Flow

```
┌──────────────────┐
│  LinkedIn.com    │
│   (Web Server)   │
└────────┬─────────┘
         │ HTTPS
         ▼
┌──────────────────────────────────────────┐
│     Selenium WebDriver (Edge Browser)    │
│  ┌────────────────────────────────────┐  │
│  │  bot_v2.py                         │  │
│  │  ├─ start_browser()                │  │
│  │  ├─ run_main_bot_logic()           │  │
│  │  ├─ interact_with_feed_human()     │  │
│  │  └─ calculate_smart_parameters()   │  │
│  └────────────────────────────────────┘  │
└──────────┬───────────────────────────────┘
           │
      ┌────┴─────────┬────────────┬────────────┐
      │              │            │            │
      ▼              ▼            ▼            ▼
  ┌────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐
  │SQLite  │  │CSV       │  │Text      │  │Edge    │
  │Queries │  │History   │  │Files     │  │Profile │
  │(.db)   │  │(.csv)    │  │(.txt)    │  │(.data) │
  └────────┘  └────┬─────┘  └──────────┘  └────────┘
                   │
                   ▼
           ┌──────────────────┐
           │ dashboard_app.py │
           │ (Streamlit UI)   │
           └──────────────────┘
           http://localhost:8501
```

## Component Architecture

### 1. Core Bot Engine (`bot_v2.py`)

**Responsibility**: Orchestrate all automation workflows

**Key Execution Loop**:
```python
start_browser()
  ├─ run_quick_connects()         # Bypass daily connection limits
  ├─ interact_with_feed_human()   # Like/comment feed, collect profiles
  ├─ random_browsing_habit()      # Simulate real user behavior
  ├─ run_networker()              # Follow top profiles (SSI boost)
  ├─ run_reciprocator()           # Accept pending invitations
  ├─ withdraw_old_invites()       # Clean up stale requests (optional)
  └─ run_main_bot_logic()         # Main group automation loop
     ├─ Scroll group feed
     ├─ Collect target profiles
     ├─ Visit & evaluate profiles
     ├─ Connect/follow based on roles
     └─ Log all interactions
```

**Global State**:
```python
SESSION_CONNECTION_COUNT = 0    # Connections sent this session
SESSION_FOLLOW_COUNT = 0        # Profiles followed this session
SESSION_WITHDRAWN_COUNT = 0     # Invitations withdrawn this session

LIMITS_CONFIG = {
    "CONNECTION": (5, 8),       # Random range per session
    "FOLLOW": (10, 15),
    "PROFILES_SCAN": (20, 30),
    "FEED_POSTS": (30, 50)
}

PROBS = {
    "FEED_LIKE": (0.20, 0.30),
    "FEED_COMMENT": (0.05, 0.15),
    "GROUP_LIKE": (0.40, 0.50),
    "GROUP_COMMENT": (0.10, 0.15)
}
```

### 2. Auto-Regulation Engine

**Purpose**: Scale behavior based on account age (SSI growth trajectory)

**Four Operational Modes**:

| Mode | Condition | Connection Limit | Follow Limit | Comment Prob | Strategy |
|------|-----------|------------------|--------------|--------------|----------|
| **AQUECIMENTO** | Days < 3 | 3-6 | 5-8 | 5-15% | Low profile, observe market |
| **CRESCIMENTO** | 3-14 days | 10 | 8-12 | 0% | Moderate engagement, no comments |
| **CRUZEIRO** | 14+ days, SSI < 40 | 10-15 | 12-18 | 25-35% | Stable, sustainable pace |
| **ELITE** | SSI > 40 | 15-20 | 15-20 | 35-50% | Influencer mode, high volume |

**Implementation** (`calculate_smart_parameters()`):
```python
# Reads ssi_history.csv to determine:
days_run = count_unique_dates()
last_ssi = get_latest_ssi_score()

# Returns:
return (limits_dict, probs_dict)
```

### 3. Database Layer

**Dual Strategy**: SQLite (current state) + CSV (historical trends)

#### SQLite Schema
```sql
-- bot_data.db

-- Interaction history
CREATE TABLE interactions (
    profile_url TEXT PRIMARY KEY,
    name TEXT,
    headline TEXT,
    source TEXT,        -- "Group", "Feed", "QuickConnect"
    status TEXT,        -- "Visited", "Connected", "Followed"
    timestamp DATETIME
);

-- Profile analytics
CREATE TABLE profile_analytics (
    timestamp DATETIME,
    profile_views INT,
    post_impressions INT,
    search_appearances INT,
    followers INT
);

-- SSI history (optional)
CREATE TABLE ssi_history (
    date DATE PRIMARY KEY,
    total_ssi REAL,
    people_score REAL,
    insight_score REAL,
    brand_score REAL,
    relationship_score REAL,
    ssi_rank_industry INT,
    ssi_rank_network INT
);
```

#### CSV Format
```csv
ssi_history.csv:
Date,Total_SSI,People,Insights,Brand,Relationships,Industry_Rank,Network_Rank
2025-12-01,35.5,45,30,25,40,500,1200
2025-12-02,36.2,46,31,26,41,480,1180
```

#### Session Logs
```
CSV/GroupBot-14-47-26-612732.csv
─────────────────────────────────
Name, URL, Status, Timestamp, ConnectionLimit, FollowLimit, ...
John Doe, /in/johndoe, Connected, 14:47:30, 10, 15, ...
```

### 4. Stealth Layer

**Goal**: Appear as human user to LinkedIn's detection systems

**Mechanisms**:

| Mechanism | Implementation | Effect |
|-----------|-----------------|--------|
| **Browser Fingerprint** | Random window size (1024-1920 x 768-1080) | Avoid "bot-like" window dimensions |
| **Human Typing** | `human_type()` - 4% error rate, 60-280ms delays | Natural keystroke patterns |
| **Randomized Delays** | `human_sleep()` with SPEED_FACTOR | Variable pauses between actions |
| **Mouse Movements** | `random_mouse_hover()`, scroll patterns | Simulate real interaction |
| **Language Detection** | `langdetect.detect()` on post text | Only engage English content |
| **Long Pauses** | `sleep_after_connection()` (45-90s) | Simulate profile reading time |
| **CDP Masking** | `Object.defineProperty(navigator.webdriver)` | Hide Selenium webdriver detection |

### 5. AI Integration

**Component**: Comment generation via g4f

**Flow**:
```python
post_text = "Great insights on ML pipelines!"

# 1. Language check
if is_text_english(post_text):
    
    # 2. Generate comment
    comment = get_ai_comment(post_text)
    
    # 3. Type naturally
    human_type(comment_field, comment)
    
    # 4. Log result
    log_interaction_db(url, name, headline, "Group", "Commented")
```

**Error Handling**: If g4f fails or AI_CLIENT is None, comment step silently skips.

## Data Flow Examples

### Workflow 1: Group Automation

```
1. Navigate to GROUP_URL
   └─ random_key selects from LINKEDIN_GROUPS_LIST (13 groups)

2. Collect Profiles
   ├─ Loop through group posts
   ├─ Extract profile links (href="/in/...")
   ├─ Add to profiles_queued list
   ├─ Check PROFILES_TO_SCAN limit
   └─ Scroll if needed

3. Visit & Interact
   ├─ For each profile URL:
   │  ├─ GET profile page
   │  ├─ Extract: name, headline, profile_views
   │  ├─ Evaluate: match against TARGET_ROLES?
   │  ├─ Connect? (if SESSION_CONNECTION_COUNT < LIMIT)
   │  ├─ Follow? (if not connected, is top profile, SESSION_FOLLOW_COUNT < LIMIT)
   │  └─ log_interaction_db()
   │
   └─ Stop when SESSION limits reached

4. Logging
   ├─ SQLite: interactions table
   ├─ CSV: /CSV/GroupBot-{timestamp}.csv
   └─ Text: visitedUsers.txt
```

### Workflow 2: Dashboard Analytics

```
dashboard_app.py:

1. Load Data
   ├─ Read ssi_history.csv
   │  └─ Parse dates, sort chronologically
   ├─ Query bot_data.db
   │  ├─ SELECT * FROM interactions
   │  └─ SELECT * FROM profile_analytics
   └─ Calculate derived metrics

2. Render Visualizations (30+)
   ├─ KPI Section
   │  ├─ Current SSI
   │  ├─ SSI Change
   │  ├─ Total Connections
   │  └─ SSI Rank
   ├─ Line Charts
   │  ├─ SSI Trend
   │  ├─ Profile Views Over Time
   │  └─ Search Appearances
   ├─ Bar Charts
   │  ├─ Engagement by Source
   │  └─ Interaction Types
   └─ Heatmaps & Correlations

3. Style
   └─ Apply Heineken colors (#286529 dark green, #ca2819 red, #8ebf48 lime)
```

## Extension Points

### Adding New Automation Workflow

1. **Create function in `bot_v2.py`**:
   ```python
   def my_new_workflow(browser):
       # Implement workflow
       # Use human_sleep() for delays
       # Log via log_interaction_db()
       pass
   ```

2. **Call from `start_browser()`**:
   ```python
   try:
       my_new_workflow(browser)
   except Exception as e:
       print(f"Error: {e}")
       raise
   ```

3. **Respect limits**:
   ```python
   if SESSION_CONNECTION_COUNT < CONNECTION_LIMIT:
       # Perform action
       SESSION_CONNECTION_COUNT += 1
   ```

### Adding New Database Table

1. **Update schema in `init_db()`**:
   ```python
   c.execute('''CREATE TABLE IF NOT EXISTS my_table (
       id INTEGER PRIMARY KEY,
       data TEXT,
       timestamp DATETIME
   )''')
   ```

2. **Create logging function**:
   ```python
   def log_my_data(value):
       conn = sqlite3.connect(DB_NAME)
       c = conn.cursor()
       c.execute("INSERT INTO my_table VALUES (?, ?, ?)", 
                 (None, value, datetime.datetime.now()))
       conn.commit()
       conn.close()
   ```

## Performance Considerations

### Timing
- **Typical Session**: 30-60 minutes
- **SPEED_FACTOR impact**: 1.5x multiplier = 45-90 minute session
- **Main bottleneck**: LinkedIn page load times (anti-bot protection)

### Database
- **Query Performance**: SQLite with B-tree indexes on profile_url
- **CSV Size**: Grows ~50-100 rows per 1-hour session
- **Recommended Cleanup**: Archive sessions monthly, keep last 3 months

### Memory
- **Selenium WebDriver**: ~200-300 MB
- **Full Dataset**: < 10 MB (SQLite + CSV)
- **No memory leaks**: Browser restarts on critical errors

## Security Considerations

### What the Bot Does NOT Store
- Passwords or authentication tokens
- Personal messages or connection notes
- Profile images or sensitive data

### What the Bot DOES Store
- Profile URLs and public headings
- Interaction metadata (timestamps, action types)
- SSI scores and aggregate metrics

### Compliance
- User responsible for LinkedIn TOS compliance
- Educational use only
- Respect rate limits and anti-spam policies

---

**Last Updated**: December 6, 2025 | **Section**: System Architecture
