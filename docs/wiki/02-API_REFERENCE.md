# API Reference

Comprehensive function reference for all major components in the LinkedIn Bot.

## Core Bot Functions (`bot_v2.py`)

### Initialization & Lifecycle

#### `init_db()`
Creates SQLite database schema for interactions and analytics.

**Signature**:
```python
def init_db() -> None
```

**Creates Tables**:
- `interactions` - Profile visit logs
- `profile_analytics` - Dashboard metrics
- `ssi_history` - SSI trend tracking

**Example**:
```python
init_db()  # Auto-called on script load
```

---

#### `start_browser()`
Initializes Edge WebDriver with stealth configuration, then runs complete bot workflow.

**Signature**:
```python
def start_browser() -> None
```

**Workflow**:
1. Kill existing Edge processes
2. Configure EdgeOptions (stealth, randomized window size)
3. Initialize WebDriver with `msedgedriver.exe`
4. Execute automation sequence:
   - `run_quick_connects()`
   - `interact_with_feed_human()`
   - `random_browsing_habit()`
   - `run_networker()`, `run_reciprocator()`
   - `run_main_bot_logic()`
5. Gracefully close browser

**Example**:
```python
if __name__ == "__main__":
    start_browser()
```

**Error Handling**:
- Catches invalid session errors, auto-restarts browser
- Re-raises critical errors to halt execution
- Ensures browser.quit() called even on exception

---

### Main Automation Functions

#### `run_main_bot_logic(browser, sniper_targets=None)`
Primary automation loop: Scans LinkedIn group, collects profiles, connects/follows based on criteria.

**Signature**:
```python
def run_main_bot_logic(browser, sniper_targets=None) -> None
```

**Parameters**:
- `browser` (WebDriver) - Active Selenium WebDriver
- `sniper_targets` (list, optional) - Pre-filtered profile URLs

**Workflow**:
```
1. Navigate to GROUP_URL (random group from LINKEDIN_GROUPS_LIST)
2. Loop through group posts (max PROFILES_TO_SCAN)
   └─ Extract profile links from post authors
3. For each profile URL:
   ├─ Load profile page
   ├─ Extract: name, headline, profile_views
   ├─ Evaluate role keywords against TARGET_ROLES
   ├─ If target role:
   │  └─ Connect (if SESSION_CONNECTION_COUNT < CONNECTION_LIMIT)
   ├─ Else if top profile:
   │  └─ Follow (if SESSION_FOLLOW_COUNT < FOLLOW_LIMIT)
   └─ Log result: log_interaction_db()
4. Stop when limits reached or max pages scanned
```

**Example**:
```python
# Called from start_browser()
run_main_bot_logic(browser)
# Expected console output:
# [1/25] Perfil: John Doe | data scientist
#    -> [ALVO] Conectando (0/10)...
#    -> [SUCCESS] Conectado. Total: 1/10
```

**Limits**:
- `CONNECTION_LIMIT` - Max connections per session
- `FOLLOW_LIMIT` - Max follows per session
- `PROFILES_TO_SCAN` - Max profiles to visit

---

#### `interact_with_feed_human(browser)`
Engages with LinkedIn feed: likes/comments posts, collects profile links.

**Signature**:
```python
def interact_with_feed_human(browser) -> None
```

**Actions**:
1. Navigate to `https://www.linkedin.com/feed/`
2. Scroll through posts (max `FEED_POSTS_LIMIT`)
3. For each post:
   - **Like**: Probability = `FEED_LIKE_PROB`
   - **Comment**: Probability = `FEED_COMMENT_PROB`
   - **Collect profiles**: Extract author URL if matches high-value keywords
4. Human-like delays between actions

**Example**:
```python
interact_with_feed_human(browser)
# Internally performs:
# - human_scroll(browser)
# - perform_reaction_varied(browser, post)
# - get_ai_comment(post.text)
# - perform_comment(browser, post, comment)
```

---

#### `run_quick_connects(browser, limit, keywords, base_url)`
Bypasses daily connection limit by using LinkedIn search filters.

**Signature**:
```python
def run_quick_connects(browser, limit, keywords, base_url) -> None
```

**Parameters**:
- `browser` (WebDriver) - Active Selenium WebDriver
- `limit` (int) - Max quick connects (e.g., 10)
- `keywords` (list) - Target roles to search for
- `base_url` (str) - Search URL with filters

**Example**:
```python
run_quick_connects(
    browser,
    limit=QUICK_CONNECT_LIMIT,
    keywords=TARGET_ROLES,
    base_url=BASE_QUICK_CONNECT_URL
)
# Performs 10 "Quick Connections" via search results
```

---

### Interaction Functions

#### `connect_with_user(browser, name, headline, group_name) -> bool`
Sends connection request to a profile.

**Signature**:
```python
def connect_with_user(browser, name, headline, group_name) -> bool
```

**Parameters**:
- `browser` (WebDriver) - Active Selenium WebDriver
- `name` (str) - User's display name
- `headline` (str) - User's headline (role)
- `group_name` (str) - Group where profile was found

**Returns**:
- `True` - Connection sent successfully
- `False` - Connection failed or already pending

**Logs**:
```python
SESSION_CONNECTION_COUNT += 1
log_interaction_db(url, name, headline, "Group", "Connected")
```

**Example**:
```python
if connect_with_user(browser, "Jane Smith", "Data Scientist", "AI Group"):
    print("✓ Connected")
    SESSION_CONNECTION_COUNT += 1
```

---

#### `follow_user(browser) -> bool`
Follows a profile (boosts SSI).

**Signature**:
```python
def follow_user(browser) -> bool
```

**Returns**:
- `True` - Follow successful
- `False` - Already following or error

**Example**:
```python
if follow_user(browser):
    SESSION_FOLLOW_COUNT += 1
```

---

#### `perform_reaction_varied(browser, post_element) -> bool`
Likes a post with random variation (sometimes skips).

**Signature**:
```python
def perform_reaction_varied(browser, post_element) -> bool
```

**Example**:
```python
if random.random() < FEED_LIKE_PROB:
    perform_reaction_varied(browser, post)
```

---

#### `perform_comment(browser, post_element, comment_text) -> bool`
Comments on a post with human-like typing.

**Signature**:
```python
def perform_comment(browser, post_element, comment_text) -> bool
```

**Example**:
```python
comment = get_ai_comment(post_text)
if perform_comment(browser, post, comment):
    save_commented_post(urn)
```

---

### Utility Functions

#### `human_sleep(min_seconds=2, max_seconds=5) -> None`
Randomized delay simulating human behavior.

**Signature**:
```python
def human_sleep(min_seconds=2, max_seconds=5) -> None
```

**Implementation**:
```python
def human_sleep(min_seconds=2, max_seconds=5):
    base_time = random.uniform(min_seconds, max_seconds)
    time.sleep(get_factored_time(base_time))
```

**IMPORTANT**: Always use instead of `time.sleep()`.

**Example**:
```python
# Safe - uses SPEED_FACTOR
human_sleep(5, 10)

# Avoid - no randomization
time.sleep(7)
```

---

#### `get_factored_time(seconds) -> float`
Multiplies delay by `SPEED_FACTOR` for safety.

**Signature**:
```python
def get_factored_time(seconds) -> float
```

**Formula**: `seconds * SPEED_FACTOR`

**Example**:
```python
# With SPEED_FACTOR = 1.5
get_factored_time(10)  # Returns 15.0
```

---

#### `sleep_after_connection()`
Extended pause simulating reading profile (45-90 seconds).

**Signature**:
```python
def sleep_after_connection() -> None
```

**Example**:
```python
if connect_with_user(browser, name, headline, group):
    sleep_after_connection()  # Simulates reading profile
```

---

#### `human_type(element, text) -> None`
Types text with 4% error rate and variable keystroke speed.

**Signature**:
```python
def human_type(element, text) -> None
```

**Features**:
- 4% chance of typo per character
- Keystroke delay: 60-280ms
- Auto-corrects typos with backspace

**Example**:
```python
# Sends connection note with human typing
note_field = browser.find_element(By.ID, "note-input")
human_type(note_field, "I'd love to connect!")
```

---

#### `human_scroll(browser) -> None`
Scrolls page with random patterns and mouse movements.

**Signature**:
```python
def human_scroll(browser) -> None
```

**Example**:
```python
human_scroll(browser)  # Scrolls 3-7 times with delays
```

---

#### `is_text_english(text) -> bool`
Detects if text is English using `langdetect`.

**Signature**:
```python
def is_text_english(text) -> bool
```

**Returns**:
- `True` - Detected as English
- `False` - Different language or error

**Example**:
```python
if FEED_ENGLISH_ONLY and not is_text_english(post_text):
    continue  # Skip non-English posts
```

---

#### `get_ai_comment(post_text) -> str`
Generates contextual comment using g4f AI.

**Signature**:
```python
def get_ai_comment(post_text) -> str
```

**Parameters**:
- `post_text` (str) - Post content to comment on

**Returns**:
- Comment text (str, 1-2 sentences)

**Fallback**: Returns empty string if AI unavailable

**Example**:
```python
comment = get_ai_comment("Great insights on machine learning!")
if comment:
    perform_comment(browser, post, comment)
```

---

### Data Logging Functions

#### `log_interaction_db(url, name, headline, source, status) -> None`
Logs profile interaction to SQLite database.

**Signature**:
```python
def log_interaction_db(url, name, headline, source, status) -> None
```

**Parameters**:
- `url` (str) - Profile URL
- `name` (str) - User name
- `headline` (str) - User's headline/role
- `source` (str) - Where profile came from ("Group", "Feed", "QuickConnect")
- `status` (str) - Action taken ("Visited", "Connected", "Followed")

**Example**:
```python
log_interaction_db(
    "https://linkedin.com/in/johndoe",
    "John Doe",
    "Senior Data Scientist",
    "Group",
    "Connected"
)
```

---

#### `log_analytics_db(views, impressions, searches, followers) -> None`
Logs profile analytics snapshot.

**Signature**:
```python
def log_analytics_db(views, impressions, searches, followers) -> None
```

**Parameters**:
- `views` (int) - Profile views this month
- `impressions` (int) - Post impressions
- `searches` (int) - Search appearances
- `followers` (int) - Current follower count

**Example**:
```python
log_analytics_db(
    views=150,
    impressions=1200,
    searches=45,
    followers=5000
)
```

---

#### `add_to_csv(data, time_str) -> None`
Appends row to session CSV log.

**Signature**:
```python
def add_to_csv(data, time_str) -> None
```

**Parameters**:
- `data` (list) - [name, url, status, timestamp, connection_limit, follow_limit, ...]
- `time_str` (str) - Session timestamp (format: "HH-MM-SS-MICROSECONDS")

**Example**:
```python
add_to_csv([
    "John Doe",
    "/in/johndoe",
    "Connected",
    "14:47:30",
    10, 15, 0.25, 0.10, 20
], TIME)
```

---

### Configuration Functions

#### `calculate_smart_parameters() -> tuple[dict, dict]`
Calculates adaptive limits and probabilities based on SSI history.

**Signature**:
```python
def calculate_smart_parameters() -> tuple[dict, dict]
```

**Returns**: `(limits_config, probs_config)`

**Logic**:
```
If days_run < 3:
    Mode = AQUECIMENTO (Low profile)
    Connections: 3-6, Comments: 5-15%
Elif days_run < 14:
    Mode = CRESCIMENTO (Moderate)
    Connections: 10, Comments: 0%
Elif last_ssi > 40:
    Mode = ELITE (High volume)
    Connections: 15-20, Comments: 35-50%
Else:
    Mode = CRUZEIRO (Stable)
    Connections: 10-15, Comments: 25-35%
```

**Example**:
```python
if AUTO_REGULATE:
    LIMITS_CONFIG, PROBS = calculate_smart_parameters()
    # Automatically scales bot behavior
```

---

## Database Functions (`database_manager.py`)

#### `init_db()`
Initializes database tables.

```python
from database_manager import init_db
init_db()  # Creates bot_data.db schema
```

---

#### `log_interaction(url, name, headline, source, status)`
Alternative logging function (from database_manager.py).

```python
from database_manager import log_interaction
log_interaction(
    url="https://linkedin.com/in/user",
    name="User Name",
    headline="Role",
    source="Group",
    status="Connected"
)
```

---

#### `log_ssi(data_dict)`
Logs SSI scores to database.

```python
log_ssi({
    'Date': '2025-12-06',
    'Total_SSI': 38.5,
    'People': 45,
    'Insights': 30,
    'Brand': 25,
    'Relationships': 40,
    'Industry_Rank': 500,
    'Network_Rank': 1200
})
```

---

## Scraper Functions (`d.py`)

#### `run_scraper()`
Extracts LinkedIn profile URLs using search filters and pagination.

**Signature**:
```python
def run_scraper() -> None
```

**Configuration** (in `d.py`):
```python
BASE_URL = 'https://www.linkedin.com/search/results/people/?...'
START_PAGE = 1
END_PAGE = 5
MAX_LIMIT = 10
```

**Output**: Saves profile URLs to `links_coletados.txt`

**Example**:
```bash
python d.py
# Extracts up to 10 profiles from pages 1-5 of search results
```

---

## Streamlit Dashboard (`dashboard_app.py`)

#### `load_data() -> tuple[DataFrame, DataFrame, DataFrame]`
Loads analytics from SQLite and CSV.

**Signature**:
```python
def load_data() -> tuple[DataFrame, DataFrame, DataFrame]
```

**Returns**:
- `ssi_df` - SSI history from CSV
- `interactions_df` - Interactions from SQLite
- `analytics_df` - Profile analytics from SQLite

**Example**:
```python
ssi_df, interactions_df, analytics_df = load_data()
print(f"Total interactions logged: {len(interactions_df)}")
```

---

#### `main_dashboard()`
Renders complete Streamlit dashboard.

**Signature**:
```python
def main_dashboard() -> None
```

**Features**:
- KPI cards (SSI, connections, followers)
- Line charts (SSI trend, profile views)
- Bar charts (engagement by source)
- Correlation analysis
- Engagement heatmaps

**Run**:
```bash
streamlit run dashboard_app.py
# Opens http://localhost:8501
```

---

## Usage Examples

### Example 1: Run Complete Automation Session
```python
from bot_v2 import *

AUTO_REGULATE = True
SPEED_FACTOR = 1.5

start_browser()
# Automatically runs:
# - Quick connects
# - Feed engagement
# - Main group automation
# - Logs all interactions
```

### Example 2: Manual Connection with Logging
```python
from selenium import webdriver
from bot_v2 import human_sleep, log_interaction_db, connect_with_user

browser = webdriver.Edge()
browser.get("https://linkedin.com/in/target-user")

if connect_with_user(browser, "Target Name", "Data Scientist", "MyGroup"):
    log_interaction_db(
        "https://linkedin.com/in/target-user",
        "Target Name",
        "Data Scientist",
        "Manual",
        "Connected"
    )
    human_sleep(45, 90)

browser.quit()
```

### Example 3: Query Interactions
```python
import sqlite3

conn = sqlite3.connect("bot_data.db")
cursor = conn.cursor()

# Get all connections from this session
connections = cursor.execute(
    "SELECT * FROM interactions WHERE status='Connected'"
).fetchall()

print(f"Total connections: {len(connections)}")
for profile_url, name, headline, source, status, timestamp in connections:
    print(f"  {name} ({headline}) - {timestamp}")

conn.close()
```

---

**Last Updated**: December 6, 2025 | **API Version**: 1.0
