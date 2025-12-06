# 📊 Lista Completa de Gráficos do Dashboard

## 🎯 Total: 40+ Gráficos Interativos

---

## 📍 SEÇÃO 1: KPI (4 Métricas)

```
┌─────────────────────────────────────────────┐
│ SSI Total Atual                             │ 41.0
├─────────────────────────────────────────────┤
│ Taxa de Conexão (Último Dia)                │ 0.0%
├─────────────────────────────────────────────┤
│ Total de Conexões ✨                        │ 1523
├─────────────────────────────────────────────┤
│ Followers Totais ✨                         │ 1510
└─────────────────────────────────────────────┘
```

---

## 📍 SEÇÃO 2: SSI Components (10 Gráficos)

### Plot 1: Total SSI Over Time
```
Tipo: Line Chart
Eixo X: Data
Eixo Y: Total_SSI
Cor: Dark Green
Descrição: Evolução do SSI total ao longo do tempo
```

### Plot 2: SSI Increase Daily ✨
```
Tipo: Line Chart
Eixo X: Data
Eixo Y: SSI_Increase
Cor: Lime Green
Descrição: Aumento diário de SSI
```

### Plots 3-4: Brand Component
```
Tipo: Line Chart + Scatter (Correlação)
Eixo X: Data / Brand Score
Eixo Y: Brand Score / Total SSI
Cor: Lime Green / Red
Descrição: Componente de marca e impacto no SSI
```

### Plots 5-6: People Component
```
Tipo: Line Chart + Scatter
Eixo X: Data / People Score
Eixo Y: People Score / Total SSI
Cor: Lime Green / Red
Descrição: Componente de redes e impacto
```

### Plots 7-8: Insights Component
```
Tipo: Line Chart + Scatter
Eixo X: Data / Insights Score
Eixo Y: Insights Score / Total SSI
Cor: Lime Green / Red
Descrição: Componente de insights e impacto
```

### Plots 9-10: Relationships Component
```
Tipo: Line Chart + Scatter
Eixo X: Data / Relationships Score
Eixo Y: Relationships Score / Total SSI
Cor: Lime Green / Red
Descrição: Componente de relacionamentos e impacto
```

---

## 📍 SEÇÃO 3: Interaction Metrics (8 Gráficos)

### Plots 11-12: Connection Limit
```
Tipo: Line Chart + Scatter
Eixo X: Data / Connection Limit
Eixo Y: Connection Limit / Total SSI
Cor: Medium Dark Green / Red
Descrição: Limite dinâmico de conexões
```

### Plots 13-14: Follow Limit
```
Tipo: Line Chart + Scatter
Eixo X: Data / Follow Limit
Eixo Y: Follow Limit / Total SSI
Cor: Medium Dark Green / Red
Descrição: Limite dinâmico de follows
```

### Plots 15-16: Profiles to Scan
```
Tipo: Line Chart + Scatter
Eixo X: Data / Profiles to Scan
Eixo Y: Profiles to Scan / Total SSI
Cor: Medium Dark Green / Red
Descrição: Meta de perfis a varrer
```

### Plots 17-18: Feed Posts Limit
```
Tipo: Line Chart + Scatter
Eixo X: Data / Feed Posts Limit
Eixo Y: Feed Posts Limit / Total SSI
Cor: Medium Dark Green / Red
Descrição: Limite de posts do feed para engajar
```

---

## 📍 SEÇÃO 3B: Conexões & Followers ✨ NOVO (4 Gráficos)

### Plot 19: Total Connections Over Time ✨
```
Tipo: Line Chart
Eixo X: Data
Eixo Y: Total_Connections
Cor: Dark Green
Descrição: Histórico acumulado de conexões
Novo: SIM - Métrica crítica que faltava
```

### Plot 20: New Connections Accepted Per Day ✨
```
Tipo: Line Chart
Eixo X: Data
Eixo Y: New_Connections_Accepted
Cor: Lime Green
Descrição: Quantas conexões foram aceitas por dia
Novo: SIM - Métrica de conversão importante
```

### Plot 21: Total Followers Over Time ✨
```
Tipo: Line Chart
Eixo X: Data
Eixo Y: Total_Followers
Cor: Red
Descrição: Histórico acumulado de followers
Novo: SIM - Métr

ica de alcance
```

### Plot 22: Conexões vs SSI (Correlação) ✨
```
Tipo: Scatter Chart
Eixo X: Total Connections
Eixo Y: Total SSI
Cor: Red
Descrição: Impacto de conexões no SSI
Novo: SIM - Análise de causalidade
```

---

## 📍 SEÇÃO 4: Probability Metrics (6 Gráficos)

### Plot 23: Group Like Probability
```
Tipo: Line Chart
Eixo X: Data
Eixo Y: Group_Like_Prob
Cor: Lime Green
Descrição: Probabilidade de dar like em posts de grupo
```

### Plot 24: Group Comment Probability
```
Tipo: Line Chart
Eixo X: Data
Eixo Y: Group_Comment_Prob
Cor: Red
Descrição: Probabilidade de comentar em posts de grupo
```

### Plot 25: Feed Like Probability
```
Tipo: Line Chart
Eixo X: Data
Eixo Y: Feed_Like_Prob
Cor: Medium Dark Green
Descrição: Probabilidade de dar like no feed
```

### Plot 26: Feed Comment Probability
```
Tipo: Line Chart
Eixo X: Data
Eixo Y: Feed_Comment_Prob
Cor: Dark Green
Descrição: Probabilidade de comentar no feed
```

### Plot 27: SSI Increase vs Group Comments (Correlação)
```
Tipo: Scatter Chart
Eixo X: Group_Comment_Prob
Eixo Y: SSI_Increase
Cor: Red
Descrição: Impacto de comentários em grupo no SSI
```

### Plot 28: SSI Increase vs Feed Likes (Correlação)
```
Tipo: Scatter Chart
Eixo X: Feed_Like_Prob
Eixo Y: SSI_Increase
Cor: Red
Descrição: Impacto de likes no feed no SSI
```

---

## 📍 SEÇÃO 4B: Parâmetros Operacionais ✨ NOVO (4 Gráficos)

### Plot 29: Speed Factor Over Time ✨
```
Tipo: Line Chart
Eixo X: Data
Eixo Y: Speed_Factor
Cor: Medium Dark Green
Descrição: Fator de velocidade (1.5 = 50% mais rápido)
Novo: SIM - Métrica de performance
```

### Plot 30: Withdrawn Count Over Time ✨
```
Tipo: Line Chart
Eixo X: Data
Eixo Y: Withdrawn_Count
Cor: Red
Descrição: Convites retirados (limpeza de SSI)
Novo: SIM - Métrica de manutenção
```

### Plot 31: Speed Factor vs Total SSI (Correlação) ✨
```
Tipo: Scatter Chart
Eixo X: Speed_Factor
Eixo Y: Total_SSI
Cor: Red
Descrição: Impacto da velocidade no SSI
Novo: SIM - Análise de otimização
```

### Plot 32: Withdrawn Count vs Total SSI (Correlação) ✨
```
Tipo: Scatter Chart
Eixo X: Withdrawn_Count
Eixo Y: Total_SSI
Cor: Red
Descrição: Impacto de convites retirados no SSI
Novo: SIM - Análise de estratégia
```

---

## 📍 SEÇÃO 5: Engagement & Conversion Analysis (10+ Gráficos)

### Plot 33: Total Attempts Per Day
```
Tipo: Line Chart
Eixo X: Data
Eixo Y: Total Attempts
Cor: Dark Green
Descrição: Tentativas de conexão/follow por dia
```

### Plot 34: Connections Sent Per Day
```
Tipo: Line Chart
Eixo X: Data
Eixo Y: Connections Sent
Cor: Lime Green
Descrição: Convites de conexão enviados por dia
```

### Plot 35: Daily Conversion Rate (%)
```
Tipo: Line Chart
Eixo X: Data
Eixo Y: Conversion Rate
Cor: Red
Descrição: Taxa de conversão de tentativas para conexões
```

### Plot 36: Connections vs Total SSI (Correlação)
```
Tipo: Scatter Chart
Eixo X: Connections
Eixo Y: Total_SSI
Cor: Red
Descrição: Impacto de conexões no SSI
```

### Plot 37: Interactions by Source (Bar Chart)
```
Tipo: Bar Chart
Eixo X: Source (Sniper, Group, Reciprocator, etc)
Eixo Y: Count
Cor: Dark Green
Descrição: Distribuição de interações por origem
```

### Plot 38: Top 5 Target Roles
```
Tipo: Bar Chart
Eixo X: Role (headline)
Eixo Y: Count
Cor: Medium Dark Green
Descrição: Roles mais encontradas
```

### Plot 39: Profile Views (Dashboard Analytics)
```
Tipo: Line Chart
Eixo X: Data
Eixo Y: Profile Views
Cor: Lime Green
Descrição: Visualizações de perfil ao longo do tempo
```

### Plot 40: Post Impressions (Dashboard Analytics)
```
Tipo: Line Chart
Eixo X: Data
Eixo Y: Post Impressions
Cor: Dark Green
Descrição: Impressões de posts ao longo do tempo
```

### Plot 41: Total SSI vs Profile Views (Correlação)
```
Tipo: Scatter Chart
Eixo X: Profile Views
Eixo Y: Total_SSI
Cor: Red
Descrição: Impacto de views no SSI
```

### Plot 42: SSI Increase vs Post Impressions (Correlação)
```
Tipo: Scatter Chart
Eixo X: Post Impressions
Eixo Y: SSI_Increase
Cor: Red
Descrição: Impacto de impressões no crescimento de SSI
```

---

## 📊 Resumo Estatístico

```
Total de Gráficos:              42+
├─ Line Charts (Trend):         18
├─ Scatter Charts (Correlação): 12
├─ Bar Charts (Distribuição):   2
├─ KPI Cards (Métricas):        4
└─ Mixed (diferentes tipos):    6

Cores Heineken Usadas:
├─ Dark Green (#286529):        12 gráficos
├─ Lime Green (#8ebf48):        10 gráficos
├─ Red (#ca2819):               14 gráficos (correlações)
├─ Medium Dark Green (#527832): 6 gráficos
└─ Off White (#f2f2f1):         Background

Seções Principais:             6
├─ KPIs:                        1
├─ SSI Components:             2
├─ Interaction Metrics:        2
├─ Probabilidades:             1
├─ Parâmetros Operacionais:    1 ✨
└─ Engagement & Conversion:    1

Novos Gráficos ✨:             12
├─ SSI_Increase:               1
├─ Total_Connections:          2 (line + correlation)
├─ Total_Followers:            2 (line + correlation)
├─ New_Connections_Accepted:   1
├─ Speed_Factor:               2 (line + correlation)
└─ Withdrawn_Count:            2 (line + correlation)
```

---

## 🎨 Paleta de Cores por Tipo

| Tipo de Gráfico | Cor Principal | Cor Secundária |
|-----------------|---------------|----------------|
| SSI Trends | Dark Green | - |
| Componentes | Lime Green | - |
| Limites | Medium Dark Green | - |
| Probabilidades | Lime Green + Red | - |
| Correlações | Red | - |
| Analytics | Lime Green + Dark Green | - |
| Operacional | Medium Dark Green + Red | - |

---

## 🚀 Como Explorar

1. **Começar pelos KPIs** - Visão geral rápida
2. **SSI Components** - Entender cada componente
3. **Interaction Metrics** - Ver limites dinâmicos
4. **Conexões & Followers** - Acompanhar crescimento
5. **Probabilidades** - Análise de engajamento
6. **Operacionais** - Otimizar velocidade
7. **Engagement** - Analisar conversão

---

**Dashboard Completo e Pronto! 🎉**
