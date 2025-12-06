# 🤖 LinkedIn Engagement Automation Bot

A sophisticated Selenium-based automation system that autonomously builds professional networks on LinkedIn through strategic, human-like interactions while maintaining strict anti-detection protocols.

## ⚡ Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure settings in bot_v2.py (see Configuration section)
# Update: AUTO_REGULATE, TARGET_ROLES, LIMITS_CONFIG

# 3. Run the bot
python bot_v2.py

# 4. View analytics dashboard
streamlit run dashboard_app.py
```

## 📋 Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Documentation](#documentation)
- [Troubleshooting](#troubleshooting)

## ✨ Features

### 🎯 Intelligent Engagement
- **Auto-Regulation Engine**: Adapts behavior based on SSI score and days running
- **Smart Targeting**: Target specific roles and keywords in high-value connections
- **AI-Powered Comments**: Generates contextual comments using g4f (free GPT)
- **Multi-Channel Engagement**: Feed interactions, group posts, profile visits

### 🛡️ Stealth & Anti-Detection
- **Randomized Window Sizes**: Browser fingerprint variation
- **Human-Like Typing**: 4% error rate with natural keystroke delays (60-280ms)
- **Dynamic Delays**: `human_sleep()` with randomization and speed factor
- **Language Filtering**: Only engages with English content (configurable)
- **Random Browsing**: Simulates natural navigation patterns

### 📊 Analytics & Monitoring
- **Dual Database**: SQLite for real-time data + CSV for historical trends
- **SSI Tracking**: Monitor your Social Selling Index growth
- **Engagement Metrics**: Profile views, impressions, search appearances
- **Streamlit Dashboard**: 30+ visualizations with Heineken brand styling

### 🔄 Multiple Automation Modes
- **Group Automation**: Scans, likes, comments, and connects in target groups
- **Feed Interaction**: Engages with feed posts and collects profiles
- **Quick Connects**: Bypasses connection limits using search filters
- **Sniper Targeting**: Collects and priorities profiles by keywords

## 🏗️ Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────┐
│           LinkedIn Bot Architecture                  │
├─────────────────────────────────────────────────────┤
│                                                      │
│  ┌─────────────────┐        ┌──────────────────┐   │
│  │   bot_v2.py     │        │  dashboard_app   │   │
│  │   (Automation)  │───────▶│   (Analytics)    │   │
│  └────────┬────────┘        └──────────────────┘   │
│           │                                         │
│           ├──────────────┬────────────┬────────┐   │
│           │              │            │        │   │
│      ┌────▼──┐    ┌─────▼──┐  ┌────▼──┐  ┌──▼──┐ │
│      │SQLite │    │  CSV   │  │Text   │  │Edge │ │
│      │Queries│    │History │  │Files  │  │Prof │ │
│      └───────┘    └────────┘  └───────┘  └─────┘ │
│                                                    │
└────────────────────────────────────────────────────┘
```

### Data Layer
- **SQLite Databases**:
  - `bot_data.db` - Main interactions and analytics
  - `linkedin_data.db` - Alternative data store
- **CSV Archives**: `ssi_history.csv`, dated session logs in `/CSV`
- **Session Tracking**: `visitedUsers.txt`, `commentedPosts.txt`

### Processing Layer
- **Core Orchestration**: `bot_v2.py` - Manages browser lifecycle and workflows
- **Utility Scripts**: 
  - `d.py` - Profile scraper with pagination
  - `database_manager.py` - DB abstraction layer
- **AI Integration**: `g4f.client.Client` for comment generation

### Presentation Layer
- **Dashboard**: `dashboard_app.py` - Streamlit UI with 30+ plots

## 🚀 Installation

### Prerequisites
- **Python 3.7+**
- **Edge/Chromium browser** (bot uses Edge)
- **msedgedriver.exe** in project root (download from [EdgeDriver releases](https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/))

### Step-by-Step Setup

1. **Clone Repository**
   ```bash
   git clone https://github.com/casamentopedrogabi/linkedin-bot.git
   cd linkedin-bot
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv venv
   source venv/Scripts/activate  # Windows
   # or
   source venv/bin/activate      # macOS/Linux
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Download WebDriver**
   - Download `msedgedriver.exe` matching your Edge version
   - Place in project root directory

5. **Verify Setup**
   ```bash
   python -c "from selenium import webdriver; print('✓ Selenium installed')"
   ```

## ⚙️ Configuration

### Control Panel (bot_v2.py, lines 43-130)

| Setting | Type | Default | Purpose |
|---------|------|---------|---------|
| `AUTO_REGULATE` | bool | `False` | Enable adaptive behavior scaling |
| `SPEED_FACTOR` | float | `1.5` | Delay multiplier (1.5x = slower = safer) |
| `FEED_ENGLISH_ONLY` | bool | `True` | Filter non-English content |
| `AI_PERSONA` | str | "Senior Data Scientist..." | Context for AI-generated comments |
| `QUICK_CONNECT_LIMIT` | int | `10` | Max quick connects per session |
| `CONNECT_WITH_USERS` | bool | `True` | Enable connection requests |
| `SAVECSV` | bool | `True` | Log to CSV files |
| `SEND_AI_NOTE` | int | `0` | Send note with connection (1=yes, 0=no) |

### Limits Configuration

```python
# Manual mode (when AUTO_REGULATE = False)
LIMITS_CONFIG = {
    "CONNECTION": (5, 8),      # Random range per session
    "FOLLOW": (10, 15),
    "PROFILES_SCAN": (20, 30),
    "FEED_POSTS": (30, 50)
}

PROBS = {
    "FEED_LIKE": (0.20, 0.30),      # 20-30% chance per post
    "FEED_COMMENT": (0.05, 0.15),
    "GROUP_LIKE": (0.40, 0.50),
    "GROUP_COMMENT": (0.10, 0.15)
}
```

### Target Configuration

```python
# Priority keywords for engagement
HIGH_VALUE_KEYWORDS = [
    "machine learning", "data scientist", "databricks",
    "aws", "python development", # ... more keywords
]

# Roles to actively connect with
TARGET_ROLES = [
    "chief data officer", "vp of data", "lead data scientist",
    # ... more roles
]
```

## 🎮 Usage

### Launch the Bot

```bash
python bot_v2.py
```

**Expected Output:**
```
🤖 Bot Started.
Agendado para: 14:32:15
🧠 [AUTO-PILOT] Diagnóstico: 5 dias de uso | SSI Atual: 38
  -> Modo: CRUZEIRO (Estabilidade)

--- INÍCIO TEST: QUICK CONNECTS ---
[✓] 7 quick connects enviadas
--- FIM TESTE: QUICK CONNECTS ---

[1/25] Perfil: John Doe | data scientist, ml engineer
    -> [ALVO] Conectando (0/10)...
    -> [SUCCESS] Conectado. Total: 1/10
```

### View Analytics Dashboard

```bash
streamlit run dashboard_app.py
```

Accesses metrics at `http://localhost:8501` with:
- Key Performance Indicators (KPIs)
- SSI trends over time
- Engagement heatmaps
- Connection success rates
- Profile view analytics

### Run Profile Scraper

```bash
python d.py
```

Extracts LinkedIn profiles matching search criteria. Configure in `d.py`:
- `BASE_URL` - Search filters
- `START_PAGE` / `END_PAGE` - Page range
- `MAX_LIMIT` - Profile count limit

## 📚 Documentation

Complete wiki available in `/docs/wiki/`:

- **[Architecture Guide](./docs/wiki/01-ARCHITECTURE.md)** - Deep dive into system design
- **[API Reference](./docs/wiki/02-API_REFERENCE.md)** - Function signatures and examples
- **[Database Schema](./docs/wiki/03-DATABASE_SCHEMA.md)** - Table structures and queries
- **[Configuration Guide](./docs/wiki/04-CONFIGURATION.md)** - Detailed setting explanations
- **[Dashboard Guide](./docs/wiki/05-DASHBOARD_GUIDE.md)** - Analytics features
- **[Troubleshooting](./docs/wiki/06-TROUBLESHOOTING.md)** - Common issues and fixes
- **[Development Guide](./docs/wiki/07-DEVELOPMENT.md)** - Contributing and extending

## 🔧 Troubleshooting

### Common Issues

**Bot won't start - "msedgedriver.exe not found"**
```
✓ Download correct version from: https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/
✓ Place in project root
✓ Verify with: dir msedgedriver.exe (Windows) or ls msedgedriver.exe (Mac/Linux)
```

**"Invalid Session ID" error**
```
✓ Browser crashed during automation
✓ Bot auto-restarts browser and continues
✓ Check logs for activity
```

**No interactions logged**
```
✓ Check LIMITS_CONFIG values aren't 0
✓ Verify AUTO_REGULATE settings
✓ Check SQLite database: python -c "import sqlite3; sqlite3.connect('bot_data.db').cursor().execute('SELECT COUNT(*) FROM interactions').fetchone()"
```

For more help, see **[Troubleshooting Guide](./docs/wiki/06-TROUBLESHOOTING.md)**.

## 📊 Data & Privacy

- **No Personal Data Stored**: Bot only logs interaction metadata (profile URL, name, headline, timestamp)
- **Local Database**: All data stored locally in SQLite/CSV
- **Session Isolation**: Each run creates timestamped logs in `/CSV`
- **Auto-Deletion**: Old session files can be manually cleaned

## ⚖️ Legal & Ethical

This tool is for **educational purposes and network building**. Users are responsible for:
- Complying with LinkedIn's Terms of Service
- Respecting LinkedIn's rate limits and anti-bot policies
- Using authentic engagement (not spam)
- Following local laws and regulations

## 🤝 Contributing

Contributions welcome! See [Development Guide](./docs/wiki/07-DEVELOPMENT.md) for:
- Code style guidelines
- Testing procedures
- Pull request process
- Feature request process

## 📝 License

This project is provided as-is for personal use. Check LICENSE file for details.

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/casamentopedrogabi/linkedin-bot/issues)
- **Documentation**: `/docs/wiki/`
- **AI Coding Guide**: `.github/copilot-instructions.md`

---

**Last Updated**: December 6, 2025 | **Status**: Active Development
