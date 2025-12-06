# Troubleshooting Guide

Common issues and solutions for the LinkedIn Bot.

---

## Installation & Setup Issues

### ❌ "ModuleNotFoundError: No module named 'selenium'"

**Cause**: Dependencies not installed

**Solution**:
```bash
pip install -r requirements.txt
```

**Verify**:
```python
python -c "from selenium import webdriver; print('✓ Selenium OK')"
```

---

### ❌ "msedgedriver.exe not found"

**Cause**: WebDriver not in project root

**Solution**:
1. Check your Edge version:
   - Open Edge → Settings → About Microsoft Edge
   - Note the version (e.g., "131.0.123.456")

2. Download matching driver:
   - Visit: https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/
   - Select your OS and version
   - Extract `msedgedriver.exe`

3. Place in project root:
   ```bash
   # Verify file exists
   ls -la msedgedriver.exe  # macOS/Linux
   dir msedgedriver.exe     # Windows
   ```

4. Test:
   ```python
   from selenium.webdriver.edge.service import Service
   from selenium import webdriver
   
   service = Service("msedgedriver.exe")
   driver = webdriver.Edge(service=service)
   print("✓ Driver initialized")
   driver.quit()
   ```

---

### ❌ "Invalid session ID" error mid-session

**Cause**: Browser crashed due to LinkedIn anti-bot protection or system memory

**Solution**: Bot automatically restarts browser and continues
- Check console for error message
- Reduce `SPEED_FACTOR` next session (use 2.0 instead of 1.5)
- Reduce connection limits

**Prevention**:
```python
SPEED_FACTOR = 2.0      # Slower = safer
CONNECT_WITH_USERS = True

# In manual mode, reduce limits
LIMITS_CONFIG = {
    "CONNECTION": (3, 5),    # Lower than default
    "FOLLOW": (5, 8),
    "PROFILES_SCAN": (15, 20),
    "FEED_POSTS": (20, 30)
}
```

---

## Bot Execution Issues

### ❌ Bot won't start - "Port 8501 is already in use"

**Cause**: Streamlit or another process using port

**Solution**:
```bash
# Kill process using port 8501
# Windows:
netstat -ano | findstr :8501
taskkill /PID {PID} /F

# macOS/Linux:
lsof -i :8501
kill -9 {PID}
```

**Or use different port**:
```bash
streamlit run dashboard_app.py --server.port 8502
```

---

### ❌ "No interactions logged" - database empty

**Cause**: 
1. Limits are 0
2. Bot crashed immediately
3. Wrong database

**Debug**:
```bash
# Check if database exists
sqlite3 bot_data.db ".tables"

# Count records
sqlite3 bot_data.db "SELECT COUNT(*) FROM interactions;"

# Show latest interactions
sqlite3 bot_data.db "SELECT * FROM interactions ORDER BY timestamp DESC LIMIT 5;"
```

**Solutions**:

**Problem 1: Limits are 0**
```python
# Verify in bot_v2.py
print(f"CONNECTION_LIMIT: {CONNECTION_LIMIT}")
print(f"FOLLOW_LIMIT: {FOLLOW_LIMIT}")

# Should be > 0
if CONNECTION_LIMIT == 0:
    CONNECTION_LIMIT = 5  # Reset to default
```

**Problem 2: Check database initialization**
```python
from bot_v2 import init_db
init_db()  # Force database creation

# Verify tables exist
import sqlite3
conn = sqlite3.connect('bot_data.db')
cursor = conn.cursor()
cursor.execute(".tables")
print(cursor.fetchall())
conn.close()
```

---

### ❌ Bot keeps clicking "Connect" but nothing happens

**Cause**: Connection button selector changed or different page layout

**Solution**:
1. Manually check LinkedIn's current button structure:
   - Open any profile
   - Right-click "Connect" button → Inspect
   - Find CSS class or XPath

2. Update `connect_with_user()` in `bot_v2.py`:
   ```python
   # Old (may be outdated)
   connect_btn = browser.find_element(By.CLASS_NAME, "artdeco-button")
   
   # New (after inspecting)
   connect_btn = browser.find_element(By.XPATH, "//button[contains(text(), 'Connect')]")
   ```

3. Test with one profile:
   ```python
   LIMITS_CONFIG["CONNECTION"] = (1, 1)
   VERBOSE = True
   start_browser()
   ```

---

### ❌ "Timeout waiting for page load"

**Cause**: LinkedIn page taking >60 seconds to load (anti-bot)

**Solution**:

**Increase timeout**:
```python
# In start_browser()
browser.set_page_load_timeout(120)  # 2 minutes instead of 60
```

**Reduce speed aggressiveness**:
```python
SPEED_FACTOR = 2.5      # Much slower
QUICK_CONNECT_LIMIT = 0 # Skip quick connects
LIMITS_CONFIG["CONNECTION"] = (1, 2)  # Very conservative
```

**Add retry logic**:
```python
max_retries = 3
for attempt in range(max_retries):
    try:
        browser.get(url)
        break
    except TimeoutException:
        if attempt < max_retries - 1:
            time.sleep(30)  # Wait before retry
        else:
            raise
```

---

## Data & Database Issues

### ❌ Dashboard shows "No data to display"

**Cause**: Missing CSV or SQLite

**Solution**:

**Check 1: Run bot first**
```bash
python bot_v2.py  # Creates data
python -m streamlit run dashboard_app.py  # Displays it
```

**Check 2: Verify CSV exists**
```bash
ls -la ssi_history.csv  # macOS/Linux
dir ssi_history.csv     # Windows

# If missing, create it
echo "Date,Total_SSI,People,Insights,Brand,Relationships,Industry_Rank,Network_Rank" > ssi_history.csv
```

**Check 3: Verify SQLite**
```bash
sqlite3 bot_data.db "SELECT COUNT(*) FROM interactions;"
```

---

### ❌ "Database locked" error

**Cause**: Multiple processes writing to same DB simultaneously

**Solution**:

**Close other writers**:
```bash
# Check what's accessing the database
lsof | grep bot_data.db  # macOS/Linux

# Close conflicting process
ps aux | grep python
kill {PID}
```

**Add retry with backoff**:
```python
import sqlite3
import time

def log_interaction_db_retry(url, name, headline, source, status, max_retries=3):
    for attempt in range(max_retries):
        try:
            conn = sqlite3.connect('bot_data.db', timeout=10)
            # ... write operation ...
            conn.commit()
            break
        except sqlite3.OperationalError as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                print(f"DB locked, retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise
```

---

### ❌ CSV file has missing or corrupt data

**Cause**: Bot crashed mid-write or file permission issue

**Solution**:

**Repair CSV**:
```python
import pandas as pd

# Read and validate
df = pd.read_csv('ssi_history.csv')

# Remove incomplete rows
df = df.dropna(subset=['Date', 'Total_SSI'])

# Re-save
df.to_csv('ssi_history.csv', index=False)
```

**Prevent future issues**:
```python
# In add_to_csv(), add error handling
try:
    with open(path, 'a', newline='', encoding='utf-8') as f:
        csv.writer(f).writerow(data)
except IOError as e:
    print(f"CSV write error: {e}")
    # Retry or log to SQLite instead
```

---

## Authentication & LinkedIn Issues

### ❌ Bot gets logged out

**Cause**: Session expired or too much activity detected

**Solution**:

**Check 1: Verify cookies/session valid**
```python
# Navigate to profile page to test auth
browser.get('https://linkedin.com/me')
time.sleep(5)

if 'linkedin.com/me' not in browser.current_url:
    print("❌ Not authenticated - need to log in manually")
else:
    print("✓ Authentication valid")
```

**Check 2: Manually log in first**
- Run bot with reduced automation first
- Let bot navigate to LinkedIn naturally
- Manually complete any 2FA if needed
- Then proceed with automation

**Check 3: Use Edge profile**
```python
# Already done in bot_v2.py, but verify:
ud = os.path.join(os.environ['USERPROFILE'], 'AppData', 'Local', 'Microsoft', 'Edge', 'User Data')
opts.add_argument(f"--user-data-dir={ud}")
opts.add_argument("--profile-directory=Default")
```

---

### ❌ "Account restricted" or "Unusual activity"

**Cause**: Too many connections/follows triggered LinkedIn security

**Solution**:

**Immediate**:
1. Stop bot
2. Log in to LinkedIn account manually
3. Verify identity if prompted
4. Try profile visit (should work)

**Prevention for next session**:
```python
# Significantly reduce activity
AUTO_REGULATE = True
SPEED_FACTOR = 3.0        # Maximum safety

# Or manually set very conservative limits
LIMITS_CONFIG = {
    "CONNECTION": (1, 2),
    "FOLLOW": (2, 3),
    "PROFILES_SCAN": (5, 10),
    "FEED_POSTS": (10, 15)
}

PROBS = {
    "FEED_LIKE": (0.05, 0.10),
    "FEED_COMMENT": (0, 0),
    "GROUP_LIKE": (0.10, 0.20),
    "GROUP_COMMENT": (0, 0)
}
```

**Wait before resuming**: 2-3 days of inactivity often resets restriction counters

---

## Performance Issues

### ❌ Bot very slow - taking 2+ hours

**Cause**: 
1. `SPEED_FACTOR` too high
2. LinkedIn throttling
3. System resources low

**Solution**:

**Reduce delay**:
```python
SPEED_FACTOR = 1.0  # Default was 1.5, try 1.0
```

**Monitor system resources**:
```bash
# Check memory usage
top  # macOS/Linux
tasklist  # Windows

# Restart if needed
killall python
sleep 5
python bot_v2.py
```

**Reduce scope**:
```python
LIMITS_CONFIG["PROFILES_SCAN"] = (5, 10)  # Scan fewer profiles
FEED_POSTS_LIMIT = (10, 20)
```

---

### ❌ Memory leak - program uses 500MB+ RAM

**Cause**: 
1. Selenium not releasing resources
2. Large data structures not cleared

**Solution**:

**Force garbage collection**:
```python
import gc

# In main loop, periodically clean up
for i in range(100):
    # Do work
    if i % 10 == 0:
        gc.collect()
```

**Restart browser periodically**:
```python
def start_browser_with_restarts(num_cycles=5):
    for cycle in range(num_cycles):
        start_browser()  # Includes browser.quit()
        gc.collect()
        time.sleep(60)  # Cool down between cycles
```

---

## Debugging Tools

### Enable Debug Mode

```python
# In bot_v2.py, add at top
import logging
logging.basicConfig(level=logging.DEBUG)

# Add verbose output
VERBOSE = True
```

### Check Browser State

```python
# During bot execution, query browser state
print(f"Current URL: {browser.current_url}")
print(f"Page title: {browser.title}")
print(f"Cookies: {len(browser.get_cookies())}")

# Screenshot for debugging
browser.save_screenshot("debug_screenshot.png")
```

### Query Logs

```bash
# View all interactions logged
sqlite3 bot_data.db "SELECT name, status, COUNT(*) FROM interactions GROUP BY status;"

# Show session timeline
sqlite3 bot_data.db "SELECT status, COUNT(*) as count, datetime(MIN(timestamp)) as first, datetime(MAX(timestamp)) as last FROM interactions GROUP BY status;"
```

---

## Common Success Patterns

### ✓ Bot works well when:
- Running during off-peak hours (9 PM - 9 AM)
- SSI score 25-45 (good momentum zone)
- Using `SPEED_FACTOR = 1.5-2.0`
- Engaging with relevant high-value keywords
- Sleeping 48 hours between aggressive sessions

### ✓ Maximized connections:
- Set `SEND_AI_NOTE = 1` (personalized messages)
- Use specific, relevant `TARGET_ROLES`
- Connect with 8-12 users per session (not 20+)
- Follow top profiles in between

---

## Getting Help

1. **Check logs**: Review console output for error patterns
2. **Query database**: Use SQLite to understand data state
3. **Reduce scope**: Test with 1 connection, 0 follows
4. **Check browser**: Take screenshots to debug visual issues
5. **Inspect selectors**: Use browser dev tools to verify button locations

---

**Last Updated**: December 6, 2025 | **Version**: 1.0
