import sqlite3
import datetime
import pandas as pd

DB_NAME = "linkedin_data.db"

def init_db():
    """Initializes the SQLite database with necessary tables."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Table: Interaction History (Replaces visitedUsers.txt and CSV logs)
    c.execute('''CREATE TABLE IF NOT EXISTS interactions (
                    profile_url TEXT PRIMARY KEY,
                    name TEXT,
                    headline TEXT,
                    source TEXT,
                    status TEXT,
                    timestamp DATETIME
                )''')
    
    # Table: SSI History (For charts)
    c.execute('''CREATE TABLE IF NOT EXISTS ssi_history (
                    date DATE PRIMARY KEY,
                    total_ssi REAL,
                    people_score REAL,
                    insight_score REAL,
                    brand_score REAL,
                    relationship_score REAL,
                    ssi_rank_industry INT,
                    ssi_rank_network INT
                )''')

    # Table: Dashboard Analytics (From linkedin.com/dashboard/)
    c.execute('''CREATE TABLE IF NOT EXISTS profile_analytics (
                    timestamp DATETIME,
                    profile_views INT,
                    post_impressions INT,
                    search_appearances INT
                )''')
    
    conn.commit()
    conn.close()

def log_interaction(url, name, headline, source, status):
    """Logs a user interaction safely ignoring duplicates."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("INSERT OR IGNORE INTO interactions VALUES (?, ?, ?, ?, ?, ?)", 
                  (url, name, headline, source, status, timestamp))
        # Update status if already exists
        c.execute("UPDATE interactions SET status = ?, timestamp = ? WHERE profile_url = ?", 
                  (status, timestamp, url))
        conn.commit()
    except Exception as e:
        print(f"[DB Error] {e}")
    finally:
        conn.close()

def log_ssi(data_dict):
    """Logs SSI stats."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute('''INSERT OR REPLACE INTO ssi_history VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                  (data_dict['Date'], data_dict['Total_SSI'], data_dict['People'], 
                   data_dict['Insights'], data_dict['Brand'], data_dict['Relationships'],
                   data_dict['Industry_Rank'], data_dict['Network_Rank']))
        conn.commit()
    except Exception as e:
        print(f"[DB Error] SSI Log: {e}")
    finally:
        conn.close()

def log_analytics(views, impressions, searches):
    """Logs profile analytics."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO profile_analytics VALUES (?, ?, ?, ?)", 
              (timestamp, views, impressions, searches))
    conn.commit()
    conn.close()

def get_dataframe(query):
    """Returns a pandas DataFrame from a SQL query."""
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

# Auto-initialize on import
init_db()