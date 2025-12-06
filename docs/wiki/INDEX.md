# 📚 Documentation Wiki Index

Complete guide to all documentation for the LinkedIn Engagement Automation Bot.

---

## 📖 Documentation Structure

### Main Documentation Files

**[README.md](../README.md)** - Project Overview
- Quick start guide
- Feature summary
- Installation steps
- Basic usage

---

### Wiki Pages

1. **[01-ARCHITECTURE.md](./01-ARCHITECTURE.md)** - System Design
   - High-level data flow
   - Component architecture
   - Auto-regulation engine
   - Database strategy
   - **Read this if**: You want to understand how the bot works internally

2. **[02-API_REFERENCE.md](./02-API_REFERENCE.md)** - Function Reference
   - Every public function documented
   - Parameter descriptions
   - Return values & examples
   - Usage patterns
   - **Read this if**: You're extending the bot or calling functions

3. **[03-DATABASE_SCHEMA.md](./03-DATABASE_SCHEMA.md)** - Data Structures
   - SQLite table schemas
   - Column descriptions
   - Useful queries
   - Backup & archival
   - **Read this if**: You need to query or modify data

4. **[04-CONFIGURATION.md](./04-CONFIGURATION.md)** - Configuration Guide
   - All settings explained
   - Configuration examples
   - Preset profiles (aggressive, balanced, conservative)
   - Common mistakes
   - **Read this if**: You want to customize bot behavior

5. **[05-DASHBOARD_GUIDE.md](./05-DASHBOARD_GUIDE.md)** - Analytics Dashboard
   - Dashboard features
   - KPIs and charts
   - Customization
   - Performance tips
   - **Read this if**: You want to monitor bot performance or add metrics

6. **[06-TROUBLESHOOTING.md](./06-TROUBLESHOOTING.md)** - Problem Solving
   - Common issues & solutions
   - Installation errors
   - Runtime problems
   - Debugging techniques
   - **Read this if**: Something isn't working

7. **[07-DEVELOPMENT.md](./07-DEVELOPMENT.md)** - Contributing Guide
   - Code style guidelines
   - Adding new features
   - Testing procedures
   - Git workflow
   - **Read this if**: You're contributing or extending features

8. **[08-EXAMPLES_SCENARIOS.md](./08-EXAMPLES_SCENARIOS.md)** - Real-World Use Cases
   - 7+ complete scenarios
   - Configuration presets
   - Expected results
   - A/B testing examples
   - **Read this if**: You want ready-to-use configurations

---

## 🎯 Quick Navigation by Goal

### Getting Started
1. Read: [README.md](../README.md) - Quick start
2. Install: Follow setup steps
3. Configure: Use [04-CONFIGURATION.md](./04-CONFIGURATION.md) → "Example: Balanced Mode"
4. Run: `python bot_v2.py`

### Understanding How It Works
1. Read: [01-ARCHITECTURE.md](./01-ARCHITECTURE.md) - System overview
2. Explore: [02-API_REFERENCE.md](./02-API_REFERENCE.md) - Key functions
3. Query: [03-DATABASE_SCHEMA.md](./03-DATABASE_SCHEMA.md) - Data model

### Customizing Behavior
1. Reference: [04-CONFIGURATION.md](./04-CONFIGURATION.md) - All settings
2. Example: [08-EXAMPLES_SCENARIOS.md](./08-EXAMPLES_SCENARIOS.md) - Copy preset
3. Extend: [07-DEVELOPMENT.md](./07-DEVELOPMENT.md) - Add features

### Monitoring & Analyzing
1. Launch: [05-DASHBOARD_GUIDE.md](./05-DASHBOARD_GUIDE.md) - Dashboard setup
2. Query: [03-DATABASE_SCHEMA.md](./03-DATABASE_SCHEMA.md) - Write SQL
3. Track: Export data and analyze trends

### Solving Problems
1. Check: [06-TROUBLESHOOTING.md](./06-TROUBLESHOOTING.md) - Find your issue
2. Debug: Use query commands to inspect state
3. Test: Reduce limits and try again

### Contributing Code
1. Read: [07-DEVELOPMENT.md](./07-DEVELOPMENT.md) - Style & workflow
2. Test: Unit and integration test examples
3. Review: Checklist before submitting

---

## 📊 Key Concepts

### Operational Modes
Bot automatically scales behavior through 4 modes:
- **AQUECIMENTO** (Days 0-3): Low profile, safety-first
- **CRESCIMENTO** (3-14 days): Moderate engagement
- **CRUZEIRO** (14+ days, SSI < 40): Stable, sustainable
- **ELITE** (SSI > 40): High-volume networking

**Learn more**: [01-ARCHITECTURE.md → Auto-Regulation Engine](./01-ARCHITECTURE.md#2-auto-regulation-engine)

### Stealth Mechanisms
Bot appears human through:
- Randomized browser fingerprint
- Human-like typing with errors
- Variable delays and mouse movements
- Language detection for content
- Long pauses simulating profile reading

**Learn more**: [01-ARCHITECTURE.md → Stealth Layer](./01-ARCHITECTURE.md#4-stealth-layer)

### Data Dual Strategy
Stores data in two places:
- **SQLite**: Current state, real-time queries
- **CSV**: Historical trends, dashboard charting

**Learn more**: [01-ARCHITECTURE.md → Database Layer](./01-ARCHITECTURE.md#3-database-layer)

### Session Limits
Each run uses random ranges:
- Connections: 5-8 per session (configurable)
- Follows: 10-15 per session
- Profiles scanned: 20-30 (limits visits)
- Engagement rate: 30-50% of posts

**Learn more**: [04-CONFIGURATION.md → Limit Configuration](./04-CONFIGURATION.md#manual-limits-limits_config)

---

## 🔍 Commonly Referenced Files

### Code Files
- **bot_v2.py** - Main automation engine (~2100 lines)
- **dashboard_app.py** - Streamlit analytics UI
- **database_manager.py** - Database utilities
- **d.py** - Profile scraper

### Data Files
- **bot_data.db** - SQLite database (interactions, analytics)
- **ssi_history.csv** - Historical SSI scores
- **CSV/** - Timestamped session logs
- **visitedUsers.txt** - Fallback profile tracking

---

## 📋 Configuration Presets

Quick copy-paste configurations for common scenarios:

### Aggressive Growth (30 days, 100+ connections)
```python
AUTO_REGULATE = True
SPEED_FACTOR = 1.0
LIMITS_CONFIG = {"CONNECTION": (15, 20), ...}
SEND_AI_NOTE = 1
```
**Details**: [08-EXAMPLES_SCENARIOS.md → Scenario 1](./08-EXAMPLES_SCENARIOS.md#scenario-1-building-ssi-fast-aggressive-growth)

### Conservative Stealth (Slow steady growth)
```python
AUTO_REGULATE = True
SPEED_FACTOR = 2.5
LIMITS_CONFIG = {"CONNECTION": (2, 3), ...}
```
**Details**: [08-EXAMPLES_SCENARIOS.md → Scenario 2](./08-EXAMPLES_SCENARIOS.md#scenario-2-sustainable-networking-conservative)

### High-Value Targeting (Quality over quantity)
```python
LIMITS_CONFIG = {"CONNECTION": (3, 5), ...}
TARGET_ROLES = ["chief data officer", "vp of data", ...]
SEND_AI_NOTE = 1
```
**Details**: [08-EXAMPLES_SCENARIOS.md → Scenario 3](./08-EXAMPLES_SCENARIOS.md#scenario-3-targeted-high-value-connections-only)

**More presets**: See [08-EXAMPLES_SCENARIOS.md](./08-EXAMPLES_SCENARIOS.md)

---

## 🛠️ Common Tasks

### "How do I run the bot?"
→ [README.md → Usage](../README.md#usage) or [04-CONFIGURATION.md → Getting Started](./04-CONFIGURATION.md#next-steps)

### "How do I see results?"
→ [05-DASHBOARD_GUIDE.md → Dashboard Overview](./05-DASHBOARD_GUIDE.md#dashboard-overview)

### "How do I change the bot's behavior?"
→ [04-CONFIGURATION.md](./04-CONFIGURATION.md)

### "What's in the database?"
→ [03-DATABASE_SCHEMA.md](./03-DATABASE_SCHEMA.md)

### "How do I add a new feature?"
→ [07-DEVELOPMENT.md → Adding New Features](./07-DEVELOPMENT.md#adding-new-features)

### "How do I fix an error?"
→ [06-TROUBLESHOOTING.md](./06-TROUBLESHOOTING.md)

### "What's the best configuration for my goal?"
→ [08-EXAMPLES_SCENARIOS.md](./08-EXAMPLES_SCENARIOS.md)

### "How does the bot work internally?"
→ [01-ARCHITECTURE.md](./01-ARCHITECTURE.md)

---

## 📝 Glossary

| Term | Definition | Learn More |
|------|-----------|-----------|
| **SSI** | Social Selling Index - LinkedIn's measure of profile quality (0-100) | [02-API_REFERENCE.md](./02-API_REFERENCE.md) |
| **AQUECIMENTO** | Warm-up mode for new accounts (Days 0-3) | [01-ARCHITECTURE.md](./01-ARCHITECTURE.md) |
| **CRESCIMENTO** | Growth phase (Days 3-14) | [01-ARCHITECTURE.md](./01-ARCHITECTURE.md) |
| **CRUZEIRO** | Cruise phase - stable sustainable behavior | [01-ARCHITECTURE.md](./01-ARCHITECTURE.md) |
| **ELITE** | High-volume mode for influencers (SSI > 40) | [01-ARCHITECTURE.md](./01-ARCHITECTURE.md) |
| **SPEED_FACTOR** | Multiplier for all delays (1.5 = 1.5x slower) | [04-CONFIGURATION.md](./04-CONFIGURATION.md) |
| **TARGET_ROLES** | LinkedIn headline keywords to prioritize | [04-CONFIGURATION.md](./04-CONFIGURATION.md) |
| **Stealth** | Anti-detection mechanisms | [01-ARCHITECTURE.md](./01-ARCHITECTURE.md) |
| **Human Sleep** | Randomized delay function (never use bare time.sleep) | [02-API_REFERENCE.md](./02-API_REFERENCE.md) |

---

## 🚀 Getting Help

1. **Check Documentation First**
   - Search this wiki for keywords
   - Use Quick Navigation (above) to jump to topic
   - Review Examples Scenarios for similar use case

2. **Consult Troubleshooting**
   - [06-TROUBLESHOOTING.md](./06-TROUBLESHOOTING.md) covers 20+ issues
   - Includes debug queries and solutions

3. **Review Code Examples**
   - [02-API_REFERENCE.md](./02-API_REFERENCE.md) has function examples
   - [07-DEVELOPMENT.md](./07-DEVELOPMENT.md) has extension examples
   - [08-EXAMPLES_SCENARIOS.md](./08-EXAMPLES_SCENARIOS.md) has real workflows

4. **Query Your Data**
   - [03-DATABASE_SCHEMA.md](./03-DATABASE_SCHEMA.md) has useful SQL queries
   - Run queries to debug state: `sqlite3 bot_data.db "SELECT ..."`

---

## 📦 What's Included

✅ Complete automation bot  
✅ Streamlit analytics dashboard  
✅ SQLite database with historical data  
✅ CSV session logging  
✅ Configuration presets  
✅ 8 wiki pages (this documentation)  
✅ API reference  
✅ Troubleshooting guide  
✅ Development guide  
✅ Real-world examples  

---

## 🔄 Documentation Updates

This wiki is actively maintained. Check [README.md](../README.md) for "Last Updated" date.

**Last Updated**: December 6, 2025

---

## 📞 Quick Links

- **GitHub**: https://github.com/casamentopedrogabi/linkedin-bot
- **Project Root**: `../README.md`
- **AI Coding Guide**: `../.github/copilot-instructions.md`
- **Configuration Examples**: `./04-CONFIGURATION.md`
- **Real Scenarios**: `./08-EXAMPLES_SCENARIOS.md`

---

**Happy automating! 🚀**
