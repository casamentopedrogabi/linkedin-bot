#!/bin/bash

# Cores para deixar bonito
GREEN='\033[0;32m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${CYAN}=========================================${NC}"
echo -e "${CYAN}   🤖 LINKEDIN BOT v2.0 - AUTO SETUP     ${NC}"
echo -e "${CYAN}=========================================${NC}"

# 1. Verificar Python
if ! command -v python &> /dev/null; then
    echo -e "${RED}❌ Python não encontrado! Instale o Python e adicione ao PATH.${NC}"
    exit 1
fi

# 2. Criar Ambiente Virtual (se não existir)
if [ ! -d "venv" ]; then
    echo -e "${GREEN}📦 Criando ambiente virtual (venv)...${NC}"
    python -m venv venv
else
    echo -e "${GREEN}✅ Ambiente virtual já existe.${NC}"
fi

# 3. Ativar Ambiente
# Tenta ativar no padrão Windows (Scripts) ou Linux (bin)
if [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
elif [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
else
    echo -e "${RED}❌ Não foi possível ativar o venv.${NC}"
    exit 1
fi

# 4. Instalar Dependências (CORRIGIDO PARA WINDOWS)
echo -e "${GREEN}⬇️  Verificando e instalando bibliotecas...${NC}"
# O comando python -m pip evita o erro de bloqueio de arquivo no Windows
python -m pip install --upgrade pip -q
python -m pip install selenium pandas g4f langdetect streamlit plotly   beautifulsoup4 webdriver-manager selenium-stealth langdetect -q matplotlib seaborn

# 5. Verificar EdgeDriver
if [ ! -f "msedgedriver.exe" ]; then
    echo -e "${RED}⚠️  AVISO CRÍTICO:${NC} O arquivo 'msedgedriver.exe' não foi encontrado nesta pasta."
    echo "   O bot não funcionará sem ele. Baixe e coloque aqui."
    echo "   (Pressione ENTER para continuar mesmo assim ou CTRL+C para sair)"
    read
fi

# 6. Inicializar Banco de Dados
echo -e "${GREEN}🗄️  Verificando Banco de Dados...${NC}"
if [ -f "database_manager.py" ]; then
    python -c "import database_manager; database_manager.init_db(); print('   -> Database conectado/criado com sucesso.')"
else
    echo -e "${RED}❌ ERRO:${NC} O arquivo 'database_manager.py' está faltando!"
    exit 1
fi

# 7. Menu de Execução
echo ""
echo "O que você deseja fazer agora?"
echo "1) 🔫 Rodar o BOT (Sniper + Group)"
echo "2) 📊 Abrir o DASHBOARD (Streamlit)"
echo "3) ❌ Sair"
echo ""
read -p "Escolha [1-3]: " opcao

case $opcao in
    1)
        echo -e "${CYAN}🚀 Iniciando Bot v2.0...${NC}"
        python bot_v2.py
        ;;
    2)
        echo -e "${CYAN}📊 Subindo Dashboard Heineken...${NC}"
        streamlit run dashboard_app.py
        ;;
    3)
        echo "Saindo. Para rodar novamente, use: ./setup.sh"
        deactivate
        exit 0
        ;;
    *)
        echo "Opção inválida."
        ;;
esac