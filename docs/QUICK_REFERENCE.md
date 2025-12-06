# 📋 Quick Reference Card

One-page cheat sheet for common tasks.

---

## 🚀 Getting Started (5 min)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Download msedgedriver.exe matching your Edge version
# Save to project root directory

# 3. Run bot
python bot_v2.py

# 4. View dashboard (in another terminal)
streamlit run dashboard_app.py
# Opens: http://localhost:8501
```

---

## ⚙️ Essential Configuration

**In `bot_v2.py` (lines 43-130)**:

```python
# Safety/Speed
AUTO_REGULATE = True      # Intelligent scaling
SPEED_FACTOR = 1.5        # 1.5x slower = safer (1.0-3.0)

# Limits (random range per session)
LIMITS_CONFIG = {
    "CONNECTION": (8, 12),
    "FOLLOW": (12, 18),
    "PROFILES_SCAN": (25, 40),
    "FEED_POSTS": (30, 50)
}

# Engagement rates (probability)
PROBS = {
    "FEED_LIKE": (0.30, 0.50),
    "FEED_COMMENT": (0.10, 0.20),
    "GROUP_LIKE": (0.40, 0.60),
    "GROUP_COMMENT": (0.10, 0.15)
}

# Targets
TARGET_ROLES = ["data scientist", "cto", "vp of data"]
HIGH_VALUE_KEYWORDS = ["machine learning", "databricks", "python"]

# General
CONNECT_WITH_USERS = True
SAVECSV = True
VERBOSE = True
SEND_AI_NOTE = 0  # 0=no note, 1=send AI-generated note
```

---

## 📊 Key Functions

| Function | What It Does | Example |
|----------|-------------|---------|
| `start_browser()` | Run complete session | `start_browser()` |
| `run_main_bot_logic()` | Scan group + connect | Called automatically |
| `interact_with_feed_human()` | Like/comment feed | Called automatically |
| `human_sleep()` | Safe pause (always use this!) | `human_sleep(5, 10)` |
| `log_interaction_db()` | Record action | `log_interaction_db(url, name, headline, "Group", "Connected")` |
| `calculate_smart_parameters()` | Auto-scale behavior | Called if AUTO_REGULATE=True |

---

## 💾 Database Queries

```bash
# Open database
sqlite3 bot_data.db

# Count all interactions
SELECT COUNT(*) FROM interactions;

# Today's connections
SELECT * FROM interactions 
WHERE DATE(timestamp)=DATE('now') AND status='Connected';

# Engagement by source
SELECT source, COUNT(*) FROM interactions GROUP BY source;

# Role targeting effectiveness
SELECT headline, COUNT(*) as connections 
FROM interactions 
WHERE status='Connected' 
GROUP BY headline 
ORDER BY connections DESC LIMIT 5;

# Check SSI history
SELECT date, total_ssi FROM ssi_history 
ORDER BY date DESC LIMIT 7;
```

---

## 🎯 Configuration Presets

### Conservative (Low Risk)
```python
SPEED_FACTOR = 2.5
LIMITS_CONFIG = {"CONNECTION": (2, 3), "FOLLOW": (3, 5), "PROFILES_SCAN": (10, 15), "FEED_POSTS": (10, 20)}
PROBS = {"FEED_LIKE": (0.05, 0.15), "FEED_COMMENT": (0, 0.05), ...}
```

### Balanced (Recommended)
```python
SPEED_FACTOR = 1.5
LIMITS_CONFIG = {"CONNECTION": (8, 12), "FOLLOW": (12, 18), "PROFILES_SCAN": (25, 40), "FEED_POSTS": (30, 50)}
PROBS = {"FEED_LIKE": (0.30, 0.50), "FEED_COMMENT": (0.10, 0.20), ...}
```

### Aggressive (High Risk/Reward)
```python
SPEED_FACTOR = 1.0
LIMITS_CONFIG = {"CONNECTION": (15, 20), "FOLLOW": (20, 30), "PROFILES_SCAN": (50, 80), "FEED_POSTS": (80, 120)}
PROBS = {"FEED_LIKE": (0.60, 0.80), "FEED_COMMENT": (0.30, 0.50), ...}
```

---

## 🐛 Troubleshooting Quick Fixes

| Problem | Solution |
|---------|----------|
| **"msedgedriver not found"** | Download from https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/, save to root |
| **"No interactions logged"** | Check `LIMITS_CONFIG` values (not 0), verify database exists |
| **"Bot very slow"** | Reduce `SPEED_FACTOR` (1.5 → 1.0), reduce `CONNECTION` limit |
| **"Account restricted"** | Set `SPEED_FACTOR = 3.0`, reduce all limits by 50%, wait 3 days |
| **"Invalid Session ID"** | Browser crashed - bot auto-restarts, check logs for errors |
| **"Database locked"** | Close other processes using bot_data.db |

---

## 📈 Monitoring Checklist

Daily:
- [ ] Check SSI score (LinkedIn profile)
- [ ] View dashboard: `streamlit run dashboard_app.py`
- [ ] Query interactions: `SELECT COUNT(*) FROM interactions WHERE DATE(timestamp)=DATE('now')`

Weekly:
- [ ] Review SSI trend in dashboard
- [ ] Check engagement by source
- [ ] Analyze role-wise connection success rates

---

## 🔄 Operational Modes

Bot automatically switches based on `days_run` and `SSI`:

| Mode | Days | SSI | Connections/Day | Comments | Strategy |
|------|------|-----|-----------------|----------|----------|
| AQUECIMENTO | 0-3 | - | 3-6 | 5-15% | Low profile |
| CRESCIMENTO | 3-14 | - | 10 | 0% | Ramp up |
| CRUZEIRO | 14+ | <40 | 10-15 | 25-35% | Steady |
| ELITE | - | >40 | 15-20 | 35-50% | High volume |

---

## 📝 Code Patterns (Copy-Paste)

### Adding a limit check
```python
if SESSION_CONNECTION_COUNT < CONNECTION_LIMIT:
    # Do something
    SESSION_CONNECTION_COUNT += 1
```

### Logging an interaction
```python
log_interaction_db(
    url="https://linkedin.com/in/user",
    name="User Name",
    headline="Role",
    source="Group",  # or "Feed", "QuickConnect"
    status="Connected"  # or "Followed", "Visited"
)
```

### Human-like pause
```python
human_sleep(5, 10)  # Always use this, never time.sleep()
```

### Language filtering
```python
if FEED_ENGLISH_ONLY and is_text_english(post_text):
    # Engage with post
    pass
```

### AI commenting
```python
comment = get_ai_comment(post_text)
if comment and perform_comment(browser, post, comment):
    log_interaction_db(url, name, headline, source, "Commented")
```

---

## 🗂️ Important Files

| File | Purpose | Size |
|------|---------|------|
| `bot_v2.py` | Main automation | 2100 lines |
| `dashboard_app.py` | Analytics UI | 326 lines |
| `database_manager.py` | DB utilities | 95 lines |
| `d.py` | Scraper | 146 lines |
| `bot_data.db` | Main database | ~5MB |
| `ssi_history.csv` | SSI trends | ~50KB |

---

## 📚 Documentation Locations

- **Overall guide**: `README.md`
- **Quick start**: `README.md` → Usage
- **All settings**: `docs/wiki/04-CONFIGURATION.md`
- **All functions**: `docs/wiki/02-API_REFERENCE.md`
- **Database**: `docs/wiki/03-DATABASE_SCHEMA.md`
- **Issues**: `docs/wiki/06-TROUBLESHOOTING.md`
- **Examples**: `docs/wiki/08-EXAMPLES_SCENARIOS.md`
- **Index**: `docs/wiki/INDEX.md`

---

## ⚡ Pro Tips

1. **Always use `human_sleep()`**, never bare `time.sleep()`
2. **Set `VERBOSE = True`** when testing new config
3. **Start with `LIMITS_CONFIG["CONNECTION"] = (1, 1)`** to test
4. **Monitor SSI after each session** - should see +0.3-0.5 per day
5. **Use `AUTO_REGULATE = True`** - it's smarter than manual
6. **Space sessions 48h apart** - gives LinkedIn time to register changes
7. **Export data weekly** - backup important metrics
8. **Test edge cases** - what if no profiles found? Page doesn't load?

---

## 🎮 Quick Commands

```bash
# Run bot
python bot_v2.py

# Launch dashboard
streamlit run dashboard_app.py

# Run scraper
python d.py

# Query database
sqlite3 bot_data.db "SELECT COUNT(*) FROM interactions;"

# View recent interactions
sqlite3 bot_data.db "SELECT * FROM interactions ORDER BY timestamp DESC LIMIT 5;"

# Export to CSV
sqlite3 bot_data.db ".mode csv" "SELECT * FROM interactions;" > export.csv

# Clear old data (backup first!)
sqlite3 bot_data.db "DELETE FROM interactions WHERE DATE(timestamp) < DATE('now', '-90 days');"
```

---

## 📊 Expected Performance

### Conservative Setup
- **Connections/day**: 2-4
- **Session duration**: 60-90 min
- **SSI gain/week**: +1-2 points
- **Risk level**: Low
- **Best for**: Accounts <3 months old

### Balanced Setup
- **Connections/day**: 8-12
- **Session duration**: 45-60 min
- **SSI gain/week**: +3-5 points
- **Risk level**: Medium
- **Best for**: Most situations

### Aggressive Setup
- **Connections/day**: 15-25
- **Session duration**: 30-45 min
- **SSI gain/week**: +5-8 points
- **Risk level**: High
- **Best for**: Established accounts only

---

## 🆘 Emergency Procedures

**If account gets restricted**:
```python
# 1. Disable bot immediately
# 2. Log in manually to verify
# 3. Set conservative config:
SPEED_FACTOR = 3.0
LIMITS_CONFIG = {"CONNECTION": (1, 1), "FOLLOW": (1, 1), ...}
# 4. Wait 3-5 days before resuming
# 5. Run with very low limits for 1 week
```

**If bot crashes**:
- Check: `SELECT COUNT(*) FROM interactions;` to see what was logged
- Restart: `python bot_v2.py`
- Bot auto-resumes from where it stopped

**If no data logged**:
- Verify: `sqlite3 bot_data.db ".tables"` (should show tables)
- Check: `LIMITS_CONFIG` values (should be > 0)
- Force init: `python -c "from bot_v2 import init_db; init_db()"`

---

**Last Updated**: December 6, 2025

For detailed help, see `docs/wiki/INDEX.md`
