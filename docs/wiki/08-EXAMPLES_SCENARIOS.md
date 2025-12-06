# Usage Examples & Scenarios

Real-world examples of configuring and running the LinkedIn Bot for different goals.

---

## Scenario 1: Building SSI Fast (Aggressive Growth)

**Goal**: Maximum SSI growth in 30 days

**Configuration**:

```python
# bot_v2.py

AUTO_REGULATE = True      # Let bot scale intelligently
SPEED_FACTOR = 1.0        # Faster (higher risk, faster results)

LIMITS_CONFIG = {
    "CONNECTION": (15, 20),
    "FOLLOW": (20, 30),
    "PROFILES_SCAN": (60, 100),
    "FEED_POSTS": (80, 120)
}

PROBS = {
    "FEED_LIKE": (0.60, 0.80),
    "FEED_COMMENT": (0.30, 0.50),
    "GROUP_LIKE": (0.70, 0.90),
    "GROUP_COMMENT": (0.20, 0.30)
}

QUICK_CONNECT_LIMIT = 20
SEND_AI_NOTE = 1              # Personalized messages
CONNECT_WITH_USERS = True
```

**Expected Results**:
- Day 1-3: 5-10 connections (AQUECIMENTO mode)
- Day 4-14: 100-150 connections
- Day 15-30: 200-300 connections
- **Total SSI gain**: +8-12 points

**Risks**:
- Higher chance of "unusual activity" warning
- May trigger account restriction if pushed too far
- Session duration: 45+ minutes per run

**Mitigation**:
- Run during off-peak hours (11 PM - 8 AM)
- Space out sessions: 48-72 hours between runs
- Monitor SSI dashboard weekly
- If restricted, pause for 3-5 days

---

## Scenario 2: Sustainable Networking (Conservative)

**Goal**: Steady growth with low detection risk

**Configuration**:

```python
# bot_v2.py

AUTO_REGULATE = True
SPEED_FACTOR = 2.0        # Slower (lower risk)

LIMITS_CONFIG = {
    "CONNECTION": (5, 8),
    "FOLLOW": (8, 12),
    "PROFILES_SCAN": (20, 30),
    "FEED_POSTS": (20, 40)
}

PROBS = {
    "FEED_LIKE": (0.20, 0.40),
    "FEED_COMMENT": (0.05, 0.15),
    "GROUP_LIKE": (0.30, 0.50),
    "GROUP_COMMENT": (0.05, 0.10)
}

QUICK_CONNECT_LIMIT = 5
SEND_AI_NOTE = 0          # No personalization (faster)
CONNECT_WITH_USERS = True
```

**Expected Results**:
- ~6 connections per session
- ~2-3 followers per session
- Minimal activity flags
- Session duration: 60-90 minutes

**Advantages**:
- Very low detection risk
- Consistent, predictable growth
- Account stays healthy

---

## Scenario 3: Targeted High-Value Connections Only

**Goal**: Connect with 50 specific decision-makers in data/ML

**Configuration**:

```python
# bot_v2.py

AUTO_REGULATE = False
SPEED_FACTOR = 1.5

# Very selective
LIMITS_CONFIG = {
    "CONNECTION": (3, 5),      # Quality > quantity
    "FOLLOW": (2, 3),
    "PROFILES_SCAN": (15, 25),
    "FEED_POSTS": (0, 10)      # Minimal feed engagement
}

PROBS = {
    "FEED_LIKE": (0, 0),                  # No feed likes/comments
    "FEED_COMMENT": (0, 0),
    "GROUP_LIKE": (0.10, 0.20),
    "GROUP_COMMENT": (0, 0)
}

# Narrow targeting
TARGET_ROLES = [
    "chief data officer", "vp of data", "head of analytics",
    "lead data scientist", "principal engineer"
]

HIGH_VALUE_KEYWORDS = [
    "databricks", "data engineering", "machine learning",
    "data platform", "analytics"
]

QUICK_CONNECT_LIMIT = 0
SEND_AI_NOTE = 1          # Always send personalized notes
CONNECT_WITH_USERS = True
```

**Workflow**:
1. Run bot daily for 2-3 weeks
2. Total: ~15-20 connections per week
3. Over 4 weeks: ~60-80 targeted connections

**Success Metrics**:
- High acceptance rate (40-50% vs 20-30% generic)
- Many conversations initiated
- Valuable relationship building

**Manual Customization**:
```python
# For one-off campaigns, modify TARGET_ROLES dynamically
if is_tuesday():  # Day-specific targeting
    TARGET_ROLES = ["recruiter", "hiring manager"]
else:
    TARGET_ROLES = ["data scientist", "ml engineer"]
```

---

## Scenario 4: Engagement-First (Comments & Insights)

**Goal**: Build thought leadership through engagement

**Configuration**:

```python
# bot_v2.py

AUTO_REGULATE = False
SPEED_FACTOR = 2.0

LIMITS_CONFIG = {
    "CONNECTION": (2, 4),       # Minimal connections
    "FOLLOW": (5, 10),
    "PROFILES_SCAN": (10, 15),
    "FEED_POSTS": (50, 100)     # Heavy feed engagement
}

PROBS = {
    "FEED_LIKE": (0.50, 0.70),
    "FEED_COMMENT": (0.30, 0.50),   # High comment rate
    "GROUP_LIKE": (0.60, 0.80),
    "GROUP_COMMENT": (0.25, 0.40)   # Active in groups
}

AI_PERSONA = "I am a thought leader in AI and data science with 15 years experience building ML platforms."

QUICK_CONNECT_LIMIT = 0
SEND_AI_NOTE = 0
CONNECT_WITH_USERS = False     # Focus on visibility, not connects
```

**Expected Results**:
- 30-50 comments per session
- 40+ likes per session
- Increased post visibility
- Followers gain from engagement

**Bonus: Track engagement ROI**:

```python
# Query engagement impact
import sqlite3
conn = sqlite3.connect('bot_data.db')
cursor = conn.cursor()

# Comments per session
comments = cursor.execute(
    "SELECT COUNT(*) FROM interactions WHERE status='Commented' AND DATE(timestamp)=DATE('now')"
).fetchone()[0]

# Followers gained
followers_today = cursor.execute(
    "SELECT followers FROM profile_analytics WHERE DATE(timestamp)=DATE('now') ORDER BY timestamp DESC LIMIT 1"
).fetchone()

print(f"Comments posted: {comments}")
print(f"Followers gained: {followers_today}")
```

---

## Scenario 5: A/B Testing Different Strategies

**Goal**: Compare two engagement strategies over 2 weeks each

**Configuration for Strategy A (Connections)**:

```python
# week1_connections.py
SPEED_FACTOR = 1.5
LIMITS_CONFIG["CONNECTION"] = (10, 15)
LIMITS_CONFIG["FOLLOW"] = (10, 15)
PROBS["FEED_COMMENT"] = (0.10, 0.20)
SEND_AI_NOTE = 1
```

**Configuration for Strategy B (Engagement)**:

```python
# week2_engagement.py
SPEED_FACTOR = 2.0
LIMITS_CONFIG["CONNECTION"] = (2, 4)
LIMITS_CONFIG["FEED_POSTS"] = (60, 100)
PROBS["FEED_COMMENT"] = (0.40, 0.60)
SEND_AI_NOTE = 0
```

**Measurement & Comparison**:

```python
import pandas as pd
import sqlite3

# Query results
conn = sqlite3.connect('bot_data.db')

# Week 1 (Connections Strategy)
week1 = pd.read_sql_query("""
    SELECT 
        COUNT(*) as interactions,
        SUM(CASE WHEN status='Connected' THEN 1 ELSE 0 END) as connections,
        SUM(CASE WHEN status='Commented' THEN 1 ELSE 0 END) as comments,
        (SELECT total_ssi FROM ssi_history WHERE date IN (SELECT MIN(DATE(timestamp)) FROM interactions WHERE timestamp LIKE '2025-12-01%')) as ssi_start,
        (SELECT total_ssi FROM ssi_history WHERE date IN (SELECT MAX(DATE(timestamp)) FROM interactions WHERE timestamp LIKE '2025-12-07%')) as ssi_end
    FROM interactions 
    WHERE timestamp LIKE '2025-12-01%' OR timestamp LIKE '2025-12-07%'
""", conn)

# Week 2 (Engagement Strategy)
week2 = pd.read_sql_query("""
    SELECT 
        COUNT(*) as interactions,
        SUM(CASE WHEN status='Connected' THEN 1 ELSE 0 END) as connections,
        SUM(CASE WHEN status='Commented' THEN 1 ELSE 0 END) as comments,
        (SELECT total_ssi FROM ssi_history WHERE date IN (SELECT MIN(DATE(timestamp)) FROM interactions WHERE timestamp LIKE '2025-12-08%')) as ssi_start,
        (SELECT total_ssi FROM ssi_history WHERE date IN (SELECT MAX(DATE(timestamp)) FROM interactions WHERE timestamp LIKE '2025-12-14%')) as ssi_end
    FROM interactions 
    WHERE timestamp LIKE '2025-12-08%' OR timestamp LIKE '2025-12-14%'
""", conn)

# Compare
print("Strategy A (Connections):")
print(week1)
print("\nStrategy B (Engagement):")
print(week2)
print(f"\nSSI Gain - Strategy A: {week1['ssi_end'] - week1['ssi_start']}")
print(f"SSI Gain - Strategy B: {week2['ssi_end'] - week2['ssi_start']}")
```

---

## Scenario 6: Recovery After Account Restriction

**Goal**: Rebuild account trust after LinkedIn restriction

**Configuration**:

```python
# Minimal bot activity
SPEED_FACTOR = 3.0          # Maximum slowness

LIMITS_CONFIG = {
    "CONNECTION": (1, 2),    # Very minimal
    "FOLLOW": (1, 2),
    "PROFILES_SCAN": (5, 10),
    "FEED_POSTS": (5, 15)
}

PROBS = {
    "FEED_LIKE": (0.05, 0.15),
    "FEED_COMMENT": (0, 0.02),
    "GROUP_LIKE": (0.10, 0.20),
    "GROUP_COMMENT": (0, 0)
}

AUTO_REGULATE = False       # Lock in safe settings
CONNECT_WITH_USERS = True   # Bot can still run, but very conservative
```

**Recovery Plan**:
1. **Days 1-5**: Bot disabled, only manual LinkedIn activity
2. **Days 6-10**: Bot with extreme caution (config above)
3. **Days 11+**: Gradually increase if no issues

**Monitoring**:
```python
# Check daily for restrictions
def check_account_health(browser):
    browser.get('https://linkedin.com/me')
    
    # If redirects or shows warning = restricted
    if 'restriction' in browser.page_source.lower():
        print("❌ Account still restricted")
        return False
    
    if 'unusual activity' in browser.page_source.lower():
        print("⚠️ Unusual activity warning")
        return False
    
    print("✓ Account looks healthy")
    return True
```

---

## Scenario 7: Integrated Campaign (Multi-Week)

**Goal**: 12-week campaign to reach 60+ meaningful connections

**Week-by-Week Plan**:

```
Week 1-3 (AQUECIMENTO):
  - Conservative: 2-4 connections/day
  - Focus: Profile optimization, engagement
  - Goal: Establish patterns
  
Week 4-7 (CRESCIMENTO):
  - Moderate: 8-12 connections/day
  - Focus: Target roles, AI comments
  - Goal: Rapid growth
  
Week 8-10 (CRUZEIRO):
  - Balanced: 8-12 connections/day
  - Focus: Relationship nurturing
  - Goal: Maintain momentum
  
Week 11-12 (ELITE):
  - If SSI > 40: High volume 15-20/day
  - Or sustained at Week 8-10 pace
  - Goal: Cross finish line

Expected Result: 60-100 quality connections, SSI +15-20 points
```

**Implementation**:

```python
# bot_v2.py with date-based logic

from datetime import datetime, timedelta

start_date = datetime(2025, 12, 1)
days_running = (datetime.now() - start_date).days

if days_running < 21:
    print("Week 1-3: AQUECIMENTO phase")
    LIMITS_CONFIG["CONNECTION"] = (2, 4)
elif days_running < 49:
    print("Week 4-7: CRESCIMENTO phase")
    LIMITS_CONFIG["CONNECTION"] = (8, 12)
elif days_running < 70:
    print("Week 8-10: CRUZEIRO phase")
    LIMITS_CONFIG["CONNECTION"] = (8, 12)
else:
    print("Week 11-12: ELITE phase")
    LIMITS_CONFIG["CONNECTION"] = (15, 20)
```

---

## Daily Operations Checklist

### Before Each Session

- [ ] Review yesterday's SSI: Check `ssi_history.csv`
- [ ] Inspect bot logs: `cat bot_debug.log | tail -20`
- [ ] Verify database: `sqlite3 bot_data.db "SELECT COUNT(*) FROM interactions;"`
- [ ] Check account health: Log into LinkedIn manually
- [ ] Review configuration: Ensure `LIMITS_CONFIG` is appropriate

### During Execution

```bash
# Monitor in terminal
tail -f bot_debug.log

# In another terminal, monitor database growth
watch -n 5 'sqlite3 bot_data.db "SELECT COUNT(*) FROM interactions;"'
```

### After Session

- [ ] Check SSI change: Compare before/after in dashboard
- [ ] Review interactions: `SELECT * FROM interactions ORDER BY timestamp DESC LIMIT 10;`
- [ ] Note any warnings: Search logs for "unusual activity", "restriction"
- [ ] Update campaign notes: Document results and observations

---

## Troubleshooting by Scenario

### "Connections not working" (Scenario 1-3)

```python
# Test 1: Verify selector
LIMITS_CONFIG["CONNECTION"] = (1, 1)
VERBOSE = True
# Run and check console output
```

### "No SSI growth despite many connections" (Scenario 1)

```python
# SSI grows from quality, not quantity
# Solution: Increase TARGET_ROLES specificity

# Bad (too general):
TARGET_ROLES = ["manager", "engineer"]

# Good (specific):
TARGET_ROLES = ["data engineering manager", "ml lead"]
```

### "Account restricted after first week" (Scenario 2)

```python
# Too aggressive too soon
# Fix: Use AUTO_REGULATE = True
# Or manually limit: LIMITS_CONFIG["CONNECTION"] = (3, 5)
```

---

## Automation Scheduling

**Run bot daily at optimal time**:

```bash
# macOS/Linux: Crontab
0 2 * * * cd /path/to/bot && python bot_v2.py

# Windows: Task Scheduler
# Create task: "Run bot daily at 2 AM"
# Action: python.exe C:\path\to\bot\bot_v2.py
```

---

## Next Steps

1. **Choose a scenario** that matches your goal
2. **Update configuration** in `bot_v2.py`
3. **Test with limits**: Set `LIMITS_CONFIG["CONNECTION"] = (1, 1)` first
4. **Monitor dashboard** throughout campaign
5. **Adjust as needed**: Increase if healthy, decrease if warned

See **[Configuration Guide](./04-CONFIGURATION.md)** for detailed setting descriptions.

---

**Last Updated**: December 6, 2025 | **Examples Version**: 1.0
