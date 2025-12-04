import random
import datetime
import time
import csv
import os
import re
import sqlite3 # ADDED: For the Dashboard
from datetime import timedelta

# --- EXTERNAL LIBRARIES ---
try:
    from langdetect import detect, LangDetectException
except ImportError:
    print("CRITICAL ERROR: Install langdetect lib -> pip install langdetect")
    exit()

# AI Client Initialization
try:
    from g4f.client import Client
    ai_client = Client()
    if ai_client is None:
        raise Exception("G4F Client failed to initialize.")
except ImportError:
    print("Warning: g4f not installed. AI disabled.")
    Client = None
    ai_client = None
except Exception as e:
    print(f"Warning: Error initializing g4f. AI disabled. Detail: {e}")
    ai_client = None

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service as EdgeService
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException
import pandas as pd

# ==============================================================================
# ⚙️ INTELLIGENT CONTROL PANEL
# ==============================================================================

# 1. OPERATION MODE (AUTO PILOT)
AUTO_REGULATE = True 

# 2. SPEED
SPEED_FACTOR = 1.5
DRIVER_FILENAME = "msedgedriver.exe"

# 3. AI & LANGUAGE
FEED_ENGLISH_ONLY = True 
AI_PERSONA = "I am a Senior Data Scientist experienced in Python, Databricks, ML and Big Data Strategy."

# 4. TARGETS
TARGET_ROLES = [
    "head of data", "chief data officer", "director of data", "cto", 
    "vp of engineering", "head of analytics", "data science manager",
    "analytics manager", "product owner",
    "senior data scientist", "lead data scientist", "staff data scientist",
    "tech recruiter", "technical recruiter", "talent acquisition", 
    "hr business partner"
]

# 5. MANUAL LIMITS (Fallback if AUTO_REGULATE = False)
LIMITS_CONFIG = {
    "CONNECTION": (5, 10),
    "FOLLOW": (10, 15),
    "PROFILES_SCAN": (20, 30),
    "FEED_POSTS": (20, 30)
}

# 6. MANUAL PROBABILITIES (Fallback if AUTO_REGULATE = False)
PROBS = {
    "FEED_LIKE": (0.40, 0.60),
    "FEED_COMMENT": (0.25, 0.30),
    "GROUP_LIKE": (0.50, 0.70),    
    "GROUP_COMMENT": (0.10, 0.20)  
}

# 7. GENERAL SETTINGS
CONNECT_WITH_USERS = True
SAVECSV = True
VERBOSE = True
# NEW: Variable to control sending notes. (1 = Send Note, 0 = Send Direct)
SEND_AI_NOTE = 1 

# FULL LIST OF GROUPS (OLD + NEW)
LINKEDIN_GROUPS_LIST = [
    "https://www.linkedin.com/groups/3732032/",
    "https://www.linkedin.com/groups/3063585/",
    "https://www.linkedin.com/groups/3990648/",
    "https://www.linkedin.com/groups/35222/",
    "https://www.linkedin.com/groups/45655/",
    "https://www.linkedin.com/groups/961087/",
    "https://www.linkedin.com/groups/60878/",
    "https://www.linkedin.com/groups/10350430/",
    "https://www.linkedin.com/groups/4376214/",
    "https://www.linkedin.com/groups/7039829/",
    "https://www.linkedin.com/groups/6773411/",
    "https://www.linkedin.com/groups/1814785/",
    "https://www.linkedin.com/groups/7037632/",
]

# ==============================================================================
# [NEW] DATABASE INTEGRATION (SQLITE)
# ==============================================================================
DB_NAME = "bot_data.db"

def init_db():
    """Creates the database if it doesn't exist."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Interactions Table
    c.execute('''CREATE TABLE IF NOT EXISTS interactions (
                    profile_url TEXT PRIMARY KEY,
                    name TEXT,
                    headline TEXT,
                    source TEXT,
                    status TEXT,
                    timestamp DATETIME
                )''')
    # Analytics Table (Dashboard) - ADDED 'followers'
    c.execute('''CREATE TABLE IF NOT EXISTS profile_analytics (
                    timestamp DATETIME,
                    profile_views INT,
                    post_impressions INT,
                    followers INT,
                    search_appearances INT
                )''')
    conn.commit()
    conn.close()

def log_interaction_db(url, name, headline, source, status):
    """Saves interaction to SQL."""
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Use INSERT OR REPLACE to ensure recently visited profiles update status
        c.execute("INSERT OR REPLACE INTO interactions VALUES (?, ?, ?, ?, ?, ?)", 
                  (url, name, headline, source, status, ts))
        conn.commit()
        conn.close()
    except: pass

def log_analytics_db(views, impressions, followers, searches):
    """Saves dashboard data."""
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Ensure the column order matches the CREATE TABLE statement
        c.execute("INSERT INTO profile_analytics VALUES (?, ?, ?, ?, ?)", (ts, views, impressions, followers, searches))
        conn.commit()
        conn.close()
    except Exception as e:
        if VERBOSE: print(f"DB Log Analytics Error: {e}")
        pass

# Initialize DB on script load
init_db()

# ==============================================================================
# AUTO-REGULATION LOGIC (FULL AUTO-PILOT)
# ==============================================================================

def calculate_smart_parameters():
    """
    Defines LIMITS and PROBABILITIES based on history (days run) and current SSI.
    Returns a tuple: (limits_dict, probs_dict)
    """
    history_file = 'ssi_history.csv'
    days_run = 0
    last_ssi = 0
    
    if os.path.exists(history_file):
        try:
            df = pd.read_csv(history_file)
            # Use 'Date' column to count unique days run
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce').dt.strftime('%Y-%m-%d')
            days_run = df['Date'].dropna().nunique()
            last_ssi = df['Total_SSI'].iloc[-1] if not df.empty else 0
        except: pass
    
    print(f"\n🧠 [AUTO-PILOT] Diagnosis: {days_run} days run | Current SSI: {last_ssi}")
    
    # LEVEL 1: WARMUP (0 to 7 days) -> Behavior: Shy Observer
    if days_run < 3:
        print("    -> Mode: WARMUP (Low Profile & Safety)")
        limits = {
            "CONNECTION": (3, 6),
            "FOLLOW": (5, 8),
            "PROFILES_SCAN": (10, 15),
            "FEED_POSTS": (10, 15)
        }
        probs = {
            "FEED_LIKE": (0.30, 0.50),    
            "FEED_COMMENT": (0.05, 0.15), 
            "GROUP_LIKE": (0.40, 0.60),
            "GROUP_COMMENT": (0.05, 0.10)
        }
        return limits, probs
    
    # LEVEL 2: GROWTH (7 to 14 days) -> Behavior: Active Participant
    elif days_run < 14:
        print("    -> Mode: GROWTH (Moderate Engagement)")
        limits = {
            "CONNECTION": (6, 10),
            "FOLLOW": (8, 12),
            "PROFILES_SCAN": (15, 25),
            "FEED_POSTS": (15, 20)
        }
        probs = {
            "FEED_LIKE": (0.45, 0.65),
            "FEED_COMMENT": (0.15, 0.25), 
            "GROUP_LIKE": (0.50, 0.70),
            "GROUP_COMMENT": (0.10, 0.20)
        }
        return limits, probs
    
    # LEVEL 4: ELITE (SSI > 70) -> Behavior: Top Voice / Influencer
    elif last_ssi > 70:
        print("    -> Mode: ELITE (High Impact)")
        limits = {
            "CONNECTION": (15, 20),
            "FOLLOW": (15, 20),
            "PROFILES_SCAN": (40, 60),
            "FEED_POSTS": (30, 50)
        }
        probs = {
            "FEED_LIKE": (0.60, 0.80),    
            "FEED_COMMENT": (0.35, 0.50), 
            "GROUP_LIKE": (0.70, 0.90),
            "GROUP_COMMENT": (0.30, 0.50)
        }
        return limits, probs
        
    # LEVEL 3: CRUISE (Default after 14 days) -> Behavior: Consistent Professional
    else:
        print("    -> Mode: CRUISE (Stability)")
        limits = {
            "CONNECTION": (10, 15),
            "FOLLOW": (12, 18),
            "PROFILES_SCAN": (30, 45),
            "FEED_POSTS": (20, 30)
        }
        probs = {
            "FEED_LIKE": (0.50, 0.70),
            "FEED_COMMENT": (0.25, 0.35),
            "GROUP_LIKE": (0.60, 0.80),
            "GROUP_COMMENT": (0.20, 0.30)
        }
        return limits, probs

# Applies logic IF in auto mode
if AUTO_REGULATE:
    LIMITS_CONFIG, PROBS = calculate_smart_parameters()

# ==============================================================================
# GLOBAL VARIABLE INITIALIZATION
# ==============================================================================

CONNECTION_LIMIT = int(random.randint(LIMITS_CONFIG["CONNECTION"][0], LIMITS_CONFIG["CONNECTION"][1]))
FOLLOW_LIMIT = int(random.randint(LIMITS_CONFIG["FOLLOW"][0], LIMITS_CONFIG["FOLLOW"][1]))
PROFILES_TO_SCAN = int(random.randint(LIMITS_CONFIG["PROFILES_SCAN"][0], LIMITS_CONFIG["PROFILES_SCAN"][1]))
FEED_POSTS_LIMIT = int(random.randint(LIMITS_CONFIG["FEED_POSTS"][0], LIMITS_CONFIG["FEED_POSTS"][1]))

if random.randint(0, 10) == 0: 
    CONNECTION_LIMIT = 0
    print(f'conection set 0')
if random.randint(0, 10) == 0:
    FOLLOW_LIMIT = 0
    print(f'follow limit set 0')


PAG_ABERTAS = PROFILES_TO_SCAN
FEED_URL = "https://www.linkedin.com/feed/"
random_key = random.randint(0, len(LINKEDIN_GROUPS_LIST) - 1)
GROUP_URL = LINKEDIN_GROUPS_LIST[random_key]

DAILY_LIKE_PROB = random.uniform(PROBS["GROUP_LIKE"][0], PROBS["GROUP_LIKE"][1])
DAILY_COMMENT_PROB = random.uniform(PROBS["GROUP_COMMENT"][0], PROBS["GROUP_COMMENT"][1])
FEED_LIKE_PROB = random.uniform(PROBS["FEED_LIKE"][0], PROBS["FEED_LIKE"][1])
FEED_COMMENT_PROB = random.uniform(PROBS["FEED_COMMENT"][0], PROBS["FEED_COMMENT"][1])

SESSION_CONNECTION_COUNT = 0
SESSION_FOLLOW_COUNT = 0
SESSION_WITHDRAWN_COUNT = 0
TEMP_NAME = ""
TEMP_HEADLINE = "" 
CURRENT_GROUP_NAME = "our shared group"
CONNECTED = False
TIME = str(datetime.datetime.now().time())
COMMENTED_POSTS_FILE = "commentedPosts.txt"
browser = None

# ==============================================================================
# AUXILIARY FUNCTIONS
# ==============================================================================

def get_factored_time(seconds):
    return seconds * SPEED_FACTOR

def human_sleep(min_seconds=2, max_seconds=5):
    base_time = random.uniform(min_seconds, max_seconds)
    time.sleep(get_factored_time(base_time))

def sleep_after_connection():
    base_time = random.uniform(45, 90)
    print(f"--- ☕ LONG PAUSE (Reading profile): {get_factored_time(base_time):.0f}s ---")
    time.sleep(get_factored_time(base_time))

def human_scroll(browser):
    try:
        body = browser.find_element(By.TAG_NAME, 'body')
        for _ in range(random.randint(3, 7)):
            body.send_keys(Keys.PAGE_DOWN)
            human_sleep(2, 4)
            # STEALTH: Random mouse movement while scrolling
            if random.random() < 0.3:
                random_mouse_hover(browser)
            
            if random.random() < 0.2:
                body.send_keys(Keys.ARROW_UP) # Scrolls up a bit to read
                human_sleep(1, 2)
    except: pass

def human_type(element, text):
    """Types like a human with errors and time variations."""
    for char in text:
        if random.random() < 0.04: # 4% chance of error
            wrong_char = random.choice('abcdefghijklmnopqrstuvwxyz')
            element.send_keys(wrong_char)
            time.sleep(random.uniform(0.1, 0.3))
            element.send_keys(Keys.BACKSPACE)
            time.sleep(random.uniform(0.1, 0.2))
        
        element.send_keys(char)
        time.sleep(random.uniform(0.06, 0.28)) # Natural variation

def is_text_english(text):
    try:
        if not text or len(text) < 10: return False
        return detect(text) == 'en'
    except LangDetectException: return False

def get_commented_posts():
    if not os.path.exists(COMMENTED_POSTS_FILE): return set()
    with open(COMMENTED_POSTS_FILE, 'r') as f: return set(line.strip() for line in f)

def save_commented_post(urn):
    with open(COMMENTED_POSTS_FILE, 'a') as f: f.write(f"{urn}\n")

def create_csv(data, time_str):
    time_str = time_str.replace(":", "-").replace(".", "-")
    filename = 'GroupBot-' + time_str + '.csv'
    if not os.path.exists('CSV'): os.makedirs('CSV')
    with open(os.path.join('CSV', filename), 'w', newline='', encoding='utf-8') as f:
        csv.writer(f).writerow(data)

def add_to_csv(data, time_str):
    time_str = time_str.replace(":", "-").replace(".", "-")
    path = os.path.join(os.getcwd(), 'CSV', 'GroupBot-' + time_str + '.csv')
    if os.path.exists(path):
        with open(path, 'a', newline='', encoding='utf-8') as f:
            csv.writer(f).writerow(data)

def random_mouse_hover(browser):
    try:
        els = browser.find_elements(By.TAG_NAME, 'span')
        if els: ActionChains(browser).move_to_element(random.choice(els)).perform()
    except: pass

def filter_profiles(profiles):
    if not os.path.exists('visitedUsers.txt'): return profiles
    with open('visitedUsers.txt', 'r') as f: visited = [line.strip() for line in f]
    filtered = [p for p in profiles if p not in visited]
    return filtered
    
# --- CORRECTION 1: ROBUST CONNECTION COUNT EXTRACTION (3 STRATEGIES) ---
def get_total_connections_count(browser):
    """
    Extracts the total number of connections for acceptance calculation using robust selectors.
    It attempts to find the count on the /mynetwork/ page and falls back to the /in/me/ profile page (3 strategies).
    """
    try:
        # Strategy 1: Go to My Network page - Find number by the stable link text
        browser.get("https://www.linkedin.com/mynetwork/") 
        human_sleep(5, 8) 
        
        try:
            # Stable XPath: Finds the link/element that holds the total connections number 
            xpath_stable_count = "//a[contains(@href, '/connections/view/') or contains(@href, '/conex%C3%B5es/view/')]/span[@class='t-bold']"
            el = WebDriverWait(browser, 8).until(EC.presence_of_element_located((By.XPATH, xpath_stable_count)))
            text = el.text
            
            cleaned_text = re.sub(r'[^\d\+]', '', text.replace(',', '').replace('.', ''))
            numbers = re.findall(r'\d+', cleaned_text)
            
            if numbers:
                num = int(numbers[0])
                if num == 500 and '+' in text: return 501
                return num
        except:
            pass # Continue to next strategy

        # Strategy 2: Fallback to Profile page header link
        browser.get("https://www.linkedin.com/in/me/")
        human_sleep(5, 8)
        try:
            xpath_profile_conn_link = "//a[contains(@href, '/connections') or contains(@href, '/conex%C3%B5es')]"
            el = WebDriverWait(browser, 5).until(EC.presence_of_element_located((By.XPATH, xpath_profile_conn_link)))
            
            text = el.text.split(' ')[0]
            num_str = text.replace('.', '').replace(',', '').replace('+', '').strip()
            
            if num_str.isdigit():
                num = int(num_str)
                if num == 500 and '+' in el.text: return 501
                return num
        except:
            pass
            
        # Strategy 3: SECOND FALLBACK on Profile Page (Looking for the secondary connection counter element)
        try:
            # Targets the connections counter text inside the profile header, which is very stable.
            xpath_header_counter = "//ul[contains(@class, 'pv-top-card--list')]/li[2]"
            el = WebDriverWait(browser, 5).until(EC.presence_of_element_located((By.XPATH, xpath_header_counter)))
            
            text = el.text
            cleaned_text = re.sub(r'[^\d\+]', '', text.replace(',', '').replace('.', ''))
            numbers = re.findall(r'\d+', cleaned_text)
            
            if numbers:
                num = int(numbers[0])
                if num == 500 and '+' in text: return 501
                return num
        except:
            pass

        if VERBOSE: print("    [WARNING] Failed to reliably extract total connection count.")
        return 0
    except Exception as e: 
        if VERBOSE: print(f"Error extracting connections count: {e}")
        return 0


# ==============================================================================
# INTERACTION FUNCTIONS (FEED & STEALTH)
# ==============================================================================

def interact_with_feed_human(browser):
    """Interacts with the main Feed before moving to groups."""
    global FEED_POSTS_LIMIT
    print(f"-> [FEED BOT] Starting (Limit: {FEED_POSTS_LIMIT} | English Only: {FEED_ENGLISH_ONLY})")
    try:
        browser.get("https://www.linkedin.com/feed/")
        human_sleep(5, 8)
        
        processed_count = 0
        scrolls = 0
        max_scrolls = 15
        commented_in_feed = set()

        while processed_count < FEED_POSTS_LIMIT and scrolls < max_scrolls:
            # Re-fetch posts on every scroll
            posts = browser.find_elements(By.CLASS_NAME, "feed-shared-update-v2")
            
            for post in posts:
                if processed_count >= FEED_POSTS_LIMIT: break
                
                try:
                    urn = post.get_attribute("data-urn")
                    if urn in commented_in_feed: continue

                    browser.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", post)
                    human_sleep(1.5, 3)

                    # LIKE LOGIC
                    if random.random() < FEED_LIKE_PROB:
                        perform_reaction_varied(browser, post)

                    # COMMENT LOGIC
                    if random.random() < FEED_COMMENT_PROB:
                        try:
                            # Use CSS to find the post text element
                            text_el = post.find_element(By.CSS_SELECTOR, ".update-components-text")
                            text = text_el.text
                            
                            if FEED_ENGLISH_ONLY and not is_text_english(text):
                                continue 
                            
                            if len(text) > 20:
                                comment = get_ai_comment(text)
                                # Calls the corrected perform_comment
                                if perform_comment(browser, post, comment):
                                    commented_in_feed.add(urn)
                        except: pass
                    
                    commented_in_feed.add(urn) 
                    processed_count += 1
                except: continue

            browser.execute_script("window.scrollBy(0, 800);")
            human_sleep(3, 5)
            scrolls += 1
            
        print("-> Feed Done.\n")
    except Exception as e:
        print(f"Feed Error: {e}")

def take_coffee_break():
    """Simulates a random long break."""
    if random.random() < 0.08: 
        minutes = random.randint(2, 5)
        print(f"\n💤 [STEALTH] 'Coffee Break' mode activated. Pause for {minutes} minutes...")
        time.sleep(minutes * 60)
        print("⚡ [STEALTH] Back to work.\n")

def random_browsing_habit(browser):
    """Visits random pages to simulate human browsing."""
    pages = [
        "https://www.linkedin.com/notifications/",
        "https://www.linkedin.com/jobs/",
        "https://www.linkedin.com/mynetwork/",
        "https://www.linkedin.com/me/profile-views/"
    ]
    if random.random() < 0.4: 
        target = random.choice(pages)
        print(f"\n-> [STEALTH] Random browsing (Human Behavior): {target}")
        browser.get(target)
        human_sleep(5, 10)
        human_scroll(browser)
        human_sleep(3, 6)

def withdraw_old_invites(browser):
    """Removes old invitations and returns count."""
    global SESSION_WITHDRAWN_COUNT
    print("\n-> [MAINTENANCE] Checking pending old invitations...")
    count = 0
    try:
        browser.get("https://www.linkedin.com/mynetwork/invitation-manager/sent/")
        human_sleep(6, 9)
        withdraw_buttons = browser.find_elements(By.XPATH, "//button[contains(@aria-label, 'Retirar') or contains(@aria-label, 'Withdraw')]")
        if len(withdraw_buttons) > 0:
            for btn in reversed(withdraw_buttons): 
                if count >= 2: break 
                try:
                    browser.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", btn)
                    human_sleep(1, 2)
                    btn.click()
                    human_sleep(1, 2)
                    confirm = browser.find_element(By.XPATH, "//button[contains(@class, 'artdeco-modal__confirm-btn')]")
                    confirm.click()
                    print("    -> Old invitation withdrawn (SSI cleanup).")
                    human_sleep(3, 5)
                    count += 1
                except: pass
    except Exception as e:
        print(f"Error cleaning invitations: {e}")
    
    SESSION_WITHDRAWN_COUNT += count
    return count

# ==============================================================================
# [NEW] SNIPER MODE (RECRUITER HUNT) - CORRECTION: CONNECT ON SRP
# ==============================================================================

def run_sniper_mode(browser):
    """Active search for recruiters outside groups, attempting connection directly from the Search Results Page (SRP)."""
    global SESSION_CONNECTION_COUNT
    
    if SESSION_CONNECTION_COUNT >= CONNECTION_LIMIT:
        print("\n🎯 [SNIPER MODE] Daily connection limit reached. Skipping Sniper Mode.")
        return
        
    role = random.choice(TARGET_ROLES)
    print(f"\n🎯 [SNIPER MODE] Hunting: {role} (Daily Limit Remaining: {CONNECTION_LIMIT - SESSION_CONNECTION_COUNT})")
    
    encoded = role.replace(" ", "%20")
    url = f"https://www.linkedin.com/search/results/people/?keywords={encoded}&origin=SWITCH_SEARCH_VERTICAL"
    
    browser.get(url)
    human_sleep(8, 12)
    
    # Selects all search result containers
    profiles_containers = browser.find_elements(By.XPATH, "//li[contains(@class, 'reusable-search__result-container')]")
    count = 0
    
    limit_remaining = CONNECTION_LIMIT - SESSION_CONNECTION_COUNT
    # Tries to connect up to the limit, but maximum 5 profiles on the first SRP page
    max_search_connect = min(5, limit_remaining) 
    
    for p in profiles_containers:
        if count >= max_search_connect: break 
        if SESSION_CONNECTION_COUNT >= CONNECTION_LIMIT: break
        
        try:
            # 1. Extract Profile Details from SRP Container
            link_el = p.find_element(By.XPATH, ".//a[contains(@class, 'app-aware-link')]")
            link = link_el.get_attribute("href").split('?')[0]
            
            # Tries to extract the name (usually contained in a span with aria-hidden)
            try: name_el = p.find_element(By.XPATH, ".//span[@aria-hidden='true']")
            except: name_el = link_el
            name = name_el.text.split('|')[0].strip() or "Unknown"

            # 2. Find the Connect Button inside the result container
            xpath_connect_btn_srp = ".//button[.//span[contains(text(), 'Conectar') or contains(text(), 'Connect')]]"
            
            try:
                btn = p.find_element(By.XPATH, xpath_connect_btn_srp)
                
                # Scroll to the button to ensure visibility
                browser.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", btn)
                human_sleep(1, 2)
                
                # 3. Handle the connection modal using the existing sequence
                print(f"    -> [SNIPER SRP] Target found: {name}. Attempting quick connect.")
                
                # Setting headline to role for better logging
                temp_headline = f"Targeted: {role}"
                
                # click_connect_sequence handles the click and the resulting modal
                if click_connect_sequence(browser, btn, name, temp_headline, "Sniper Search"):
                    log_interaction_db(link, name, temp_headline, "Sniper SRP", "Connected")
                    sleep_after_connection()
                    count += 1
                else:
                    log_interaction_db(link, name, temp_headline, "Sniper SRP", "Visited (Failed Connect)")
            
            except Exception as connect_e:
                # If 'Connect' button not found (it's 'Follow', 'Pending', or already 'Connected')
                if VERBOSE: print(f"    -> [SNIPER SRP] Button not 'Connect' or already processed for {name}. Skipping.")
                log_interaction_db(link, name, "", "Sniper SRP", "Visited (Skipped)")
        
        except Exception as e: 
            if VERBOSE: print(f"    [SNIPER SRP ERROR] Failed to process profile: {e}")
            continue
            
    if count > 0:
        print(f"🎯 [SNIPER MODE] Completed. Total new connections from SRP: {count}")
    else:
        print("🎯 [SNIPER MODE] No direct connections made on SRP.")

# ==============================================================================
# SSI LOGIC (WITH COMPLETE METRICS AND DASHBOARD DB)
# ==============================================================================

# --- CORRECTION 2: ROBUST DASHBOARD METRIC EXTRACTION (Language Flexible) ---
def extract_metric(driver, metric_name):
    """
    Extracts a metric value (number) from the Dashboard page using a robust XPath 
    that looks for the metric name in the context of the analytics card.
    
    This version looks for the metric name and then navigates up the DOM to find the number.
    It is more resilient to slight structural and language changes.
    """
    # Map of English name to possible localized names (adapt if necessary)
    name_map = {
        "Post impressions": ["Post impressions", "Impressões de publicação", "Impressões da publicação"],
        "Followers": ["Followers", "Seguidores"],
        "Profile viewers": ["Profile viewers", "Visualizadores de perfil", "Visualizações de perfil"],
        "Search appearances": ["Search appearances", "Pesquisas que você aparece", "Vezes que você apareceu em pesquisas"]
    }
    
    possible_names = name_map.get(metric_name, [metric_name])
    
    for name_to_try in possible_names:
        try:
            # 1. Find the parent link/section that contains the metric name
            xpath_parent = f"//a[.//p[contains(text(), '{name_to_try}')]]"
            
            # Wait for the entire metric card link to be present
            parent_element = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, xpath_parent)))
            
            # 2. Search for the bold number *inside* that specific parent card
            xpath_number_inside = ".//p[contains(@class, 'text-body-large-bold')]"
            number_element = parent_element.find_element(By.XPATH, xpath_number_inside)
            
            # Clean the text (remove dots, commas, and strip spaces)
            text = number_element.text.replace('.', '').replace(',', '').strip()
            
            numbers = re.findall(r'\d+', text)
            
            if numbers:
                return int(numbers[0])
            return 0
            
        except:
            # If search fails, try the next possible name
            continue
            
    # If the loop finishes without returning, extraction failed for all names
    if VERBOSE: print(f"    [WARNING] Failed to extract metric '{metric_name}'. No matching element found.")
    return 0
        
def update_ssi_table(raw_text, connection_limit, follow_limit, 
                     profiles_to_scan, pag_abertas, daily_like_prob, 
                     daily_comment_prob, speed_factor, feed_posts_limit,
                     feed_like_prob, feed_comment_prob, 
                     withdrawn_count, current_total_connections,
                     file_path='ssi_history.csv'):
    
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    total_match = re.search(r"(\d+)\s+out of 100", raw_text)
    total_ssi = float(total_match.group(1)) if total_match else 0.0

    industry_rank_match = re.search(r"Industry SSI\s+rank\s+Top\s+(\d+)%", raw_text)
    industry_rank = int(industry_rank_match.group(1)) if industry_rank_match else 0
    network_rank_match = re.search(r"Network SSI\s+rank\s+Top\s+(\d+)%", raw_text)
    network_rank = int(network_rank_match.group(1)) if network_rank_match else 0

    def extract_score(component_name, text):
        regex = r"(\d+(?:[\.,]\d+)?)\s+" + re.escape(component_name)
        match = re.search(regex, text)
        return float(match.group(1).replace(',', '.')) if match else 0.0

    # Comparative Calculations
    new_connections_gained = 0
    ssi_increase = 0.0
    
    if os.path.exists(file_path):
        try:
            existing_df = pd.read_csv(file_path)
            
            # Filters the last entry that is NOT today to be the comparison point.
            existing_df['Date'] = pd.to_datetime(existing_df['Date'], errors='coerce').dt.strftime('%Y-%m-%d')
            last_day_df = existing_df[existing_df['Date'] != today]
            
            if not last_day_df.empty:
                last_valid_total = last_day_df['Total_Connections'].dropna().iloc[-1] if 'Total_Connections' in last_day_df.columns else 0
                last_ssi = last_day_df['Total_SSI'].iloc[-1] if 'Total_SSI' in last_day_df.columns else 0
                
                if current_total_connections > 0 and last_valid_total > 0:
                    new_connections_gained = current_total_connections - last_valid_total
                    if new_connections_gained < 0: new_connections_gained = 0 
                
                if last_ssi > 0:
                    ssi_increase = total_ssi - last_ssi
            
        except Exception as e:
            # Print error if any, but continue with 0.0 to avoid breaking.
            print(f"Warning: Failed to calculate SSI metrics from CSV: {e}")
            pass

    new_data = {
        "Date": [today], "Total_SSI": [total_ssi],
        "SSI_Increase": [ssi_increase],
        "Industry_Rank": [industry_rank], "Network_Rank": [network_rank],
        "Brand": [extract_score("Establish your professional brand", raw_text)],
        "People": [extract_score("Find the right people", raw_text)],
        "Insights": [extract_score("Engage with insights", raw_text)],
        "Relationships": [extract_score("Build relationships", raw_text)],
        "Connection_Limit": [connection_limit], "Follow_Limit": [follow_limit],
        "Profiles_To_Scan": [profiles_to_scan], 
        "Group_Like_Prob": [daily_like_prob], "Group_Comment_Prob": [daily_comment_prob],
        "Speed_Factor": [speed_factor],
        "Feed_Posts_Limit": [feed_posts_limit],
        "Feed_Like_Prob": [feed_like_prob],
        "Feed_Comment_Prob": [feed_comment_prob],
        "Withdrawn_Count": [withdrawn_count],
        "Total_Connections": [current_total_connections],
        "New_Connections_Accepted": [new_connections_gained]
    }
    new_df = pd.DataFrame(new_data)
    
    if os.path.exists(file_path):
        existing_df = pd.read_csv(file_path)
        
        # Ensure 'Date' is clean for comparison before filtering
        existing_df['Date'] = pd.to_datetime(existing_df['Date'], errors='coerce').dt.strftime('%Y-%m-%d')
        
        for col in new_df.columns:
            if col not in existing_df.columns: existing_df[col] = pd.NA 
        # Remove existing data for today before appending new data
        if today in existing_df['Date'].values: existing_df = existing_df[existing_df['Date'] != today]
        updated_df = pd.concat([existing_df, new_df], ignore_index=True)
    else: updated_df = new_df
    
    updated_df.to_csv(file_path, index=False)
    return updated_df

def run_extraction_process():
    if not os.path.exists(DRIVER_FILENAME): return
    try: os.system("taskkill /im msedge.exe /f >nul 2>&1")
    except: pass
    
    opts = EdgeOptions()
    ud = os.path.join(os.environ['USERPROFILE'], 'AppData', 'Local', 'Microsoft', 'Edge', 'User Data')
    opts.add_argument(f"--user-data-dir={ud}")
    opts.add_argument("--profile-directory=Default")
    
    try:
        service = EdgeService(executable_path=DRIVER_FILENAME)
        driver = webdriver.Edge(options=opts, service=service)
        driver.set_page_load_timeout(60)
        
        # 1. Get total connections (uses the CORRECTED function)
        total_conns = get_total_connections_count(driver)
        print(f"Total Connections Detected: {total_conns}")
        
        # 2. Get SSI
        driver.get("https://www.linkedin.com/sales/ssi")
        time.sleep(7)
        
        # 3. Save everything (CSV + DB)
        df = update_ssi_table(
            driver.find_element(By.TAG_NAME, "body").text, 
            CONNECTION_LIMIT, FOLLOW_LIMIT, PROFILES_TO_SCAN, PAG_ABERTAS, 
            DAILY_LIKE_PROB, DAILY_COMMENT_PROB, SPEED_FACTOR, 
            FEED_POSTS_LIMIT, FEED_LIKE_PROB, FEED_COMMENT_PROB,
            SESSION_WITHDRAWN_COUNT, total_conns
        )
        print("SSI Updated.")
        print(df.tail(1))

        # [CORRECTED] Collect Dashboard data for SQLite using extract_metric
        print("📊 Collecting Analytics for Dashboard...")
        driver.get("https://www.linkedin.com/dashboard/")
        human_sleep(8, 12) # Increased wait time for dashboard
        try:
            # Use the new robust function for metric extraction (English names)
            impressions = extract_metric(driver, "Post impressions")
            followers = extract_metric(driver, "Followers")
            views = extract_metric(driver, "Profile viewers")
            search = extract_metric(driver, "Search appearances")
            
            # Log the data (log_analytics_db was updated to include followers)
            log_analytics_db(views, impressions, followers, search)
            print(f"Analytics Collected: Views={views}, Impressions={impressions}, Followers={followers}, Search={search}")
        except Exception as e: 
            print(f"Dashboard data collection error: {e}")
            pass

        driver.quit()
    except Exception as e: 
        print(f"SSI Error: {e}")
        # If error, try to close the driver
        try: driver.quit()
        except: pass


# ==============================================================================
# AI & ROBUST ACTIONS
# ==============================================================================

def generate_smart_fallback(name, group_name):
    clean = re.sub(r'[^a-zA-Z\s]', '', name).strip().split()[0].capitalize() if name and name != "Unknown" else "there"
    return f"Hi {clean}, noticed we're both in '{group_name.split('|')[0].strip()}'. I work with Data Science, would love to connect!"

def get_ai_comment(post_text):
    safe_fallbacks = [
        "Great insight, thanks for sharing!",
        "Really interesting point!",
        "Thanks for the valuable information!",
        "Well said, I agree."
    ]
    if ai_client is None: return random.choice(safe_fallbacks)
    
    clean_text = post_text.replace('\n', ' ').strip()[:800]
    # Using 'Act as' to guide the persona
    prompt = f"Act as a Data Scientist with the following expertise: '{AI_PERSONA}'.\nTask: Write a highly professional LinkedIn comment (35-55 words) on: '{clean_text}'.\nTone: Insightful, professional. Do NOT repeat the persona's description in the final comment. No hashtags." 
    
    response = call_robust_ai(prompt, 800)
    
    if not response:
        if VERBOSE: print("    [AI FAIL] Using safety phrase.")
        return random.choice(safe_fallbacks)
    return response

def generate_invite_message(name, headline="", group_name="our group", is_viewer=False):
    if not name or name == "Unknown": first = "there"
    else: first = re.sub(r'[^a-zA-Z\s]', '', name).strip().split()[0].capitalize()
    
    if is_viewer:
        prompt = f"Write a friendly LinkedIn connection message to '{first}' who recently viewed my profile. I am a Data Scientist. Keep it professional and inviting (MAX 280 chars)."
    else:
        clean_group = group_name.split('|')[0].split('(')[0].strip()
        is_recruiter = any(x in headline.lower() for x in ['recruiter', 'talent', 'hr'])
        is_tech = any(x in headline.lower() for x in ['cto', 'head', 'data', 'lead'])
        
        if is_recruiter: prompt = f"Write a professional connection message (MAX 280 chars) to Tech Recruiter '{first}'. I am Data Scientist. Mention '{clean_group}'. Start with 'Hi {first},'."
        elif is_tech: prompt = f"Write a professional connection message (MAX 280 chars) to Tech Lead '{first}'. I am Data Scientist. Mention '{clean_group}'. Start with 'Hi {first},'."
        else: prompt = f"Write a friendly connection message (MAX 280 chars) to '{first}' from '{clean_group}'. Professional. Start with 'Hi {first},'."
    
    msg = call_robust_ai(prompt, 300)
    
    if not msg or "keyword" in msg.lower() or len(msg) < 10: 
        return generate_smart_fallback(name, group_name)
    
    placeholder_pattern = r'\[.*?\]|\{.*?\}|\<.*?\>|\(.*?\)'
    if re.search(placeholder_pattern, msg):
        msg = re.sub(placeholder_pattern, first, msg)
        
    msg = re.sub(r'^(Hi|Hello|Dear)\s+.*?,', '', msg).strip()
    final = f"Hi {first}, {msg}"
    
    return final[:297] + "..." if len(final) > 300 else final

def call_robust_ai(prompt, max_len=800):
    """
    Calls the AI robustly and filters non-BMP and garbage characters.
    """
    if ai_client is None: return None
    garbage_triggers = [
        "discord server", "api error", "request failed", "unable to provide", 
        "language model", "quota exceeded", "verify you are human", "cloudflare", 
        "model does not exist", "request a model", "discord.gg", "join the", "bad gateway",
        # Filters to prevent role-playing junk that breaks EdgeDriver
        "here's the message", "here is the message", "i hope this helps", "here is a message",
        "write a friendly linkedin connection", "i am a data scientist", "write a professional connection message" 
    ]
    models_to_try = ["gpt-3.5-turbo", "mixtral-8x7b", "gpt-4"] 
    
    for model in models_to_try:
        if VERBOSE: print(f"    [AI DEBUG] Trying model: {model}")
        try:
            response = ai_client.chat.completions.create(
                model=model, messages=[{"role": "user", "content": prompt}]
            )
            clean_response = str(response.choices[0].message.content).strip().replace('"', '').replace("'", "")
            clean_response = clean_response.replace('–', '-') 

            # Removes non-BMP characters (emojis, rare symbols) that cause EdgeDriver error
            clean_response = re.sub(r'[^\U00000000-\U0000FFFF]', r'', clean_response, flags=re.UNICODE) 

            is_garbage = False
            if len(clean_response) > max_len or len(clean_response) < 5: is_garbage = True
            if any(t in clean_response.lower() for t in garbage_triggers): is_garbage = True
            if "http" in clean_response.lower() and "linkedin" not in clean_response.lower(): is_garbage = True

            if not is_garbage:
                if VERBOSE: print(f"    [AI Generated - SUCCESS] Model: {model}")
                return clean_response
            else:
                 if VERBOSE: print(f"    [JUNK AI BLOCKED - {model}] {clean_response[:30]}...")
        except Exception as e: 
             if VERBOSE: print(f"    [AI FAIL] Model {model} failed: {e}")
             continue 
    return None

def check_is_top_profile(driver):
    try:
        if driver.find_elements(By.CSS_SELECTOR, ".pv-member-badge--for-top-voice"): return True
        if "K" in driver.find_element(By.CSS_SELECTOR, ".pv-top-card--list").text: return True
    except: pass
    return False

def endorse_skills(driver):
    try:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.75);")
        human_sleep(3, 5)
        btns = driver.find_elements(By.XPATH, "//button[contains(@aria-label, 'Endorse') or contains(@aria-label, 'Recomendar')]")
        for btn in btns[:3]:
            if btn.is_displayed():
                ActionChains(driver).move_to_element(btn).click().perform()
                print("    -> [SSI] Skill Endorsed!")
                human_sleep(2, 3)
                return True
    except: pass
    return False

def perform_reaction_varied(driver, post):
    available_reactions_names = ['like', 'insightful', 'celebrate', 'love']
    try:
        btn = post.find_element(By.CSS_SELECTOR, "button[aria-label*='Like'], button[aria-label*='Gostei']")
        ActionChains(driver).move_to_element(btn).perform()
        human_sleep(0.5, 1.5)
        try:
            reactions = driver.find_elements(By.XPATH, "//button[contains(@class, 'reactions-menu__reaction')]")
            valid_reactions = []
            for r in reactions:
                aria_label = r.get_attribute('aria-label')
                if aria_label and any(name in aria_label.lower() for name in available_reactions_names):
                    valid_reactions.append(r)
            
            if valid_reactions:
                ActionChains(driver).move_to_element(random.choice(valid_reactions)).click().perform()
                print("    -> Reacted (Emotion).")
            else:
                btn.click()
                print("    -> Liked (Joinha)")
        except:
            btn.click()
            print("    -> Liked (Joinha)")
    except: pass

def perform_comment(driver, post, text):
    """Tries to comment on a post robustly."""
    try:
        # 1. Tries to click the comment button (more generic)
        xpath_comment_btn = ".//button[contains(@aria-label, 'Comment') or contains(@aria-label, 'Comentar') or contains(@class, 'comment-button')]"
        btn = post.find_element(By.XPATH, xpath_comment_btn)
        
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", btn)
        human_sleep(2, 4)
        btn.click()
        human_sleep(3, 6) # Waits for the editor to load
        
        # 2. Locates the text box (textarea or div with role='textbox')
        xpath_text_box = "//div[@role='textbox' and @aria-label] | //textarea[@name='message'] | //div[contains(@class, 'ql-editor')]"
        box = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, xpath_text_box))
        )
        
        # 3. Humanized Typing
        ActionChains(driver).move_to_element(box).click().perform()
        human_type(box, text)
        human_sleep(3, 6)
        
        # 4. Locates and clicks the Send button (More robust XPATH/ARIA-LABEL)
        xpath_post_btn = "//button[contains(@class, 'comments-comment-box__submit-button') or contains(@aria-label, 'Post') or contains(@aria-label, 'Publicar')][not(@disabled)]"
        
        # Waits for the send button to be clickable
        post_btn = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, xpath_post_btn))
        )

        post_btn.click()
             
        print(f"    -> Commented (AI): {text[:50]}...")
        human_sleep(8, 15) 
        take_coffee_break() 
        return True
        
    except Exception as e:
        print(f"    -> Failed to comment: {e}")
        # Tries to close any error modal that might have opened
        try:
             driver.find_element(By.XPATH, "//button[@aria-label='Fechar' or @aria-label='Dismiss']").click()
        except:
             pass
        return False

def follow_user(browser):
    try:
        try:
            btn_main = browser.find_element(By.XPATH, "//button[.//span[text()='Follow' or text()='Seguir']]")
            if btn_main.is_displayed():
                browser.execute_script("arguments[0].click();", btn_main)
                print(f"    -> [SSI BRAND BOOST] Followed user (Main Btn): {TEMP_NAME}")
                return True
        except: pass

        xpath_more = "//button[contains(@aria-label, 'More actions') or .//span[text()='Mais'] or .//span[text()='More']]"
        WebDriverWait(browser, 3).until(EC.element_to_be_clickable((By.XPATH, xpath_more))).click()
        human_sleep(1, 2)
        xpath_follow = "//div[contains(@class, 'dropdown')]//span[contains(text(), 'Follow') or contains(text(), 'Seguir')]"
        btn_follow = WebDriverWait(browser, 3).until(EC.element_to_be_clickable((By.XPATH, xpath_follow)))
        browser.execute_script("arguments[0].click();", btn_follow)
        print(f"    -> [SSI BRAND BOOST] Followed user (Menu): {TEMP_NAME}")
        return True
    except: return False

def connect_with_user(browser, name, headline, group_name):
    global SESSION_CONNECTION_COUNT, CONNECTED
    try:
        xpath_primary = "//button[.//span[contains(text(), 'Conectar') or contains(text(), 'Connect')]]"
        btn = browser.find_element(By.XPATH, xpath_primary)
        click_connect_sequence(browser, btn, name, headline, group_name, is_viewer=False) 
        return True
    except Exception as e:
        if 'invalid session id' in str(e).lower(): raise
        try:
            xpath_more = "//button[contains(@aria-label, 'More actions') or .//span[text()='Mais'] or .//span[text()='More']]"
            WebDriverWait(browser, 3).until(EC.element_to_be_clickable((By.XPATH, xpath_more))).click()
            human_sleep(2, 4)
            xpath_drop = "//div[contains(@class, 'dropdown')]//span[contains(text(), 'Conectar') or contains(text(), 'Connect')]"
            btn_drop = WebDriverWait(browser, 3).until(EC.element_to_be_clickable((By.XPATH, xpath_drop)))
            click_connect_sequence(browser, btn_drop, name, headline, group_name, is_viewer=False)
            return True
        except: return False

def click_connect_sequence(browser, button_element, name, headline, group_name, is_viewer=False):
    global SESSION_CONNECTION_COUNT, CONNECTED, TEMP_NAME, TEMP_HEADLINE, CURRENT_GROUP_NAME, SEND_AI_NOTE

    # Check if connection limit is reached BEFORE attempting to click the button
    if SESSION_CONNECTION_COUNT >= CONNECTION_LIMIT:
        print(f"    -> [LIMIT] Connection attempt skipped. Daily limit ({CONNECTION_LIMIT}) reached.")
        return False
        
    ActionChains(browser).move_to_element(button_element).perform()
    human_sleep(1, 2)
    browser.execute_script("arguments[0].click();", button_element)
    human_sleep(3, 6)

    # NOTE SENDING LOGIC
    if SEND_AI_NOTE == 1:
        try:
            xpath_add_note = "//button[@aria-label='Adicionar nota' or @aria-label='Add a note']"
            btn_note = WebDriverWait(browser, 5).until(EC.element_to_be_clickable((By.XPATH, xpath_add_note)))
            btn_note.click()
            
            print("    -> Generating AI Note (Waiting 10s)...")
            time.sleep(10)
            
            if is_viewer:
                message = generate_invite_message(name, "", "", is_viewer=True)
            else:
                message = generate_invite_message(name, headline, group_name)
                
            xpath_msg_box = "//textarea[@name='message']"
            msg_box = browser.find_element(By.XPATH, xpath_msg_box)
            
            human_type(msg_box, message)
            
            human_sleep(2, 4)
            
            send_selectors = [
                "//button[@aria-label='Enviar agora']",
                "//button[@aria-label='Send now']",
                "//button[@aria-label='Enviar convite']",
                "//button[@aria-label='Send invitation']",
                "//button[contains(@class, 'artdeco-button--primary') and not(@disabled)]"
            ]
            
            sent = False
            for sel in send_selectors:
                try:
                    btn = browser.find_element(By.XPATH, sel)
                    if btn.is_displayed():
                        btn.click()
                        sent = True
                        break
                except: continue
                
            if sent:
                CONNECTED = True
                SESSION_CONNECTION_COUNT += 1
                print(f"-> [SUCCESS] Invite Sent with Note to: {name}\n    Note: {message}")
                take_coffee_break() 
                return True
            else:
                raise Exception("Send button not found")
                
        except Exception as e:
            # If note fails (BMP error, AI junk, or button not found), try sending without note
            print(f"-> Failed to add note ({e}). Trying 'Send without note'...")
            try:
                browser.find_element(By.XPATH, "//button[@aria-label='Enviar sem nota' or @aria-label='Send without a note']").click()
                CONNECTED = True
                SESSION_CONNECTION_COUNT += 1
                print(f"-> [SUCCESS] Invite Sent (No Note) to: {name}")
                return True
            except: 
                return False # Total connection failure
    
    # IF SEND_AI_NOTE == 0, TRY TO SEND DIRECTLY
    else: # SEND_AI_NOTE == 0
        try:
            # Look for the 'Send' button directly in the pop-up (no note)
            send_selectors_direct = [
                "//button[@aria-label='Enviar']",
                "//button[@aria-label='Send']",
                "//button[contains(@class, 'artdeco-button--primary') and not(@disabled)]" # generic fallback
            ]
            sent = False
            for sel in send_selectors_direct:
                try:
                    btn = WebDriverWait(browser, 3).until(EC.element_to_be_clickable((By.XPATH, sel)))
                    if btn.is_displayed():
                        btn.click()
                        sent = True
                        break
                except: continue

            if sent:
                CONNECTED = True
                SESSION_CONNECTION_COUNT += 1
                print(f"-> [SUCCESS] Invite Sent (NO NOTE - Flag 0) to: {name}")
                take_coffee_break()
                return True
            else:
                 # Close modal and return false if unable to send
                 try: browser.find_element(By.XPATH, "//button[@aria-label='Fechar' or @aria-label='Dismiss']").click()
                 except: pass
                 return False
                 
        except Exception as e:
            print(f"-> Failed to send direct invite: {e}")
            return False

def run_reciprocator(browser):
    global SESSION_CONNECTION_COUNT
    print("\n-> [RECIPROCATOR] Checking 'Who viewed your profile'...")
    try:
        browser.get("https://www.linkedin.com/me/profile-views/")
        human_sleep(6, 10)
        human_scroll(browser)
        
        try:
            connect_buttons = browser.find_elements(By.XPATH, "//button[.//span[contains(text(), 'Conectar') or contains(text(), 'Connect')]]")
            processed = 0
            for btn in connect_buttons:
                if processed >= 2: break 
                if SESSION_CONNECTION_COUNT >= CONNECTION_LIMIT: break
                
                try:
                    browser.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", btn)
                    human_sleep(2, 4)
                    person_name = "Profile Viewer"
                    print(f"    -> Found disconnected viewer. Trying to connect...")
                    
                    if click_connect_sequence(browser, btn, person_name, "", "", is_viewer=True):
                        # Log to DB
                        try:
                            # Tries to extract the profile link from the parent or neighbor element
                            profile_link = btn.find_element(By.XPATH, "../../../..//a[contains(@href, '/in/')]").get_attribute("href").split('?')[0]
                        except:
                            profile_link = f"Viewer_{datetime.datetime.now().timestamp()}"
                            
                        log_interaction_db(profile_link, person_name, "", "Reciprocator", "Connected")
                        
                        processed += 1
                        sleep_after_connection()
                except Exception as e:
                    print(f"    [Reciprocator Error] {e}")
        except:
            print("    -> No new profiles to connect in this list.")
    except Exception as e:
        print(f"Reciprocator Error: {e}")

def run_networker(browser):
    print("\n-> [NETWORKER] Checking celebrations (Notificações)...")
    try:
        browser.get("https://www.linkedin.com/notifications/")
        human_sleep(6, 9)
        celebration_buttons = browser.find_elements(By.XPATH, "//button[contains(@class, 'notification-action-button') or .//span[contains(text(), 'Congratulate') or contains(text(), 'Parabéns')]]")
        
        if len(celebration_buttons) > 0:
            count = 0
            for btn in celebration_buttons:
                if count >= 3: break 
                try:
                    if btn.is_displayed():
                        browser.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", btn)
                        human_sleep(2, 3)
                        btn.click()
                        print("    -> [SSI BOOST] Celebration sent (Congrats/New Job).")
                        human_sleep(4, 7) 
                        count += 1
                except: pass
        else:
            print("    -> No pending celebrations found.")
    except Exception as e:
        print(f"Networker Error: {e}")

def run_group_bot(browser):
    """
    Corrected Version: Implements While Loop with Scroll to ensure target collection.
    Also implements generic connection to reach CONNECTION_LIMIT and cleans CSV data.
    """
    global SESSION_CONNECTION_COUNT, SESSION_FOLLOW_COUNT, CONNECTED
    if SAVECSV:
        if not os.path.exists("CSV"): os.makedirs("CSV")
        csv_header = ["Name", "Link", "Status", "Time", "Connection_Limit", "Follow_Limit", "Like_Prob", "Comment_Prob", "Profile_Scan_Limit"]
        create_csv(csv_header, TIME)

    print(f'-> Group: {GROUP_URL}')
    browser.get(GROUP_URL)
    human_sleep(10, 15)
    try: group_name = browser.find_element(By.TAG_NAME, 'h1').text
    except: group_name = "our group"
    
    print(f"-> Interacting and Collecting (Target: {PROFILES_TO_SCAN})...")
    
    profiles_queued = []
    scroll_attempts = 0
    max_scroll_attempts = 20 # Safety limit to avoid getting stuck
    
    commented_in_group = set()
    visited_file = 'visitedUsers.txt'
    if not os.path.exists(visited_file): open(visited_file, 'w').close()
    with open(visited_file, 'r') as f: visited_list = [l.strip() for l in f]

    # COLLECTION LOOP WITH SCROLL
    while len(profiles_queued) < PROFILES_TO_SCAN and scroll_attempts < max_scroll_attempts:
        # Get visible posts in the current DOM
        posts = browser.find_elements(By.CLASS_NAME, "feed-shared-update-v2")
        
        for post in posts:
            if len(profiles_queued) >= PROFILES_TO_SCAN: break
            
            try:
                # 1. Tries to extract URL
                url = ""
                try:
                    el = post.find_element(By.XPATH, ".//a[contains(@href, '/in/') and not(contains(@href, '/miniProfile/'))]")
                    url = el.get_attribute("href").split('?')[0]
                    
                    if url and url not in profiles_queued and url not in visited_list: 
                        profiles_queued.append(url)
                        if VERBOSE: print(f"    [Collected] {len(profiles_queued)}/{PROFILES_TO_SCAN}")
                except: pass

                # 2. Interactions (only if visible)
                urn = post.get_attribute("data-urn")
                if urn and urn not in commented_in_group:
                    browser.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", post)
                    human_sleep(1, 2)

                    if random.random() < DAILY_LIKE_PROB:
                        perform_reaction_varied(browser, post)

                    if random.random() < DAILY_COMMENT_PROB:
                        try:
                            text = post.text
                            if len(text) > 15:
                                if FEED_ENGLISH_ONLY and not is_text_english(text):
                                    pass
                                else:
                                    comment = get_ai_comment(text)
                                    if perform_comment(browser, post, comment):
                                        commented_in_group.add(urn)
                        except: pass
                    
                    commented_in_group.add(urn) # Marks as processed in the session
            except: continue
        
        # If target is not met yet, SCROLL
        if len(profiles_queued) < PROFILES_TO_SCAN:
            print(f"    -> Scrolling group... (Attempt {scroll_attempts+1}/{max_scroll_attempts})")
            browser.execute_script("window.scrollBy(0, 800);")
            human_sleep(3, 5) # Wait for new posts to load
            scroll_attempts += 1
    
    print(f"-> Collection finished. Visiting {len(profiles_queued)} profiles...")
    
    processed = 0
    
    for url in profiles_queued:
        if processed >= PAG_ABERTAS: break
        
        print(f"\n[{processed+1}] Visitando: {url}")
        try:
            browser.get(url)
            human_sleep(8, 12)
            processed += 1
            
            try: name = browser.title.split('|')[0].strip()
            except: name = "Unknown"
            try: headline = browser.find_element(By.XPATH, "//div[contains(@class, 'text-body-medium')]").text.lower()
            except: headline = ""
            
            status = "Visited"
            CONNECTED = False
            endorse_skills(browser)
            
            # --- START CONNECTION LOGIC (Connects if target OR if limit allows) ---
            if SESSION_CONNECTION_COUNT < CONNECTION_LIMIT:
                is_target_role = any(role in headline for role in TARGET_ROLES)
                
                if is_target_role:
                    print(f"    -> [TARGET] {headline[:30]}...")
                
                # Tries to connect if it is a TARGET OR if the global limit has not been reached
                if connect_with_user(browser, name, headline, group_name):
                    status = "Connected"
                    sleep_after_connection()
            # --- END CONNECTION LOGIC ---
            
            if status != "Connected" and SESSION_FOLLOW_COUNT < FOLLOW_LIMIT:
                if check_is_top_profile(browser):
                    if follow_user(browser):
                        status = "Followed"
                        SESSION_FOLLOW_COUNT += 1

            # [CORRECTION] Clean data to prevent 'illegal newline value: ,' CSV error
            clean_name = name.replace('\n', ' ').strip()
            clean_headline = headline.replace('\n', ' ').strip()
            clean_status = status.replace('\n', ' ').strip()

            if SAVECSV: 
                add_to_csv([
                    clean_name, # Use cleaned name
                    url, 
                    clean_status, # Use cleaned status
                    str(datetime.datetime.now().time()),
                    CONNECTION_LIMIT,
                    FOLLOW_LIMIT,
                    DAILY_LIKE_PROB,
                    DAILY_COMMENT_PROB,
                    PROFILES_TO_SCAN
                ], TIME)
            
            # [NEW] Saves to DB as well (hybrid)
            log_interaction_db(url, clean_name, clean_headline, "Group", clean_status)
                
            with open(visited_file, 'a') as f: f.write(url + '\n')
            
        except Exception as e: 
            if 'invalid session id' in str(e).lower():
                print(f"\n!!! CRITICAL SESSION ERROR: {e}")
                print("!!! Trying to close and reopen the browser to continue...")
                browser.quit()
                start_browser() 
                return 

            print(f"Visit Error: {e}")
            continue

    print("\n--- FINISHED ---")
    print(f"Total Connected: {SESSION_CONNECTION_COUNT}")
    print(f"Total Followed: {SESSION_FOLLOW_COUNT}")


# ==============================================================================
# START
# ==============================================================================

def start_browser():
    global browser
    if os.name == 'nt': 
        try: os.system("taskkill /im msedge.exe /f >nul 2>&1")
        except: pass
    
    # STEALTH: Random Window Size to avoid fingerprinting
    opts = EdgeOptions()
    width = random.randint(1024, 1920)
    height = random.randint(768, 1080)
    opts.add_argument(f"--window-size={width},{height}")
    
    ud = os.path.join(os.environ['USERPROFILE'], 'AppData', 'Local', 'Microsoft', 'Edge', 'User Data')
    opts.add_argument(f"--user-data-dir={ud}")
    opts.add_argument("--profile-directory=Default")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option('useAutomationExtension', False)
    
    try:
        service = EdgeService(executable_path=DRIVER_FILENAME)
        browser = webdriver.Edge(options=opts, service=service)
        browser.set_page_load_timeout(60) 
        
        browser.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        })

        # 1. Feed Interaction
        interact_with_feed_human(browser)
        
        # 2. Stealth & SSI Boosters (NEW)
        random_browsing_habit(browser) 
        run_networker(browser) # Happy Birthday / Congrats
        run_reciprocator(browser) # Connect with viewers
        
        if random.random() < 0.3: 
            withdraw_old_invites(browser)
            
        # 3. Main Group Logic
        run_group_bot(browser)

        # CORRECTION: Sniper Mode moved to the END to complete the limit
        if SESSION_CONNECTION_COUNT < CONNECTION_LIMIT:
             run_sniper_mode(browser)
        else:
             print("\n🎯 [SNIPER MODE] Daily limit already reached. Skipping Sniper Mode.")
        
    except Exception as e: 
        print(f"General Error: {e}")
        if browser: browser.quit()


def launch():
    if not os.path.isfile('visitedUsers.txt'): open('visitedUsers.txt', 'w').close()
    start_browser()

if __name__ == "__main__":
    print("🤖 Bot Started.")
    try:
        now = datetime.datetime.now()
        limit = now.replace(hour=15, minute=0, second=0)
        
        if now >= limit:
            print("Executing now...")
            run_extraction_process()
            if random.randint(0, 7) != 0: launch()
        else:
            wait = random.uniform(0, (limit - now).total_seconds())
            print(f"Scheduled for: {(now + timedelta(seconds=wait)).strftime('%H:%M:%S')}")
            time.sleep(wait * 0) 
            run_extraction_process()
            if random.randint(0, 7) != 0: launch()
    except KeyboardInterrupt:
        print("\n🛑 Manual Stop.")
        if browser: browser.quit()