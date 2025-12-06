# 📁 Estrutura de Diretórios - LinkedIn Bot

```
linkedin-bot/
├── 📁 src/                     # Código Python principal
│   ├── bot_v2.py              # Bot principal com automação Selenium
│   ├── d.py                    # Script de scraping de perfis
│   └── database_manager.py     # Gerenciador de banco de dados
│
├── 📁 app/                     # Aplicação Streamlit
│   ├── dashboard_app.py        # Dashboard de analytics (NOVO - Seções 5 & 6)
│   └── dashboard_app_old.py    # Versão anterior (backup)
│
├── 📁 data/                    # Dados e configurações
│   ├── bot_data.db             # Banco SQLite - interactions, profile_analytics
│   ├── linkedin_data.db        # Banco SQLite alternativo
│   ├── ssi_history.csv         # Histórico de SSI por dia
│   ├── links_coletados.txt     # Links de perfis coletados
│   ├── links_limpos.txt        # Links processados
│   ├── visitedUsers.txt        # Log de perfis visitados
│   ├── commentedPosts.txt      # Log de posts comentados (gerado em runtime)
│   └── 📁 CSV/                 # Logs de sessão por data (GroupBot-HH-MM-SS.csv)
│
├── 📁 logs/                    # Logs e registros
│   └── (Gerados em runtime)
│
├── 📁 docs/                    # Documentação
│   ├── DASHBOARD_SUMMARY.md
│   ├── COMPLETION_REPORT.md
│   └── 📁 wiki/
│
├── 📁 __pycache__/             # Cache Python (ignorado no Git)
├── 📁 perfil_robo_edge/        # Perfil Edge (ignorado no Git)
├── 📁 venv/                    # Ambiente virtual (ignorado no Git)
│
├── 📄 requirements.txt          # Dependências Python
├── 📄 setup.sh                  # Script de inicialização
├── 📄 run_dashboard.sh          # Script para rodar dashboard
├── 📄 README.md                 # Documentação principal
└── 📄 STRUCTURE.md              # Este arquivo
```

## 🔄 Como o Bot Usa os Diretórios

### Execução do Bot (src/bot_v2.py)
1. **Lê de:** `data/ssi_history.csv` - Histórico SSI
2. **Escreve para:** 
   - `data/bot_data.db` - Interações e métricas
   - `data/visitedUsers.txt` - Perfis visitados
   - `data/CSV/GroupBot-HH-MM-SS.csv` - Log da sessão
   - `data/commentedPosts.txt` - Posts comentados (runtime)
3. **Logs:** `logs/` (se configurado)

### Execução do Dashboard (app/dashboard_app.py)
1. **Lê de:**
   - `data/bot_data.db` (tabelas: interactions, profile_analytics)
   - `data/ssi_history.csv` (histórico SSI)
2. **Exibe:** 48+ gráficos com análises em tempo real

### Script de Scraping (src/d.py)
1. **Entrada:** URLs de busca LinkedIn configuráveis
2. **Saída:** `data/links_coletados.txt`, `data/CSV/`

## 💾 Banco de Dados

### profile_analytics (bot_data.db)
```
timestamp         | profile_views | post_impressions | followers | 
feed_comments     | group_comments | feed_likes | group_likes
```

**Novos campos (v2.0):**
- `feed_comments` - Comentários feitos no feed por sessão
- `group_comments` - Comentários feitos em grupos por sessão
- `feed_likes` - Likes dados no feed por sessão
- `group_likes` - Likes dados em grupos por sessão

## 🚀 Como Rodar

### Bot Principal
```bash
cd src
python bot_v2.py
```

### Dashboard
```bash
cd app
streamlit run dashboard_app.py
```

### Script de Scraping
```bash
cd src
python d.py
```

## 📊 Arquivos de Dados por Tipo

| Tipo | Local | Frequência | Função |
|------|-------|-----------|--------|
| **Banco SQL** | `data/*.db` | Contínua | Analytics, interactions |
| **CSV SSI** | `data/ssi_history.csv` | Diária | Histórico tendências |
| **Logs Sessão** | `data/CSV/*.csv` | Por sessão | Detalhes de cada execução |
| **Texto** | `data/*.txt` | Contínua | Rastreamento rápido |

## 🔒 Segurança & Backup

- `data/CSV/` - 50+ arquivos de sesão (auto-gerados)
- `perfil_robo_edge/` - Credenciais do navegador (NÃO versionar)
- `venv/` - Ambiente virtual (NÃO versionar)
- `.gitignore` deve ignorar: `venv/`, `__pycache__/`, `perfil_robo_edge/`, `*.pyc`

## 📈 Crescimento de Dados

Estimativa mensal (com execução diária):
- `bot_data.db`: ~2-5 MB
- `ssi_history.csv`: ~50 KB
- `CSV/logs/`: ~20-30 CSV files (~500KB total)
- Total: ~5-10 MB

---

**Atualizado:** Dec 6, 2025 | **Versão:** 2.0 (Reorganização + Novas Métricas)
