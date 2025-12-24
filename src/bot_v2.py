# -*- coding: utf-8 -*-
import csv
import datetime
import gc
import os
import random
import re
import sqlite3  # ADICIONADO: Para o Dashboard
import sys
import time
from datetime import timedelta

import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as EdgeService
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# Corrigir encoding no Windows para suportar emojis
if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from bs4 import BeautifulSoup

# --- BIBLIOTECAS EXTERNAS ---
try:
    from langdetect import LangDetectException, detect
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

# ==============================================================================
# ⚙️ PAINEL DE CONTROLE INTELIGENTE
# ==============================================================================

# 1. MODO DE OPERAÇÃO (PILOTO AUTOMÁTICO)
AUTO_REGULATE = False


BASE_QUICK_CONNECT_URL = "https://www.linkedin.com/search/results/people/?facetNetwork=%5B%22S%22%5D&geoUrn=%5B%22101165590%22%2C%22103350119%22%2C%22102890719%22%2C%22106693272%22%2C%22100364837%22%2C%22105646813%22%2C%22101282230%22%2C%22104738515%22%5D&origin=FACETED_SEARCH"
# ==============================================================================
# FUNÇÕES AUXILIARES
# ==============================================================================

# 2. VELOCIDADE
SPEED_FACTOR = 4
DRIVER_FILENAME = "msedgedriver.exe"

# 3. IA & IDIOMA
FEED_ENGLISH_ONLY = True
AI_PERSONA = "I am a Senior Data Scientist experienced in Python, Databricks, ML and Big Data Strategy."

# 4. ALVOS

HIGH_VALUE_KEYWORDS = [
    # Data Science & ML
    "lead",
    "machine learning",
    "deep learning",
    "generative ai",
    "llms",
    "nlp",
    "reinforcement learning",
    "data scientist",
    "ml engineer",
    "ml engineer",
    # Big Data & Cloud
    "apache spark",
    "databricks",
    "hadoop",
    "cloud architect",
    "aws",
    "gcp",
    "azure",
    "data engineer",
    "etl",
    "big data analytics",
    # Engenharia & DevOps
    "data governance",
    "data quality",
    "data catalog",
    "software engineer",
    "backend development",
    "python development",
    "datamodelling",
]
# 4. ALVOS (Novos alvos expandidos para conexão)
TARGET_ROLES = [
    # Liderança & Executivos
    "chief data officer",
    "cdO",
    "chief technology officer",
    "cto",
    "vp of engineering",
    "vp of data",
    "head of data",
    "head of analytics",
    "director of data",
    "director of engineering",
    "product owner",
    "engineering manager",
    "analytics director",
    "head of machine learning",
    # Especialistas Sênior (Influence)
    "lead data scientist",
    "staff data scientist",
    "principal data scientist",
    "senior data scientist",
    "data science manager",
    "ml engineering lead",
    "tech lead",
    # Recrutamento & RH
    "tech recruiter",
    "technical recruiter",
    "talent acquisition",
    "hr business partner",
    "recruiting manager",
    "recruitment specialist",
]

# 5. LIMITES MANUAIS (Fallback se AUTO_REGULATE = False)
LIMITS_CONFIG = {
    "CONNECTION": (10, 18),
    "FOLLOW": (10, 15),
    "PROFILES_SCAN": (40, 50),
    "FEED_POSTS": (40, 50),
}


QUICK_CONNECT_LIMIT = int(
    random.randint(LIMITS_CONFIG["CONNECTION"][0], LIMITS_CONFIG["CONNECTION"][1])
)

# 6. PROBABILIDADES MANUAIS (Fallback se AUTO_REGULATE = False)
PROBS = {
    "FEED_LIKE": (0.20, 0.30),
    "FEED_COMMENT": (0.05, 0.15),
    "GROUP_LIKE": (0.3, 0.40),
    "GROUP_COMMENT": (0.10, 0.15),
}


# 7. CONFIGURAÇÕES GERAIS
CONNECT_WITH_USERS = True
SAVECSV = True
VERBOSE = True
# NOVO: Variável para controlar o envio de notas. (1 = Enviar Nota, 0 = Enviar Direto)
SEND_AI_NOTE = 0

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
# CAMINHOS DE DADOS (ESTRUTURA REORGANIZADA)
# ==============================================================================
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)
DB_NAME = os.path.join(DATA_DIR, "bot_data.db")


def init_db():
    """Cria o banco de dados se não existir e garante o schema ATUALIZADO."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Tabela de Interações
    c.execute("""CREATE TABLE IF NOT EXISTS interactions (
                    profile_url TEXT PRIMARY KEY,
                    name TEXT,
                    headline TEXT,
                    source TEXT,
                    status TEXT,
                    timestamp DATETIME
                )""")

    # Tabela de Analytics (Dashboard) - Schema ATUALIZADO com engajamento
    c.execute("""CREATE TABLE IF NOT EXISTS profile_analytics (
                    timestamp DATETIME,
                    profile_views INT,
                    post_impressions INT,
                    search_appearances INT,
                    followers INT,
                    feed_comments INT,
                    group_comments INT,
                    feed_likes INT,
                    group_likes INT
                )""")

    # Lógica para adicionar colunas faltantes
    try:
        c.execute("SELECT followers FROM profile_analytics LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("ALTER TABLE profile_analytics ADD COLUMN followers INT")

    try:
        c.execute("SELECT feed_comments FROM profile_analytics LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("ALTER TABLE profile_analytics ADD COLUMN feed_comments INT")

    try:
        c.execute("SELECT group_comments FROM profile_analytics LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("ALTER TABLE profile_analytics ADD COLUMN group_comments INT")

    try:
        c.execute("SELECT feed_likes FROM profile_analytics LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("ALTER TABLE profile_analytics ADD COLUMN feed_likes INT")

    try:
        c.execute("SELECT group_likes FROM profile_analytics LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("ALTER TABLE profile_analytics ADD COLUMN group_likes INT")

    conn.commit()
    conn.close()


def log_interaction_db(url, name, headline, source, status):
    """Salva interação no SQL."""
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Use INSERT OR REPLACE para garantir que perfis visitados recentemente atualizem o status
        c.execute(
            "INSERT OR REPLACE INTO interactions VALUES (?, ?, ?, ?, ?, ?)",
            (url, name, headline, source, status, ts),
        )
        conn.commit()
        conn.close()
    except:
        pass


def log_analytics_db(
    views,
    impressions,
    searches,
    followers,
    feed_comments=0,
    group_comments=0,
    feed_likes=0,
    group_likes=0,
):
    """Salva dados do dashboard com engajamento (comentários e curtidas)."""
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # SQL com 9 placeholders (timestamp, views, impressions, searches, followers, feed_comments, group_comments, feed_likes, group_likes)
        c.execute(
            "INSERT INTO profile_analytics VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                ts,
                views,
                impressions,
                searches,
                followers,
                feed_comments,
                group_comments,
                feed_likes,
                group_likes,
            ),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        # Adicionei um print para depuração, caso o erro persista
        print(f"Erro ao logar analytics no DB: {e}")
        pass


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
    history_file = os.path.join(DATA_DIR, "ssi_history.csv")
    days_run = 0
    last_ssi = 0

    if os.path.exists(history_file):
        try:
            df = pd.read_csv(history_file)
            # Use 'Date' column to count unique days run
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.strftime(
                "%Y-%m-%d"
            )
            days_run = df["Date"].dropna().nunique()
            last_ssi = df["Total_SSI"].iloc[-1] if not df.empty else 0
        except:
            pass

    print(
        f"\n🧠 [AUTO-PILOT] Diagnóstico: {days_run} dias de uso | SSI Atual: {last_ssi}"
    )

    # NÍVEL 1: AQUECIMENTO (0 a 7 dias) -> Comportamento: Observador Tímido
    if days_run < 3:
        print(" -> Modo: AQUECIMENTO (Low Profile & Safety)")
        limits = {
            "CONNECTION": (3, 6),
            "FOLLOW": (5, 8),
            "PROFILES_SCAN": (10, 15),
            "FEED_POSTS": (10, 15),
        }
        probs = {
            "FEED_LIKE": (0.30, 0.50),
            "FEED_COMMENT": (0.05, 0.15),
            "GROUP_LIKE": (0.40, 0.60),
            "GROUP_COMMENT": (0.05, 0.10),
        }
        return limits, probs

    # NÍVEL 2: CRESCIMENTO (7 a 14 dias) -> Comportamento: Participante Ativo
    elif days_run < 14:
        print(" -> Modo: CRESCIMENTO (Engajamento Moderado)")
        limits = {
            "CONNECTION": (10, 10),
            "FOLLOW": (8, 12),
            "PROFILES_SCAN": (0, 15),
            "FEED_POSTS": (0, 2),  # 15 a 20
        }
        probs = {
            "FEED_LIKE": (0.1, 0.65),
            "FEED_COMMENT": (0.0, 0.0),
            "GROUP_LIKE": (0.1, 0.70),
            "GROUP_COMMENT": (0.00, 0.00),
        }
        return limits, probs

    # NÍVEL 4: ELITE (SSI > 70) -> Comportamento: Top Voice / Influencer
    elif last_ssi > 40:
        print("    -> Modo: ELITE (Alto Impacto)")
        limits = {
            "CONNECTION": (15, 20),
            "FOLLOW": (15, 20),
            "PROFILES_SCAN": (40, 60),
            "FEED_POSTS": (30, 50),
        }
        probs = {
            "FEED_LIKE": (0.60, 0.80),
            "FEED_COMMENT": (0.35, 0.50),
            "GROUP_LIKE": (0.70, 0.90),
            "GROUP_COMMENT": (0.30, 0.50),
        }
        return limits, probs

    # NÍVEL 3: CRUZEIRO (Padrão após 14 dias) -> Comportamento: Profissional Consistente
    else:
        print("    -> Modo: CRUZEIRO (Estabilidade)")
        limits = {
            "CONNECTION": (10, 15),
            "FOLLOW": (12, 18),
            "PROFILES_SCAN": (30, 45),
            "FEED_POSTS": (20, 30),
        }
        probs = {
            "FEED_LIKE": (0.50, 0.70),
            "FEED_COMMENT": (0.25, 0.35),
            "GROUP_LIKE": (0.60, 0.80),
            "GROUP_COMMENT": (0.20, 0.30),
        }
        return limits, probs


# Aplica a lógica SE estiver no automático
if AUTO_REGULATE:
    LIMITS_CONFIG, PROBS = calculate_smart_parameters()

# ==============================================================================
# INICIALIZAÇÃO DE VARIÁVEIS GLOBAIS
# ==============================================================================

CONNECTION_LIMIT = int(
    random.randint(LIMITS_CONFIG["CONNECTION"][0], LIMITS_CONFIG["CONNECTION"][1])
)
FOLLOW_LIMIT = int(
    random.randint(LIMITS_CONFIG["FOLLOW"][0], LIMITS_CONFIG["FOLLOW"][1])
)
PROFILES_TO_SCAN = int(
    random.randint(LIMITS_CONFIG["PROFILES_SCAN"][0], LIMITS_CONFIG["PROFILES_SCAN"][1])
)
FEED_POSTS_LIMIT = int(
    random.randint(LIMITS_CONFIG["FEED_POSTS"][0], LIMITS_CONFIG["FEED_POSTS"][1])
)

if random.randint(0, 10) == 0:
    CONNECTION_LIMIT = 0
    print("conection set 0")
if random.randint(0, 10) == 0:
    FOLLOW_LIMIT = 0
    print("follow limit set 0")


PAG_ABERTAS = PROFILES_TO_SCAN
FEED_URL = "https://www.linkedin.com/feed/"
random_key = random.randint(0, len(LINKEDIN_GROUPS_LIST) - 1)
GROUP_URL = LINKEDIN_GROUPS_LIST[random_key]

DAILY_LIKE_PROB = random.uniform(PROBS["GROUP_LIKE"][0], PROBS["GROUP_LIKE"][1])
DAILY_COMMENT_PROB = random.uniform(
    PROBS["GROUP_COMMENT"][0], PROBS["GROUP_COMMENT"][1]
)
FEED_LIKE_PROB = random.uniform(PROBS["FEED_LIKE"][0], PROBS["FEED_LIKE"][1])
FEED_COMMENT_PROB = random.uniform(PROBS["FEED_COMMENT"][0], PROBS["FEED_COMMENT"][1])

SESSION_CONNECTION_COUNT = 0
SESSION_FOLLOW_COUNT = 0
SESSION_WITHDRAWN_COUNT = 0
SESSION_FEED_COMMENTS = 0
SESSION_GROUP_COMMENTS = 0
SESSION_FEED_LIKES = 0
SESSION_GROUP_LIKES = 0
TEMP_NAME = ""
TEMP_HEADLINE = ""
CURRENT_GROUP_NAME = "our shared group"
CONNECTED = False
TIME = str(datetime.datetime.now().time())
COMMENTED_POSTS_FILE = os.path.join(DATA_DIR, "commentedPosts.txt")
LOGS_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")
os.makedirs(LOGS_DIR, exist_ok=True)
browser = None
# Exemplo de como definir a variável global (Adicione no seu painel de controle)


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
        body = browser.find_element(By.TAG_NAME, "body")
        for _ in range(random.randint(3, 7)):
            body.send_keys(Keys.PAGE_DOWN)
            human_sleep(5, 10)
            # STEALTH: Movimento aleatório do mouse enquanto rola
            if random.random() < 0.3:
                random_mouse_hover(browser)

            if random.random() < 0.2:
                body.send_keys(Keys.ARROW_UP)  # Volta um pouco pra ler
                human_sleep(1, 2)
    except:
        pass


def human_type(element, text):
    """Digita como humano com erros e variações de tempo."""
    for char in text:
        if random.random() < 0.04:  # 4% chance de erro
            wrong_char = random.choice("abcdefghijklmnopqrstuvwxyz")
            element.send_keys(wrong_char)
            time.sleep(random.uniform(0.1, 0.3))
            element.send_keys(Keys.BACKSPACE)
            time.sleep(random.uniform(0.1, 0.2))

        element.send_keys(char)
        time.sleep(random.uniform(0.06, 0.28))  # Variação natural


def is_text_english(text):
    try:
        if not text or len(text) < 10:
            return False
        return detect(text) == "en"
    except LangDetectException:
        return False


def get_commented_posts():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(COMMENTED_POSTS_FILE):
        return set()
    with open(COMMENTED_POSTS_FILE, "r") as f:
        return set(line.strip() for line in f)


def save_commented_post(urn):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(COMMENTED_POSTS_FILE, "a") as f:
        f.write(f"{urn}\n")


def create_csv(data, time_str):
    filename = "GroupBot-" + time_str.replace(":", "-").replace(".", "-") + ".csv"
    csv_dir = os.path.join(DATA_DIR, "CSV")
    os.makedirs(csv_dir, exist_ok=True)
    with open(os.path.join(csv_dir, filename), "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(data)


def add_to_csv(data, time_str):
    csv_dir = os.path.join(DATA_DIR, "CSV")
    os.makedirs(csv_dir, exist_ok=True)
    path = os.path.join(
        csv_dir, "GroupBot-" + time_str.replace(":", "-").replace(".", "-") + ".csv"
    )
    if os.path.exists(path):
        with open(path, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(data)


# ==============================================================================
# FUNÇÕES DE INTERAÇÃO (FEED & STEALTH)
# ==============================================================================


def interact_with_feed_human(browser):
    """Interage com o Feed principal antes de ir para os grupos."""
    global FEED_POSTS_LIMIT, SESSION_FEED_COMMENTS, SESSION_FEED_LIKES
    print(
        f"-> [FEED BOT] Starting (Limit: {FEED_POSTS_LIMIT} | English Only: {FEED_ENGLISH_ONLY})"
    )
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
                if processed_count >= FEED_POSTS_LIMIT:
                    break

                try:
                    urn = post.get_attribute("data-urn")
                    if urn in commented_in_feed:
                        continue

                    browser.execute_script(
                        "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                        post,
                    )
                    human_sleep(1.5, 3)

                    # LIKE LOGIC
                    if random.random() < FEED_LIKE_PROB:
                        if perform_reaction_varied(browser, post, "feed"):
                            SESSION_FEED_LIKES += 1

                    # COMMENT LOGIC
                    if random.random() < FEED_COMMENT_PROB:
                        try:
                            text_el = post.find_element(
                                By.CSS_SELECTOR, ".update-components-text"
                            )
                            text = text_el.text

                            if FEED_ENGLISH_ONLY and not is_text_english(text):
                                continue

                            if len(text) > 20:
                                comment = get_ai_comment(text)
                                if perform_comment(browser, post, comment, "feed"):
                                    commented_in_feed.add(urn)
                                    SESSION_FEED_COMMENTS += 1
                        except Exception:
                            pass

                    commented_in_feed.add(urn)
                    processed_count += 1
                except Exception:
                    continue

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
            el = browser.find_element(
                By.CSS_SELECTOR, ".mn-community-summary__entity-info"
            )
            text = el.text
            numbers = re.findall(r"\d+", text.replace(".", "").replace(",", ""))
            if numbers:
                return int(numbers[0])
        except:
            pass
        return 0
    except:
        return 0


def take_coffee_break():
    """Simula uma pausa longa aleatória."""
    if random.random() < 0.08:
        minutes = random.randint(2, 5)
        print(
            f"\n💤 [STEALTH] Modo 'Coffee Break' ativado. Pausa de {minutes} minutos..."
        )
        time.sleep(minutes * 60)
        print("⚡ [STEALTH] De volta ao trabalho.\n")


def random_browsing_habit(browser):
    """Visita páginas aleatórias para simular navegação humana."""
    pages = [
        "https://www.linkedin.com/notifications/",
        "https://www.linkedin.com/jobs/",
        "https://www.linkedin.com/mynetwork/",
        "https://www.linkedin.com/me/profile-views/",
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
        withdraw_buttons = browser.find_elements(
            By.XPATH,
            "//button[contains(@aria-label, 'Retirar') or contains(@aria-label, 'Withdraw')]",
        )
        if len(withdraw_buttons) > 0:
            for btn in reversed(withdraw_buttons):
                if count >= 2:
                    break
                try:
                    browser.execute_script(
                        "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                        btn,
                    )
                    human_sleep(1, 2)
                    btn.click()
                    human_sleep(1, 2)
                    confirm = browser.find_element(
                        By.XPATH,
                        "//button[contains(@class, 'artdeco-modal__confirm-btn')]",
                    )
                    confirm.click()
                    print("    -> Convite antigo retirado (Limpeza SSI).")
                    human_sleep(3, 5)
                    count += 1
                except:
                    pass
    except Exception as e:
        print(f"Erro na limpeza de convites: {e}")

    SESSION_WITHDRAWN_COUNT += count
    return count


# ==============================================================================
# [NOVO] SNIPER MODE (CAÇA RECRUTADORES)
# ==============================================================================

# ==============================================================================
# [NOVO] SNIPER MODE (CAÇA RECRUTADORES) - CORRIGIDO LOG
# ==============================================================================

# ==============================================================================
# [NOVO] SNIPER MODE (CAÇA RECRUTADORES) - CORRIGIDO O CICLO DE VISITA
# ==============================================================================


def run_sniper_mode(browser):
    """Busca ativa por recrutadores fora dos grupos com log detalhado e ciclo de visita."""
    global SESSION_CONNECTION_COUNT

    limit_remaining = CONNECTION_LIMIT - SESSION_CONNECTION_COUNT
    if limit_remaining <= 0:
        print(
            "\n🎯 [SNIPER MODE] Limite diário de conexões já atingido. Pulando Sniper Mode."
        )
        return

    role = random.choice(TARGET_ROLES)
    print(
        f"\n🎯 [SNIPER MODE] Caçando: {role} (Limite Restante: {limit_remaining} / {CONNECTION_LIMIT})"
    )

    encoded = role.replace(" ", "%20")
    # Busca por pessoas em 2º grau de conexão para otimizar convites
    url = f"https://www.linkedin.com/search/results/people/?facetNetwork=%5B%22S%22%5D&keywords={encoded}&origin=SWITCH_SEARCH_VERTICAL"

    browser.get(url)
    human_sleep(8, 12)

    # Coleta todos os containers de resultado (cada container é um perfil)
    profiles = browser.find_elements(
        By.XPATH, "//li[contains(@class, 'reusable-search__result-container')]"
    )
    count_visited = 0

    # Limita a tentativa de conexão para não ser muito agressivo na pesquisa
    max_search_connect = min(5, limit_remaining)

    main_window = browser.current_window_handle

    for p in profiles:
        # Se atingir o limite de conexões da sessão ou o limite do Sniper Mode
        if count_visited >= max_search_connect:
            break
        if SESSION_CONNECTION_COUNT >= CONNECTION_LIMIT:
            break

        link = ""
        name = "Unknown"
        headline = ""

        try:
            # 1. Tenta extrair o link, nome e headline da página de busca
            link_el = p.find_element(
                By.XPATH, ".//a[contains(@class, 'app-aware-link')]"
            )
            link = link_el.get_attribute("href").split("?")[0]

            try:
                name = p.find_element(
                    By.CSS_SELECTOR,
                    ".entity-result__title-text > a > span[aria-hidden='true']",
                ).text
            except:
                pass
            try:
                headline = p.find_element(
                    By.CSS_SELECTOR, ".entity-result__primary-subtitle"
                ).text.lower()
            except:
                pass

            print(
                f"[{SESSION_CONNECTION_COUNT + 1}/{CONNECTION_LIMIT}] 🕵️  Analisando (Sniper): **{name}**"
            )

            # 2. Abre nova aba, muda o foco e navega para o perfil
            browser.execute_script("window.open('');")
            browser.switch_to.window(browser.window_handles[-1])
            browser.get(link)
            human_sleep(6, 10)

            # 3. Executa a lógica de interação (Conexão/Log)
            is_target = any(r in headline for r in TARGET_ROLES)

            if is_target:
                print(f"    -> [ALVO] Headline: {headline[:40]}...")
                if connect_with_user(browser, name, headline, "Sniper Search"):
                    log_interaction_db(link, name, headline, "Sniper", "Connected")
                    print(
                        f"    -> [SUCCESS] **Conectado**. Total: {SESSION_CONNECTION_COUNT}/{CONNECTION_LIMIT}"
                    )
                    sleep_after_connection()
                else:
                    # Falhou em conectar (já conectado, pendente, ou erro no modal)
                    log_interaction_db(link, name, headline, "Sniper", "Visited/Fail")
                    print("    -> [FAIL] Falha ao conectar ou já pendente/conectado.")
            else:
                log_interaction_db(link, name, headline, "Sniper", "Visited/Skipped")
                print("    -> [SKIP] Não é alvo.")

            # 4. Fecha a aba do perfil e volta para a aba principal de busca
            browser.close()
            browser.switch_to.window(main_window)
            count_visited += 1

        except Exception as e:
            print(f"    -> [ERRO NO CICLO DE VISITA] {e}")
            # Garante que a aba atual seja fechada, se for a aba extra
            if (
                len(browser.window_handles) > 1
                and browser.current_window_handle != main_window
            ):
                try:
                    browser.close()
                except:
                    pass

            # Garante que o foco volte para a aba principal para continuar a iteração
            try:
                browser.switch_to.window(main_window)
            except:
                pass
            continue

    print(
        f"🎯 [SNIPER MODE] Concluído. Conexões feitas na sessão: {SESSION_CONNECTION_COUNT}"
    )


# ==============================================================================
# FUNÇÃO PRINCIPAL DE GRUPO - CORRIGIDO LOG
# ==============================================================================

# ==============================================================================
# FUNÇÃO PRINCIPAL DE VARREDURA (SUBSTITUI run_group_bot)
# ==============================================================================


def run_main_bot_logic(browser, sniper_targets=None):
    """
    Combina coleta de perfis do grupo com alvos Sniper e varre a lista completa.
    """
    global SESSION_CONNECTION_COUNT, SESSION_FOLLOW_COUNT, CONNECTED

    if SAVECSV:
        if not os.path.exists("CSV"):
            os.makedirs("CSV")
        csv_header = [
            "Name",
            "Link",
            "Status",
            "Time",
            "Connection_Limit",
            "Follow_Limit",
            "Like_Prob",
            "Comment_Prob",
            "Profile_Scan_Limit",
        ]
        create_csv(csv_header, TIME)

    # CORREÇÃO DE SEGURANÇA: Garante que sniper_targets seja uma lista vazia se for None
    if sniper_targets is None:
        sniper_targets = []

    # 1. COLETA E INTERAÇÃO NO GRUPO
    print(f"-> Group: {GROUP_URL}")
    browser.get(GROUP_URL)
    human_sleep(10, 15)
    try:
        group_name = browser.find_element(By.TAG_NAME, "h1").text
    except:
        group_name = "our group"

    print(f"-> Interagindo e Coletando perfis do Grupo (Meta: {PROFILES_TO_SCAN})...")

    profiles_queued = []
    scroll_attempts = 0
    max_scroll_attempts = 20

    commented_in_group = set()
    visited_file = os.path.join(DATA_DIR, "visitedUsers.txt")
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(visited_file):
        open(visited_file, "w").close()
    with open(visited_file, "r") as f:
        visited_list = [l.strip() for l in f]

    # LOOP DE COLETA COM SCROLL (do Grupo)
    while (
        len(profiles_queued) < PROFILES_TO_SCAN
        and scroll_attempts < max_scroll_attempts
    ):
        posts = browser.find_elements(By.CLASS_NAME, "feed-shared-update-v2")

        # Debug: mostrar quantos posts encontrados
        if scroll_attempts == 0 and len(posts) == 0:
            print(
                "    [DEBUG] Nenhum post encontrado com CLASS 'feed-shared-update-v2'. Tentando alternativas..."
            )
            # Tenta alternativa
            posts = browser.find_elements(
                By.XPATH,
                "//div[contains(@class, 'feed')]//div[contains(@class, 'update')]",
            )

        if len(posts) > 0 and scroll_attempts == 0:
            print(f"    [DEBUG] {len(posts)} posts encontrados no grupo")

        # Se ainda não achou posts, tenta com BeautifulSoup
        if len(posts) == 0 and scroll_attempts == 0:
            try:
                soup = BeautifulSoup(browser.page_source, "html.parser")
                profile_links = []
                for link in soup.find_all("a", href=True):
                    href = link["href"]
                    if "/in/" in href and "/miniProfile/" not in href:
                        clean_link = href.split("?")[0]
                        if (
                            clean_link not in profile_links
                            and clean_link not in visited_list
                            and clean_link not in profiles_queued
                        ):
                            profile_links.append(clean_link)
                            profiles_queued.append(clean_link)
                            if len(profiles_queued) >= PROFILES_TO_SCAN:
                                break

                if len(profile_links) > 0:
                    print(
                        f"    [DEBUG] {len(profile_links)} links de perfil extraídos com BeautifulSoup"
                    )
                    break  # Sai do loop se encontrou links com BS
            except Exception as e:
                print(f"    [DEBUG] Erro ao usar BeautifulSoup: {e}")

        for post in posts:
            if len(profiles_queued) >= PROFILES_TO_SCAN:
                break

            try:
                # Tenta extrair URL e Enfileirar (múltiplas estratégias)
                url = ""
                try:
                    # Estratégia 1: XPath direto para perfil
                    el = post.find_element(
                        By.XPATH,
                        ".//a[contains(@href, '/in/') and not(contains(@href, '/miniProfile/'))]",
                    )
                    url = el.get_attribute("href").split("?")[0]
                except Exception:
                    pass

                if not url:
                    try:
                        # Estratégia 2: Procurar pelo data-member-ocid
                        el = post.find_element(By.XPATH, ".//a[@data-member-ocid]")
                        href = el.get_attribute("href")
                        if "/in/" in href:
                            url = href.split("?")[0]
                    except Exception:
                        pass

                if not url:
                    try:
                        # Estratégia 3: Buscar por qualquer link que tenha /in/
                        all_links = post.find_elements(By.TAG_NAME, "a")
                        for link in all_links:
                            href = link.get_attribute("href")
                            if href and "/in/" in href and "/miniProfile/" not in href:
                                url = href.split("?")[0]
                                break
                    except Exception:
                        pass

                if url and url not in profiles_queued and url not in visited_list:
                    profiles_queued.append(url)
                    if VERBOSE:
                        print(
                            f"    [Coletado Grupo] {len(profiles_queued)}/{PROFILES_TO_SCAN}"
                        )

                # Interações (Likes/Comments)
                urn = post.get_attribute("data-urn")
                if urn and urn not in commented_in_group:
                    browser.execute_script(
                        "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                        post,
                    )
                    human_sleep(1, 2)
                    if random.random() < DAILY_LIKE_PROB:
                        if perform_reaction_varied(browser, post, "group"):
                            SESSION_GROUP_LIKES += 1
                    if random.random() < DAILY_COMMENT_PROB:
                        try:
                            text = post.text
                            if len(text) > 15 and (
                                not FEED_ENGLISH_ONLY or is_text_english(text)
                            ):
                                comment = get_ai_comment(text)
                                if perform_comment(browser, post, comment, "group"):
                                    commented_in_group.add(urn)
                                    SESSION_GROUP_COMMENTS += 1
                        except Exception:
                            pass

                    commented_in_group.add(urn)
            except:
                continue

        if len(profiles_queued) < PROFILES_TO_SCAN:
            print(
                f"    -> Scrollando grupo... (Tentativa {scroll_attempts + 1}/{max_scroll_attempts})"
            )
            try:
                browser.execute_script("window.scrollBy(0, 800);")
                human_sleep(5, 8)  # Aumentado de 3-5 para 5-8 segundos
                gc.collect()  # NOVO: Limpa memória após cada scroll para evitar crashes
            except Exception as e:
                print(f"    [ERRO SCROLL] {str(e)[:80]}... Interrompendo coleta.")
                break  # Sai do loop se scroll falhar (tab crash ou DOM issue)
            scroll_attempts += 1

    # 2. ADICIONA ALVOS SNIPER À LISTA DE PERFIS
    if sniper_targets:
        print(f"-> Incorporando {len(sniper_targets)} alvos Sniper...")
        # Adiciona alvos sniper apenas se não foram visitados ou coletados ainda
        for url in sniper_targets:
            if url not in profiles_queued and url not in visited_list:
                profiles_queued.append(url)

    total_profiles_to_visit = min(PAG_ABERTAS, len(profiles_queued))
    print(
        f"\n-> Varredura finalizada. Visitando **{total_profiles_to_visit}** perfis (Grupo + Sniper)..."
    )

    # 3. LOOP DE VISITA COM LOG DETALHADO (Único para todos os perfis)
    processed = 0

    for url in profiles_queued:
        if processed >= PAG_ABERTAS:
            break

        name = "Unknown"
        headline = ""
        status = "Visited"
        CONNECTED = False

        # Determina a origem para o log DB
        source = "Group"
        if url in sniper_targets:
            source = "Sniper"

        try:
            browser.get(url)
            human_sleep(8, 12)
            processed += 1

            try:
                name = browser.title.split("|")[0].strip()
            except:
                name = "Unknown"
            try:
                headline = browser.find_element(
                    By.XPATH, "//div[contains(@class, 'text-body-medium')]"
                ).text.lower()
            except:
                headline = ""

            print(
                f"\n[{processed}/{total_profiles_to_visit}] Perfil ({source}): **{name}** ({headline[:30]}...)"
            )

            endorse_skills(browser)

            # 1. Tenta CONECTAR (se for alvo e houver limite)
            if SESSION_CONNECTION_COUNT < CONNECTION_LIMIT:
                if any(role in headline for role in TARGET_ROLES):
                    print(
                        f"    -> [ALVO] Conectando ({SESSION_CONNECTION_COUNT}/{CONNECTION_LIMIT})..."
                    )
                    if connect_with_user(browser, name, headline, group_name):
                        status = "Connected"
                        print(
                            f"    -> [SUCCESS] **Conectado**. Total: {SESSION_CONNECTION_COUNT}/{CONNECTION_LIMIT}"
                        )
                        sleep_after_connection()
                    else:
                        print("    -> [FAIL] Falha ao conectar ou já pendente.")

            # 2. Tenta SEGUIR (se não conectou, for Top Profile e houver limite)
            if status not in ["Connected"] and SESSION_FOLLOW_COUNT < FOLLOW_LIMIT:
                if check_is_top_profile(browser):
                    if follow_user(browser):
                        status = "Followed"
                        SESSION_FOLLOW_COUNT += 1
                        print(
                            f"    -> [SUCCESS] **Seguido** (SSI Boost). Total: {SESSION_FOLLOW_COUNT}/{FOLLOW_LIMIT}"
                        )
                elif VERBOSE:
                    print("    -> [SKIP] Não é Top Profile para seguir.")

            # 3. Log final
            log_interaction_db(url, name, headline, source, status)
            visited_file_path = os.path.join(DATA_DIR, "visitedUsers.txt")
            with open(visited_file_path, "a") as f:
                f.write(url + "\n")

            # Log CSV
            if SAVECSV:
                add_to_csv(
                    [
                        name,
                        url,
                        status,
                        str(datetime.datetime.now().time()),
                        CONNECTION_LIMIT,
                        FOLLOW_LIMIT,
                        DAILY_LIKE_PROB,
                        DAILY_COMMENT_PROB,
                        PROFILES_TO_SCAN,
                    ],
                    TIME,
                )

        except Exception as e:
            if "invalid session id" in str(e).lower():
                print(f"\n!!! ERRO CRÍTICO DE SESSÃO: {e}")
                browser.quit()
                start_browser()
                return
            print(f"Erro visita: {e}")
            continue

    print("\n--- VARREDURA FINALIZADA ---")
    print(f"Total Connected na Sessão: {SESSION_CONNECTION_COUNT}/{CONNECTION_LIMIT}")
    print(f"Total Followed na Sessão: {SESSION_FOLLOW_COUNT}/{FOLLOW_LIMIT}")


# ==============================================================================
# [NOVO] COLETA SNIPER (APENAS LINKS)
# ==============================================================================

# ==============================================================================
# [NOVO] COLETA SNIPER (APENAS LINKS) - CORREÇÃO AGRESSIVA DE XPATH
# ==============================================================================


# ==============================================================================
# [NOVO] COLETA SNIPER (PAGINAÇÃO E XPATH CORRIGIDO)
# ==============================================================================

# ==============================================================================
# [NOVO] COLETA SNIPER (COM ESPERA EXPLÍCITA E FILTRO ROBUSTO)
# ==============================================================================

# ==============================================================================
# [NOVO] COLETA SNIPER (COM FILTRO DE LOCALIZAÇÃO E ESPERA EXPLÍCITA)
# ==============================================================================


import random

# ==============================================================================
# [NOVO] COLETA SNIPER (COM BEAUTIFULSOUP ROBUSTO)
# ==============================================================================

# ==============================================================================
# [NOVO] COLETA SNIPER (COM BEAUTIFULSOUP ROBUSTO - LÓGICA CONFIRMADA)
# ==============================================================================


# NOTA: Assumindo que BASE_SNIPER_URL é uma variável global definida no seu painel de controle.

# ==============================================================================
# [NOVO] COLETA SNIPER (COM URL BASE CONSTANTE)
# ==============================================================================


def collect_sniper_targets(browser):
    """
    Busca ativa por alvos iterando pelas primeiras 3 páginas de resultados da busca,
    usando a BASE_SNIPER_URL fornecida e apenas variando o parâmetro 'page'.
    Retorna: list de URLs únicas.
    """
    global CONNECTION_LIMIT, SESSION_CONNECTION_COUNT, BASE_SNIPER_URL

    # ⚠️ AVISO: Certifique-se de que BASE_SNIPER_URL está definida e acessível globalmente!
    if "BASE_SNIPER_URL" not in globals() or not BASE_SNIPER_URL:
        print(
            "\n❌ ERRO CRÍTICO: BASE_SNIPER_URL não está definida no escopo global. Pulando coleta Sniper."
        )
        return []

    limit_remaining = CONNECTION_LIMIT - SESSION_CONNECTION_COUNT
    if limit_remaining <= 0:
        print(
            "\n🎯 [SNIPER MODE] Limite diário de conexões já atingido. Pulando coleta Sniper."
        )
        return []

    print("\n🎯 [SNIPER COLLECT] Usando URL Base Fixa (Iterando 3 páginas).")

    profiles_links = set()
    MAX_PAGES = 3
    MAX_LIMIT = 30  # Limite máximo de links para coletar

    for page_num in range(1, MAX_PAGES + 1):
        if len(profiles_links) >= MAX_LIMIT:
            break

        # CONSTRUÇÃO DA URL: Apenas anexa "&page={page_num}" à URL base
        url = f"{BASE_SNIPER_URL}&page={page_num}"

        print(f"    -> Navegando para página {page_num}...")
        browser.get(url)

        # Pausa inicial (AUMENTADA)
        time.sleep(get_factored_time(5))

        try:
            # ROLAGEM AGRESSIVA (Para forçar Lazy Load)
            print("    📜 Scrolling page to load elements...")
            browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(get_factored_time(3))
            browser.execute_script(
                "window.scrollTo(0, document.body.scrollHeight / 2);"
            )
            time.sleep(get_factored_time(1))
            browser.execute_script("window.scrollTo(0, 0);")
            time.sleep(get_factored_time(1))

            # 2. PARSE HTML com BeautifulSoup
            soup = BeautifulSoup(browser.page_source, "html.parser")

            # 3. Extração de links de perfil (Lógica BS4 confirmada)
            all_links = soup.find_all("a", href=True)
            profiles_found_on_this_page = 0
            initial_count = len(profiles_links)

            for link in all_links:
                if len(profiles_links) >= MAX_LIMIT:
                    break

                href = link["href"]

                # Filter: Only profile links (/in/)
                if (
                    "/in/" in href
                    and "linkedin.com/in/" in href
                    or href.startswith("/in/")
                ):
                    # Cleanup: Remove query params
                    clean_link = href.split("?")[0]

                    # Fix relative links
                    if clean_link.startswith("/in/"):
                        clean_link = "https://www.linkedin.com" + clean_link

                    # === GARBAGE FILTER (ACo/ACw) ===
                    slug = clean_link.split("/in/")[-1].strip("/")

                    # If slug starts with "ACo" or "ACw", it is internal garbage
                    if not slug.startswith("ACo") and not slug.startswith("ACw"):
                        if clean_link not in profiles_links:
                            profiles_links.add(clean_link)
                            profiles_found_on_this_page += 1

            new_count = len(profiles_links) - initial_count

            if new_count > 0:
                print(
                    f"    -> Página {page_num}: ✅ Coletados {new_count} novos links. Total: {len(profiles_links)}."
                )
            else:
                print(
                    f"    -> Página {page_num}: ⚠️ Não foi encontrado nenhum link novo válido. Total: {len(profiles_links)}."
                )

        except Exception as e:
            print(f"    -> [ERRO COLETA SNIPER] Falha na página {page_num}: {e}")

        # Pausa humana entre páginas
        time.sleep(random.uniform(4, 7))

    print(
        f"\n    -> Coleta Sniper concluída. Total de links coletados: {len(profiles_links)}."
    )
    return list(profiles_links)


# ==============================================================================
BASE_SNIPER_URL = "https://www.linkedin.com/search/results/people/?geoUrn=%5B%22101165590%22%2C%22103350119%22%2C%22102890719%22%2C%22106693272%22%2C%22100364837%22%2C%22105646813%22%2C%22101282230%22%2C%22104738515%22%5D&keywords=vp%20of%20data&origin=FACETED_SEARCH"


# ==============================================================================
# [NOVO] CONEXÕES RÁPIDAS (5 Diretas, Injeção de Keyword)
# ==============================================================================
# NOTE: BASE_QUICK_CONNECT_URL must be defined globally, containing geoUrns and facetNetwork, but NOT keywords.

# ==============================================================================
# [NOVO] CONEXÕES RÁPIDAS (Corrigida: Stale Element e XPATH para <a>)
# ==============================================================================
# The necessary imports are assumed to be present at the top of the file
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# import random


def run_quick_connects(browser):
    """
    Access BASE_QUICK_CONNECT_URL with TARGET_ROLES keywords and look for connection buttons/links.
    Clicks them across multiple pages until QUICK_CONNECT_LIMIT is reached.
    """

    global SESSION_CONNECTION_COUNT, CONNECTION_LIMIT

    # Settings for this run
    connect_count = 0
    page = 1
    max_pages = 20

    print(
        f"\n⚡️ [QUICK CONNECTS] Tentando {QUICK_CONNECT_LIMIT} conexões diretas...",
        flush=True,
    )

    keyword = random.choice(TARGET_ROLES)
    print(f"    🎯 Buscando por: '{keyword}'", flush=True)
    keyword_encoded = keyword.replace(" ", "%20")
    quick_connect_url_with_keyword = (
        f"{BASE_QUICK_CONNECT_URL}&keywords={keyword_encoded}"
    )

    while connect_count < QUICK_CONNECT_LIMIT and page <= max_pages:
        url = (
            quick_connect_url_with_keyword
            if page == 1
            else f"{quick_connect_url_with_keyword}&page={page}&spellCorrectionEnabled=true"
        )

        print(f"    -> Página {page}...")
        browser.get(url)
        human_sleep(8, 12)

        # Scroll to load all results
        for _ in range(2):
            browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            human_sleep(1, 2)
        browser.execute_script("window.scrollTo(0, 0);")

        try:
            # Enhanced XPath to find both <a> and <button> containing "Invite...to connect"
            # This covers the new HTML structure you provided
            query = "//*[(self::a or self::button) and contains(@aria-label, 'Invite') and contains(@aria-label, 'to connect')]"
            invite_elements = browser.find_elements(By.XPATH, query)

            if not invite_elements:
                print(f"    -> Nenhum botão de conexão encontrado na página {page}.")
                page += 1
                continue

            print(f"    -> Encontrados {len(invite_elements)} botões de conexão")

            for element in invite_elements:
                if connect_count >= QUICK_CONNECT_LIMIT:
                    break

                name = "Unknown"
                try:
                    aria_label = element.get_attribute("aria-label")
                    if aria_label and "Invite " in aria_label:
                        name = aria_label.split("Invite ")[1].split(" to connect")[0]

                    # Ensure element is in view
                    browser.execute_script(
                        "arguments[0].scrollIntoView({block: 'center'});", element
                    )
                    human_sleep(1, 2)

                    # Click the Connect button
                    browser.execute_script("arguments[0].click();", element)
                    print(f"    -> Tentando conectar com: {name}")
                    human_sleep(3, 4)

                    # Handle the "Send without a note" modal
                    modal_closed = False
                    try:
                        wait_modal = WebDriverWait(browser, 4)
                        # Target the 'Send without a note' button specifically
                        send_btn = wait_modal.until(
                            EC.element_to_be_clickable(
                                (
                                    By.XPATH,
                                    "//button[@aria-label='Send without a note' or @aria-label='Enviar sem nota']",
                                )
                            )
                        )
                        browser.execute_script("arguments[0].click();", send_btn)
                        modal_closed = True
                        print(f"    -> [✓] {name} (Convite enviado)")
                    except Exception:
                        # Check if a direct 'Send' button exists as fallback
                        try:
                            direct_send = browser.find_element(
                                By.XPATH,
                                "//button[contains(@class, 'artdeco-button--primary') and contains(., 'Send')]",
                            )
                            browser.execute_script("arguments[0].click();", direct_send)
                            modal_closed = True
                        except:
                            pass

                    if modal_closed:
                        connect_count += 1
                        SESSION_CONNECTION_COUNT += 1
                        human_sleep(4, 6)
                    else:
                        # If stuck, try to escape the modal
                        browser.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                        print(f"    -> [!] Modal não respondeu para {name}")

                except Exception as e:
                    print(f"    -> [✗] Erro ao processar item: {str(e)[:40]}")
                    continue

        except Exception as e:
            print(f"    -> Erro na coleta da página: {str(e)[:50]}")

        page += 1

    print(f"⚡️ [QUICK CONNECTS] Concluído: {connect_count} conexões.")


# ==============================================================================


def update_ssi_table(
    raw_text,
    connection_limit,
    follow_limit,
    profiles_to_scan,
    pag_abertas,
    daily_like_prob,
    daily_comment_prob,
    speed_factor,
    feed_posts_limit,
    feed_like_prob,
    feed_comment_prob,
    withdrawn_count,
    current_total_connections,
    current_total_followers,  # 14º PARÂMETRO
    file_path=None,
):
    if file_path is None:
        file_path = os.path.join(DATA_DIR, "ssi_history.csv")
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
        return float(match.group(1).replace(",", ".")) if match else 0.0

    # Cálculos Comparativos
    new_connections_gained = 0
    ssi_increase = 0.0

    if os.path.exists(file_path):
        try:
            existing_df = pd.read_csv(file_path)

            # Filtra a última entrada que NÃO é de hoje para ser o ponto de comparação.
            existing_df["Date"] = pd.to_datetime(
                existing_df["Date"], errors="coerce"
            ).dt.strftime("%Y-%m-%d")
            last_day_df = existing_df[existing_df["Date"] != today]

            if not last_day_df.empty:
                # CORREÇÃO CRÍTICA: Trata o caso da coluna 'Total_Connections' não existir em arquivos antigos
                last_valid_total = 0
                if "Total_Connections" in last_day_df.columns:
                    last_valid_total = (
                        last_day_df["Total_Connections"].dropna().iloc[-1]
                        if not last_day_df["Total_Connections"].dropna().empty
                        else 0
                    )

                last_ssi = (
                    last_day_df["Total_SSI"].iloc[-1]
                    if "Total_SSI" in last_day_df.columns
                    else 0
                )

                if current_total_connections > 0 and last_valid_total > 0:
                    new_connections_gained = (
                        current_total_connections - last_valid_total
                    )
                    if new_connections_gained < 0:
                        new_connections_gained = 0

                if last_ssi > 0:
                    ssi_increase = total_ssi - last_ssi

        except Exception as e:
            print(f"Warning: Failed to calculate SSI metrics from CSV: {e}")
            pass

    new_data = {
        "Date": [today],
        "Total_SSI": [total_ssi],
        "SSI_Increase": [ssi_increase],
        "Industry_Rank": [industry_rank],
        "Network_Rank": [network_rank],
        "Brand": [extract_score("Establish your professional brand", raw_text)],
        "People": [extract_score("Find the right people", raw_text)],
        "Insights": [extract_score("Engage with insights", raw_text)],
        "Relationships": [extract_score("Build relationships", raw_text)],
        "Connection_Limit": [connection_limit],
        "Follow_Limit": [follow_limit],
        "Profiles_To_Scan": [profiles_to_scan],
        "Group_Like_Prob": [daily_like_prob],
        "Group_Comment_Prob": [daily_comment_prob],
        "Speed_Factor": [speed_factor],
        "Feed_Posts_Limit": [feed_posts_limit],
        "Feed_Like_Prob": [feed_like_prob],
        "Feed_Comment_Prob": [feed_comment_prob],
        "Withdrawn_Count": [withdrawn_count],
        "Total_Connections": [current_total_connections],
        "New_Connections_Accepted": [new_connections_gained],
        "Total_Followers": [current_total_followers],  # NOVO CAMPO AQUI
    }
    new_df = pd.DataFrame(new_data)

    if os.path.exists(file_path):
        existing_df = pd.read_csv(file_path)

        # Ensure 'Date' is clean for comparison before filtering
        existing_df["Date"] = pd.to_datetime(
            existing_df["Date"], errors="coerce"
        ).dt.strftime("%Y-%m-%d")

        # GARANTE que todas as colunas novas existam no DataFrame antigo (evita erro de concat)
        for col in new_df.columns:
            if col not in existing_df.columns:
                existing_df[col] = pd.NA

        # Remove existing data for today before appending new data
        if today in existing_df["Date"].values:
            existing_df = existing_df[existing_df["Date"] != today]
        updated_df = pd.concat([existing_df, new_df], ignore_index=True)
    else:
        updated_df = new_df

    updated_df.to_csv(file_path, index=False)
    return updated_df


def generate_smart_fallback(name, group_name):
    """
    CORREÇÃO: Simplifica o fallback para evitar erros de formatação da IA,
    garantindo que o nome de usuário (first) esteja sempre presente.
    """
    clean = (
        re.sub(r"[^a-zA-Z\s]", "", name).strip().split()[0].capitalize()
        if name and name != "Unknown"
        else "there"
    )

    # Mensagem mais simples e robusta
    fallback_message = (
        f"Hi {clean}, saw we are in the same group: '{group_name.split('|')[0].strip()}'. "
        f"As a Senior Data Scientist, I'd love to connect with fellow professionals."
    )
    return (
        fallback_message[:297] + "..."
        if len(fallback_message) > 300
        else fallback_message
    )


def connect_with_user(browser, name, headline, group_name):
    """
    Tenta a conexão primária e o fallback mais robusto para o menu 'Mais'.
    """
    global SESSION_CONNECTION_COUNT
    if SESSION_CONNECTION_COUNT >= CONNECTION_LIMIT:
        print(
            f"    -> [LIMIT] Connection attempt skipped. Daily limit ({CONNECTION_LIMIT}) reached."
        )
        return False

    try:
        # Tenta 1: Botão primário de 'Conectar' (mais comum)
        xpath_primary = "//button[.//span[contains(text(), 'Conectar') or contains(text(), 'Connect')]]"
        btn = browser.find_element(By.XPATH, xpath_primary)

        return click_connect_sequence(
            browser, btn, name, headline, group_name, is_viewer=False
        )

    except Exception as e:
        if "invalid session id" in str(e).lower():
            raise  # Erro crítico não-recuperável

        # Tentativa 2: Procura no menu 'Mais' (More actions)
        try:
            xpath_more = "//button[contains(@aria-label, 'More actions') or .//span[text()='Mais'] or .//span[text()='More']]"

            # Tenta clicar no botão 'Mais ações'
            btn_more = WebDriverWait(browser, 5).until(
                EC.element_to_be_clickable((By.XPATH, xpath_more))
            )

            # Usa JS click para garantir que o dropdown abra, evitando interceptação
            browser.execute_script("arguments[0].click();", btn_more)
            human_sleep(2, 4)

            # Procura o botão 'Conectar' DENTRO do dropdown
            xpath_drop = "//div[contains(@class, 'dropdown')]//span[contains(text(), 'Conectar') or contains(text(), 'Connect')]"
            btn_drop = WebDriverWait(browser, 5).until(
                EC.element_to_be_clickable((By.XPATH, xpath_drop))
            )

            return click_connect_sequence(
                browser, btn_drop, name, headline, group_name, is_viewer=False
            )

        except Exception as more_e:
            # Se falhou o primário e o menu 'Mais'
            print(
                f"    -> [SKIP] Não encontrou botão 'Conectar' (Primário ou Menu 'Mais'). Detalhe do erro: {more_e}"
            )
            return False


def click_connect_sequence(
    browser, button_element, name, headline, group_name, is_viewer=False
):
    """
    Sequência blindada para clique no botão Connect e manipulação do modal.
    Usa JS Click para evitar ElementClickInterceptedException.
    """
    global SESSION_CONNECTION_COUNT, CONNECTED, SEND_AI_NOTE

    if SESSION_CONNECTION_COUNT >= CONNECTION_LIMIT:
        return False

    # 1. Clica no botão 'Conectar' usando JS para evitar interceptação
    try:
        ActionChains(browser).move_to_element(button_element).perform()
        human_sleep(1, 2)
        browser.execute_script("arguments[0].click();", button_element)
        print(
            "    -> [CLICK] Botão Connect clicado. Esperando modal aparecer...",
            flush=True,
        )

        # ESPERA EXPLÍCITA: Aguarda o modal aparecer antes de fazer qualquer coisa
        try:
            WebDriverWait(browser, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//div[@data-test-modal-id='send-invite-modal']")
                )
            )
            print(
                "    ✅ [MODAL] Modal detectado! Procurando botão 'Send without a note'...",
                flush=True,
            )
        except Exception as modal_wait_error:
            print(
                f"    ❌ [MODAL] Timeout esperando modal: {modal_wait_error}",
                flush=True,
            )
            return False

    except Exception as e:
        print(
            f"    -> [ERROR] Failed to click 'Connect' button (JS/ActionChains): {e}",
            flush=True,
        )
        return False  # Falhou na primeira etapa

    # 1.5 NOVO: Fecha o modal "Add a note to your invitation?" clicando em "Send without a note"
    modal_closed_successfully = False
    try:
        # Múltiplos seletores para o botão "Send without a note" com diferentes estratégias
        send_without_note_selectors = [
            # 1. Seletor por aria-label com contains (case-insensitive)
            (
                "XPATH 1 (aria-label)",
                "//button[contains(@aria-label, 'Send without a note')]",
            ),
            # 2. Seletor por aria-label em português
            ("XPATH 2 (Enviar)", "//button[contains(@aria-label, 'Enviar sem nota')]"),
            # 3. Buscar span com texto e subir para button
            (
                "XPATH 3 (span ancestor)",
                "//span[contains(text(), 'Send without a note')]/ancestor::button",
            ),
            # 4. Buscar button que contém span com o texto
            (
                "XPATH 4 (contains span)",
                "//button[.//span[contains(text(), 'Send without a note')]]",
            ),
            # 5. Buscar o último button primário na actionbar (mais comum)
            (
                "XPATH 5 (actionbar primary)",
                "//div[contains(@class, 'artdeco-modal__actionbar')]//button[contains(@class, 'artdeco-button--primary')]",
            ),
            # 6. Buscar button primário dentro do modal
            (
                "XPATH 6 (modal primary last)",
                "//div[@data-test-modal-id='send-invite-modal']//button[contains(@class, 'artdeco-button--primary')][last()]",
            ),
            # 7. CSS Selector para button na actionbar
            (
                "CSS 7 (actionbar)",
                "div.artdeco-modal__actionbar button.artdeco-button--primary",
            ),
            # 8. Buscar qualquer button ml1 que seja primary
            (
                "XPATH 8 (ml1 primary)",
                "//button[contains(@class, 'artdeco-button--primary') and contains(@class, 'ml1')]",
            ),
        ]

        btn_no_note = None
        for selector_type, selector_value in send_without_note_selectors:
            try:
                print(f"    -> [DEBUG] Tentando {selector_type}...", flush=True)
                if selector_type.startswith("CSS"):
                    btn_no_note = WebDriverWait(browser, 3).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector_value))
                    )
                else:  # XPATH
                    btn_no_note = WebDriverWait(browser, 3).until(
                        EC.element_to_be_clickable((By.XPATH, selector_value))
                    )
                if btn_no_note:
                    print(
                        f"    ✅ [ENCONTRADO] Botão com seletor: {selector_type}",
                        flush=True,
                    )
                    break
            except Exception:
                print(f"    ❌ [FALHOU] {selector_type}", flush=True)
                continue

        if btn_no_note:
            print("    -> [CLICANDO] Executando clique no botão...", flush=True)
            try:
                browser.execute_script(
                    "arguments[0].scrollIntoView(true);", btn_no_note
                )
                human_sleep(0.5, 1)
                browser.execute_script("arguments[0].click();", btn_no_note)
                print(
                    "    ✅ [CLICADO] Botão 'Send without a note' foi clicado!",
                    flush=True,
                )

                # AGUARDA O MODAL DESAPARECER COMPLETAMENTE
                print("    -> [AGUARDANDO] Esperando modal fechar...", flush=True)
                try:
                    WebDriverWait(browser, 10).until(
                        EC.invisibility_of_element_located(
                            (By.XPATH, "//div[@data-test-modal-id='send-invite-modal']")
                        )
                    )
                    print(
                        "    ✅ [MODAL FECHADO] Modal desapareceu com sucesso!",
                        flush=True,
                    )
                    modal_closed_successfully = True
                except Exception as modal_close_error:
                    print(f"    ❌ [MODAL NÃO FECHOU] {modal_close_error}", flush=True)
                    # Mesmo que o wait falhe, marca como sucesso se o clique foi feito
                    modal_closed_successfully = True
            except Exception as click_error:
                print(f"    ❌ [ERRO AO CLICAR] {click_error}", flush=True)
        else:
            # Se nenhum seletor funcionou, tenta JavaScript puro para encontrar e clicar
            if VERBOSE:
                print(
                    "    -> [DEBUG] Nenhum seletor funcionou. Tentando JS puro...",
                    flush=True,
                )
            try:
                # JavaScript que procura o botão e clica nele
                js_code = """
                var buttons = document.querySelectorAll('button');
                for (var i = 0; i < buttons.length; i++) {
                    if (buttons[i].getAttribute('aria-label') && 
                        buttons[i].getAttribute('aria-label').includes('Send without a note')) {
                        buttons[i].click();
                        return true;
                    }
                    // Também procura por text content
                    if (buttons[i].textContent && 
                        buttons[i].textContent.includes('Send without a note') &&
                        buttons[i].className.includes('artdeco-button--primary')) {
                        buttons[i].click();
                        return true;
                    }
                }
                return false;
                """
                result = browser.execute_script(js_code)
                if result:
                    if VERBOSE:
                        print("    -> [DEBUG] Botão clicado via JavaScript", flush=True)
                    human_sleep(3, 5)
                    modal_closed_successfully = True
                else:
                    if VERBOSE:
                        print(
                            "    -> [DEBUG] JavaScript não encontrou o botão",
                            flush=True,
                        )
            except Exception as js_error:
                if VERBOSE:
                    print(
                        f"    -> [DEBUG] Erro no JS: {str(js_error)[:50]}", flush=True
                    )
                pass
    except Exception as modal_error:
        # Se não encontrar o botão "Send without a note", continua (talvez o modal já esteja fechado)
        if VERBOSE:
            print(
                f"    -> [DEBUG] Modal 'Send without a note' não encontrado: {str(modal_error)[:50]}",
                flush=True,
            )
        pass

    # SE conseguiu clicar em "Send without a note", marca como sucesso e retorna
    if modal_closed_successfully:
        CONNECTED = True
        SESSION_CONNECTION_COUNT += 1
        print(f"    -> [SUCCESS] Invite Sent (Direct - No Note) to: {name}", flush=True)
        return True

    # 2. Lógica de Envio de Nota vs. Envio Direto
    if SEND_AI_NOTE == 1:
        try:
            xpath_add_note = (
                "//button[@aria-label='Adicionar nota' or @aria-label='Add a note']"
            )
            btn_note = WebDriverWait(browser, 5).until(
                EC.element_to_be_clickable((By.XPATH, xpath_add_note))
            )
            btn_note.click()
            human_sleep(4, 6)  # Mais tempo após o clique na nota

            print("    -> Generating AI Note (Waiting 10s)...")
            time.sleep(10)

            message = generate_invite_message(
                name, headline, group_name, is_viewer=is_viewer
            )

            xpath_msg_box = "//textarea[@name='message']"
            msg_box = browser.find_element(By.XPATH, xpath_msg_box)

            human_type(msg_box, message)
            human_sleep(3, 5)

            # Tenta enviar a nota
            xpath_send_button = "//button[contains(@class, 'artdeco-button--primary') and (.//span[text()='Enviar agora'] or .//span[text()='Send now'])]"
            btn_send = WebDriverWait(browser, 5).until(
                EC.element_to_be_clickable((By.XPATH, xpath_send_button))
            )
            browser.execute_script("arguments[0].click();", btn_send)

            CONNECTED = True
            SESSION_CONNECTION_COUNT += 1
            print(f"-> [SUCCESS] Invite Sent with Note to: {name}\n    Note: {message}")
            return True

        except Exception as e:
            print(f"-> Failed to add note ({e}). Trying 'Send without note'...")
            # Tenta o fallback: enviar sem nota (se o modal de nota estiver aberto)
            try:
                # Múltiplos seletores para encontrar "Send without a note"
                send_without_note_selectors = [
                    "//button[@aria-label='Send without a note']",
                    "//button[@aria-label='Enviar sem nota']",
                    "//button//span[text()='Send without a note']/ancestor::button",
                    "//button[contains(.//span, 'Send without a note')]",
                    "//div[@class*='artdeco-modal__actionbar']//button[contains(@class, 'artdeco-button--primary')]",
                ]

                btn_no_note = None
                for sel in send_without_note_selectors:
                    try:
                        btn_no_note = WebDriverWait(browser, 2).until(
                            EC.element_to_be_clickable((By.XPATH, sel))
                        )
                        if btn_no_note:
                            break
                    except:
                        continue

                if btn_no_note:
                    browser.execute_script("arguments[0].click();", btn_no_note)
                    CONNECTED = True
                    SESSION_CONNECTION_COUNT += 1
                    print(
                        f"-> [SUCCESS] Invite Sent (No Note - Note Failed) to: {name}"
                    )
                    return True
                else:
                    raise Exception("Could not find 'Send without a note' button")
            except Exception as fallback_e:
                # Se falhou a nota e o fallback, tenta fechar o modal
                print(f"-> Fallback failed ({fallback_e}). Closing modal...")
                try:
                    browser.find_element(
                        By.XPATH,
                        "//button[@aria-label='Fechar' or @aria-label='Dismiss']",
                    ).click()
                except:
                    pass
                print("-> [FAIL] Total failure to send invite. Modal dismissed.")
                return False

    # 3. Envio Direto (SEND_AI_NOTE == 0)
    else:
        try:
            # Tenta encontrar o botão de 'Enviar' ou 'Send' no primeiro modal (sem nota)
            send_selectors_direct = [
                "//button[contains(@class, 'artdeco-button--primary') and (.//span[text()='Enviar'] or .//span[text()='Send'])]",
                "//button[contains(@class, 'artdeco-button--primary') and not(@disabled)]",  # fallback genérico
            ]
            sent = False
            for sel in send_selectors_direct:
                try:
                    btn = WebDriverWait(browser, 3).until(
                        EC.element_to_be_clickable((By.XPATH, sel))
                    )
                    browser.execute_script("arguments[0].click();", btn)
                    sent = True
                    break
                except:
                    continue

            if sent:
                CONNECTED = True
                SESSION_CONNECTION_COUNT += 1
                print(f"-> [SUCCESS] Invite Sent (NO NOTE - Flag 0) to: {name}")
                return True
            else:
                # Fecha o modal se não conseguir enviar
                try:
                    browser.find_element(
                        By.XPATH,
                        "//button[@aria-label='Fechar' or @aria-label='Dismiss']",
                    ).click()
                except:
                    pass
                print("-> [FAIL] Total failure to send direct invite. Modal dismissed.")
                return False

        except Exception as e:
            print(f"-> Failed to send direct invite: {e}")
            return False


def run_extraction_process():
    if not os.path.exists(DRIVER_FILENAME):
        return
    try:
        os.system("taskkill /im msedge.exe /f >nul 2>&1")
    except:
        pass

    opts = EdgeOptions()
    ud = os.path.join(
        os.environ["USERPROFILE"], "AppData", "Local", "Microsoft", "Edge", "User Data"
    )
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
        # time.sleep(7)

        # Salva o texto da página SSI ANTES de mudar de página
        ssi_raw_text = driver.find_element(By.TAG_NAME, "body").text

        # 3. Coleta dados do Dashboard (Views, Impressions, Searches, Followers)
        print("📊 Coletando Analytics para Dashboard (incluindo Followers)...")
        driver.get("https://www.linkedin.com/dashboard/")
        # time.sleep(5)

        # Inicialização das variáveis para garantir que existam para a chamada da função
        views = 0
        impressions = 0
        search = 0
        followers = 0

        try:
            txt = driver.find_element(By.TAG_NAME, "body").text

            # Extração de Views, Impressions, Searches
            views_match = re.search(r"(\d+)\s+profile views", txt)
            impressions_match = re.search(r"(\d+)\s+post impressions", txt)
            search_match = re.search(r"(\d+)\s+search appearances", txt)

            views = int(views_match.group(1)) if views_match else 0
            impressions = int(impressions_match.group(1)) if impressions_match else 0
            search = int(search_match.group(1)) if search_match else 0

            # Extração de Followers
            items = driver.find_elements(By.CSS_SELECTOR, ".pcd-analytics-view-item")
            for item in items:
                if "Followers" in item.text:
                    try:
                        count_text = item.find_element(
                            By.CSS_SELECTOR, ".text-body-large-bold"
                        ).text
                        followers = int(count_text.replace(",", "").strip())
                        break
                    except Exception as e:
                        print(
                            f"Warning: Failed to extract Followers count from element: {e}"
                        )

        except Exception as e:
            print(f"Warning: Failed to extract dashboard metrics or followers: {e}")

        print(
            f"Extracted: Views={views}, Impressions={impressions}, Searches={search}, Followers={followers}"
        )

        # 4. Salva tudo (CSV + DB) - AGORA COM 'followers' DEFINIDO
        df = update_ssi_table(
            ssi_raw_text,  # Usando o texto SSI salvo no passo 2
            CONNECTION_LIMIT,
            FOLLOW_LIMIT,
            PROFILES_TO_SCAN,
            PAG_ABERTAS,
            DAILY_LIKE_PROB,
            DAILY_COMMENT_PROB,
            SPEED_FACTOR,
            FEED_POSTS_LIMIT,
            FEED_LIKE_PROB,
            FEED_COMMENT_PROB,
            SESSION_WITHDRAWN_COUNT,
            total_conns,
            followers,  # NOVO PARAMETRO - AGORA DEFINIDO
        )
        print("SSI Updated.")
        print(df.tail(1))

        # Coleta dados do Dashboard para o SQLite
        log_analytics_db(views, impressions, search, followers)

        driver.quit()
    except Exception as e:
        print(f"SSI Error: {e}")
        # Se houver erro, tenta fechar o driver
        try:
            driver.quit()
        except:
            pass


# ==============================================================================
# IA & AÇÕES BLINDADAS
# ==============================================================================


def get_ai_comment(post_text):
    safe_fallbacks = [
        "Great insight, thanks for sharing!",
        "Really interesting point!",
        "Thanks for the valuable information!",
        "Well said, I agree.",
    ]
    if ai_client is None:
        return random.choice(safe_fallbacks)

    clean_text = post_text.replace("\n", " ").strip()[:800]
    # Usando 'Act as' para orientar a persona
    prompt = f"Act as a Data Scientist with the following expertise: '{AI_PERSONA}'.\nTask: Write a highly professional LinkedIn comment (35-55 words) on: '{clean_text}'.\nTone: Insightful, professional. Do NOT repeat the persona's description in the final comment. No hashtags."

    response = call_robust_ai(prompt, 800)

    if not response:
        if VERBOSE:
            print("    [IA FAIL] Usando frase de segurança.")
        return random.choice(safe_fallbacks)
    return response


def generate_invite_message(name, headline="", group_name="our group", is_viewer=False):
    if not name or name == "Unknown":
        first = "there"
    else:
        first = re.sub(r"[^a-zA-Z\s]", "", name).strip().split()[0].capitalize()

    if is_viewer:
        prompt = f"Write a friendly LinkedIn connection message to '{first}' who recently viewed my profile. I am a Data Scientist. Keep it professional and inviting (MAX 280 chars)."
    else:
        clean_group = group_name.split("|")[0].split("(")[0].strip()
        is_recruiter = any(x in headline.lower() for x in ["recruiter", "talent", "hr"])
        is_tech = any(x in headline.lower() for x in ["cto", "head", "data", "lead"])

        if is_recruiter:
            prompt = f"Write a professional connection message (MAX 280 chars) to Tech Recruiter '{first}'. I am Data Scientist. Mention '{clean_group}'. Start with 'Hi {first},'."
        elif is_tech:
            prompt = f"Write a professional connection message (MAX 280 chars) to Tech Lead '{first}'. I am Data Scientist. Mention '{clean_group}'. Start with 'Hi {first},'."
        else:
            prompt = f"Write a friendly connection message (MAX 280 chars) to '{first}' from '{clean_group}'. Professional. Start with 'Hi {first},'."

    msg = call_robust_ai(prompt, 300)

    if not msg or "keyword" in msg.lower() or len(msg) < 10:
        return generate_smart_fallback(name, group_name)

    placeholder_pattern = r"\[.*?\]|\{.*?\}|\<.*?\>|\(.*?\)"
    if re.search(placeholder_pattern, msg):
        msg = re.sub(placeholder_pattern, first, msg)

    msg = re.sub(r"^(Hi|Hello|Dear)\s+.*?,", "", msg).strip()
    final = f"Hi {first}, {msg}"

    return final[:297] + "..." if len(final) > 300 else final


def call_robust_ai(prompt, max_len=800):
    """
    Chama a IA de forma robusta e filtra caracteres não-BMP e de lixo.
    """
    if ai_client is None:
        return None
    garbage_triggers = [
        "discord server",
        "api error",
        "request failed",
        "unable to provide",
        "language model",
        "quota exceeded",
        "verify you are human",
        "cloudflare",
        "model does not exist",
        "request a model",
        "discord.gg",
        "join the",
        "bad gateway",
        # CORREÇÃO: Filtros mais rigorosos para evitar o lixo de role-playing que quebra o EdgeDriver
        "here's the message",
        "here is the message",
        "i hope this helps",
        "here is a message",
        "write a friendly linkedin connection",
        "i am a data scientist",
        "write a professional connection message",
    ]
    models_to_try = ["gpt-4"]

    for model in models_to_try:
        if VERBOSE:
            print(f" [AI DEBUG] Trying model: {model}")
        try:
            response = ai_client.chat.completions.create(
                model=model, messages=[{"role": "user", "content": prompt}]
            )
            clean_response = (
                str(response.choices[0].message.content)
                .strip()
                .replace('"', "")
                .replace("'", "")
            )
            clean_response = clean_response.replace("–", "-")

            # CORREÇÃO: Remove caracteres não-BMP (emojis, símbolos raros) que causam erro do EdgeDriver
            clean_response = re.sub(
                r"[^\U00000000-\U0000FFFF]", r"", clean_response, flags=re.UNICODE
            )

            is_garbage = False
            if len(clean_response) > max_len or len(clean_response) < 5:
                is_garbage = True
            if any(t in clean_response.lower() for t in garbage_triggers):
                is_garbage = True
            if (
                "http" in clean_response.lower()
                and "linkedin" not in clean_response.lower()
            ):
                is_garbage = True

            if not is_garbage:
                if VERBOSE:
                    print(f"    [AI Generated - SUCCESS] Model: {model}")
                return clean_response
            else:
                if VERBOSE:
                    print(f"    [IA LIXO BLOQUEADO - {model}] {clean_response[:30]}...")
        except Exception as e:
            if VERBOSE:
                print(f"    [AI FAIL] Model {model} failed: {e}")
            continue
    return None


def check_is_top_profile(driver):
    """
    Define se o perfil é um 'Top Profile' para fins de Follow (SSI Boost),
    checando: Badge Top Voice, Contagem de Seguidores/Conexões > 500/1000,
    e/ou se a Headline contém termos-chave de TI (Data Scientist, ML, etc.).
    """

    # 1. VERIFICAÇÃO DE BADGE (Top Voice)
    try:
        # Busca pelo badge oficial Top Voice/Voz Líder
        if driver.find_elements(By.CSS_SELECTOR, ".pv-member-badge--for-top-voice"):
            if VERBOSE:
                print("    -> [Top Profile] Motivo: Badge 'Top Voice' detectado.")
            return True
    except:
        pass

    # 2. VERIFICAÇÃO DE CONTADORES (1K+ ou 500+ conexões)
    try:
        # Seletor para os novos layouts de contagem
        counter_list = driver.find_elements(
            By.XPATH,
            "//ul[contains(@class, 'pv-top-card--list') or contains(@class, 'kGmuhOGiyWvadwWIiRwaCpwPqbmrJQYbqqZcM')]//li",
        )

        for item in counter_list:
            text = item.text.lower()

            # Verifica se tem "K" (milhares, indicando grande alcance)
            if "k" in text:
                if VERBOSE:
                    print(
                        "    -> [Top Profile] Motivo: Contagem 'K' (milhares) detectada."
                    )
                return True

            # Verifica se tem o padrão "500+" (que é o máximo que aparece para conexões)
            if "500+" in text and ("connection" in text or "conex" in text):
                if VERBOSE:
                    print("    -> [Top Profile] Motivo: 500+ Conexões detectadas.")
                return True

    except:
        pass

    # 3. VERIFICAÇÃO DE HEADLINE (Alvo Técnico) - USANDO NOVA LISTA
    try:
        headline = driver.find_element(
            By.XPATH,
            "//div[contains(@class, 'text-body-medium') and contains(@class, 'break-words')]",
        ).text.lower()

        # Usa a variável global HIGH_VALUE_KEYWORDS
        if any(kw in headline for kw in HIGH_VALUE_KEYWORDS):
            if VERBOSE:
                print(
                    f"    -> [Top Profile] Motivo: Headline de Alto Valor Técnico ({headline[:20]}...)."
                )
            return True
    except:
        pass

    return False


def endorse_skills(driver):
    try:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.75);")
        human_sleep(3, 5)
        btns = driver.find_elements(
            By.XPATH,
            "//button[contains(@aria-label, 'Endorse') or contains(@aria-label, 'Recomendar')]",
        )
        for btn in btns[:3]:
            if btn.is_displayed():
                ActionChains(driver).move_to_element(btn).click().perform()
                print("    -> [SSI] Skill Endorsed!")
                human_sleep(2, 3)
                return True
    except:
        pass
    return False


def perform_reaction_varied(driver, post, source="group"):
    available_reactions_names = ["like", "insightful", "celebrate", "love"]
    try:
        btn = post.find_element(
            By.CSS_SELECTOR, "button[aria-label*='Like'], button[aria-label*='Gostei']"
        )
        ActionChains(driver).move_to_element(btn).perform()
        human_sleep(0.5, 1.5)
        try:
            reactions = driver.find_elements(
                By.XPATH, "//button[contains(@class, 'reactions-menu__reaction')]"
            )
            valid_reactions = []
            for r in reactions:
                aria_label = r.get_attribute("aria-label")
                if aria_label and any(
                    name in aria_label.lower() for name in available_reactions_names
                ):
                    valid_reactions.append(r)

            if valid_reactions:
                ActionChains(driver).move_to_element(
                    random.choice(valid_reactions)
                ).click().perform()
                print("    -> Reacted (Emotion).")
            else:
                btn.click()
                print("    -> Liked (Joinha)")
        except:
            btn.click()
            print("    -> Liked (Joinha)")
    except:
        pass


def perform_comment(driver, post, text, source="group"):
    try:
        btn = post.find_element(
            By.CSS_SELECTOR,
            "button[aria-label*='Comment'], button[aria-label*='Comentar'], .comment-button",
        )
        driver.execute_script(
            "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", btn
        )
        human_sleep(2, 4)
        btn.click()
        human_sleep(2, 5)
        box = post.find_element(By.CSS_SELECTOR, ".ql-editor, div[role='textbox']")
        ActionChains(driver).move_to_element(box).click().perform()
        human_type(box, text)
        human_sleep(3, 6)
        post.find_element(
            By.CSS_SELECTOR,
            "button.comments-comment-box__submit-button, button[class*='primary']",
        ).click()
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
            btn_main = browser.find_element(
                By.XPATH, "//button[.//span[text()='Follow' or text()='Seguir']]"
            )
            if btn_main.is_displayed():
                browser.execute_script("arguments[0].click();", btn_main)
                print(f"    -> [SSI BRAND BOOST] Followed user (Main Btn): {TEMP_NAME}")
                return True
        except:
            pass

        xpath_more = "//button[contains(@aria-label, 'More actions') or .//span[text()='Mais'] or .//span[text()='More']]"
        WebDriverWait(browser, 3).until(
            EC.element_to_be_clickable((By.XPATH, xpath_more))
        ).click()
        human_sleep(3, 7)
        xpath_follow = "//div[contains(@class, 'dropdown')]//span[contains(text(), 'Follow') or contains(text(), 'Seguir')]"
        btn_follow = WebDriverWait(browser, 3).until(
            EC.element_to_be_clickable((By.XPATH, xpath_follow))
        )
        browser.execute_script("arguments[0].click();", btn_follow)
        print(f"    -> [SSI BRAND BOOST] Followed user (Menu): {TEMP_NAME}")
        return True
    except:
        return False


def filter_profiles(profiles):
    visited_file = os.path.join(DATA_DIR, "visitedUsers.txt")
    if not os.path.exists(visited_file):
        return profiles
    with open(visited_file, "r") as f:
        visited = [line.strip() for line in f]
    filtered = [p for p in profiles if p not in visited]
    return filtered


def run_reciprocator(browser):
    global SESSION_CONNECTION_COUNT
    print("\n-> [RECIPROCATOR] Verificando 'Quem viu seu perfil'...")
    try:
        browser.get("https://www.linkedin.com/me/profile-views/")
        human_sleep(30, 60)
        human_scroll(browser)

        try:
            connect_buttons = browser.find_elements(
                By.XPATH,
                "//button[.//span[contains(text(), 'Conectar') or contains(text(), 'Connect')]]",
            )
            processed = 0
            for btn in connect_buttons:
                if processed >= 2:
                    break
                if SESSION_CONNECTION_COUNT >= CONNECTION_LIMIT:
                    break

                try:
                    browser.execute_script(
                        "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                        btn,
                    )
                    human_sleep(5, 15)
                    person_name = "Profile Viewer"
                    print(
                        "    -> Encontrado visualizador desconectado. Tentando conectar..."
                    )

                    if click_connect_sequence(
                        browser, btn, person_name, "", "", is_viewer=True
                    ):
                        # Log para DB
                        try:
                            # Tenta extrair o link do perfil do elemento pai ou vizinho
                            profile_link = (
                                btn.find_element(
                                    By.XPATH, "../../../..//a[contains(@href, '/in/')]"
                                )
                                .get_attribute("href")
                                .split("?")[0]
                            )
                        except:
                            profile_link = (
                                f"Viewer_{datetime.datetime.now().timestamp()}"
                            )

                        log_interaction_db(
                            profile_link, person_name, "", "Reciprocator", "Connected"
                        )

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
        human_sleep(10, 30)
        celebration_buttons = browser.find_elements(
            By.XPATH,
            "//button[contains(@class, 'notification-action-button') or .//span[contains(text(), 'Congratulate') or contains(text(), 'Parabéns')]]",
        )

        if len(celebration_buttons) > 0:
            count = 0
            for btn in celebration_buttons:
                if count >= 3:
                    break
                try:
                    if btn.is_displayed():
                        browser.execute_script(
                            "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                            btn,
                        )
                        human_sleep(2, 3)
                        btn.click()
                        print(
                            "    -> [SSI BOOST] Celebração enviada (Parabéns/Cargo Novo)."
                        )
                        human_sleep(4, 7)
                        count += 1
                except:
                    pass
        else:
            print("    -> Nenhuma celebração pendente encontrada.")
    except Exception as e:
        print(f"Erro no Networker: {e}")


# ==============================================================================
# FUNÇÃO PRINCIPAL DE GRUPO - CORRIGIDO LOG
# ==============================================================================


def run_group_bot(browser):
    """
    Versão Corrigida: Implementa Loop While com Scroll e log detalhado
    do perfil sendo visitado e a ação tomada.
    """
    global SESSION_CONNECTION_COUNT, SESSION_FOLLOW_COUNT, CONNECTED
    if SAVECSV:
        if not os.path.exists("CSV"):
            os.makedirs("CSV")
        csv_header = [
            "Name",
            "Link",
            "Status",
            "Time",
            "Connection_Limit",
            "Follow_Limit",
            "Like_Prob",
            "Comment_Prob",
            "Profile_Scan_Limit",
        ]
        create_csv(csv_header, TIME)

    print(f"-> Group: {GROUP_URL}")
    browser.get(GROUP_URL)
    human_sleep(25, 50)
    try:
        group_name = browser.find_element(By.TAG_NAME, "h1").text
    except:
        group_name = "our group"

    print(f"-> Interagindo e Coletando (Meta: {PROFILES_TO_SCAN})...")

    profiles_queued = []
    scroll_attempts = 0
    max_scroll_attempts = 20

    commented_in_group = set()
    visited_file = os.path.join(DATA_DIR, "visitedUsers.txt")
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(visited_file):
        open(visited_file, "w").close()
    with open(visited_file, "r") as f:
        visited_list = [l.strip() for l in f]

    # LOOP DE COLETA COM SCROLL
    while (
        len(profiles_queued) < PROFILES_TO_SCAN
        and scroll_attempts < max_scroll_attempts
    ):
        # Pega posts visíveis na DOM atual
        posts = browser.find_elements(By.CLASS_NAME, "feed-shared-update-v2")

        for post in posts:
            if len(profiles_queued) >= PROFILES_TO_SCAN:
                break

            try:
                # 1. Tenta extrair URL e Enfileirar
                url = ""
                try:
                    el = post.find_element(
                        By.XPATH,
                        ".//a[contains(@href, '/in/') and not(contains(@href, '/miniProfile/'))]",
                    )
                    url = el.get_attribute("href").split("?")[0]

                    if url and url not in profiles_queued and url not in visited_list:
                        profiles_queued.append(url)
                        if VERBOSE:
                            print(
                                f"    [Coletado] {len(profiles_queued)}/{PROFILES_TO_SCAN}"
                            )
                except:
                    pass

                # 2. Interações
                urn = post.get_attribute("data-urn")
                if urn and urn not in commented_in_group:
                    browser.execute_script(
                        "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                        post,
                    )
                    human_sleep(10, 20)

                    if random.random() < DAILY_LIKE_PROB:
                        perform_reaction_varied(browser, post)

                    if random.random() < DAILY_COMMENT_PROB:
                        try:
                            text = post.text
                            if len(text) > 15 and (
                                not FEED_ENGLISH_ONLY or is_text_english(text)
                            ):
                                comment = get_ai_comment(text)
                                if perform_comment(browser, post, comment):
                                    commented_in_group.add(urn)
                        except:
                            pass

                    commented_in_group.add(urn)  # Marca como processado na sessão
            except:
                continue

        # Se ainda não bateu a meta, SCROLL
        if len(profiles_queued) < PROFILES_TO_SCAN:
            print(
                f"    -> Scrollando grupo... (Tentativa {scroll_attempts + 1}/{max_scroll_attempts})"
            )
            try:
                browser.execute_script("window.scrollBy(0, 800);")
                human_sleep(15, 30)
                gc.collect()  # Limpa memória após scroll
            except Exception as e:
                print(f"    [ERRO SCROLL] {str(e)[:80]}... Interrompendo coleta.")
                break  # Sai do loop se scroll falhar
            scroll_attempts += 1

    print(f"\n-> Coleta finalizada. Visitando {len(profiles_queued)} perfis...")

    # LOOP DE VISITA COM LOG DETALHADO
    processed = 0

    for url in profiles_queued:
        if processed >= PAG_ABERTAS:
            break

        name = "Unknown"
        headline = ""
        status = "Visited"
        CONNECTED = False

        try:
            browser.get(url)
            human_sleep(15, 30)
            processed += 1

            try:
                name = browser.title.split("|")[0].strip()
            except:
                name = "Unknown"
            try:
                headline = browser.find_element(
                    By.XPATH, "//div[contains(@class, 'text-body-medium')]"
                ).text.lower()
            except:
                headline = ""

            print(
                f"\n[{processed}/{PAG_ABERTAS}] Perfil: **{name}** ({headline[:30]}...)"
            )

            endorse_skills(browser)

            # 1. Tenta CONECTAR (se for alvo e houver limite)
            if SESSION_CONNECTION_COUNT < CONNECTION_LIMIT:
                if any(role in headline for role in TARGET_ROLES):
                    print(
                        f"    -> [ALVO] Conectando ({SESSION_CONNECTION_COUNT}/{CONNECTION_LIMIT})..."
                    )
                    if connect_with_user(browser, name, headline, group_name):
                        status = "Connected"
                        print(
                            f"    -> [SUCCESS] **Conectado**. Total: {SESSION_CONNECTION_COUNT}/{CONNECTION_LIMIT}"
                        )
                        sleep_after_connection()
                    else:
                        print("    -> [FAIL] Falha ao conectar ou já pendente.")

            # 2. Tenta SEGUIR (se não conectou, for Top Profile e houver limite)
            if status not in ["Connected"] and SESSION_FOLLOW_COUNT < FOLLOW_LIMIT:
                if check_is_top_profile(browser):
                    if follow_user(browser):
                        status = "Followed"
                        SESSION_FOLLOW_COUNT += 1
                        print(
                            f"    -> [SUCCESS] **Seguido** (SSI Boost). Total: {SESSION_FOLLOW_COUNT}/{FOLLOW_LIMIT}"
                        )
                elif VERBOSE:
                    # Este é o local do seu log de SKIP, o erro NÃO ocorre aqui.
                    print("    -> [SKIP] Não é Top Profile para seguir.")

            # 3. Log final - AQUI É ONDE A FUNÇÃO log_interaction_db É CHAMADA
            log_interaction_db(url, name, headline, "Group", status)
            visited_file_path = os.path.join(DATA_DIR, "visitedUsers.txt")
            with open(visited_file_path, "a") as f:
                f.write(url + "\n")

            # Log CSV
            if SAVECSV:
                add_to_csv(
                    [
                        name,
                        url,
                        status,
                        str(datetime.datetime.now().time()),
                        CONNECTION_LIMIT,
                        FOLLOW_LIMIT,
                        DAILY_LIKE_PROB,
                        DAILY_COMMENT_PROB,
                        PROFILES_TO_SCAN,
                    ],
                    TIME,
                )

        except Exception as e:
            if "invalid session id" in str(e).lower():
                print(f"\n!!! ERRO CRÍTICO DE SESSÃO: {e}")
                browser.quit()
                start_browser()
                return

            # Se o erro for 'log_interaction_db' is not defined, ele virá DAQUI
            # se a linha de cima não for a causa direta.
            print(f"Erro visita: {e}")
            continue

    print("\n--- GRUPO FINALIZADO ---")
    print(f"Total Connected na Sessão: {SESSION_CONNECTION_COUNT}/{CONNECTION_LIMIT}")
    print(f"Total Followed na Sessão: {SESSION_FOLLOW_COUNT}/{FOLLOW_LIMIT}")


def random_mouse_hover(browser):
    try:
        els = browser.find_elements(By.TAG_NAME, "span")
        if els:
            ActionChains(browser).move_to_element(random.choice(els)).perform()
    except:
        pass


def create_csv(data, time_str):
    time_str = time_str.replace(":", "-").replace(".", "-")
    filename = "GroupBot-" + time_str + ".csv"
    if not os.path.exists("CSV"):
        os.makedirs("CSV")
    with open(os.path.join("CSV", filename), "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(data)


def add_to_csv(data, time_str):
    time_str = time_str.replace(":", "-").replace(".", "-")
    path = os.path.join(os.getcwd(), "CSV", "GroupBot-" + time_str + ".csv")
    if os.path.exists(path):
        with open(path, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(data)


# ==============================================================================
# START
# ==============================================================================

# ==============================================================================
# START
# ==============================================================================

# ==============================================================================
# START (COM QUICK CONNECTS)
# ==============================================================================

# ==============================================================================
# START (COM TRATAMENTO DE ERRO DETALHADO)
# ==============================================================================


def start_browser():
    global browser
    if os.name == "nt":
        try:
            os.system("taskkill /im msedge.exe /f >nul 2>&1")
        except:
            pass

    # STEALTH: Random Window Size para evitar fingerprinting
    opts = EdgeOptions()
    width = random.randint(1024, 1920)
    height = random.randint(768, 1080)
    opts.add_argument(f"--window-size={width},{height}")

    ud = os.path.join(
        os.environ["USERPROFILE"], "AppData", "Local", "Microsoft", "Edge", "User Data"
    )
    opts.add_argument(f"--user-data-dir={ud}")
    opts.add_argument("--profile-directory=Default")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)

    try:
        service = EdgeService(executable_path=DRIVER_FILENAME)
        browser = webdriver.Edge(options=opts, service=service)
        browser.set_page_load_timeout(120)
        browser.set_script_timeout(120)

        browser.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            },
        )

        # --- AÇÕES DO BOT ---

        # 1. Conexões Rápidas (Novo modo de bypass de limite)
        try:
            run_quick_connects(browser)
        except Exception as e:
            print(f"    -> Quick Connects erro: {str(e)[:80]}")

        # 2. Feed Interaction
        try:
            interact_with_feed_human(browser)
        except Exception as e:
            print(f"Feed Error: {e}")
            # Não levanta exceção - continua mesmo se feed falhar

        # 3. Stealth & SSI Boosters (NEW)
        try:
            random_browsing_habit(browser)
        except Exception as e:
            print(f"Erro no random browsing: {e}")

        try:
            run_networker(browser)
        except Exception as e:
            print(f"Erro no Networker: {e}")

        try:
            run_reciprocator(browser)
        except Exception as e:
            print(f"Erro no Reciprocator: {e}")

        try:
            if random.random() < 0.3:
                withdraw_old_invites(browser)
        except Exception as e:
            print(f"Erro ao withdrawar convites: {e}")

        # 4. COLETA SNIPER PROFUNDA
        try:
            # sniper_targets = collect_sniper_targets(browser)
            print("test")
        except Exception as e:
            print(f"Erro na coleta Sniper: {e}")

        # 5. LÓGICA PRINCIPAL: Varre Grupo + Sniper (para o limite diário)
        try:
            run_main_bot_logic(browser)
        except Exception as e:
            print(f"!!! ERRO FATAL: Falha em run_main_bot_logic. Detalhe: {e}")
            raise

        # Fim da sessão, fechar o navegador
        browser.quit()

    except Exception as e:
        print(f"\n🛑 ERRO GERAL NO INÍCIO DA AUTOMAÇÃO: {e}")
        # Garante que o driver feche se ele foi aberto
        if "browser" in locals() and browser:
            try:
                browser.quit()
            except:
                pass

    # ==============================================================================
    # START (REDUZIDA PARA TESTE DE CONEXÃO E COLETA)
    # ==============================================================================

    # def start_browser():
    #     """
    #     Função de inicialização do navegador. Reduzida para testar
    #     apenas a lógica de Quick Connects e Coleta Sniper.
    #     """
    #     global browser
    #     # Garantir que o processo Edge esteja fechado antes de começar
    #     if os.name == 'nt':
    #         try: os.system("taskkill /im msedge.exe /f >nul 2>&1")
    #         except: pass

    #     # Configuração do Edge Options (STEALTH)
    #     opts = EdgeOptions()
    #     width = random.randint(1024, 1920)
    #     height = random.randint(768, 1080)
    #     opts.add_argument(f"--window-size={width},{height}")

    #     ud = os.path.join(os.environ['USERPROFILE'], 'AppData', 'Local', 'Microsoft', 'Edge', 'User Data')
    #     opts.add_argument(f"--user-data-dir={ud}")
    #     opts.add_argument("--profile-directory=Default")
    #     opts.add_argument("--disable-blink-features=AutomationControlled")
    #     opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    #     opts.add_experimental_option('useAutomationExtension', False)

    #     try:
    #         service = EdgeService(executable_path=DRIVER_FILENAME)
    #         browser = webdriver.Edge(options=opts, service=service)
    #         browser.set_page_load_timeout(60)

    #         browser.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
    #             "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    #         })

    #         # --- TESTE DAS AÇÕES CRÍTICAS ---

    #         # 1. Teste de Conexões Rápidas (Bypass de limite)
    #         try:
    #             print("\n--- INÍCIO TESTE: QUICK CONNECTS ---")
    #             run_quick_connects(browser)
    #             print("--- FIM TESTE: QUICK CONNECTS ---")
    #         except Exception as e:
    #             print(f"\n!!! ERRO FATAL NO QUICK CONNECTS. Detalhe: {e}")
    #             raise

    #         # 2. Teste de Coleta Sniper (Paginação e Extrator)
    #         try:
    #             print("\n--- INÍCIO TESTE: COLETA SNIPER ---")
    #             sniper_targets = collect_sniper_targets(browser)
    #             print(f"Resultado Final da Coleta Sniper: {len(sniper_targets)} links.")
    #             if VERBOSE:
    #                  for i, url in enumerate(sniper_targets[:5]):
    #                      print(f"    Link {i+1}: {url}")
    #             print("--- FIM TESTE: COLETA SNIPER ---")
    #         except Exception as e:
    #             print(f"\n!!! ERRO FATAL NA COLETA SNIPER. Detalhe: {e}")
    #             raise

    #         # Fim da sessão, fechar o navegador
    #         browser.quit()

    except Exception as e:
        print(f"\n🛑 ERRO GERAL NA INICIALIZAÇÃO DA SESSÃO: {e}")
        # Garante que o driver feche se ele foi aberto
        if "browser" in locals() and browser:
            try:
                browser.quit()
            except:
                pass


def launch():
    if not os.path.isfile("visitedUsers.txt"):
        open("visitedUsers.txt", "w").close()
    start_browser()


if __name__ == "__main__":
    print("🤖 Bot Started.")
    try:
        now = datetime.datetime.now()
        limit = now.replace(hour=15, minute=0, second=0)

        if now >= limit:
            print("Executando já...")
            run_extraction_process()
            if random.randint(0, 7) != 0:
                launch()
        else:
            wait = random.uniform(0, (limit - now).total_seconds())
            print(
                f"Agendado para: {(now + timedelta(seconds=wait)).strftime('%H:%M:%S')}"
            )
            time.sleep(wait * 0)
            run_extraction_process()
            if random.randint(0, 7) != 0:
                launch()
    except KeyboardInterrupt:
        print("\n🛑 Parada Manual.")
        if browser:
            browser.quit()
