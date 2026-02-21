# -*- coding: utf-8 -*-
import csv
import datetime
import functools
import gc
import os
import random
import re
import sqlite3  # ADICIONADO: Para o Dashboard
import sys
import time

# Força o Python a mostrar o print imediatamente, linha por linha
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.service import Service as EdgeService
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

sys.stdout.reconfigure(line_buffering=True)
# Isso obriga todo print a aparecer imediatamente
print = functools.partial(print, flush=True)
# Corrigir encoding no Windows para suportar emojis
if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


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

# 2. VELOCIDADE (OTIMIZAÇÃO: Delays mais inteligentes)
SPEED_FACTOR = 3.5  # Reduzido de 4 (melhor performance com cache)
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

# GRUPO-ESPECÍFICO: Keywords para conexões em grupos (mais inclusivo)
GROUP_TARGET_KEYWORDS = [
    # Data & Analytics
    "data scientist",
    "data engineer",
    "machine learning",
    "analytics",
    "business intelligence",
    "data analysis",
    "ml engineer",
    "deep learning",
    "python",
    "sql",
    # Cloud & Infrastructure
    "cloud engineer",
    "aws",
    "azure",
    "gcp",
    "devops",
    "infrastructure",
    "kubernetes",
    "docker",
    # AI & Emerging Tech
    "artificial intelligence",
    "generative ai",
    "nlp",
    "computer vision",
    "llm",
    # Senior Levels
    "senior",
    "lead",
    "staff",
    "principal",
    "manager",
    "architect",
    # Tech Skills
    "software engineer",
    "backend",
    "full stack",
    "frontend",
    "react",
    "node",
    "java",
    "scala",
    # Additional
    "technical",
    "engineering",
    "developer",
    "programmer",
]

# 5. LIMITES MANUAIS (Fallback se AUTO_REGULATE = False) - OTIMIZAÇÃO: Aumentados
LIMITS_CONFIG = {
    "CONNECTION": (25, 32),     # +25% | Mais conexões
    "FOLLOW": (20, 35),         # +40% | Mais follows
    "PROFILES_SCAN": (55, 75),  # +67% | Mais profiles
    "FEED_POSTS": (30, 45),     # +50% | Mais engagement
}

# 5. LIMITES MANUAIS (Fallback se AUTO_REGULATE = False)
# LIMITS_CONFIG = {
#     "CONNECTION": (0, 1),
#     "FOLLOW": (3, 5),
#     "PROFILES_SCAN": (4, 5),
#     "FEED_POSTS": (4, 5),
# }

# NOTA: QUICK_CONNECT_LIMIT será calculado como SNIPER_CONNECTION_LIMIT (abaixo)
QUICK_CONNECT_RATE = 0.25  # 25% para Sniper, 75% para Grupo (mais peso no grupo direto)

# 6. PROBABILIDADES MANUAIS (Fallback se AUTO_REGULATE = False) - OTIMIZAÇÃO: +50% engagement
PROBS = {
    "FEED_LIKE": (0.35, 0.45),      # +75% | Mais likes
    "FEED_COMMENT": (0.15, 0.25),   # +50% | Mais comentários
    "GROUP_LIKE": (0.35, 0.45),     # +75% | Mais engagement em grupos
    "GROUP_COMMENT": (0.15, 0.25),  # +50% | Taxa de comentário otimizada
}


# 7. CONFIGURAÇÕES GERAIS
CONNECT_WITH_USERS = True
SAVECSV = True
VERBOSE = True
# NOVO: Variável para controlar o envio de notas. (1 = Enviar Nota, 0 = Enviar Direto)
SEND_AI_NOTE = 0

# ==============================================================================
# 8. FILTROS SSI-SAFE (Conectar APENAS com pessoas que CRESCEM seu SSI)
# ==============================================================================
MIN_CONNECTIONS = 300  # Mínimo de conexões pra ser confiável
MIN_FOLLOWERS = 500  # Influenciadores aumentam seu SSI
MAX_POSTING_DAYS_AGO = 30  # Só pessoas ativas (postaram nos últimos 30 dias)
MIN_RECOMMENDATIONS = 2  # Credibilidade mínima
MIN_SKILLS = 3  # Perfil preenchido
PROFILE_COMPLETION_MIN = 75  # % de completude do perfil
REQUIRE_CERTIFICATIONS = False  # Priorizar certifications
SSI_SAFE_MODE = True  # Ativa todos os filtros acima

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

    # Tabela de Conexões Enviadas (Para evitar reprocessar perfis)
    c.execute("""CREATE TABLE IF NOT EXISTS connection_sent (
                    profile_id TEXT PRIMARY KEY,
                    profile_url TEXT UNIQUE,
                    name TEXT,
                    headline TEXT,
                    sent_at DATETIME,
                    status TEXT DEFAULT 'pending'
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
    except Exception:
        pass


def extract_profile_id(profile_url):
    """Extrai o ID único do perfil da URL do LinkedIn."""
    try:
        # Remove query params
        clean_url = profile_url.split("?")[0]
        # Extrai o ID após /in/
        if "/in/" in clean_url:
            return clean_url.split("/in/")[1].rstrip("/")
        return clean_url
    except Exception:
        return None


def log_connection_sent(profile_url, name, headline):
    """Registra que uma conexão foi enviada para um perfil."""
    try:
        profile_id = extract_profile_id(profile_url)
        if not profile_id:
            return False

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # INSERT OR REPLACE para casos onde o perfil já existe
        c.execute(
            """INSERT OR REPLACE INTO connection_sent (profile_id, profile_url, name, headline, sent_at, status)
               VALUES (?, ?, ?, ?, ?, 'pending')""",
            (profile_id, profile_url, name, headline, ts),
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def is_connection_sent(profile_url):
    """Verifica se já enviou conexão para este perfil."""
    try:
        profile_id = extract_profile_id(profile_url)
        if not profile_id:
            return False

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT 1 FROM connection_sent WHERE profile_id = ?", (profile_id,))
        result = c.fetchone()
        conn.close()

        return result is not None
    except Exception:
        return False


def is_already_connected(profile_url):
    """Verifica se JÁ ESTÁ CONECTADO com este perfil (encontrou Remove connection antes)."""
    try:
        profile_id = extract_profile_id(profile_url)
        if not profile_id:
            return False

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute(
            "SELECT 1 FROM connection_sent WHERE profile_id = ? AND status = 'already_connected'",
            (profile_id,),
        )
        result = c.fetchone()
        conn.close()

        return result is not None
    except Exception:
        return False


def log_already_connected(profile_url, name, headline):
    """Registra que JÁ ESTÁ CONECTADO com este perfil (encontrou Remove connection)."""
    try:
        profile_id = extract_profile_id(profile_url)
        if not profile_id:
            return False

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # INSERT OR REPLACE para atualizar status para already_connected
        c.execute(
            """INSERT OR REPLACE INTO connection_sent (profile_id, profile_url, name, headline, sent_at, status)
               VALUES (?, ?, ?, ?, ?, 'already_connected')""",
            (profile_id, profile_url, name, headline, ts),
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def get_connection_sent_count():
    """Retorna o total de conexões enviadas (para logging)."""
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM connection_sent")
        count = c.fetchone()[0]
        conn.close()
        return count
    except Exception:
        return 0


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
        except Exception:
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

if random.randint(0, 30) == 0:
    CONNECTION_LIMIT = 0
    print("conection set 0")
if random.randint(0, 30) == 0:
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

# ==============================================================================
# LIMITES INDEPENDENTES POR BLOCO (SNIPER vs GRUPO) - COM INT PARA EVITAR DECIMAIS
# ==============================================================================
SNIPER_CONNECTION_LIMIT = int(
    CONNECTION_LIMIT * QUICK_CONNECT_RATE
)  # Sniper tem seu próprio limite (50%)
SNIPER_CONNECTION_COUNT = 0  # Contador separado para Sniper
GROUP_CONNECTION_LIMIT = int(
    CONNECTION_LIMIT * (1 - QUICK_CONNECT_RATE)
)  # Grupo tem seu próprio limite (50%)
GROUP_CONNECTION_COUNT = 0  # Contador separado para Grupo
CONNECTED = False
TIME = str(datetime.datetime.now().time())
COMMENTED_POSTS_FILE = os.path.join(DATA_DIR, "commentedPosts.txt")
LOGS_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")
os.makedirs(LOGS_DIR, exist_ok=True)
browser = None

# OTIMIZAÇÃO 1: Cache em memória para posts comentados (crítica para performance)
COMMENTED_POSTS_CACHE = set()
COMMENTED_POSTS_CACHE_LOADED = False
# Exemplo de como definir a variável global (Adicione no seu painel de controle)

# ==============================================================================
# 🚀 NOVAS FUNÇÕES DE SSI BOOST (ADICIONE ISSO AO SEU CÓDIGO)
# ==============================================================================


def natural_mouse_move(browser, element):
    """
    Simula o movimento humano: move até o elemento, passa um pouco (overshoot),
    pausa para 'reação' e corrige a mira antes de clicar.
    """
    try:
        # 1. Cria a cadeia de ações
        actions = ActionChains(browser)

        # 2. Move para o elemento (movimento macro)
        actions.move_to_element(element)

        # 3. Adiciona o "Erro Humano" (Overshoot)
        # Simula que o mouse passou ou não chegou exatamente no pixel central (3 a 7 pixels de erro)
        x_jitter = random.randint(-7, 7)
        y_jitter = random.randint(-7, 7)

        # Move o offset (erro)
        actions.move_by_offset(x_jitter, y_jitter)

        # 4. Pausa de "Micro-reação" (o cérebro processando que o mouse parou)
        actions.pause(random.uniform(0.1, 0.3))

        # 5. Corrige a mira de volta para o centro do elemento (opcional, mas bom para botões pequenos)
        # Se o botão for grande, nem precisa corrigir, mas por segurança corrigimos:
        actions.move_by_offset(-x_jitter, -y_jitter)

        # Executa tudo
        actions.perform()

    except Exception:
        # Fallback de segurança: se a firula falhar, faz o básico
        # print(f"Erro no mouse natural: {e}") # Descomente para debug
        try:
            ActionChains(browser).move_to_element(element).perform()
        except Exception:
            pass  # Se até isso falhar, deixa o código principal tentar o JS click depois


def human_reading_behavior(browser):
    """
    Simula leitura humana: rola a tela para baixo, pausa para ler,
    e as vezes volta um pouco para cima (releitura).
    """
    try:
        print("    -> [SSI] Simulando comportamento de leitura...")
        # Varia entre 2 e 4 movimentos
        for _ in range(random.randint(2, 4)):
            scroll_amount = random.randint(200, 550)
            browser.execute_script(f"window.scrollBy(0, {scroll_amount});")
            human_sleep(2, 4)

            # 30% de chance de voltar um pouco a tela (releitura)
            if random.random() < 0.30:
                browser.execute_script("window.scrollBy(0, -150);")
                human_sleep(1, 2)
    except Exception:
        pass


def micro_engagement_feed(browser):
    """
    Quebra o padrão de robô indo ao feed principal para simular um usuário
    distraído ou engajado, rolando um pouco e voltando.
    """
    try:
        print("  -> [SSI BOOST] Micro-engajamento distribuído no feed...")
        main_window = browser.current_window_handle
        # Abre feed em nova aba para não perder o ponto da lista
        browser.execute_script("window.open('https://www.linkedin.com/feed/');")
        browser.switch_to.window(browser.window_handles[-1])

        human_sleep(8, 15)

        # Rola o feed aleatoriamente
        for _ in range(random.randint(1, 3)):
            browser.execute_script(f"window.scrollBy(0, {random.randint(300, 700)});")
            human_sleep(2, 5)

        browser.close()
        browser.switch_to.window(main_window)
    except Exception:
        pass


def strategic_endorse_skills(driver):
    """
    Endossa APENAS skills que estão na sua lista de HIGH_VALUE_KEYWORDS.
    Isso aumenta a relevância do seu perfil para o algoritmo.
    """
    try:
        # Rola até o fundo onde geralmente ficam as skills
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.70);")
        human_sleep(3, 5)

        btns = driver.find_elements(
            By.XPATH,
            "//button[contains(@aria-label, 'Endorse') or contains(@aria-label, 'Recomendar')]",
        )
        endorsed_count = 0

        for btn in btns:
            if endorsed_count >= 2:
                break  # Limite de 2 por pessoa

            skill_name = btn.get_attribute("aria-label").lower()
            # Só clica se a skill tiver a ver com a sua área
            if any(kw in skill_name for kw in HIGH_VALUE_KEYWORDS):
                driver.execute_script("arguments[0].click();", btn)
                print(
                    f"    -> [SSI] Skill '{skill_name[:20]}...' endossada estrategicamente!"
                )
                human_sleep(2, 4)
                endorsed_count += 1
    except Exception:
        pass


def get_factored_time(seconds):
    return seconds * SPEED_FACTOR


def human_sleep(min_seconds=2, max_seconds=5):
    base_time = random.uniform(min_seconds, max_seconds)
    time.sleep(get_factored_time(base_time))


def smart_sleep(min_sec=1, max_sec=3, context="default"):
    """OTIMIZAÇÃO: Delays adaptativos baseado em contexto (mais óptimo)."""
    if context == "fetch":
        delay = random.uniform(0.2, 0.8)  # Fetches são rápidas
    elif context == "click":
        delay = random.uniform(0.4, 1.5)  # Cliques humanos
    elif context == "scroll":
        delay = random.uniform(1.5, 4)  # Scroll natural
    elif context == "read":
        delay = random.uniform(3, 8)  # Tempo de leitura
    elif context == "input":
        delay = random.uniform(0.8, 2.5)  # Digitação
    else:
        delay = random.uniform(min_sec, max_sec)
    
    time.sleep(get_factored_time(delay))


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
    except Exception:
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
    """OTIMIZAÇÃO: Usa cache em memória ao invés de ler arquivo toda vez."""
    global COMMENTED_POSTS_CACHE, COMMENTED_POSTS_CACHE_LOADED
    
    if COMMENTED_POSTS_CACHE_LOADED:
        return COMMENTED_POSTS_CACHE
    
    # Primeira vez: carrega arquivo
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(COMMENTED_POSTS_FILE):
        try:
            with open(COMMENTED_POSTS_FILE, "r") as f:
                COMMENTED_POSTS_CACHE = set(line.strip() for line in f)
        except:
            COMMENTED_POSTS_CACHE = set()
    
    COMMENTED_POSTS_CACHE_LOADED = True
    return COMMENTED_POSTS_CACHE


def save_commented_post(urn):
    """OTIMIZAÇÃO: Salva em cache em memória + arquivo (o mais rápido possível)."""
    global COMMENTED_POSTS_CACHE
    
    # Atualiza cache em memória (instantâneo)
    COMMENTED_POSTS_CACHE.add(urn)
    
    # Salva em arquivo (background)
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(COMMENTED_POSTS_FILE, "a") as f:
        f.write(f"{urn}\n")


def extract_post_url(driver, post_element):
    """
    Extrai a URL do post a partir do elemento post.
    Tenta múltiplos seletores para encontrar o link de permalink do post.
    """
    try:
        # Tenta encontrar o link de permalink do post
        selectors = [
            "a[href*='/feed/update/']",
            "a[href*='linkedin.com/feed/']",
            "a[data-test-id='post.link']",
            ".update-components-header__text-link",
        ]

        for selector in selectors:
            try:
                link_element = post_element.find_element(By.CSS_SELECTOR, selector)
                href = link_element.get_attribute("href")
                if href and "linkedin.com" in href:
                    # Remove parâmetros de query para normalizar
                    post_url = href.split("?")[0] if "?" in href else href
                    return post_url
            except:
                continue

        # Fallback: Tenta extrair de data-urn
        try:
            urn = post_element.get_attribute("data-urn")
            if urn:
                return urn
        except:
            pass

        return None
    except Exception:
        return None


def is_post_already_commented(driver, post_element):
    """
    Verifica se um post já foi comentado anteriormente.
    Compara a URL/URN do post com o arquivo de histórico.
    """
    try:
        post_identifier = extract_post_url(driver, post_element)
        if not post_identifier:
            return False

        commented_posts = get_commented_posts()
        return post_identifier in commented_posts
    except Exception:
        return False


def register_post_commented(driver, post_element):
    """
    Registra um post como comentado no arquivo de histórico.
    """
    try:
        post_identifier = extract_post_url(driver, post_element)
        if post_identifier:
            save_commented_post(post_identifier)
            return True
    except Exception:
        pass
    return False


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
# OTIMIZAÇÃO: Funções de Coleta e Filtragem Otimizadas
# ==============================================================================

def batch_filter_posts(posts, max_age_days=7):
    """
    OTIMIZAÇÃO: Filtra posts em batch (mais rápido que individual).
    Pula posts muito antigos, duplicados, etc.
    Prioriza posts com mais comentários (melhor visibilidade).
    """
    valid_posts = []
    cutoff_time = datetime.datetime.now() - datetime.timedelta(days=max_age_days)
    post_scores = []  # (post, engagement_score)
    
    for post in posts:
        try:
            # Skip posts muito pequenos (provavelmente spam)
            if len(post.text) < 15:
                continue
            
            # Skip se não tem engagement (sem reações previstas)
            urn = post.get_attribute("data-urn")
            if not urn:
                continue
                
            # Skip se já comentado
            if is_post_already_commented(None, post):
                continue
            
            # Prioriza posts com mais comentários visíveis (mais engagement = mais visibilidade)
            try:
                comment_count_text = post.find_element(By.XPATH, ".//span[contains(text(), 'comment')]").text
                comment_count = int(''.join(filter(str.isdigit, comment_count_text))) if comment_count_text else 0
            except:
                comment_count = 0
            
            post_scores.append((post, comment_count))
        except:
            continue
    
    # Ordena por engagement score (descendente) e retorna
    post_scores.sort(key=lambda x: x[1], reverse=True)
    valid_posts = [post for post, score in post_scores]
    
    return valid_posts


def extract_profiles_batch(driver, posts, max_profiles=None):
    """
    OTIMIZAÇÃO: Extrai profiles em batch com BeautifulSoup (muito mais rápido).
    """
    profiles = []
    soup = BeautifulSoup(driver.page_source, "html.parser")
    
    seen_urls = set()
    for link in soup.find_all("a", href=True):
        href = link["href"]
        
        if "/in/" in href and "/miniProfile/" not in href:
            clean_link = href.split("?")[0]
            if not clean_link.startswith("http"):
                clean_link = "https://www.linkedin.com" + clean_link
            
            if clean_link not in seen_urls:
                profiles.append(clean_link)
                seen_urls.add(clean_link)
                
                if max_profiles and len(profiles) >= max_profiles:
                    break
    
    return profiles


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
                            # Proteção: Verifica se já foi comentado anteriormente
                            if is_post_already_commented(browser, post):
                                if VERBOSE:
                                    print(
                                        "    -> [SKIP] Post já foi comentado em execução anterior. Pulando..."
                                    )
                                commented_in_feed.add(urn)
                                continue

                            text_el = post.find_element(
                                By.CSS_SELECTOR, ".update-components-text"
                            )
                            text = text_el.text

                            if FEED_ENGLISH_ONLY and not is_text_english(text):
                                continue

                            if len(text) > 20:
                                comment = get_ai_comment(text)
                                if perform_comment(browser, post, comment, "feed"):
                                    # Registra o post como comentado
                                    register_post_commented(browser, post)
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
        except Exception:
            pass
        return 0
    except Exception:
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
                except Exception:
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
    global SESSION_CONNECTION_COUNT, SNIPER_CONNECTION_COUNT

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
            except Exception:
                pass
            try:
                headline = p.find_element(
                    By.CSS_SELECTOR, ".entity-result__primary-subtitle"
                ).text.lower()
            except Exception:
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
                    SNIPER_CONNECTION_COUNT += 1
                    print(
                        f"    -> [SUCCESS] **Conectado**. Sniper: {SNIPER_CONNECTION_COUNT}/{SNIPER_CONNECTION_LIMIT} | Total: {SESSION_CONNECTION_COUNT}/{CONNECTION_LIMIT}"
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
                except Exception:
                    pass

            # Garante que o foco volte para a aba principal para continuar a iteração
            try:
                browser.switch_to.window(main_window)
            except Exception:
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
    Combina coleta de perfis do grupo com alvos Sniper e varre a lista completa
    aplicando comportamento humano avançado (SSI Boost).
    """
    global \
        SNIPER_CONNECTION_COUNT, \
        GROUP_CONNECTION_COUNT, \
        SESSION_FOLLOW_COUNT, \
        CONNECTED, \
        SESSION_CONNECTION_COUNT
    # Globais de estatísticas da sessão
    global SESSION_GROUP_LIKES, SESSION_GROUP_COMMENTS

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

    # Garante lista vazia se None
    if sniper_targets is None:
        sniper_targets = []

    # ---------------------------------------------------------
    # 1. NAVEGAÇÃO E COLETA NO GRUPO
    # ---------------------------------------------------------
    print(f"-> Group: {GROUP_URL}")
    browser.get(GROUP_URL)
    human_sleep(10, 15)

    try:
        group_name = browser.find_element(By.TAG_NAME, "h1").text
    except Exception:
        group_name = "our group"

    print(f"-> Interagindo e Coletando perfis do Grupo (Meta: {PROFILES_TO_SCAN})...")

    profiles_queued = []
    scroll_attempts = 0
    max_scroll_attempts = 20
    commented_in_group = set()

    visited_file = os.path.join(DATA_DIR, "visitedUsers.txt")
    if not os.path.exists(visited_file):
        open(visited_file, "w").close()
    with open(visited_file, "r") as f:
        visited_list = [l.strip() for l in f]

    # LOOP DE COLETA (SCROLL + EXTRAÇÃO)
    while (
        len(profiles_queued) < PROFILES_TO_SCAN
        and scroll_attempts < max_scroll_attempts
    ):
        # Tentativa de pegar posts
        posts = browser.find_elements(By.CLASS_NAME, "feed-shared-update-v2")

        # Fallback se não achar pela classe padrão
        if not posts:
            posts = browser.find_elements(
                By.XPATH,
                "//div[contains(@class, 'feed')]//div[contains(@class, 'update')]",
            )

        # Fallback BeautifulSoup (se o Selenium falhar na DOM inicial)
        if not posts and scroll_attempts == 0:
            try:
                soup = BeautifulSoup(browser.page_source, "html.parser")
                for link in soup.find_all("a", href=True):
                    href = link["href"]
                    if "/in/" in href and "/miniProfile/" not in href:
                        clean_link = href.split("?")[0]
                        if not clean_link.startswith("http"):
                            clean_link = "https://www.linkedin.com" + clean_link

                        if (
                            clean_link not in profiles_queued
                            and clean_link not in visited_list
                        ):
                            profiles_queued.append(clean_link)
                            if len(profiles_queued) >= PROFILES_TO_SCAN:
                                break
            except Exception as e:
                print(f"    [DEBUG] Erro BeautifulSoup: {e}")

        # Processamento dos Posts (Coleta + Interação)
        for post in posts:
            if len(profiles_queued) >= PROFILES_TO_SCAN:
                break
            try:
                # Extração de URL
                try:
                    url_el = post.find_element(
                        By.XPATH,
                        ".//a[contains(@href, '/in/') and not(contains(@href, '/miniProfile/'))]",
                    )
                    url = url_el.get_attribute("href").split("?")[0]

                    if url and url not in profiles_queued and url not in visited_list:
                        profiles_queued.append(url)
                        if VERBOSE:
                            print(
                                f"    [Coletado Grupo] {len(profiles_queued)}/{PROFILES_TO_SCAN}"
                            )
                except Exception:
                    pass

                # Interações Rápidas no Feed do Grupo (Like/Comment)
                urn = post.get_attribute("data-urn")
                if urn and urn not in commented_in_group:
                    # Scroll até o post para interação real
                    browser.execute_script(
                        "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                        post,
                    )
                    human_sleep(1, 2)

                    if random.random() < DAILY_LIKE_PROB:
                        perform_reaction_varied(browser, post, "group")
                        try:
                            SESSION_GROUP_LIKES += 1
                        except Exception:
                            pass  # Evita erro se a var global não existir

                    if random.random() < DAILY_COMMENT_PROB:
                        # Proteção: Verifica se já foi comentado anteriormente
                        if is_post_already_commented(browser, post):
                            if VERBOSE:
                                print(
                                    "    -> [SKIP] Post já foi comentado em execução anterior. Pulando..."
                                )
                            commented_in_group.add(urn)
                        else:
                            text = post.text
                            if len(text) > 20 and is_text_english(text):
                                comment = get_ai_comment(text)
                                if perform_comment(browser, post, comment, "group"):
                                    # Registra o post como comentado
                                    register_post_commented(browser, post)
                                    commented_in_group.add(urn)
                                    try:
                                        SESSION_GROUP_COMMENTS += 1
                                    except Exception:
                                        pass

                    commented_in_group.add(urn)  # Marca como visto
            except Exception:
                continue

        # Scroll e Limpeza
        if len(profiles_queued) < PROFILES_TO_SCAN:
            print(
                f"    -> Scrollando grupo... ({scroll_attempts + 1}/{max_scroll_attempts})"
            )
            try:
                browser.execute_script("window.scrollBy(0, 800);")
                human_sleep(5, 8)
                gc.collect()  # Limpeza de memória crítica
            except Exception as e:
                print(f"    [ERRO SCROLL] {str(e)[:50]}... Interrompendo coleta.")
                break
            scroll_attempts += 1

    # ---------------------------------------------------------
    # 2. INTEGRAÇÃO COM TARGETS DO SNIPER
    # ---------------------------------------------------------
    if sniper_targets:
        print(f"-> Incorporando {len(sniper_targets)} alvos Sniper...")
        for url in sniper_targets:
            if url not in profiles_queued and url not in visited_list:
                profiles_queued.append(url)

    total_profiles = min(PAG_ABERTAS, len(profiles_queued))
    print(f"\n-> Iniciando visitas otimizadas em {total_profiles} perfis...")

    # ---------------------------------------------------------
    # 3. LOOP DE VISITAS OTIMIZADO (COM TEMPERO SSI)
    # ---------------------------------------------------------
    processed = 0
    for url in profiles_queued:
        if processed >= PAG_ABERTAS:
            break

        # [NOVO] VALIDAÇÃO PRÉ-ABERTURA: Pula perfis já processados
        # Evita gastar tempo abrindo perfis que já visitou
        if is_connection_sent(url):
            if VERBOSE:
                print(f"[SKIP] {url} - Convite já enviado em run anterior. Pulando...")
            continue
        if is_already_connected(url):
            if VERBOSE:
                print(f"[SKIP] {url} - Já conectado em run anterior. Pulando...")
            continue

        # [TEMPERO 1] Pausa de Micro-Engajamento a cada 6 perfis
        # Simula usuário indo checar o feed rapidinho
        if processed > 0 and processed % 6 == 0:
            micro_engagement_feed(browser)

        source = "Sniper" if url in sniper_targets else "Group"
        name = "Unknown"
        headline = ""
        status = "Visited"

        try:
            browser.get(url)
            # Aumentado o tempo inicial para garantir carregamento total
            human_sleep(6, 10)

            # [TEMPERO 2] Comportamento de Leitura Humana (Dwell Time)
            human_reading_behavior(browser)

            # Extração de Dados
            try:
                name = browser.title.split("|")[0].strip()
                headline = browser.find_element(
                    By.XPATH, "//div[contains(@class, 'text-body-medium')]"
                ).text.lower()
            except Exception:
                pass  # Mantém valores padrão

            processed += 1
            print(f"[{processed}/{total_profiles}] ({source}) {name}")

            # [TEMPERO 3] Endosso Estratégico (Só skills do nicho)
            strategic_endorse_skills(browser)

            # Lógica de Conexão (Sniper vs Group com contadores separados)
            # Sniper: Use strict TARGET_ROLES (executivos, leads)
            # Group: Use inclusive GROUP_TARGET_KEYWORDS (mid-to-senior profiles)
            is_sniper_target = any(role in headline for role in TARGET_ROLES)
            is_group_target = any(
                keyword in headline for keyword in GROUP_TARGET_KEYWORDS
            )

            if source == "Sniper":
                should_connect = is_sniper_target
            else:  # Group
                should_connect = is_group_target
                if VERBOSE and is_group_target:
                    print(
                        f"    -> [GROUP MATCH] Headline matches keywords: {headline[:60]}"
                    )

            if should_connect:
                if source == "Sniper":
                    # Sniper usa seu próprio limite (independente de SESSION_CONNECTION_COUNT)
                    if SNIPER_CONNECTION_COUNT < SNIPER_CONNECTION_LIMIT:
                        print("    -> [ALVO-SNIPER] Tentando conectar...")
                        if connect_with_user(browser, name, headline, group_name):
                            status = "Connected"
                            SNIPER_CONNECTION_COUNT += 1
                            SESSION_CONNECTION_COUNT += 1
                            print(
                                f"    -> [SNIPER OK] {SNIPER_CONNECTION_COUNT}/{SNIPER_CONNECTION_LIMIT}"
                            )
                            sleep_after_connection()
                    else:
                        print(
                            f"    -> [SNIPER LIMIT] {SNIPER_CONNECTION_COUNT}/{SNIPER_CONNECTION_LIMIT} atingido. Pulando..."
                        )
                else:
                    # Group usa seu próprio limite (independente de SESSION_CONNECTION_COUNT)
                    if GROUP_CONNECTION_COUNT < GROUP_CONNECTION_LIMIT:
                        print("    -> [ALVO-GROUP] Tentando conectar...")
                        if connect_with_user(browser, name, headline, group_name):
                            status = "Connected"
                            GROUP_CONNECTION_COUNT += 1
                            SESSION_CONNECTION_COUNT += 1
                            print(
                                f"    -> [GROUP OK] {GROUP_CONNECTION_COUNT}/{GROUP_CONNECTION_LIMIT}"
                            )
                            sleep_after_connection()
                    else:
                        print(
                            f"    -> [GROUP LIMIT] {GROUP_CONNECTION_COUNT}/{GROUP_CONNECTION_LIMIT} atingido. Pulando..."
                        )

            # Lógica de Follow (SSI Boost para Top Profiles)
            if status == "Visited" and SESSION_FOLLOW_COUNT < FOLLOW_LIMIT:
                if check_is_top_profile(browser):
                    if follow_user(browser):
                        status = "Followed"
                        SESSION_FOLLOW_COUNT += 1
                        print("    -> [SSI] Seguiu Top Profile.")

            # Logs Finais
            log_interaction_db(url, name, headline, source, status)
            with open(visited_file, "a") as f:
                f.write(url + "\n")

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

            # Limpeza de memória a cada perfil para evitar crash do navegador
            gc.collect()

        except Exception as e:
            if "invalid session id" in str(e).lower():
                print(f"\n!!! ERRO CRÍTICO DE SESSÃO: {e}")
                browser.quit()
                return  # Encerra para reiniciar
            print(f"Erro ao visitar {url}: {e}")
            continue

    print("\n--- VARREDURA FINALIZADA ---")
    print(
        f"Total Connected (Sniper): {SNIPER_CONNECTION_COUNT}/{SNIPER_CONNECTION_LIMIT}"
    )
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
    Clicks them across multiple pages until SNIPER_CONNECTION_LIMIT is reached.
    """

    global \
        SESSION_CONNECTION_COUNT, \
        CONNECTION_LIMIT, \
        SNIPER_CONNECTION_COUNT, \
        GROUP_CONNECTION_COUNT

    # Settings for this run
    connect_count = 0
    page = 1
    max_pages = 8  # REDUZIDO de 20 para 5 páginas máximo
    consecutive_empty_pages = 0

    print(
        f"\n⚡️ [QUICK CONNECTS] Tentando {SNIPER_CONNECTION_LIMIT} conexões diretas...",
        flush=True,
    )

    keyword = random.choice(TARGET_ROLES)
    print(f"    🎯 Buscando por: '{keyword}'", flush=True)
    keyword_encoded = keyword.replace(" ", "%20")
    quick_connect_url_with_keyword = (
        f"{BASE_QUICK_CONNECT_URL}&keywords={keyword_encoded}"
    )

    while connect_count < SNIPER_CONNECTION_LIMIT and page <= max_pages:
        url = (
            quick_connect_url_with_keyword
            if page == 1
            else f"{quick_connect_url_with_keyword}&page={page}&spellCorrectionEnabled=true"
        )

        print(f"    -> Página {page}...")
        try:
            browser.get(url)
            human_sleep(5, 8)
        except Exception as e:
            error_msg = str(e).lower()
            if "invalid session id" in error_msg or "session deleted" in error_msg:
                print(
                    f"    ⚠️ Session expired. Aborting quick connects (completed {connect_count}/{SNIPER_CONNECTION_LIMIT})"
                )
                raise  # Re-raise to trigger outer restart logic
            print(f"    -> Erro ao carregar página {page}: {e}")
            page += 1  # ✅ Continua para a próxima página, não quebra tudo
            continue  # ✅ Pula para a próxima iteração do while

        # Scroll to load all results
        for _ in range(2):
            browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            human_sleep(1, 2)
        browser.execute_script("window.scrollTo(0, 0);")

        try:
            # Extrai todos os links de perfil usando BeautifulSoup (mais robusto)
            soup = BeautifulSoup(browser.page_source, "html.parser")
            all_links = soup.find_all("a", href=True)

            profile_links = []
            visited_file = os.path.join(DATA_DIR, "visitedUsers.txt")
            visited = set()
            if os.path.exists(visited_file):
                with open(visited_file, "r") as vf:
                    visited = set(l.strip() for l in vf if l.strip())

            for link in all_links:
                if len(profile_links) >= (SNIPER_CONNECTION_LIMIT - connect_count):
                    break

                href = link.get("href", "")

                # Filtra apenas links de perfil LinkedIn (/in/)
                if "/in/" not in href:
                    continue

                # Remove query params
                clean_href = href.split("?")[0]

                # Ignora links relativos ou inválidos
                if not clean_href.startswith("http"):
                    if clean_href.startswith("/in/"):
                        clean_href = "https://www.linkedin.com" + clean_href
                    else:
                        continue

                # Filtra lixo (ACo, ACw)
                if "/preload/" in clean_href or "/custom-invite/" in clean_href:
                    continue

                # Evita duplicatas e visitados
                if clean_href not in profile_links and clean_href not in visited:
                    profile_links.append(clean_href)

            if not profile_links:
                print(f"    -> Nenhum perfil extraído na página {page}.")
                consecutive_empty_pages += 1
                if consecutive_empty_pages >= 2:  # REDUZIDO de 3 para 2
                    print("    -> Muitas páginas vazias. Interrompendo quick connects.")
                    break
                page += 1
                continue

            # reset consecutive empty page counter when we have results
            consecutive_empty_pages = 0

            print(
                f"    -> Extraídos {len(profile_links)} perfis para visita na página {page}."
            )

            # Visita cada perfil e tenta conectar usando a rotina robusta
            visited_count_on_page = 0
            for link in profile_links:
                if (
                    connect_count >= SNIPER_CONNECTION_LIMIT
                    or SESSION_CONNECTION_COUNT >= CONNECTION_LIMIT
                ):
                    print(
                        f"    -> Limite de conexões atingido ({connect_count}/{SNIPER_CONNECTION_LIMIT}). Parando."
                    )
                    break

                try:
                    print(f"    -> Visitando perfil: {link}")
                    browser.get(link)
                    human_sleep(6, 10)

                    # Extrai nome e headline (quando possível)
                    pname = "Unknown"
                    pheadline = ""
                    try:
                        pname = browser.title.split("|")[0].strip()
                    except Exception:
                        pass
                    try:
                        pheadline = browser.find_element(
                            By.XPATH, "//div[contains(@class, 'text-body-medium')]"
                        ).text.lower()
                    except Exception:
                        pass

                    if connect_with_user(browser, pname, pheadline, keyword):
                        connect_count += 1
                        SNIPER_CONNECTION_COUNT += 1
                        SESSION_CONNECTION_COUNT += 1
                        visited_count_on_page += 1
                        human_sleep(4, 6)
                        print(
                            f"    -> [✓] Convite enviado para: {pname} ({SNIPER_CONNECTION_COUNT}/{SNIPER_CONNECTION_LIMIT})"
                        )
                    else:
                        print(f"    -> [✗] Não conseguiu enviar convite para: {pname}")
                        visited_count_on_page += 1

                    # marca como visitado imediatamente para evitar reaparecer em outras páginas
                    try:
                        if link not in visited:
                            with open(visited_file, "a", encoding="utf-8") as vf:
                                vf.write(link + "\n")
                            visited.add(link)
                    except Exception:
                        pass

                except Exception as e:
                    error_msg = str(e).lower()
                    if (
                        "invalid session id" in error_msg
                        or "session deleted" in error_msg
                    ):
                        print(
                            f"    ⚠️ Session expired mid-profile visit. Aborting quick connects (completed {connect_count}/{SNIPER_CONNECTION_LIMIT})"
                        )
                        raise  # Re-raise to trigger outer restart logic
                    print(f"    -> Erro ao visitar perfil {link}: {str(e)[:50]}")
                    continue

            if VERBOSE:
                print(
                    f"    -> Visitados {visited_count_on_page}/{len(profile_links)} perfis na página {page}."
                )

        except Exception as e:
            print(f"    -> Erro na coleta da página: {str(e)[:50]}")

        page += 1

    print(
        f"⚡️ [QUICK CONNECTS] Concluído: {connect_count}/{SNIPER_CONNECTION_LIMIT} conexões Sniper."
    )


# ==============================================================================


def update_ssi_table(
    html_content,  # AGORA RECEBE O HTML BRUTO, NÃO SÓ O TEXTO
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
    current_total_followers,
    file_path=None,
):
    if file_path is None:
        file_path = os.path.join(DATA_DIR, "ssi_history.csv")

    today = datetime.datetime.now().strftime("%Y-%m-%d")

    # --- NOVA LÓGICA DE EXTRAÇÃO VIA BEAUTIFULSOUP (PRECISÃO MÁXIMA) ---
    soup = BeautifulSoup(html_content, "html.parser")

    # 1. Total SSI (Busca no caption do gráfico)
    try:
        total_ssi_elem = soup.select_one(
            ".user-ssi-score__donut-chart-caption .ssi-score__value"
        )
        total_ssi = float(total_ssi_elem.text.strip()) if total_ssi_elem else 0.0
    except Exception:
        total_ssi = 0.0

    # 2. Ranks (Industry & Network)
    industry_rank = 0
    network_rank = 0
    try:
        # Procura os blocos de rank
        ranks = soup.find_all("div", class_="ssi-rank")
        for rank in ranks:
            text = rank.text.lower()
            val_elem = rank.find("span", class_="t-40")  # Classe do número grande
            if val_elem:
                val = int(val_elem.text.strip())
                if "industry" in text:
                    industry_rank = val
                elif "network" in text:
                    network_rank = val
    except Exception:
        pass

    # 3. Os 4 Pilares (Extraídos direto da barra de progresso)
    def get_progress_value(elem_id):
        try:
            elem = soup.find("progress", id=elem_id)
            if elem and elem.has_attr("value"):
                return float(elem["value"])
        except Exception:
            pass
        return 0.0

    brand_score = get_progress_value("establish-brand__sub-score-bar")
    people_score = get_progress_value("find-people__sub-score-bar")
    insights_score = get_progress_value("engage-with-insights__sub-score-bar")
    relationships_score = get_progress_value("build-relationships__sub-score-bar")

    print(
        f"🔍 SSI EXTRAÍDO: Total={total_ssi} | Brand={brand_score} | People={people_score} | Insights={insights_score} | Build={relationships_score}"
    )

    # --- FIM DA EXTRAÇÃO ---

    # Cálculos Comparativos (Mantido igual)
    new_connections_gained = 0
    ssi_increase = 0.0

    if os.path.exists(file_path):
        try:
            existing_df = pd.read_csv(file_path)
            existing_df["Date"] = pd.to_datetime(
                existing_df["Date"], errors="coerce"
            ).dt.strftime("%Y-%m-%d")
            last_day_df = existing_df[existing_df["Date"] != today]

            if not last_day_df.empty:
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
            print(f"Warning: Failed to calculate metrics: {e}")

    new_data = {
        "Date": [today],
        "Total_SSI": [total_ssi],
        "SSI_Increase": [ssi_increase],
        "Industry_Rank": [industry_rank],
        "Network_Rank": [network_rank],
        "Brand": [brand_score],
        "People": [people_score],
        "Insights": [insights_score],
        "Relationships": [relationships_score],
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
        "Total_Followers": [current_total_followers],
    }
    new_df = pd.DataFrame(new_data)

    if os.path.exists(file_path):
        existing_df = pd.read_csv(file_path)
        existing_df["Date"] = pd.to_datetime(
            existing_df["Date"], errors="coerce"
        ).dt.strftime("%Y-%m-%d")

        for col in new_df.columns:
            if col not in existing_df.columns:
                existing_df[col] = pd.NA

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
    Tenta a conexão com SSI-SAFE mode ativado.
    Filtra APENAS perfis que garantem crescimento de SSI:
    - Mínimo 300 conexões + 500 seguidores
    - Ativo (postou nos últimos 30 dias)
    - 2+ recomendações + 3+ skills
    - Headline com roles de alto nível
    """
    global SESSION_CONNECTION_COUNT

    # ===== NOVO: CHECK DE PERFIS JÁ CONECTADOS =====
    # Evita reprocessar perfis aos quais já enviou conexão
    try:
        current_url = browser.current_url
        if is_connection_sent(current_url):
            if VERBOSE:
                print(
                    f"    -> [SKIP CONVITE] Conexão já enviada para {name}. Pulando..."
                )
            return False
        if is_already_connected(current_url):
            if VERBOSE:
                print(
                    f"    -> [SKIP JÁ CONECTADO] Você já está conectado com {name}. Pulando..."
                )
            return False
    except Exception:
        pass

    # ===== NOVO: DETECÇÃO DE TOP VOICE =====
    # Perfis Top Voice têm estrutura HTML diferente e conexões podem não ser visíveis
    # Solução: relaxar filtro de conexões para Top Voices (usar followers como métrica)
    page_source = browser.page_source
    is_top_voice = False
    try:
        soup_check = BeautifulSoup(page_source, "html.parser")
        # Procura pelo badge "Top Voice" (múltiplas formas possíveis)
        top_voice_patterns = [
            "Top Voice",
            "linkedin-bug-influencer",  # classe SVG do badge
            "pv-top-voice-badge",  # classe do badge
        ]
        page_text = soup_check.get_text()
        for pattern in top_voice_patterns:
            if pattern in page_source:
                is_top_voice = True
                break
    except Exception:
        pass

    # FILTRO 1: Conexões Mínimas (EXTRAÇÃO ROBUSTA COM BeautifulSoup)
    try:
        page_source = browser.page_source
        soup = BeautifulSoup(page_source, "html.parser")

        # Procura especificamente pelo <li> que contém "connections" (não "followers")
        conn_count = None

        # Busca todos os <li> da seção de stats
        all_lis = soup.find_all("li", class_="text-body-small")

        for li in all_lis:
            li_text = li.get_text().lower()
            # Verifica se este li contém a palavra "connections"
            if "connections" in li_text:
                # Extrai o número (pode ser "500+", "45", etc)
                numbers = re.findall(r"(\d+)", li.get_text())
                if numbers:
                    conn_count = int(numbers[0])
                    break  # Encontrou, sai do loop

        if not conn_count:
            # Fallback 2: Procura por "connections" em <li> que tem link
            li_with_link = soup.find("li", class_="text-body-small")
            if li_with_link:
                # Procura o próximo <li> (pode estar em um <a> dentro)
                parent_ul = li_with_link.find_parent("ul")
                if parent_ul:
                    all_items = parent_ul.find_all("li")
                    for item in all_items:
                        if "connections" in item.get_text().lower():
                            numbers = re.findall(r"(\d+)", item.get_text())
                            if numbers:
                                conn_count = int(numbers[0])
                                break

        if not conn_count:
            # Fallback 3: Tenta no body_text
            body_text = browser.find_element(By.TAG_NAME, "body").text
            # Procura DEPOIS da palavra "connection" (pega a ÚLTIMA ocorrência)
            matches = list(re.finditer(r"(\d+)\s+connections?", body_text))
            if matches:
                conn_count = int(matches[-1].group(1))  # Pega o ÚLTIMO match

        if not conn_count:
            if is_top_voice:
                # NOVA LÓGICA: Top Voices têm estrutura HTML diferente
                # Conexões não são visíveis, mas followers sim
                # Relaxar filtro: aceitar Top Voice com base em followers
                print(
                    f"    -> [FILTER 1] {name} é TOP VOICE - conexões não visíveis (comum em perfis famosos)"
                )
                print(
                    "    -> [FILTER 1] Relaxando filtro de conexões para Top Voice, validando com followers..."
                )
                # Continua para FILTRO 2 (followers) sem retornar False
            else:
                print(
                    "    -> [FILTER 1] Não consegui extrair contagem de conexões. Pulando..."
                )
                return False
        elif conn_count < MIN_CONNECTIONS:
            if is_top_voice:
                # Top Voice mostrando número baixo = bug de extração
                # Confiar no badge Top Voice + número alto de followers
                print(
                    f"    -> [FILTER 1] {name} mostrou {conn_count} conexões (claramente bug para Top Voice)"
                )
                print(
                    "    -> [FILTER 1] Perfil é TOP VOICE, relaxando filtro de conexões..."
                )
                # Continua para FILTRO 2 (followers)
            else:
                print(
                    f"    -> [FILTER 1] {name} tem apenas {conn_count} conexões (min: {MIN_CONNECTIONS}). Pulando..."
                )
                return False

        # FILTRO 2: Seguidores Mínimos (SSI-SAFE: Influenciadores > SSI crescimento)
        if SSI_SAFE_MODE:
            followers_count = None
            # Procura por "followers" na página HTML
            followers_match = re.search(
                r"([\d,]+)\s*followers?", page_source, re.IGNORECASE
            )
            if followers_match:
                followers_count = int(followers_match.group(1).replace(",", ""))

            if not followers_count:
                if is_top_voice:
                    # Top Voices geralmente têm muitos followers
                    # Se é Top Voice mas não conseguimos extrair, aceitar com confiança
                    print(
                        f"    -> [FILTER 2] {name} é TOP VOICE, followers não extraído mas badge confirma influência. Aceitando..."
                    )
                else:
                    print(
                        "    -> [FILTER 2] Não consegui extrair contagem de seguidores. Pulando..."
                    )
                    return False
            elif followers_count < MIN_FOLLOWERS:
                if is_top_voice and followers_count >= 5000:
                    # Top Voice com 5k+ followers ainda vale a pena conectar
                    print(
                        f"    -> [FILTER 2] {name} tem {followers_count} seguidores (abaixo de {MIN_FOLLOWERS})"
                    )
                    print(
                        f"    -> [FILTER 2] Mas é TOP VOICE com {followers_count}+ followers, relaxando limite..."
                    )
                else:
                    print(
                        f"    -> [FILTER 2] {name} tem apenas {followers_count} seguidores (min: {MIN_FOLLOWERS}). Pulando..."
                    )
                    return False

            # FILTRO 3: Atividade dentro de 1 ano (Qualquer atividade recente é OK)
            # Aceita: 1d, 2w, 3m, "Posted X ago", "recently", etc
            # Rejeita: "1+ year ago", "years ago" (muito antigo)
            activity_patterns = [
                r"posted\s+(\d+)\s+days? ago",  # Posted 5 days ago
                r"posted\s+this\s+week",
                r"posted\s+today",
                r"posted\s+\d+\s+hours? ago",
                r"posted\s+\d+\s+minutes? ago",
                r"\d+[dwm]\b",  # 1d, 2w, 3m, etc (day, week, month)
                r"posted\s+\d+[dwm]",  # "posted 1w", "posted 3d"
                r"\d+\s+days? ago",  # "5 days ago"
                r"\d+\s+weeks? ago",  # "2 weeks ago"
                r"\d+\s+months? ago",  # "1 month ago"
                r"posted\s+last\s+week",  # "posted last week"
                r"posted\s+recently",  # "posted recently"
            ]

            # Rejeita APENAS se ver "years ago" ou "1+ year"
            reject_patterns = [
                r"\d+\s+years? ago",  # "2 years ago", "3 years ago"
                r"posted\s+\d+\s+years? ago",  # "posted 2 years ago"
            ]

            has_recent_activity = False
            for pattern in activity_patterns:
                if re.search(pattern, page_source, re.IGNORECASE):
                    has_recent_activity = True
                    break

            # Verifica se é muito antigo
            is_too_old = False
            for pattern in reject_patterns:
                if re.search(pattern, page_source, re.IGNORECASE):
                    is_too_old = True
                    break

            if is_too_old:
                if is_top_voice:
                    # Top Voices podem ter "years ago" mas ainda são valiosos
                    print(
                        f"    -> [FILTER 3] {name} última postagem antiga, MAS é TOP VOICE - aceitando..."
                    )
                else:
                    print(
                        f"    -> [FILTER 3] {name} postou há MAIS de 1 ano. Pulando..."
                    )
                    return False

            if not has_recent_activity:
                # Se não encontrou padrão explícito, mas também não é muito antigo, aceita mesmo assim
                # (pode ter postado recentemente mas o texto não é claro)
                if is_top_voice:
                    if VERBOSE:
                        print(
                            f"    -> [FILTER 3] {name} - atividade indefinida, MAS é TOP VOICE, aceitando..."
                        )
                else:
                    if VERBOSE:
                        print(
                            f"    -> [FILTER 3] {name} - atividade indefinida, aceitando..."
                        )

        # FILTRO 4: Verifica se já está conectado (múltiplas formas de detecção)
        body_text = browser.find_element(By.TAG_NAME, "body").text
        body_lower = body_text.lower()
        already_connected_indicators = [
            "already connected",
            "remove your connection",
            "remove connection",
            "you're connected",
            "você está conectado",
            "remover conexão",
        ]

        for indicator in already_connected_indicators:
            if indicator in body_lower:
                print(f"    -> [ALREADY] {name} já está conectado. Pulando...")
                # NOVO: Salva no banco que já está conectado (para nunca mais abrir)
                try:
                    current_url = browser.current_url
                    log_already_connected(current_url, name, headline)
                except Exception:
                    pass
                return False

        # FILTRO 5: Verifica se existe botão "Remove connection" ou similar no DOM
        # Isso é um sinal de que já estão conectados
        try:
            remove_buttons = browser.find_elements(
                By.XPATH,
                "//button[contains(@aria-label, 'Remove') and contains(@aria-label, 'connection')] | //div[@aria-label and contains(@aria-label, 'Remove') and contains(@aria-label, 'connection')]",
            )
            if remove_buttons and len(remove_buttons) > 0:
                print(
                    f"    -> [ALREADY DOM] {name} tem botão 'Remove connection'. Pulando..."
                )
                # NOVO: Salva no banco que já está conectado
                try:
                    current_url = browser.current_url
                    log_already_connected(current_url, name, headline)
                except Exception:
                    pass
                return False
        except Exception:
            pass

        # FILTRO 6: Se vê botão "Message" MAS NÃO vê "Connect", significa que já é amigo
        # No LinkedIn, quando você já está conectado com alguém, só aparece "Message", não "Connect"
        try:
            message_buttons = browser.find_elements(
                By.XPATH,
                "//button[contains(@aria-label, 'Message')] | //a[contains(@aria-label, 'Message')] | //*[@aria-label and contains(@aria-label, 'Message')]",
            )

            connect_buttons = browser.find_elements(
                By.XPATH,
                "//button[contains(@aria-label, 'Connect') or contains(@aria-label, 'Invite')] | //a[contains(@aria-label, 'Connect') or contains(@aria-label, 'Invite')] | //*[@aria-label and (contains(@aria-label, 'Connect') or contains(@aria-label, 'Invite'))]",
            )

            # Se tem Message mas NÃO tem Connect/Invite = já é amigo
            if (
                message_buttons
                and len(message_buttons) > 0
                and (not connect_buttons or len(connect_buttons) == 0)
            ):
                print(
                    f"    -> [MESSAGE ONLY] {name} tem botão 'Message' apenas - já é sua conexão. Pulando..."
                )
                # NOVO: Salva no banco que já está conectado
                try:
                    current_url = browser.current_url
                    log_already_connected(current_url, name, headline)
                except Exception:
                    pass
                return False
        except Exception:
            pass

    except Exception:
        pass

    try:
        # ESPERA: Garante que o DOM carregou
        human_sleep(3, 5)

        # SCROLL AGRESSIVO para garantir que o bloco principal está visível
        for _ in range(3):
            browser.execute_script(
                "window.scrollTo(0, document.body.scrollHeight * 0.2);"
            )
            human_sleep(0.5, 1)
        human_sleep(1, 2)

        # ===== CRÍTICO: PROCURAR APENAS NO BLOCO PRINCIPAL (div.ph5.pb5) =====
        # NÃO procurar em <aside> ou outras seções com sugestões
        # A sidebar (<aside>) contém "More profiles for you", "People you may know" etc
        # com botões Connect que NUNCA devemos clicar

        profile_card = None
        try:
            # Procura pelo bloco PRINCIPAL do perfil (class estável)
            # Este é o ÚNICO local onde queremos clicar em Connect
            profile_card = WebDriverWait(browser, 3).until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        "//div[contains(@class, 'ph5') and contains(@class, 'pb5')]",
                    )
                )
            )
            if VERBOSE:
                print("    -> [BLOCO] Perfil principal encontrado (IGNORANDO sidebar)")
        except Exception:
            profile_card = None

        # Se encontrou o bloco PRINCIPAL, procurar botão Connect APENAS DENTRO DELE
        if profile_card:
            # Tenta botão Connect direto (sem menu)
            try:
                # XPath restrito ao contexto do elemento encontrado (perfil principal)
                # find_element dentro de profile_card só busca dentro dele
                connect_btn = profile_card.find_element(
                    By.XPATH,
                    ".//button[(contains(@aria-label, 'Connect') or contains(@aria-label, 'Invite')) and not(ancestor::aside)]",
                )
                if connect_btn and connect_btn.is_displayed():
                    if VERBOSE:
                        print(
                            "    -> [BOTÃO DIRETO] Encontrado NO BLOCO PRINCIPAL, tentando clicar..."
                        )
                    result = click_connect_sequence(
                        browser,
                        connect_btn,
                        name,
                        headline,
                        group_name,
                        is_viewer=False,
                    )
                    if result:
                        return True
            except Exception:
                pass

            # Se Connect direto não está visível, procura no dropdown "More actions"
            try:
                more_btn = profile_card.find_element(
                    By.XPATH,
                    ".//button[contains(@aria-label, 'More actions') and not(ancestor::aside)]",
                )
                if more_btn and more_btn.is_displayed():
                    if VERBOSE:
                        print(
                            "    -> [MORE ACTIONS] Encontrado no BLOCO PRINCIPAL, abrindo dropdown..."
                        )

                    # Clica no More actions
                    ActionChains(browser).move_to_element(more_btn).perform()
                    human_sleep(0.5, 1)
                    browser.execute_script("arguments[0].click();", more_btn)
                    human_sleep(2, 4)

                    # Aguarda dropdown visível e DENTRO DO BLOCO PRINCIPAL
                    try:
                        dropdown_visible = WebDriverWait(browser, 3).until(
                            EC.presence_of_element_located(
                                (
                                    By.XPATH,
                                    "//div[contains(@class,'artdeco-dropdown__content') and (not(@aria-hidden) or @aria-hidden='false') and not(ancestor::aside)]",
                                )
                            )
                        )
                        human_sleep(0.5, 1)

                        # Procura "Connect" dentro do dropdown aberto (restrito ao bloco principal)

                        connect_items = dropdown_visible.find_elements(
                            By.XPATH,
                            ".//div[contains(@aria-label, 'Connect') and not(ancestor::aside)]",
                        )
                        for item in connect_items:
                            if item.is_displayed():
                                if VERBOSE:
                                    print(
                                        "    -> [DROPDOWN CONNECT] Encontrado no BLOCO PRINCIPAL, tentando clicar..."
                                    )
                                result = click_connect_sequence(
                                    browser,
                                    item,
                                    name,
                                    headline,
                                    group_name,
                                    is_viewer=False,
                                )
                                if result:
                                    return True
                    except Exception:
                        pass
            except Exception:
                pass

        # Se a tentativa baseada no bloco do nome não encontrou nada, manter as estratégias existentes
        # ===== TENTATIVA 1b: Botão "Connect" direto visível (APENAS DO PERFIL PRINCIPAL) =====
        direct_connect_selectors = [
            "//div[contains(@class, 'pv-profile-sticky-header') or contains(@class, 'pvs-sticky-header-profile-actions')]//button[contains(@aria-label, 'Invite') and contains(@aria-label, 'to connect') and not(ancestor::aside)]",
            "(//button[contains(@aria-label, 'Invite') and contains(@aria-label, 'to connect') and not(ancestor::aside)])[1]",
            "(//button[contains(@class, 'artdeco-button--primary') and contains(@aria-label, 'Invite') and not(ancestor::aside)])[1]",
            "(//button[.//span[text()='Connect'] and not(ancestor::aside)])[1]",
        ]

        for xpath_direct in direct_connect_selectors:
            try:
                btn = WebDriverWait(browser, 3).until(
                    EC.element_to_be_clickable((By.XPATH, xpath_direct))
                )
                if VERBOSE:
                    print(
                        "    -> [BOTÃO DIRETO FALLBACK] Tentando clicar (bloqueando sidebar)..."
                    )

                result = click_connect_sequence(
                    browser, btn, name, headline, group_name, is_viewer=False
                )
                if result:
                    return True
                # Se falhou, tenta o menu como fallback
                break
            except Exception:
                continue

        # ===== TENTATIVA 2: "Connect" dentro do menu 'More actions' (FALLBACK) =====
        print("    -> [FALLBACK] Tentando menu 'More actions' (bloqueando sidebar)...")
        more_action_selectors = [
            # Primeiro: procura por ID que contém "profile-overflow-action" (mais confiável)
            "//button[contains(@id, 'profile-overflow-action') and not(ancestor::aside)]",
            # Segundo: qualquer "More actions" que seja próximo ao perfil (não em contatos secundários)
            "(//button[contains(@aria-label, 'More actions') and not(ancestor::aside)])[1]",
        ]

        for xpath_more in more_action_selectors:
            try:
                btn_more = WebDriverWait(browser, 5).until(
                    EC.presence_of_element_located((By.XPATH, xpath_more))
                )

                # Scroll para garantir visibilidade
                browser.execute_script("arguments[0].scrollIntoView(true);", btn_more)
                human_sleep(1, 2)

                # Clica com JS (mais confiável)
                browser.execute_script("arguments[0].click();", btn_more)
                print("    -> [DROPDOWN OPENING] Aguardando dropdown abrir...")
                human_sleep(2, 4)

                # Procura "Connect" no dropdown com múltiplas estratégias
                # O dropdown contém divs/buttons. Procurar especificamente por "Invite to connect"
                # Evitar falsos positivos como "Remove your connection"
                dropdown_selectors = [
                    # Strategy 1: Procura especificamente por "Invite" na aria-label
                    "//div[@role='button' and contains(@aria-label, 'Invite') and contains(@aria-label, 'to connect')]",
                    # Strategy 2: Procura por "Invite" sem "Remove"
                    "//div[@role='button' and contains(@aria-label, 'Invite') and not(contains(@aria-label, 'Remove'))]",
                    # Strategy 3: Procura por span com "Connect" + role button
                    "//span[text()='Connect']/ancestor::div[@role='button']",
                    # Strategy 4: Último recurso - "Invite" em qualquer lugar
                    "//*[@role='button' and contains(@aria-label, 'Invite to')]",
                ]

                connect_found = False
                for i, xpath_drop in enumerate(dropdown_selectors):
                    try:
                        # Usa presence em vez de visibility porque aria-hidden não impede clique
                        btn_drop = WebDriverWait(browser, 2).until(
                            EC.presence_of_element_located((By.XPATH, xpath_drop))
                        )

                        aria_label = (
                            btn_drop.get_attribute("aria-label") or btn_drop.text[:60]
                        )
                        if VERBOSE:
                            print(f"    -> [DROPDOWN FOUND #{i + 1}] {aria_label}")

                        result = click_connect_sequence(
                            browser,
                            btn_drop,
                            name,
                            headline,
                            group_name,
                            is_viewer=False,
                        )
                        if result:
                            return True
                        connect_found = True
                        break
                    except TimeoutException:
                        if VERBOSE:
                            print(f"    -> [DROPDOWN TIMEOUT #{i + 1}]")
                        continue
                    except Exception as e:
                        if VERBOSE:
                            print(
                                f"    -> [DROPDOWN ERROR #{i + 1}] {type(e).__name__}"
                            )
                        continue

                # Se o dropdown abriu mas não tem connect, fecha e tenta próximo seletor
                if not connect_found:
                    try:
                        browser.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                    except Exception:
                        pass
                continue

            except TimeoutException:
                if VERBOSE:
                    print(
                        f"    -> [MORE TIMEOUT] Botão 'More actions' não encontrado: {xpath_more[:50]}"
                    )
                continue
            except Exception as e:
                if VERBOSE:
                    print(
                        f"    -> [MORE ERROR] Erro ao tentar More actions: {str(e)[:60]}"
                    )
                continue

        # VERIFICAÇÃO FINAL: Se chegou aqui, nada funcionou. Checar se é porque já é amigo
        try:
            body_final = browser.find_element(By.TAG_NAME, "body").text.lower()
            already_connected_keywords = [
                "already connected",
                "remove your connection",
                "remove connection",
                "you're connected",
                "connected with",
            ]

            is_already_connected = any(
                keyword in body_final for keyword in already_connected_keywords
            )

            if is_already_connected:
                print(f"    -> [JÁ AMIGO] {name} já é seu conexão. Pulando...")
                return False

        except Exception:
            pass

        # Se nada funcionou
        print(f"    -> [SKIP] Não conseguiu conectar com {name}")
        return False

    except Exception as e:
        if "invalid session id" in str(e).lower():
            raise
        if VERBOSE:
            print(f"    -> [ERRO] Falha em connect_with_user: {e}")
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

    try:
        # 1. Clica no botão 'Conectar'
        ActionChains(browser).move_to_element(button_element).perform()
        human_sleep(1, 2)
        browser.execute_script("arguments[0].click();", button_element)
        print("    -> [CLICK] Botão Connect clicado. Aguardando modal...", flush=True)

        human_sleep(3, 5)

        # 2. Aguarda modal aparecer com timeout generoso
        try:
            WebDriverWait(browser, 5).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//div[contains(@class, 'artdeco-modal')]")
                )
            )
        except Exception:
            print("    -> [TIMEOUT] Modal não apareceu dentro do esperado", flush=True)

        # 3. Tenta enviar apenas com button tipo "Send without note"
        send_button_selectors = [
            "//button[contains(@aria-label, 'Send without')]",
            "//button[.//span[contains(text(), 'Send without')]]",
            "//button[contains(@aria-label, 'Enviar sem')]",
        ]

        for sel in send_button_selectors:
            try:
                btn_send = WebDriverWait(browser, 3).until(
                    EC.presence_of_element_located((By.XPATH, sel))
                )
                if btn_send.is_displayed():
                    browser.execute_script("arguments[0].click();", btn_send)
                    print(f"    -> [SEND OK] Invite enviado para {name}", flush=True)

                    # ===== NOVO: REGISTRA CONEXÃO ENVIADA =====
                    try:
                        profile_url = browser.current_url
                        log_connection_sent(profile_url, name, "")
                    except Exception:
                        pass

                    SESSION_CONNECTION_COUNT += 1
                    human_sleep(2, 4)
                    return True
            except Exception:
                continue

        # 4. Se não achou "Send without note", procura por qualquer botão primary
        try:
            primary_btns = browser.find_elements(
                By.XPATH,
                "//div[contains(@class, 'artdeco-modal__actionbar')]//button[contains(@class, 'artdeco-button--primary')]",
            )
            if primary_btns:
                browser.execute_script("arguments[0].click();", primary_btns[-1])
                print(
                    f"    -> [SEND FALLBACK] Invite enviado para {name} (fallback)",
                    flush=True,
                )

                # ===== NOVO: REGISTRA CONEXÃO ENVIADA =====
                try:
                    profile_url = browser.current_url
                    log_connection_sent(profile_url, name, "")
                except Exception:
                    pass

                SESSION_CONNECTION_COUNT += 1
                human_sleep(2, 4)
                return True
        except Exception:
            pass

        # 5. Fallback final: fechar modal
        print("    -> [PARTIAL] Modal não respondeu corretamente", flush=True)
        try:
            browser.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
        except Exception:
            pass
        return False

    except Exception as e:
        if VERBOSE:
            print(f"    -> [ERROR] click_connect_sequence falhou: {e}", flush=True)
        try:
            browser.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
        except Exception:
            pass
        return False


def run_extraction_process():
    if not os.path.exists(DRIVER_FILENAME):
        return
    try:
        os.system("taskkill /im msedge.exe /f >nul 2>&1")
    except Exception:
        pass

    opts = EdgeOptions()

    # --- [NOVO] ROTAÇÃO DE USER-AGENT E ANTI-FINGERPRINT ---
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
    ]
    agent = random.choice(user_agents)
    opts.add_argument(f"user-agent={agent}")

    # Randomiza tamanho da janela para evitar detecção por resolução padrão
    width = random.randint(1024, 1920)
    height = random.randint(768, 1080)
    opts.add_argument(f"--window-size={width},{height}")
    # -------------------------------------------------------

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
        print("📊 Acessando página de SSI...")
        driver.get("https://www.linkedin.com/sales/ssi")
        # Pequeno sleep para garantir renderização do JS
        time.sleep(5)

        # O SEGREDO: Pegar o page_source (HTML completo), não o .text
        ssi_html_source = driver.page_source

        # 3. Coleta dados do Dashboard
        print("📊 Coletando Analytics para Dashboard...")
        driver.get("https://www.linkedin.com/dashboard/")
        time.sleep(3)

        views = 0
        impressions = 0
        search = 0
        followers = 0

        try:
            txt = driver.find_element(By.TAG_NAME, "body").text
            # Regex simples para dashboard (costuma funcionar bem aqui)
            if m := re.search(r"(\d+)\s+profile views", txt):
                views = int(m.group(1))
            if m := re.search(r"(\d+)\s+post impressions", txt):
                impressions = int(m.group(1))
            if m := re.search(r"(\d+)\s+search appearances", txt):
                search = int(m.group(1))

            # Followers via seletor específico
            try:
                # Tenta pegar followers de forma mais genérica se a classe mudar
                followers_elem = driver.find_element(
                    By.XPATH,
                    "//*[contains(text(), 'Followers')]/preceding-sibling::div | //*[contains(text(), 'Followers')]/../div[1]",
                )
                followers = int(followers_elem.text.replace(",", "").strip())
            except Exception:
                # Fallback
                if m := re.search(r"(\d+)\s+Followers", txt):
                    followers = int(m.group(1))

        except Exception as e:
            print(f"Warning: Dashboard extraction issues: {e}")

        print(f"Extracted: Views={views}, Followers={followers}")

        # 4. Processa e Salva (Passando o HTML do SSI)
        df = update_ssi_table(
            ssi_html_source,  # HTML AQUI
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
            followers,
        )
        print("SSI Updated successfully.")

        log_analytics_db(views, impressions, search, followers)
        driver.quit()

    except Exception as e:
        print(f"Critical Error in Extraction: {e}")
        try:
            driver.quit()
        except Exception:
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
    except Exception:
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

    except Exception:
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
    except Exception:
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
    except Exception:
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
        except Exception:
            btn.click()
            print("    -> Liked (Joinha)")
    except Exception:
        pass


def perform_comment(driver, post, text, source="group"):
    try:
        # Try multiple selectors for comment button
        comment_button_selectors = [
            "button[aria-label*='Comment']",
            "button[aria-label*='Comentar']",
            ".comment-button",
            "button[data-test-id*='comment']",
            "button.comments-comment-meta__comment-toggle",
            "button.feed-shared-control-menu__trigger",
        ]

        btn = None
        for selector in comment_button_selectors:
            try:
                btn = post.find_element(By.CSS_SELECTOR, selector)
                if btn and btn.is_displayed():
                    print(f"    -> Found comment button with selector: {selector}")
                    break
            except:
                continue

        if not btn:
            print("    -> Failed to comment: No comment button found")
            return False

        driver.execute_script(
            "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", btn
        )
        human_sleep(2, 4)
        btn.click()
        print("    -> Comment button clicked, waiting for comment box to appear...")
        human_sleep(3, 6)  # Increased wait time

        # Check if post expanded and look for comment box within the expanded post
        try:
            # Look for comment box within the post element itself
            post_comment_selectors = [
                "div[contenteditable='true']",
                "textarea",
                ".ql-editor",
                "[role='textbox']",
            ]
            for sel in post_comment_selectors:
                try:
                    box = post.find_element(By.CSS_SELECTOR, sel)
                    if box and box.is_displayed():
                        print(
                            f"    -> Found comment box within post with selector: {sel}"
                        )
                        # Continue with the rest of the function
                        break
                except:
                    continue
            else:
                # If not found within post, search globally
                pass
        except:
            pass

        # Debug: Check for any contenteditable elements on the page
        all_contenteditable = driver.find_elements(
            By.CSS_SELECTOR, "[contenteditable='true']"
        )
        print(
            f"    -> DEBUG: Found {len(all_contenteditable)} contenteditable elements on page after clicking comment"
        )

        # Check if a modal appeared
        modal_selectors = [
            "div.modal__overlay",
            "div[data-test-id='comment-modal']",
            "div.artdeco-modal",
            "div.comments-modal",
        ]
        modal_found = False
        for modal_sel in modal_selectors:
            modals = driver.find_elements(By.CSS_SELECTOR, modal_sel)
            if modals:
                print(f"    -> DEBUG: Found modal with selector: {modal_sel}")
                modal_found = True
                break

        # Multiple fallback selectors for comment box
        box = None
        selectors = [
            # Current LinkedIn selectors (2024-2025)
            (
                By.CSS_SELECTOR,
                "div[data-test-id='comment-input'] div[contenteditable='true']",
            ),
            (
                By.CSS_SELECTOR,
                "div.comments-comment-box__form-container div[contenteditable='true']",
            ),
            (
                By.CSS_SELECTOR,
                "div.feed-shared-comments-list__comment-form div[contenteditable='true']",
            ),
            (
                By.CSS_SELECTOR,
                "div[data-test-id='comment-composer'] div[contenteditable='true']",
            ),
            (By.CSS_SELECTOR, "div.comment-form div[contenteditable='true']"),
            # Modal/overlay selectors
            (By.CSS_SELECTOR, "div.modal__overlay div[contenteditable='true']"),
            (
                By.CSS_SELECTOR,
                "div[data-test-id='comment-modal'] div[contenteditable='true']",
            ),
            # Regular input elements (not just contenteditable)
            (By.CSS_SELECTOR, "textarea"),
            (By.CSS_SELECTOR, "input[type='text']"),
            (By.CSS_SELECTOR, "input[placeholder*='comment' i]"),
            (By.CSS_SELECTOR, "input[placeholder*='Comment' i]"),
            # Legacy selectors (still might work)
            (By.CSS_SELECTOR, "div[contenteditable='true'][role='textbox']"),
            (By.CSS_SELECTOR, "div.ql-editor"),
            (By.CSS_SELECTOR, "div[role='textbox']"),
            (By.CSS_SELECTOR, "[contenteditable='true']"),
            (By.CSS_SELECTOR, ".comments-comment-box__comment-textbox"),
            (By.CSS_SELECTOR, "[placeholder*='comment' i]"),
            (By.CSS_SELECTOR, "[placeholder*='Comment' i]"),
            # XPath fallbacks
            (By.XPATH, "//div[@contenteditable='true' and @role='textbox']"),
            (By.XPATH, "//div[@role='textbox']"),
            (By.XPATH, "//div[@contenteditable='true']"),
            (By.XPATH, "//textarea"),
            (By.XPATH, "//input[@type='text']"),
            # More specific LinkedIn selectors
            (By.CSS_SELECTOR, ".comments-comment-box .ql-editor"),
            (
                By.CSS_SELECTOR,
                ".feed-shared-control-menu__trigger + div [contenteditable='true']",
            ),
            # Newer selectors for expanded comments
            (
                By.CSS_SELECTOR,
                "div.feed-shared-update-v2__comments [contenteditable='true']",
            ),
            (
                By.CSS_SELECTOR,
                "div.social-detail-social-counts__comments-list [contenteditable='true']",
            ),
        ]

        for selector_type, selector_value in selectors:
            try:
                elements = driver.find_elements(selector_type, selector_value)
                if elements:
                    print(
                        f"    -> Found {len(elements)} elements with selector: {selector_value}"
                    )
                for elem in elements:
                    if elem and elem.is_displayed():
                        # Check if element is within the post area
                        try:
                            post_rect = post.rect
                            elem_rect = elem.rect
                            # Check if element is roughly within post bounds
                            if (
                                abs(elem_rect["y"] - post_rect["y"]) < 500
                                and elem_rect["width"] > 50
                                and elem_rect["height"] > 20
                            ):
                                box = elem
                                print(
                                    f"    -> Found comment box with selector: {selector_value}"
                                )
                                break
                        except:
                            # If rect check fails, try basic checks
                            try:
                                post_y = driver.execute_script(
                                    "return arguments[0].getBoundingClientRect().top",
                                    post,
                                )
                                elem_y = driver.execute_script(
                                    "return arguments[0].getBoundingClientRect().top",
                                    elem,
                                )
                                elem_height = driver.execute_script(
                                    "return arguments[0].offsetHeight", elem
                                )
                                elem_width = driver.execute_script(
                                    "return arguments[0].offsetWidth", elem
                                )
                                if (
                                    abs(elem_y - post_y) < 500
                                    and elem_width > 50
                                    and elem_height > 20
                                ):
                                    box = elem
                                    print(
                                        f"    -> Found comment box with selector: {selector_value}"
                                    )
                                    break
                            except:
                                # If all rect checks fail, just use basic checks
                                if driver.execute_script(
                                    "return arguments[0].offsetHeight > 0", elem
                                ):
                                    box = elem
                                    print(
                                        f"    -> Found comment box with selector: {selector_value}"
                                    )
                                    break
                if box:
                    break
            except Exception:
                continue

        if not box:
            print("    -> Failed to comment: No comment box found")
            # Fallback: Try to send comment via keyboard shortcut or focus on active element
            try:
                print("    -> Attempting keyboard fallback for comment...")
                # Try Ctrl+Enter to submit, or focus on any input that might have appeared
                active_element = driver.execute_script("return document.activeElement")
                if active_element and active_element.tag_name.lower() in [
                    "input",
                    "textarea",
                    "div",
                ]:
                    print(
                        "    -> Found active input element, trying to type comment..."
                    )
                    active_element.send_keys(text)
                    human_sleep(1, 2)
                    # Try to submit
                    ActionChains(driver).key_down(Keys.CONTROL).send_keys(
                        Keys.RETURN
                    ).key_up(Keys.CONTROL).perform()
                    print(f"    -> Commented via keyboard fallback: {text[:50]}...")
                    human_sleep(8, 15)
                    take_coffee_break()
                    return True
                else:
                    print("    -> No active input element found for keyboard fallback")
            except Exception as e:
                print(f"    -> Keyboard fallback failed: {e}")
            return False

        print(
            f"    -> Comment box found, dimensions: {box.rect if hasattr(box, 'rect') else 'N/A'}, displayed: {box.is_displayed()}"
        )

        # Scroll box into view and ensure it's fully loaded
        driver.execute_script(
            "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
            box,
        )
        human_sleep(2, 3)  # Longer wait for full loading

        # Wait for element to be fully interactable
        max_wait = 10
        wait_count = 0
        while wait_count < max_wait:
            try:
                if box.is_displayed() and driver.execute_script(
                    "return arguments[0].offsetHeight > 10 && arguments[0].offsetWidth > 50",
                    box,
                ):
                    break
            except:
                pass
            human_sleep(0.5, 1)
            wait_count += 1

        if wait_count >= max_wait:
            print("    -> Failed to comment: Comment box not fully loaded")
            return False

        # Try multiple click methods
        clicked = False
        click_methods = [
            lambda: driver.execute_script(
                "arguments[0].click(); arguments[0].focus();", box
            ),
            lambda: ActionChains(driver).move_to_element(box).click().perform(),
            lambda: box.click(),
        ]

        for click_method in click_methods:
            try:
                click_method()
                human_sleep(0.5, 1)
                # Check if box is now focused/active
                if driver.execute_script(
                    "return document.activeElement === arguments[0]", box
                ):
                    clicked = True
                    break
            except Exception:
                continue

        if not clicked:
            print("    -> Failed to comment: Could not click comment box")
            return False

        human_sleep(1, 2)

        # Type the comment with multiple methods
        typed = False
        type_methods = [
            lambda: box.send_keys(text),
            lambda: driver.execute_script(
                "arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('input', {bubbles: true}));",
                box,
                text,
            ),
            lambda: human_type(box, text),
        ]

        for type_method in type_methods:
            try:
                type_method()
                human_sleep(0.5, 1)
                # Check if text was entered
                current_value = driver.execute_script(
                    "return arguments[0].textContent || arguments[0].value", box
                )
                if current_value and len(current_value.strip()) > 0:
                    typed = True
                    break
            except Exception:
                continue

        if not typed:
            print("    -> Failed to comment: Could not type comment")
            return False
        human_sleep(3, 6)

        # Multiple fallback selectors for submit button
        submit_btn = None
        submit_selectors = [
            (By.CSS_SELECTOR, "button.comments-comment-box__submit-button"),
            (By.CSS_SELECTOR, "button[class*='primary'][class*='submit']"),
            (By.XPATH, "//button[contains(@class, 'submit')]"),
            (
                By.XPATH,
                "//button[contains(., 'Post') or contains(., 'Comment') or contains(., 'Postar') or contains(., 'Comentar')]",
            ),
            (
                By.CSS_SELECTOR,
                "button[aria-label*='Post'], button[aria-label*='Postar']",
            ),
        ]

        for selector_type, selector_value in submit_selectors:
            try:
                submit_btn = driver.find_element(selector_type, selector_value)
                if submit_btn and submit_btn.is_displayed():
                    # Scroll into view before clicking
                    driver.execute_script(
                        "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                        submit_btn,
                    )
                    human_sleep(1, 2)
                    break
            except Exception:
                continue

        if submit_btn:
            try:
                driver.execute_script("arguments[0].click();", submit_btn)
            except Exception:
                submit_btn.click()
        else:
            # Try keyboard shortcut (Ctrl+Enter)
            ActionChains(driver).key_down(Keys.CONTROL).send_keys(Keys.RETURN).key_up(
                Keys.CONTROL
            ).perform()
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
        except Exception:
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
    except Exception:
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
                        except Exception:
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
        except Exception:
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
                except Exception:
                    pass
        else:
            print("    -> Nenhuma celebração pendente encontrada.")
    except Exception as e:
        print(f"Erro no Networker: {e}")


# ==============================================================================
# FUNÇÃO PRINCIPAL DE GRUPO - CORRIGIDO LOG
# ==============================================================================


def run_group_bot(browser, extra_targets=None):
    """
    Versão Corrigida: Implementa Loop While com Scroll e log detalhado
    do perfil sendo visitado e a ação tomada.
    """
    global \
        GROUP_CONNECTION_COUNT, \
        SESSION_FOLLOW_COUNT, \
        CONNECTED, \
        SESSION_CONNECTION_COUNT
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
    except Exception:
        group_name = "our group"

    print(f"-> Interagindo e Coletando (Meta: {PROFILES_TO_SCAN})...")

    # Garante lista vazia se None (permite passar uma lista externa de perfis)
    if extra_targets is None:
        extra_targets = []

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
                except Exception:
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
                            # Proteção: Verifica se já foi comentado anteriormente
                            if is_post_already_commented(browser, post):
                                if VERBOSE:
                                    print(
                                        "    -> [SKIP] Post já foi comentado em execução anterior. Pulando..."
                                    )
                                commented_in_group.add(urn)
                            else:
                                text = post.text
                                if len(text) > 15 and (
                                    not FEED_ENGLISH_ONLY or is_text_english(text)
                                ):
                                    comment = get_ai_comment(text)
                                    if perform_comment(browser, post, comment):
                                        # Registra o post como comentado
                                        register_post_commented(browser, post)
                                        commented_in_group.add(urn)
                        except Exception:
                            pass

                    commented_in_group.add(urn)  # Marca como processado na sessão
            except Exception:
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

    # Integra targets externos (lista) ao final da coleta do grupo
    if extra_targets:
        print(f"-> Incorporando {len(extra_targets)} alvos externos à fila do grupo...")
        for url in extra_targets:
            if url not in profiles_queued:
                profiles_queued.append(url)

    print(f"\n-> Coleta finalizada. Visitando {len(profiles_queued)} perfis...")

    # LOOP DE VISITA COM LOG DETALHADO
    processed = 0

    for url in profiles_queued:
        if processed >= PAG_ABERTAS:
            break

        # ===== NOVO: SKIP PERFIS JÁ CONECTADOS =====
        if is_connection_sent(url):
            if VERBOSE:
                print("    -> [CACHE] Perfil já conectado. Pulando...")
            continue

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
            except Exception:
                name = "Unknown"
            try:
                headline = browser.find_element(
                    By.XPATH, "//div[contains(@class, 'text-body-medium')]"
                ).text.lower()
            except Exception:
                headline = ""

            print(
                f"\n[{processed}/{PAG_ABERTAS}] Perfil: **{name}** ({headline[:30]}...)"
            )

            endorse_skills(browser)

            # 1. Tenta CONECTAR (se for alvo e houver limite - Grupo tem seu próprio limite)
            if GROUP_CONNECTION_COUNT < GROUP_CONNECTION_LIMIT:
                if any(role in headline for role in TARGET_ROLES):
                    print(
                        f"    -> [ALVO] Conectando ({GROUP_CONNECTION_COUNT}/{GROUP_CONNECTION_LIMIT})..."
                    )
                    if connect_with_user(browser, name, headline, group_name):
                        status = "Connected"
                        GROUP_CONNECTION_COUNT += 1
                        SESSION_CONNECTION_COUNT += (
                            1  # Mantém total de sessão para logging
                        )
                        print(
                            f"    -> [SUCCESS] **Conectado**. Total: {GROUP_CONNECTION_COUNT}/{GROUP_CONNECTION_LIMIT}"
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
    print(f"Total Connected (Grupo): {GROUP_CONNECTION_COUNT}/{GROUP_CONNECTION_LIMIT}")
    print(f"Total Followed na Sessão: {SESSION_FOLLOW_COUNT}/{FOLLOW_LIMIT}")
    print("\n--- RESUMO GERAL ---")
    print(f"Total de Conexões (Sniper + Grupo): {SESSION_CONNECTION_COUNT}")
    print(f"  • Sniper: {SNIPER_CONNECTION_COUNT}/{SNIPER_CONNECTION_LIMIT}")
    print(f"  • Grupo: {GROUP_CONNECTION_COUNT}/{GROUP_CONNECTION_LIMIT}")
    print(
        f"📊 Histórico: {get_connection_sent_count()} conexões já enviadas (total acumulado)"
    )


def random_mouse_hover(browser):
    try:
        els = browser.find_elements(By.TAG_NAME, "span")
        if els:
            ActionChains(browser).move_to_element(random.choice(els)).perform()
    except Exception:
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
    max_retries = 3
    retry_count = 0

    while retry_count < max_retries:
        try:
            if os.name == "nt":
                try:
                    # Aguarda antes de matar processos antigos
                    time.sleep(0.5)
                    os.system("taskkill /im msedge.exe /f >nul 2>&1")
                    time.sleep(1)  # Aguarda para evitar DevToolsActivePort issue
                except Exception:
                    pass

            # STEALTH: Random Window Size para evitar fingerprinting
            opts = EdgeOptions()
            width = random.randint(1024, 1920)
            height = random.randint(768, 1080)
            opts.add_argument(f"--window-size={width},{height}")

            # Usa o perfil padrão do Edge (que já está logado no LinkedIn)
            ud = os.path.join(
                os.environ["USERPROFILE"],
                "AppData",
                "Local",
                "Microsoft",
                "Edge",
                "User Data",
            )
            opts.add_argument(f"--user-data-dir={ud}")
            opts.add_argument("--profile-directory=Default")
            opts.add_argument("--no-first-run")
            opts.add_argument("--no-default-browser-check")
            opts.add_argument("--disable-extensions")
            opts.add_argument("--disable-sync")
            opts.add_argument("--disable-blink-features=AutomationControlled")
            opts.add_experimental_option("excludeSwitches", ["enable-automation"])
            opts.add_experimental_option("useAutomationExtension", False)

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

            print("✅ Browser iniciado com sucesso!")
            print(f"⚡ OTIMIZAÇÕES ATIVAS: Cache={COMMENTED_POSTS_CACHE_LOADED}, Speed={SPEED_FACTOR}, Limits={LIMITS_CONFIG['CONNECTION']}")
            break  # Saiu do loop de retry

        except Exception as e:
            retry_count += 1
            error_msg = str(e)[:100]
            print(f"⚠️ Tentativa {retry_count}/{max_retries} falhou: {error_msg}")

            if retry_count >= max_retries:
                print(
                    f"❌ Não conseguiu iniciar o browser após {max_retries} tentativas."
                )
                print(f"    Erro final: {error_msg}")
                # Continua mesmo assim (tenta executar com browser None)
                return

            time.sleep(2)  # Aguarda antes de tentar novamente

    # --- AÇÕES DO BOT ---
    if browser is None:
        print("⚠️ Browser é None, abortando execução.")
        return

    try:
        # 1. Conexões Rápidas (Novo modo de bypass de limite)
        try:
            run_quick_connects(browser)
        except Exception as e:
            error_msg = str(e).lower()
            if "invalid session id" in error_msg or "session deleted" in error_msg:
                print("\n⚠️ Session expired during Quick Connects. Aborting run.")
                raise  # Re-raise to outer handler for restart
            print(f"    -> Quick Connects erro: {str(e)[:80]}")

        # 2. Feed Interaction
        try:
            interact_with_feed_human(browser)
        except Exception as e:
            error_msg = str(e).lower()
            if "invalid session id" in error_msg or "session deleted" in error_msg:
                print("\n⚠️ Session expired during Feed. Aborting run.")
                raise
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
            error_msg = str(e).lower()
            if "invalid session id" in error_msg or "session deleted" in error_msg:
                print("\n⚠️ Session expired during Group Logic. Aborting run.")
                raise  # Re-raise to outer handler for restart
            print(f"!!! ERRO FATAL: Falha em run_main_bot_logic. Detalhe: {e}")
            raise

        # Fim da sessão, fechar o navegador
        browser.quit()

    except Exception as e:
        error_msg = str(e).lower()
        if "invalid session id" in error_msg or "session deleted" in error_msg:
            print("\n🛑 ERRO DE SESSÃO INVÁLIDA DETECTADO. Re-levantando para restart.")
            raise  # Re-raise so launch() can restart
        print(f"\n🛑 ERRO GERAL NA EXECUÇÃO DO BOT: {e}")
        # Garante que o driver feche se ele foi aberto
        if browser is not None:
            try:
                browser.quit()
            except Exception:
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
            except Exception:
                pass


def launch():
    # OTIMIZAÇÃO: Carrega cache em memória no startup (only once!)
    get_commented_posts()
    
    if not os.path.isfile("visitedUsers.txt"):
        open("visitedUsers.txt", "w").close()
    max_restarts = 3
    restart_count = 0
    while restart_count < max_restarts:
        try:
            start_browser()
            break  # Success, exit the retry loop
        except Exception as e:
            msg = str(e).lower()
            if "invalid session id" in msg or "session deleted" in msg:
                restart_count += 1
                print(
                    f"\n⚠️ Invalid session id detected. Restarting browser ({restart_count}/{max_restarts})..."
                )
                try:
                    if "browser" in globals() and browser is not None:
                        try:
                            browser.quit()
                        except Exception:
                            pass
                except Exception:
                    pass
                time.sleep(2)
                if restart_count < max_restarts:
                    print("Retrying browser initialization...")
                    continue
                else:
                    print("❌ Reached max restart attempts. Aborting launch.")
                    return
            else:
                # Non-session error, just log and abort
                print(f"❌ Fatal error (non-session): {str(e)[:100]}")
                return


def is_browser_session_valid(b):
    try:
        if b is None:
            return False
        sid = getattr(b, "session_id", None)
        if not sid:
            return False
        # Perform a lightweight command to ensure session is alive
        _ = b.title
        return True
    except Exception:
        return False


if __name__ == "__main__":
    print("🤖 Bot Started.")
    try:
        # FORÇAR EXECUÇÃO IMEDIATA PARA TESTES
        print("Executando já...")
        run_extraction_process()
        print("✅ Extraction process concluído.")
        launch()  # Forçar execução do launch
        print("✅ Launch concluído com sucesso!")
    except KeyboardInterrupt:
        print("\n🛑 Parada Manual.")
        if browser:
            browser.quit()
