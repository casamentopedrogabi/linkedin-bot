# Development Guide

Guidelines for extending and contributing to the LinkedIn Bot.

---

## Code Style & Conventions

### Python Style Guide

Follow **PEP 8** with these project-specific conventions:

**Naming**:
```python
# Functions: snake_case
def run_main_bot_logic():
    pass

# Classes: PascalCase (if any)
class LinkedInBot:
    pass

# Constants: UPPER_SNAKE_CASE
CONNECTION_LIMIT = 10
SPEED_FACTOR = 1.5
```

**Imports**:
```python
# Group in order: stdlib, third-party, local
import os
import time
import sqlite3

from selenium import webdriver
from bs4 import BeautifulSoup
import pandas as pd

from bot_v2 import human_sleep, log_interaction_db
```

**Docstrings**:
```python
def connect_with_user(browser, name, headline, group_name):
    """
    Sends a connection request to a LinkedIn profile.
    
    Args:
        browser (WebDriver): Active Selenium WebDriver
        name (str): User's display name
        headline (str): User's professional headline
        group_name (str): Group where profile was found
    
    Returns:
        bool: True if connection sent, False if failed
    
    Raises:
        WebDriverException: If element not found or browser error
    """
    pass
```

**Comments**:
```python
# Use comments for WHY, not WHAT
# Good:
# Wait longer after connection to simulate reading profile
sleep_after_connection()

# Bad:
sleep_after_connection()  # Sleep after connection
```

---

## Adding New Features

### Example 1: Add a New Automation Workflow

**Goal**: Create a new engagement strategy (e.g., comment on all posts in a topic)

**Steps**:

**1. Create function in `bot_v2.py`**:
```python
def engage_with_topic(browser, topic_url, max_comments=5):
    """
    Engages with all posts in a specific LinkedIn topic.
    
    Args:
        browser (WebDriver): Active Selenium WebDriver
        topic_url (str): LinkedIn topic URL
        max_comments (int): Max comments to post
    """
    global SESSION_CONNECTION_COUNT
    
    try:
        browser.get(topic_url)
        human_sleep(5, 10)
        
        # Collect posts
        posts = browser.find_elements(By.XPATH, "//article[@data-id]")
        
        for i, post in enumerate(posts[:max_comments]):
            # Check limit
            if SESSION_CONNECTION_COUNT >= CONNECTION_LIMIT:
                break
            
            try:
                # Extract post info
                post_text = post.text[:100]
                
                # Language check
                if FEED_ENGLISH_ONLY and not is_text_english(post_text):
                    continue
                
                # Generate and post comment
                comment = get_ai_comment(post_text)
                if comment and perform_comment(browser, post, comment):
                    SESSION_CONNECTION_COUNT += 1
                    log_interaction_db(
                        url=topic_url,
                        name="Topic Post",
                        headline=post_text,
                        source="Topic",
                        status="Commented"
                    )
                    
                    human_sleep(10, 20)
            except Exception as e:
                if VERBOSE:
                    print(f"Error engaging post: {e}")
                continue
                
    except Exception as e:
        print(f"Error in engage_with_topic: {e}")
        raise
```

**2. Call from `start_browser()`**:
```python
# Add after feed interaction, before main group logic
try:
    engage_with_topic(
        browser, 
        topic_url="https://www.linkedin.com/feed/topic/urn:li:topic:12345",
        max_comments=5
    )
except Exception as e:
    print(f"Topic engagement failed: {e}")
```

**3. Add configuration support**:
```python
# In control panel
TOPIC_ENGAGEMENT = True
TOPIC_URL = "https://www.linkedin.com/feed/topic/urn:li:topic:12345"
TOPIC_MAX_COMMENTS = 5

# In function
if not TOPIC_ENGAGEMENT:
    return
```

**4. Test thoroughly**:
```bash
# Set conservative limits for testing
LIMITS_CONFIG = {"CONNECTION": (1, 1), ...}
VERBOSE = True
python bot_v2.py
```

---

### Example 2: Add Database Analytics

**Goal**: Track which roles convert best to connections

**Steps**:

**1. Add table to `init_db()`**:
```python
def init_db():
    # ... existing tables ...
    
    c.execute('''CREATE TABLE IF NOT EXISTS role_analytics (
        role TEXT PRIMARY KEY,
        total_targeted INT,
        connections_sent INT,
        success_rate REAL,
        last_updated DATETIME
    )''')
    
    conn.commit()
    conn.close()
```

**2. Create logging function**:
```python
def log_role_analytics(role, connections_sent):
    """Track conversion rate by role."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    try:
        # Get current stats
        c.execute("SELECT * FROM role_analytics WHERE role = ?", (role,))
        row = c.fetchone()
        
        if row:
            # Update existing
            total_targeted, connections = row[1], row[2]
            total_targeted += 1
            connections += connections_sent
        else:
            # Create new
            total_targeted = 1
            connections = connections_sent
        
        success_rate = connections / total_targeted if total_targeted > 0 else 0
        
        c.execute(
            "INSERT OR REPLACE INTO role_analytics VALUES (?, ?, ?, ?, ?)",
            (role, total_targeted, connections, success_rate, datetime.datetime.now())
        )
        conn.commit()
    except Exception as e:
        print(f"Analytics error: {e}")
    finally:
        conn.close()
```

**3. Call from `connect_with_user()`**:
```python
def connect_with_user(browser, name, headline, group_name):
    # ... existing logic ...
    
    # Extract role from headline
    for role in TARGET_ROLES:
        if role in headline.lower():
            connection_sent = True
            log_role_analytics(role, 1 if connection_sent else 0)
            break
```

**4. Query results**:
```python
# Find best-converting roles
conn = sqlite3.connect('bot_data.db')
c = conn.cursor()

results = c.execute(
    "SELECT role, success_rate FROM role_analytics ORDER BY success_rate DESC"
).fetchall()

for role, rate in results:
    print(f"{role}: {rate*100:.1f}% success rate")
```

---

### Example 3: Add Dashboard Visualization

**Goal**: Add a chart showing "Best Performing Roles"

**Steps**:

**1. Create query function**:
```python
# In dashboard_app.py
def get_role_performance():
    """Get connection success rate by role."""
    conn = sqlite3.connect("bot_data.db")
    df = pd.read_sql_query(
        "SELECT role, success_rate FROM role_analytics ORDER BY success_rate DESC",
        conn
    )
    conn.close()
    return df
```

**2. Add to dashboard**:
```python
# In main_dashboard()
st.header("3. Role Performance Analysis")

role_df = get_role_performance()

if not role_df.empty:
    fig, ax = plt.subplots(figsize=(12, 6))
    
    ax.barh(role_df['role'], role_df['success_rate'] * 100, 
            color=HEINEKEN_COLORS["lime_green"])
    ax.set_xlabel("Success Rate (%)")
    ax.set_title("Connection Success Rate by Role")
    
    st.pyplot(fig)
else:
    st.info("No role analytics yet. Run bot to generate data.")
```

---

## Testing

### Unit Tests

Create `tests/test_functions.py`:

```python
import pytest
from bot_v2 import is_text_english, get_factored_time

def test_is_text_english():
    assert is_text_english("Hello, this is English text") == True
    assert is_text_english("Bonjour, c'est du texte français") == False

def test_get_factored_time():
    SPEED_FACTOR = 1.5
    assert get_factored_time(10) == 15.0
    assert get_factored_time(0) == 0.0
```

**Run tests**:
```bash
pytest tests/test_functions.py -v
```

---

### Integration Tests

Test bot workflows with mock browser:

```python
# tests/test_workflows.py
from unittest.mock import Mock, patch
from bot_v2 import connect_with_user

def test_connect_with_user_mock():
    mock_browser = Mock()
    
    # Mock finding connect button
    mock_connect_btn = Mock()
    mock_browser.find_element.return_value = mock_connect_btn
    
    # Call function
    result = connect_with_user(mock_browser, "John Doe", "Data Scientist", "Test Group")
    
    # Verify button was clicked
    mock_connect_btn.click.assert_called_once()
```

---

## Code Review Checklist

Before submitting changes:

- [ ] **Follows PEP 8** - Run `pylint bot_v2.py`
- [ ] **Uses `human_sleep()`** - No bare `time.sleep()`
- [ ] **Respects limits** - Checks `SESSION_*_COUNT < LIMIT`
- [ ] **Logs interactions** - Calls `log_interaction_db()`
- [ ] **Language-filtered** - Uses `is_text_english()` before commenting
- [ ] **Error handling** - Try/except for critical errors
- [ ] **Docstrings** - Functions documented
- [ ] **Tested** - Works with conservative limits first
- [ ] **No hardcoded URLs** - Uses config variables
- [ ] **Backward compatible** - Old configs still work

---

## Performance Optimization

### Profile Memory Usage

```python
# Before: Stores all data in memory
all_profiles = browser.find_elements(By.XPATH, "//a[@href*='/in/']")

# After: Iterate without storing all
for profile_element in browser.find_elements(By.XPATH, "//a[@href*='/in/']"):
    url = profile_element.get_attribute("href")
    # Process and discard immediately
```

### Database Indexes

Add indexes to frequently queried columns:

```sql
CREATE INDEX IF NOT EXISTS idx_interactions_status ON interactions(status);
CREATE INDEX IF NOT EXISTS idx_interactions_timestamp ON interactions(timestamp);
CREATE INDEX IF NOT EXISTS idx_analytics_timestamp ON profile_analytics(timestamp);
```

---

## Documentation

### Adding Documentation

1. **Function docstrings**: Always include
2. **Module docstrings**: For new files
3. **Wiki updates**: For new features

**Template**:
```markdown
# Feature Name

## Overview
What does this feature do?

## Configuration
How to enable/configure?

## Usage Example
```python
# Code example
```

## Troubleshooting
Common issues?
```

---

## Git Workflow

### Commit Message Format

```
[FEATURE/FIX/DOCS] Short description

Longer description explaining:
- What changed
- Why it changed
- Any side effects or migration needed

Fixes #123 (if fixing issue)
```

**Example**:
```
[FEATURE] Add role analytics tracking

- Track connection success rate by role
- Add log_role_analytics() function
- Update dashboard with new visualization
- Helps identify high-value target roles

Fixes #45
```

---

## Release Process

### Version Bumping

Use semantic versioning: `MAJOR.MINOR.PATCH`

```
MAJOR: Breaking changes (restart from scratch)
MINOR: New features (backward compatible)
PATCH: Bug fixes (no new features)
```

**Update**:
1. Edit version in `bot_v2.py`
2. Update `CHANGELOG.md`
3. Tag in git: `git tag v1.2.0`
4. Push: `git push origin v1.2.0`

---

## Common Development Tasks

### Add a new configuration option

```python
# 1. Add to control panel
NEW_OPTION = True  # or appropriate default

# 2. Document it
"""
NEW_OPTION (bool): What does this do?
Default: True
When to change: ...
"""

# 3. Use it in code
if NEW_OPTION:
    # Do something
    pass
```

### Add a new interaction type (vs Connect/Follow/Visited)

```python
# 1. Update log_interaction_db call
status = "Endorsed"  # New status type
log_interaction_db(url, name, headline, source, status)

# 2. Update dashboard queries
statuses = interactions_df['status'].unique()
# Now includes: Visited, Connected, Followed, Endorsed

# 3. Update dashboard charts
status_counts = interactions_df['status'].value_counts()
# Pie chart automatically includes new status
```

---

## Debugging in Development

### Enable detailed logging

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot_debug.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# In functions:
logger.debug(f"Attempting connection with {name}")
logger.error(f"Connection failed: {e}")
```

### Browser screenshots for debugging

```python
# On error, capture state
try:
    connect_with_user(browser, name, headline, group)
except Exception as e:
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    browser.save_screenshot(f"error_{timestamp}.png")
    raise
```

---

## Resources

- **Python Style**: https://www.python.org/dev/peps/pep-0008/
- **Selenium Docs**: https://selenium.dev/documentation/
- **SQLite**: https://www.sqlite.org/docs.html
- **Streamlit**: https://docs.streamlit.io/

---

**Last Updated**: December 6, 2025 | **Version**: 1.0
