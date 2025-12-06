# Configuration Guide

Complete reference for configuring the LinkedIn Bot for different strategies and use cases.

## Control Panel Overview

The main configuration section is in `bot_v2.py` (lines 43-130).

```python
# ⚙️ PAINEL DE CONTROLE INTELIGENTE
```

All settings can be modified without touching core automation logic.

---

## Core Settings

### 1. Operation Mode

#### `AUTO_REGULATE`
Enables intelligent scaling based on account age and SSI score.

**Type**: `bool`
**Default**: `False`
**Values**:
- `True` - Bot auto-adjusts limits and probabilities
- `False` - Uses manual `LIMITS_CONFIG` and `PROBS`

```python
AUTO_REGULATE = False  # Manual mode (fixed limits)
# AUTO_REGULATE = True  # Auto mode (adaptive limits)
```

**Effect on Bot Behavior**:
```
AUTO_REGULATE = False:
  → Uses LIMITS_CONFIG and PROBS as-is
  → Consistent behavior across all days
  → Best for controlled testing

AUTO_REGULATE = True:
  → Reads ssi_history.csv
  → Calculates days_run and last_ssi
  → Applies mode-specific limits:
    - AQUECIMENTO (Days 0-3): Low profile
    - CRESCIMENTO (Days 3-14): Moderate
    - CRUZEIRO (14+ days): Stable
    - ELITE (SSI > 40): High volume
```

---

### 2. Speed & Timing

#### `SPEED_FACTOR`
Multiplier for all delays (safety parameter).

**Type**: `float`
**Default**: `1.5`
**Range**: `0.5` (risky, 2x faster) to `3.0` (very safe, 3x slower)

```python
SPEED_FACTOR = 1.5  # All delays = base_time * 1.5
```

**Examples**:
```python
human_sleep(10, 20)
# With SPEED_FACTOR=1.0: Sleeps 10-20 seconds
# With SPEED_FACTOR=1.5: Sleeps 15-30 seconds (default)
# With SPEED_FACTOR=2.0: Sleeps 20-40 seconds (safest)
```

**Session Duration Impact**:
- `SPEED_FACTOR = 1.0` → 30-40 min session
- `SPEED_FACTOR = 1.5` → 45-60 min session (default)
- `SPEED_FACTOR = 2.0` → 60-90 min session

---

#### `DRIVER_FILENAME`
Path to Edge WebDriver executable.

**Type**: `str`
**Default**: `"msedgedriver.exe"`
**Note**: Must be in project root or specify full path

```python
DRIVER_FILENAME = "msedgedriver.exe"
# Or with full path:
# DRIVER_FILENAME = "C:/drivers/msedgedriver.exe"
```

---

### 3. Content Filtering

#### `FEED_ENGLISH_ONLY`
Filter feed posts to English language only.

**Type**: `bool`
**Default**: `True`

```python
FEED_ENGLISH_ONLY = True  # Only comment on English posts
```

**Implementation**:
```python
if FEED_ENGLISH_ONLY and not is_text_english(post_text):
    continue  # Skip non-English posts
```

---

#### `AI_PERSONA`
Context for AI-generated comments.

**Type**: `str`
**Default**: `"I am a Senior Data Scientist experienced in Python, Databricks, ML and Big Data Strategy."`

```python
AI_PERSONA = "I am a Senior Data Scientist experienced in Python, Databricks, ML and Big Data Strategy."
```

**Used By**: `get_ai_comment()` to generate contextual comments

**Examples**:
```python
# For software engineer
AI_PERSONA = "I'm a fullstack engineer passionate about React, Node.js, and cloud architecture."

# For product manager
AI_PERSONA = "Product leader focused on user-centric design, analytics, and GTM strategy."
```

---

## Limit Configuration

### Manual Limits (`LIMITS_CONFIG`)

Used when `AUTO_REGULATE = False`.

**Type**: `dict`
**Structure**: `{"KEY": (min, max), ...}`

```python
LIMITS_CONFIG = {
    "CONNECTION": (5, 8),      # 5-8 connections per session (random)
    "FOLLOW": (10, 15),        # 10-15 follows per session
    "PROFILES_SCAN": (20, 30), # Scan 20-30 profiles max
    "FEED_POSTS": (30, 50)     # Interact with 30-50 feed posts
}
```

**How It Works**:
```python
CONNECTION_LIMIT = random.randint(5, 8)  # Randomly chosen at session start
# Result: 5, 6, 7, or 8 connections this session
```

### Probability Configuration

**Type**: `dict`
**Structure**: `{"KEY": (min_prob, max_prob), ...}`

```python
PROBS = {
    "FEED_LIKE": (0.20, 0.30),      # 20-30% chance to like feed post
    "FEED_COMMENT": (0.05, 0.15),   # 5-15% chance to comment
    "GROUP_LIKE": (0.40, 0.50),     # 40-50% chance in group posts
    "GROUP_COMMENT": (0.10, 0.15)   # 10-15% chance to comment in group
}
```

**Session-Level Randomization**:
```python
DAILY_LIKE_PROB = random.uniform(0.40, 0.50)
# At session start, picks ONE probability (e.g., 0.47)
# Applied to all group posts this session
```

---

## Target Configuration

### High-Value Keywords

Used to identify profiles worth engaging with.

**Type**: `list[str]`

```python
HIGH_VALUE_KEYWORDS = [
    # Data Science & ML
    "machine learning", "deep learning", "generative ai", "llms", "nlp",
    "reinforcement learning", "data scientist", "ml engineer", "ai specialist",
    
    # Big Data & Cloud
    "apache spark", "databricks", "hadoop", "cloud architect", 
    "aws", "gcp", "azure", "data engineer", "etl", "big data analytics",
    
    # Engineering & DevOps
    "data governance", "data quality", "data catalog", 
    "software engineer", "backend development", "python development", "datamodelling"
]
```

**Usage**: Profiles containing these keywords in headline are prioritized for engagement.

---

### Target Roles

Roles to actively connect with (filtered by profile headline).

**Type**: `list[str]`

```python
TARGET_ROLES = [
    # Leadership & Executives
    "chief data officer", "cdo", "chief technology officer", "cto", 
    "vp of engineering", "vp of data", "head of data", "head of analytics",
    
    # Senior Specialists (Influence)
    "lead data scientist", "staff data scientist", "principal data scientist",
    "senior data scientist", "data science manager", "ml engineering lead",
    
    # Recruitment & HR
    "tech recruiter", "technical recruiter", "talent acquisition"
]
```

**Matching Logic** (case-insensitive):
```python
if any(role in headline.lower() for role in TARGET_ROLES):
    connect_with_user(browser, name, headline, group)
```

---

### Quick Connect Limit

**Type**: `int`
**Default**: `10`

```python
QUICK_CONNECT_LIMIT = 10  # Send 10 quick connects before main loop
```

---

## General Settings

### Connection & Follow Toggle

#### `CONNECT_WITH_USERS`
Enable/disable sending connection requests.

**Type**: `bool`
**Default**: `True`

```python
CONNECT_WITH_USERS = True  # Send connection requests
# CONNECT_WITH_USERS = False  # Observation mode only
```

---

#### `SAVECSV`
Save session logs to CSV.

**Type**: `bool`
**Default**: `True`

```python
SAVECSV = True  # Create CSV/GroupBot-{timestamp}.csv
```

---

#### `VERBOSE`
Print debug information to console.

**Type**: `bool`
**Default**: `True`

```python
VERBOSE = True  # Print detailed logs
# VERBOSE = False  # Minimal output
```

---

### AI & Messaging

#### `SEND_AI_NOTE`
Send AI-generated note with connection request.

**Type**: `int`
**Values**: `0` (no) or `1` (yes)
**Default**: `0`

```python
SEND_AI_NOTE = 0  # Direct connection request (default)
# SEND_AI_NOTE = 1  # Send personalized note with each connection
```

**Impact**: 
- With notes: Longer per-connection time, higher acceptance rates
- Without notes: Faster connections, more volume

---

## LinkedIn Groups List

Pre-configured list of target groups.

**Type**: `list[str]`
**Count**: 13 groups (randomly selected each session)

```python
LINKEDIN_GROUPS_LIST = [
    "https://www.linkedin.com/groups/3732032/",
    "https://www.linkedin.com/groups/3063585/",
    "https://www.linkedin.com/groups/3990648/",
    "https://www.linkedin.com/groups/35222/",
    "https://www.linkedin.com/groups/45655/",
    # ... 8 more groups
]
```

**Selection**:
```python
random_key = random.randint(0, len(LINKEDIN_GROUPS_LIST) - 1)
GROUP_URL = LINKEDIN_GROUPS_LIST[random_key]
# Each session, randomly picks ONE group from the list
```

---

## Configuration Examples

### Example 1: Aggressive Growth Mode

```python
AUTO_REGULATE = True  # Auto-scale
SPEED_FACTOR = 1.0   # Faster (riskier)

LIMITS_CONFIG = {
    "CONNECTION": (15, 20),
    "FOLLOW": (20, 25),
    "PROFILES_SCAN": (50, 75),
    "FEED_POSTS": (75, 100)
}

PROBS = {
    "FEED_LIKE": (0.60, 0.80),
    "FEED_COMMENT": (0.30, 0.50),
    "GROUP_LIKE": (0.70, 0.90),
    "GROUP_COMMENT": (0.20, 0.30)
}

SEND_AI_NOTE = 1  # Personalize with notes
CONNECT_WITH_USERS = True
```

**Result**: ~20-30 connections/session, high engagement, higher detection risk

---

### Example 2: Conservative/Stealth Mode

```python
AUTO_REGULATE = False  # Manual control
SPEED_FACTOR = 2.5    # Very slow (safer)

LIMITS_CONFIG = {
    "CONNECTION": (2, 3),
    "FOLLOW": (3, 5),
    "PROFILES_SCAN": (10, 15),
    "FEED_POSTS": (10, 20)
}

PROBS = {
    "FEED_LIKE": (0.10, 0.20),
    "FEED_COMMENT": (0.02, 0.05),
    "GROUP_LIKE": (0.15, 0.25),
    "GROUP_COMMENT": (0.03, 0.08)
}

SEND_AI_NOTE = 0  # No notes
FEED_ENGLISH_ONLY = True
VERBOSE = False  # Minimal logging
```

**Result**: ~2-3 connections/session, low engagement, very stealthy

---

### Example 3: Balanced/Default Mode

```python
AUTO_REGULATE = True
SPEED_FACTOR = 1.5  # Standard

LIMITS_CONFIG = {
    "CONNECTION": (8, 12),
    "FOLLOW": (12, 18),
    "PROFILES_SCAN": (25, 40),
    "FEED_POSTS": (30, 50)
}

PROBS = {
    "FEED_LIKE": (0.30, 0.50),
    "FEED_COMMENT": (0.10, 0.20),
    "GROUP_LIKE": (0.40, 0.60),
    "GROUP_COMMENT": (0.10, 0.15)
}

SEND_AI_NOTE = 0
CONNECT_WITH_USERS = True
SAVECSV = True
```

**Result**: ~8-12 connections/session, balanced engagement, moderate risk

---

## Environment Variables (Optional)

### Chromebook/Docker Deployments

```bash
export LINKEDIN_BOT_SPEED_FACTOR=2.0
export LINKEDIN_BOT_AUTO_REGULATE=true
export LINKEDIN_BOT_LIMIT_CONNECTIONS=5

python bot_v2.py
```

**Code to support**:
```python
import os

AUTO_REGULATE = os.getenv('LINKEDIN_BOT_AUTO_REGULATE', 'False') == 'true'
SPEED_FACTOR = float(os.getenv('LINKEDIN_BOT_SPEED_FACTOR', 1.5))
```

---

## Debugging Configuration

### Enable Detailed Logging

```python
VERBOSE = True
# Prints: [1/25] Perfil: ..., -> [ALVO] Conectando ..., etc.
```

### Test with Minimal Load

```python
LIMITS_CONFIG = {
    "CONNECTION": (1, 1),      # Test 1 connection
    "FOLLOW": (1, 1),
    "PROFILES_SCAN": (3, 3),   # Scan just 3 profiles
    "FEED_POSTS": (5, 5)
}
```

### Observation Mode

```python
CONNECT_WITH_USERS = False     # Don't actually send requests
FEED_COMMENT_PROB = (0, 0)     # No comments
SEND_AI_NOTE = 0
```

---

## Configuration Validation

**Before running bot**, verify settings:

```python
# Check critical values aren't 0
assert LIMITS_CONFIG["CONNECTION"][1] > 0, "CONNECTION limit must be > 0"
assert SPEED_FACTOR > 0, "SPEED_FACTOR must be positive"

# Check driver exists
import os
assert os.path.exists(DRIVER_FILENAME), f"{DRIVER_FILENAME} not found"

# Validate ranges
for key, (min_val, max_val) in LIMITS_CONFIG.items():
    assert min_val <= max_val, f"{key}: min must be <= max"
```

---

## Common Configuration Mistakes

| ❌ Wrong | ✓ Correct | Issue |
|---------|-----------|-------|
| `SPEED_FACTOR = 0` | `SPEED_FACTOR = 1.5` | Zero causes infinite wait |
| `LIMITS_CONFIG = {"CONNECTION": 5}` | `LIMITS_CONFIG = {"CONNECTION": (3, 5)}` | Must be tuple range |
| `AUTO_REGULATE = "True"` | `AUTO_REGULATE = True` | Must be bool, not string |
| `DRIVER_FILENAME = "edge.exe"` | `DRIVER_FILENAME = "msedgedriver.exe"` | Wrong driver name |
| Modify `LIMITS_CONFIG` mid-session | Modify before `start_browser()` | Changes ignored after init |

---

## Next Steps

1. **Choose a profile** (aggressive/balanced/conservative)
2. **Update `LIMITS_CONFIG` and `PROBS`**
3. **Set `AUTO_REGULATE`** (True recommended)
4. **Test with `VERBOSE = True`**
5. **Monitor dashboard** for results
6. **Adjust if needed** for next run

See **[API Reference](./02-API_REFERENCE.md)** for function details.

---

**Last Updated**: December 6, 2025 | **Configuration Version**: 1.0
