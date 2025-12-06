#!/bin/bash

# Script para rodar o Dashboard do LinkedIn Bot (Estrutura Reorganizada)

echo "🎨 Iniciando o Dashboard do LinkedIn Bot..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 O dashboard será aberto em: http://localhost:8501"
echo ""
echo "✨ Recursos disponíveis:"
cd "$(dirname "$0")/app"
streamlit run dashboard_app.py
echo "   • 40+ gráficos interativos"
echo "   • Métricas de SSI completas"
echo "   • Análise de conexões e followers"
echo "   • Parâmetros operacionais (Speed Factor, Withdrawn Count)"
echo "   • Taxa de conversão e engajamento"
echo ""
echo "⚠️  Pressione CTRL+C para sair"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

streamlit run dashboard_app.py
