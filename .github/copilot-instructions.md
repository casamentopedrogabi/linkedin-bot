# LinkedIn Bot AI Coding Instructions

## Project Overview
This is a **LinkedIn engagement automation bot** that autonomously builds professional networks through strategic interactions. The system has three integrated components:

1. **Core Bot** (`bot_v2.py`) - Selenium-based automation engine
2. **Analytics Dashboard** (`dashboard_app.py`) - Streamlit visualization of SSI metrics and engagement
3. **Auxiliary Scripts** (`d.py`, `database_manager.py`) - Profile scraping and data persistence

## Critical Architecture Patterns

### 1. **Dual Database Strategy**
- **SQLite** (`bot_data.db`, `linkedin_data.db`) - Primary for structured data (interactions, analytics)
- **CSV** (`ssi_history.csv`) - Legacy format for historical SSI tracking; still used for dashboard charting
- **Text Files** (`visitedUsers.txt`, `commentedPosts.txt`) - Fallback session tracking
- **Pattern**: Always check both SQLite and CSV when querying engagement history. Dashboard reads both sources.

```python
# Example: Always query SSI from CSV first, then cross-reference SQLite
df = pd.read_csv("ssi_history.csv")  # Historical SSI trends
conn = sqlite3.connect(DB_NAME)      # Current session interactions
```

### 2. **Auto-Regulation Engine** (Pillar of Design)
The bot implements **adaptive behavior** using `calculate_smart_parameters()`:
- **4 operational modes** based on days_run and current SSI:
  - `AQUECIMENTO` (0-3 days): Low profile, safety-first
  - `CRESCIMENTO` (3-14 days): Moderate engagement
  - `CRUZEIRO` (14+ days, SSI < 40): Stable professional behavior
  - `ELITE` (SSI > 40): High-volume networking for influencers
- **Dynamic limits** for connections, follows, profiles scanned, feed posts
- **Dynamic engagement probabilities** for likes, comments across feed/groups
- **Fallback**: Manual `LIMITS_CONFIG` and `PROBS` dicts if `AUTO_REGULATE = False`

**Critical**: Any engagement feature must respect current mode. Check `LIMITS_CONFIG`, `PROBS`, and `SESSION_*_COUNT` globals.

### 3. **Stealth & Anti-Detection**
- **Edge browser** with randomized window sizes (`1024-1920` x `768-1080`)
- **Human-like typing** with 4% error rate and 60-280ms keystroke variance
- **Random mouse movements** and scroll patterns
- **Langdetect integration** for filtering non-English content (`FEED_ENGLISH_ONLY`)
- **Randomized delays**: `human_sleep()` with `SPEED_FACTOR` multiplier, `sleep_after_connection()` for 45-90s pauses
- **Pattern**: Always call `human_sleep()`, never use bare `time.sleep()`. Always apply language filters before commenting.

### 4. **AI-Powered Comment Generation**
- Uses `g4f.client.Client` (free GPT via g4f) with fallback if unavailable
- `AI_PERSONA` global sets context (e.g., "Senior Data Scientist experienced in Python...")
- Comments generated via `get_ai_comment()` for group posts
- **Risk**: AI comments must be concise and English-only. Failures are silent (try/except blocks).

## Data Flow & Workflows

### Primary Bot Flow (Start → Execution Loop)
```
start_browser()
  ├─ run_quick_connects() → Bypass connection limits via search
  ├─ interact_with_feed_human() → Like/comment on feed posts, collect profiles
  ├─ random_browsing_habit() → Stay unpredictable
  ├─ run_networker() & run_reciprocator() → Relationship boosters
  ├─ withdraw_old_invites() → Clean up pending (optional)
  └─ run_main_bot_logic() → Main group loop + sniper targeting
     ├─ collect_sniper_targets() → Extract profiles from group posts
     ├─ Log all interactions → log_interaction_db()
     └─ Respect SESSION_*_COUNT limits
```

### Dashboard Data Pipeline
```
load_data()
  ├─ Read "ssi_history.csv" → SSI trends over time
  ├─ Query "bot_data.db" (interactions table) → Session engagement
  ├─ Query "bot_data.db" (profile_analytics table) → Profile views/impressions
  └─ Render 30+ plots with Heineken color scheme
```

### Logging Pattern (Critical for Debugging)
- **Every profile visit**: `log_interaction_db(url, name, headline, source, status)`
  - Status values: "Visited", "Connected", "Followed"
  - Also written to `visitedUsers.txt` as fallback
  - CSV logged via `add_to_csv()` to dated files in `/CSV` folder
- **Analytics snapshots**: `log_analytics_db(views, impressions, searches, followers)`
- **SSI history**: `log_ssi()` (exists in `database_manager.py` but may be unused in main)

## Project-Specific Conventions

### 1. **Global State Management**
- **Session counters** reset per run: `SESSION_CONNECTION_COUNT`, `SESSION_FOLLOW_COUNT`, `SESSION_WITHDRAWN_COUNT`
- **Configuration overrides**: Set `AUTO_REGULATE = True` to auto-scale, or manually tune `LIMITS_CONFIG` and `PROBS`
- **Target filtering**: `TARGET_ROLES` and `HIGH_VALUE_KEYWORDS` define who to prioritize
- **Group rotation**: `LINKEDIN_GROUPS_LIST` provides 13 groups; random selection via `GROUP_URL = LINKEDIN_GROUPS_LIST[random_key]`

### 2. **Error Handling Strategy**
- **Silent failures preferred** for non-critical operations (wrapped in try/except → pass)
- **Critical errors bubble up**: Invalid session ID in `run_main_bot_logic()` triggers browser restart
- **No logging library**: All output via `print()` with emoji prefixes (e.g., `"🤖 Bot Started."`)

### 3. **Timing & Performance**
- `SPEED_FACTOR = 1.5` multiplier on all delays (default = 1.5x slower for safety)
- `DRIVER_FILENAME = "msedgedriver.exe"` must be in root directory
- Typical session runtime: 30-60 minutes depending on mode
- **Setup**: Run `setup.sh` (if present) to initialize environment

### 4. **File Organization**
- **Root scripts**: `bot_v2.py` (main), `dashboard_app.py` (UI), `d.py` (scraper utility), `database_manager.py` (DB helpers)
- **Data**: `CSV/` folder stores timestamped session logs; `ssi_history.csv` is master trend file
- **Browser profile**: `perfil_robo_edge/` stores Edge credentials and history (not versioned)
- **Dependencies**: See `requirements.txt` (selenium, pandas, g4f, langdetect, streamlit, plotly)

## AI Agent Quick Start Checklist

When enhancing this codebase:
- [ ] **Respect AUTO_REGULATE mode** - Don't hardcode behavior if auto-scaling is active
- [ ] **Use `human_sleep()` everywhere** - Never raw `time.sleep()`
- [ ] **Log interactions** - Call `log_interaction_db()` for every profile visit
- [ ] **Check session limits** - Verify `SESSION_*_COUNT < LIMIT` before major actions
- [ ] **Filter by language/keywords** - Apply `FEED_ENGLISH_ONLY` and `is_text_english()` before commenting
- [ ] **Handle g4f failures gracefully** - AI comments optional, not required for core flow
- [ ] **Test with small datasets first** - Use `END_PAGE = 1`, `MAX_LIMIT = 5` in `d.py`
- [ ] **Reference Heineken colors** in new UI: `#286529` (dark green), `#ca2819` (red), `#8ebf48` (lime)

## Key Files Reference

| File | Purpose | Key Functions |
|------|---------|---|
| `bot_v2.py` | Core automation engine | `run_main_bot_logic()`, `interact_with_feed_human()`, `calculate_smart_parameters()` |
| `dashboard_app.py` | Analytics UI | `load_data()`, 30+ plot functions, KPI section |
| `database_manager.py` | DB abstractions | `init_db()`, `log_interaction()`, `log_ssi()` |
| `d.py` | Scraper utility | Profile link extraction, pagination logic |
| `requirements.txt` | Dependencies | selenium, pandas, g4f, langdetect, streamlit, plotly |

---
**Last Updated**: December 6, 2025 | **Target Audience**: AI Coding Agents
