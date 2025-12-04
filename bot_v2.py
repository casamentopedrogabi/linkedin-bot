import random
import datetime
import time
import csv
import os
import re
import sqlite3 # ADICIONADO: Para o Dashboard
from datetime import timedelta

# --- BIBLIOTECAS EXTERNAS ---
try:
    from langdetect import detect, LangDetectException
except ImportError:
    print("ERRO CRÍTICO: Instale a lib langdetect -> pip install langdetect")
    exit()

# Inicialização do Cliente AI
try:
    from g4f.client import Client
    ai_client = Client()
    if ai_client is None:
        raise Exception("G4F Client failed to initialize.")
except ImportError:
    print("Aviso: g4f não instalado. IA desativada.")
    Client = None
    ai_client = None
except Exception as e:
    print(f"Aviso: Erro na inicialização do g4f. IA desativada. Detalhe: {e}")
    ai_client = None

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service as EdgeService
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
from selenium.common.exceptions import WebDriverException

# ==============================================================================
# ⚙️ PAINEL DE CONTROLE INTELIGENTE
# ==============================================================================

# 1. MODO DE OPERAÇÃO (PILOTO AUTOMÁTICO)
AUTO_REGULATE = True 

# 2. VELOCIDADE
SPEED_FACTOR = 1.2
DRIVER_FILENAME = "msedgedriver.exe"

# 3. IA & IDIOMA
FEED_ENGLISH_ONLY = True 
AI_PERSONA = "I am a Senior Data Scientist experienced in Python, Databricks, ML and Big Data Strategy."

# 4. ALVOS
TARGET_ROLES = [
    "head of data", "chief data officer", "director of data", "cto", 
    "vp of engineering", "head of analytics", "data science manager",
    "analytics manager", "product owner",
    "senior data scientist", "lead data scientist", "staff data scientist",
    "tech recruiter", "technical recruiter", "talent acquisition", 
    "hr business partner"
]

# 5. LIMITES MANUAIS (Fallback se AUTO_REGULATE = False)
LIMITS_CONFIG = {
    "CONNECTION": (5, 10),
    "FOLLOW": (10, 15),
    "PROFILES_SCAN": (20, 30),
    "FEED_POSTS": (20, 30)
}

# 6. PROBABILIDADES MANUAIS (Fallback se AUTO_REGULATE = False)
PROBS = {
    "FEED_LIKE": (0.40, 0.60),
    "FEED_COMMENT": (0.25, 0.30),
    "GROUP_LIKE": (0.50, 0.70),    
    "GROUP_COMMENT": (0.10, 0.20)  
}

# 7. CONFIGURAÇÕES GERAIS
CONNECT_WITH_USERS = True
SAVECSV = True
VERBOSE = True
# NOVO: Variável para controlar o envio de notas. (1 = Enviar Nota, 0 = Enviar Direto)
SEND_AI_NOTE = 1 

# LISTA COMPLETA DE GRUPOS (ANTIGOS + NOVOS)
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
# [NOVO] INTEGRAÇÃO COM BANCO DE DADOS (SQLITE)
# ==============================================================================
DB_NAME = "bot_data.db"

def init_db():
    """Cria o banco de dados se não existir."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Tabela de Interações
    c.execute('''CREATE TABLE IF NOT EXISTS interactions (
                    profile_url TEXT PRIMARY KEY,
                    name TEXT,
                    headline TEXT,
                    source TEXT,
                    status TEXT,
                    timestamp DATETIME
                )''')
    # Tabela de Analytics (Dashboard)
    c.execute('''CREATE TABLE IF NOT EXISTS profile_analytics (
                    timestamp DATETIME,
                    profile_views INT,
                    post_impressions INT,
                    search_appearances INT
                )''')
    conn.commit()
    conn.close()

def log_interaction_db(url, name, headline, source, status):
    """Salva interação no SQL."""
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Use INSERT OR REPLACE para garantir que perfis visitados recentemente atualizem o status
        c.execute("INSERT OR REPLACE INTO interactions VALUES (?, ?, ?, ?, ?, ?)", 
                  (url, name, headline, source, status, ts))
        conn.commit()
        conn.close()
    except: pass

def log_analytics_db(views, impressions, searches):
    """Salva dados do dashboard."""
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("INSERT INTO profile_analytics VALUES (?, ?, ?, ?)", (ts, views, impressions, searches))
        conn.commit()
        conn.close()
    except: pass

# Inicializa o DB ao carregar o script
init_db()

# ==============================================================================
# LÓGICA DE AUTO-REGULAÇÃO (PILOTO AUTOMÁTICO TOTAL)
# ==============================================================================

def calculate_smart_parameters():
    """
    Define LIMITES e PROBABILIDADES baseados no histórico (dias rodados) e SSI atual.
    Retorna uma tupla: (limits_dict, probs_dict)
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
    
    print(f"\n🧠 [AUTO-PILOT] Diagnóstico: {days_run} dias de uso | SSI Atual: {last_ssi}")
    
    # NÍVEL 1: AQUECIMENTO (0 a 7 dias) -> Comportamento: Observador Tímido
    if days_run < 3:
        print(" -> Modo: AQUECIMENTO (Low Profile & Safety)")
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
    
    # NÍVEL 2: CRESCIMENTO (7 a 14 dias) -> Comportamento: Participante Ativo
    elif days_run < 3:
        print(" -> Modo: CRESCIMENTO (Engajamento Moderado)")
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
    
    # NÍVEL 4: ELITE (SSI > 70) -> Comportamento: Top Voice / Influencer
    elif last_ssi > 40:
        print("    -> Modo: ELITE (Alto Impacto)")
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
        
    # NÍVEL 3: CRUZEIRO (Padrão após 14 dias) -> Comportamento: Profissional Consistente
    else:
        print("    -> Modo: CRUZEIRO (Estabilidade)")
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

# Aplica a lógica SE estiver no automático
if AUTO_REGULATE:
    LIMITS_CONFIG, PROBS = calculate_smart_parameters()

# ==============================================================================
# INICIALIZAÇÃO DE VARIÁVEIS GLOBAIS
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
# FUNÇÕES AUXILIARES
# ==============================================================================

def get_factored_time(seconds):
    return seconds * SPEED_FACTOR

def human_sleep(min_seconds=2, max_seconds=5):
    base_time = random.uniform(min_seconds, max_seconds)
    time.sleep(get_factored_time(base_time))

def sleep_after_connection():
    base_time = random.uniform(45, 90)
    print(f"--- ☕ PAUSA LONGA (Lendo perfil): {get_factored_time(base_time):.0f}s ---")
    time.sleep(get_factored_time(base_time))

def human_scroll(browser):
    try:
        body = browser.find_element(By.TAG_NAME, 'body')
        for _ in range(random.randint(3, 7)):
            body.send_keys(Keys.PAGE_DOWN)
            human_sleep(2, 4)
            # STEALTH: Movimento aleatório do mouse enquanto rola
            if random.random() < 0.3:
                random_mouse_hover(browser)
            
            if random.random() < 0.2:
                body.send_keys(Keys.ARROW_UP) # Volta um pouco pra ler
                human_sleep(1, 2)
    except: pass

def human_type(element, text):
    """Digita como humano com erros e variações de tempo."""
    for char in text:
        if random.random() < 0.04: # 4% chance de erro
            wrong_char = random.choice('abcdefghijklmnopqrstuvwxyz')
            element.send_keys(wrong_char)
            time.sleep(random.uniform(0.1, 0.3))
            element.send_keys(Keys.BACKSPACE)
            time.sleep(random.uniform(0.1, 0.2))
        
        element.send_keys(char)
        time.sleep(random.uniform(0.06, 0.28)) # Variação natural

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
    filename = 'GroupBot-' + time_str.replace(":", "-").replace(".", "-") + '.csv'
    if not os.path.exists('CSV'): os.makedirs('CSV')
    with open(os.path.join('CSV', filename), 'w', newline='', encoding='utf-8') as f:
        csv.writer(f).writerow(data)

def add_to_csv(data, time_str):
    path = os.path.join('CSV', 'GroupBot-' + time_str.replace(":", "-").replace(".", "-") + '.csv')
    if os.path.exists(path):
        with open(path, 'a', newline='', encoding='utf-8') as f: csv.writer(f).writerow(data)

# ==============================================================================
# FUNÇÕES DE INTERAÇÃO (FEED & STEALTH)
# ==============================================================================

def interact_with_feed_human(browser):
    """Interage com o Feed principal antes de ir para os grupos."""
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
                            text_el = post.find_element(By.CSS_SELECTOR, ".update-components-text")
                            text = text_el.text
                            
                            if FEED_ENGLISH_ONLY and not is_text_english(text):
                                continue 
                            
                            if len(text) > 20:
                                comment = get_ai_comment(text)
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

def get_total_connections_count(browser):
    """Extrai o número total de conexões para cálculo de aceitação."""
    try:
        browser.get("https://www.linkedin.com/mynetwork/")
        human_sleep(5, 8)
        try:
            el = browser.find_element(By.CSS_SELECTOR, ".mn-community-summary__entity-info")
            text = el.text
            numbers = re.findall(r'\d+', text.replace('.', '').replace(',', ''))
            if numbers: return int(numbers[0])
        except: pass
        return 0
    except: return 0

def take_coffee_break():
    """Simula uma pausa longa aleatória."""
    if random.random() < 0.08: 
        minutes = random.randint(2, 5)
        print(f"\n💤 [STEALTH] Modo 'Coffee Break' ativado. Pausa de {minutes} minutos...")
        time.sleep(minutes * 60)
        print("⚡ [STEALTH] De volta ao trabalho.\n")

def random_browsing_habit(browser):
    """Visita páginas aleatórias para simular navegação humana."""
    pages = [
        "https://www.linkedin.com/notifications/",
        "https://www.linkedin.com/jobs/",
        "https://www.linkedin.com/mynetwork/",
        "https://www.linkedin.com/me/profile-views/"
    ]
    if random.random() < 0.4: 
        target = random.choice(pages)
        print(f"\n-> [STEALTH] Navegação aleatória (Human Behavior): {target}")
        browser.get(target)
        human_sleep(5, 10)
        human_scroll(browser)
        human_sleep(3, 6)

def withdraw_old_invites(browser):
    """Remove convites antigos e retorna contagem."""
    global SESSION_WITHDRAWN_COUNT
    print("\n-> [MANUTENÇÃO] Verificando convites antigos pendentes...")
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
                    print("    -> Convite antigo retirado (Limpeza SSI).")
                    human_sleep(3, 5)
                    count += 1
                except: pass
    except Exception as e:
        print(f"Erro na limpeza de convites: {e}")
    
    SESSION_WITHDRAWN_COUNT += count
    return count

# ==============================================================================
# [NOVO] SNIPER MODE (CAÇA RECRUTADORES)
# ==============================================================================

def run_sniper_mode(browser):
    """Busca ativa por recrutadores fora dos grupos."""
    global SESSION_CONNECTION_COUNT
    
    if SESSION_CONNECTION_COUNT >= CONNECTION_LIMIT:
        print("\n🎯 [SNIPER MODE] Limite diário de conexões atingido. Pulando Sniper Mode.")
        return
        
    role = random.choice(TARGET_ROLES)
    print(f"\n🎯 [SNIPER MODE] Caçando: {role} (Limite Diário Restante: {CONNECTION_LIMIT - SESSION_CONNECTION_COUNT})")
    
    encoded = role.replace(" ", "%20")
    url = f"https://www.linkedin.com/search/results/people/?keywords={encoded}&origin=SWITCH_SEARCH_VERTICAL"
    
    browser.get(url)
    human_sleep(8, 12)
    
    profiles = browser.find_elements(By.XPATH, "//li[contains(@class, 'reusable-search__result-container')]")
    count = 0
    
    # Limita o Sniper a apenas a quantidade que falta para atingir o limite
    limit_remaining = CONNECTION_LIMIT - SESSION_CONNECTION_COUNT
    max_search_connect = min(3, limit_remaining) # Tenta no máximo 3 dos que restam
    
    for p in profiles:
        if count >= max_search_connect: break 
        if SESSION_CONNECTION_COUNT >= CONNECTION_LIMIT: break
        
        try:
            link = p.find_element(By.XPATH, ".//a[contains(@class, 'app-aware-link')]").get_attribute("href").split('?')[0]
            
            # Abre nova aba
            browser.execute_script("window.open('');")
            browser.switch_to.window(browser.window_handles[-1])
            browser.get(link)
            human_sleep(6, 10)
            
            try: name = browser.title.split('|')[0].strip()
            except: name = "Unknown"
            try: headline = browser.find_element(By.XPATH, "//div[contains(@class, 'text-body-medium')]").text.lower()
            except: headline = ""
            
            # Tenta conectar usando a lógica existente
            print(f"    -> [SNIPER] Analisando: {name}")
            
            # Checa se é alvo e tenta conectar
            is_target = any(r in headline for r in TARGET_ROLES)
            
            if is_target and connect_with_user(browser, name, headline, "Sniper Search"):
                log_interaction_db(link, name, headline, "Sniper", "Connected")
                sleep_after_connection()
                count += 1 # Conta apenas a conexão bem sucedida
            else:
                log_interaction_db(link, name, headline, "Sniper", "Visited")
                
            browser.close()
            browser.switch_to.window(browser.window_handles[0])
            
        except Exception as e: 
            # Fecha a aba se der erro e volta para a principal
            try: 
                browser.close()
                browser.switch_to.window(browser.window_handles[0])
            except: pass
            continue
            
# ==============================================================================
# SSI LOGIC (COM MÉTRICAS COMPLETAS E DASHBOARD DB)
# ==============================================================================

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

    # Cálculos Comparativos
    new_connections_gained = 0
    ssi_increase = 0.0
    
    if os.path.exists(file_path):
        try:
            existing_df = pd.read_csv(file_path)
            
            # Filtra a última entrada que NÃO é de hoje para ser o ponto de comparação.
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
            # Printa o erro se houver, mas continua com 0.0 para não quebrar.
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
        
        # 1. Pega total de conexões
        total_conns = get_total_connections_count(driver)
        print(f"Total Connections Detected: {total_conns}")
        
        # 2. Pega SSI
        driver.get("https://www.linkedin.com/sales/ssi")
        time.sleep(7)
        
        # 3. Salva tudo (CSV + DB)
        df = update_ssi_table(
            driver.find_element(By.TAG_NAME, "body").text, 
            CONNECTION_LIMIT, FOLLOW_LIMIT, PROFILES_TO_SCAN, PAG_ABERTAS, 
            DAILY_LIKE_PROB, DAILY_COMMENT_PROB, SPEED_FACTOR, 
            FEED_POSTS_LIMIT, FEED_LIKE_PROB, FEED_COMMENT_PROB,
            SESSION_WITHDRAWN_COUNT, total_conns
        )
        print("SSI Updated.")
        print(df.tail(1))

        # [NOVO] Coleta dados do Dashboard para o SQLite
        print("📊 Coletando Analytics para Dashboard...")
        driver.get("https://www.linkedin.com/dashboard/")
        time.sleep(5)
        try:
            txt = driver.find_element(By.TAG_NAME, "body").text
            views = int(re.search(r"(\d+)\s+profile views", txt).group(1)) if re.search(r"(\d+)\s+profile views", txt) else 0
            impressions = int(re.search(r"(\d+)\s+post impressions", txt).group(1)) if re.search(r"(\d+)\s+post impressions", txt) else 0
            search = int(re.search(r"(\d+)\s+search appearances", txt).group(1)) if re.search(r"(\d+)\s+search appearances", txt) else 0
            log_analytics_db(views, impressions, search)
        except: pass

        driver.quit()
    except Exception as e: 
        print(f"SSI Error: {e}")
        # Se houver erro, tenta fechar o driver
        try: driver.quit()
        except: pass


# ==============================================================================
# IA & AÇÕES BLINDADAS
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
    # Usando 'Act as' para orientar a persona
    prompt = f"Act as a Data Scientist with the following expertise: '{AI_PERSONA}'.\nTask: Write a highly professional LinkedIn comment (35-55 words) on: '{clean_text}'.\nTone: Insightful, professional. Do NOT repeat the persona's description in the final comment. No hashtags." 
    
    response = call_robust_ai(prompt, 800)
    
    if not response:
        if VERBOSE: print("    [IA FAIL] Usando frase de segurança.")
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
    Chama a IA de forma robusta e filtra caracteres não-BMP e de lixo.
    """
    if ai_client is None: return None
    garbage_triggers = [
        "discord server", "api error", "request failed", "unable to provide", 
        "language model", "quota exceeded", "verify you are human", "cloudflare", 
        "model does not exist", "request a model", "discord.gg", "join the", "bad gateway",
        # CORREÇÃO: Filtros mais rigorosos para evitar o lixo de role-playing que quebra o EdgeDriver
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

            # CORREÇÃO: Remove caracteres não-BMP (emojis, símbolos raros) que causam erro do EdgeDriver
            clean_response = re.sub(r'[^\U00000000-\U0000FFFF]', r'', clean_response, flags=re.UNICODE) 

            is_garbage = False
            if len(clean_response) > max_len or len(clean_response) < 5: is_garbage = True
            if any(t in clean_response.lower() for t in garbage_triggers): is_garbage = True
            if "http" in clean_response.lower() and "linkedin" not in clean_response.lower(): is_garbage = True

            if not is_garbage:
                if VERBOSE: print(f"    [AI Generated - SUCCESS] Model: {model}")
                return clean_response
            else:
                 if VERBOSE: print(f"    [IA LIXO BLOQUEADO - {model}] {clean_response[:30]}...")
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
    try:
        btn = post.find_element(By.CSS_SELECTOR, "button[aria-label*='Comment'], button[aria-label*='Comentar'], .comment-button")
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", btn)
        human_sleep(2, 4)
        btn.click()
        human_sleep(2, 5)
        box = post.find_element(By.CSS_SELECTOR, ".ql-editor, div[role='textbox']")
        ActionChains(driver).move_to_element(box).click().perform()
        human_type(box, text)
        human_sleep(3, 6)
        post.find_element(By.CSS_SELECTOR, "button.comments-comment-box__submit-button, button[class*='primary']").click()
        print(f"    -> Commented (AI): {text[:50]}...")
        human_sleep(8, 15) 
        take_coffee_break() 
        return True
    except Exception as e:
        print(f"    -> Failed to comment: {e}")
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

def filter_profiles(profiles):
    if not os.path.exists('visitedUsers.txt'): return profiles
    with open('visitedUsers.txt', 'r') as f: visited = [line.strip() for line in f]
    filtered = [p for p in profiles if p not in visited]
    return filtered

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

    # LÓGICA DE ENVIO DE NOTA (CORRIGIDA)
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
            # Se a nota falhar (erro BMP, IA lixo, ou botão não encontrado), tenta enviar sem nota
            print(f"-> Failed to add note ({e}). Trying 'Send without note'...")
            try:
                browser.find_element(By.XPATH, "//button[@aria-label='Enviar sem nota' or @aria-label='Send without a note']").click()
                CONNECTED = True
                SESSION_CONNECTION_COUNT += 1
                print(f"-> [SUCCESS] Invite Sent (No Note) to: {name}")
                return True
            except: 
                return False # Falha total na conexão
    
    # SE SEND_AI_NOTE == 0, TENTA ENVIAR DIRETO
    else: # SEND_AI_NOTE == 0
        try:
            # Procura o botão 'Enviar' ou 'Send' diretamente no pop-up (sem nota)
            send_selectors_direct = [
                "//button[@aria-label='Enviar']",
                "//button[@aria-label='Send']",
                "//button[contains(@class, 'artdeco-button--primary') and not(@disabled)]" # fallback genérico
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
                 # Fecha o modal e retorna falso se não conseguir enviar
                 try: browser.find_element(By.XPATH, "//button[@aria-label='Fechar' or @aria-label='Dismiss']").click()
                 except: pass
                 return False
                 
        except Exception as e:
            print(f"-> Failed to send direct invite: {e}")
            return False

def run_reciprocator(browser):
    global SESSION_CONNECTION_COUNT
    print("\n-> [RECIPROCATOR] Verificando 'Quem viu seu perfil'...")
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
                    print(f"    -> Encontrado visualizador desconectado. Tentando conectar...")
                    
                    if click_connect_sequence(browser, btn, person_name, "", "", is_viewer=True):
                        # Log para DB
                        try:
                            # Tenta extrair o link do perfil do elemento pai ou vizinho
                            profile_link = btn.find_element(By.XPATH, "../../../..//a[contains(@href, '/in/')]").get_attribute("href").split('?')[0]
                        except:
                            profile_link = f"Viewer_{datetime.datetime.now().timestamp()}"
                            
                        log_interaction_db(profile_link, person_name, "", "Reciprocator", "Connected")
                        
                        processed += 1
                        sleep_after_connection()
                except Exception as e:
                    print(f"    [Erro Reciprocator] {e}")
        except:
            print("    -> Ninguém novo para conectar nesta lista.")
    except Exception as e:
        print(f"Erro no Reciprocator: {e}")

def run_networker(browser):
    print("\n-> [NETWORKER] Verificando celebrações (Notificações)...")
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
                        print("    -> [SSI BOOST] Celebração enviada (Parabéns/Cargo Novo).")
                        human_sleep(4, 7) 
                        count += 1
                except: pass
        else:
            print("    -> Nenhuma celebração pendente encontrada.")
    except Exception as e:
        print(f"Erro no Networker: {e}")

def run_group_bot(browser):
    """
    Versão Corrigida: Implementa Loop While com Scroll para garantir coleta da meta.
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
    
    print(f"-> Interagindo e Coletando (Meta: {PROFILES_TO_SCAN})...")
    
    profiles_queued = []
    scroll_attempts = 0
    max_scroll_attempts = 20 # Limite de segurança para não travar
    
    commented_in_group = set()
    visited_file = 'visitedUsers.txt'
    if not os.path.exists(visited_file): open(visited_file, 'w').close()
    with open(visited_file, 'r') as f: visited_list = [l.strip() for l in f]

    # LOOP DE COLETA COM SCROLL
    while len(profiles_queued) < PROFILES_TO_SCAN and scroll_attempts < max_scroll_attempts:
        # Pega posts visíveis na DOM atual
        posts = browser.find_elements(By.CLASS_NAME, "feed-shared-update-v2")
        
        for post in posts:
            if len(profiles_queued) >= PROFILES_TO_SCAN: break
            
            try:
                # 1. Tenta extrair URL
                url = ""
                try:
                    el = post.find_element(By.XPATH, ".//a[contains(@href, '/in/') and not(contains(@href, '/miniProfile/'))]")
                    url = el.get_attribute("href").split('?')[0]
                    
                    if url and url not in profiles_queued and url not in visited_list: 
                        profiles_queued.append(url)
                        if VERBOSE: print(f"    [Coletado] {len(profiles_queued)}/{PROFILES_TO_SCAN}")
                except: pass

                # 2. Interações (apenas se visível)
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
                    
                    commented_in_group.add(urn) # Marca como processado na sessão
            except: continue
        
        # Se ainda não bateu a meta, SCROLL
        if len(profiles_queued) < PROFILES_TO_SCAN:
            print(f"    -> Scrollando grupo... (Tentativa {scroll_attempts+1}/{max_scroll_attempts})")
            browser.execute_script("window.scrollBy(0, 800);")
            human_sleep(3, 5) # Espera carregar novos posts
            scroll_attempts += 1
    
    print(f"-> Coleta finalizada. Visitando {len(profiles_queued)} perfis...")
    
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
            
            if SESSION_CONNECTION_COUNT < CONNECTION_LIMIT:
                if any(role in headline for role in TARGET_ROLES):
                    print(f"    -> [ALVO] {headline[:30]}...")
                    if connect_with_user(browser, name, headline, group_name):
                        status = "Connected"
                        sleep_after_connection()
                else:
                    if VERBOSE: print("    -> [SKIP] Não é alvo.")
            
            if status != "Connected" and SESSION_FOLLOW_COUNT < FOLLOW_LIMIT:
                if check_is_top_profile(browser):
                    if follow_user(browser):
                        status = "Followed"
                        SESSION_FOLLOW_COUNT += 1

            if SAVECSV: 
                add_to_csv([
                    name, 
                    url, 
                    status, 
                    str(datetime.datetime.now().time()),
                    CONNECTION_LIMIT,
                    FOLLOW_LIMIT,
                    DAILY_LIKE_PROB,
                    DAILY_COMMENT_PROB,
                    PROFILES_TO_SCAN
                ], TIME)
            
            # [NOVO] Salva no DB também (híbrido)
            log_interaction_db(url, name, headline, "Group", status)
                
            with open(visited_file, 'a') as f: f.write(url + '\n')
            
        except Exception as e: 
            if 'invalid session id' in str(e).lower():
                print(f"\n!!! ERRO CRÍTICO DE SESSÃO: {e}")
                print("!!! Tentando fechar e reabrir o navegador para continuar...")
                browser.quit()
                start_browser() 
                return 

            print(f"Erro visita: {e}")
            continue

    print("\n--- FINISHED ---")
    print(f"Total Connected: {SESSION_CONNECTION_COUNT}")
    print(f"Total Followed: {SESSION_FOLLOW_COUNT}")

def random_mouse_hover(browser):
    try:
        els = browser.find_elements(By.TAG_NAME, 'span')
        if els: ActionChains(browser).move_to_element(random.choice(els)).perform()
    except: pass

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

# ==============================================================================
# START
# ==============================================================================

def start_browser():
    global browser
    if os.name == 'nt': 
        try: os.system("taskkill /im msedge.exe /f >nul 2>&1")
        except: pass
    
    # STEALTH: Random Window Size para evitar fingerprinting
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

        # CORREÇÃO: Sniper Mode movido para o FINAL para completar o limite
        if SESSION_CONNECTION_COUNT < CONNECTION_LIMIT:
             run_sniper_mode(browser)
        else:
             print("\n🎯 [SNIPER MODE] Limite diário já atingido. Pulando Sniper Mode.")
        
    except Exception as e: 
        print(f"Erro Geral: {e}")
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
            print("Executando já...")
            run_extraction_process()
            if random.randint(0, 7) != 0: launch()
        else:
            wait = random.uniform(0, (limit - now).total_seconds())
            print(f"Agendado para: {(now + timedelta(seconds=wait)).strftime('%H:%M:%S')}")
            time.sleep(wait * 0) 
            run_extraction_process()
            if random.randint(0, 7) != 0: launch()
    except KeyboardInterrupt:
        print("\n🛑 Parada Manual.")
        if browser: browser.quit()