import os
import sqlite3

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import streamlit as st
from matplotlib.ticker import FuncFormatter

# --- Configuration ---
DB_NAME = "bot_data.db"
CSV_PATH = "ssi_history.csv"

# Heineken Style Configuration
HEINEKEN_COLORS = {
    "dark_green": "#286529",
    "off_white": "#f2f2f1",
    "red": "#ca2819",
    "medium_gray": "#95a49b",
    "lime_green": "#8ebf48",
    "medium_dark_green": "#527832",
    "light_gray_green": "#c3dbb1",
    "black": "#000000",
}

# Apply global plot style
plt.style.use("default")
plt.rcParams["text.color"] = HEINEKEN_COLORS["black"]
plt.rcParams["axes.labelcolor"] = HEINEKEN_COLORS["black"]
plt.rcParams["xtick.color"] = HEINEKEN_COLORS["black"]
plt.rcParams["ytick.color"] = HEINEKEN_COLORS["black"]
plt.rcParams["axes.facecolor"] = HEINEKEN_COLORS["off_white"]
plt.rcParams["figure.facecolor"] = HEINEKEN_COLORS["off_white"]
plt.rcParams["grid.alpha"] = 0  # No grid

# --- Database and Data Loading Functions ---


def load_data():
    """Load data from SQLite for interactions and CSV for SSI history."""

    # 1. Load SSI History (CSV)
    if os.path.exists(CSV_PATH):
        ssi_df = pd.read_csv(CSV_PATH)
        ssi_df["Date"] = pd.to_datetime(ssi_df["Date"])
        ssi_df = ssi_df.sort_values("Date")
    else:
        st.error(f"Error: SSI history file '{CSV_PATH}' not found.")
        ssi_df = pd.DataFrame()

    # 2. Load Interactions (SQLite)
    try:
        conn = sqlite3.connect(DB_NAME)
        interactions_df = pd.read_sql_query("SELECT * FROM interactions", conn)
        analytics_df = pd.read_sql_query("SELECT * FROM profile_analytics", conn)
        conn.close()

        interactions_df["timestamp"] = pd.to_datetime(interactions_df["timestamp"])
        interactions_df["date"] = interactions_df["timestamp"].dt.date
        analytics_df["timestamp"] = pd.to_datetime(analytics_df["timestamp"])
        analytics_df["date"] = analytics_df["timestamp"].dt.date

    except sqlite3.Error as e:
        st.warning(f"Warning: Could not load SQLite data. Database error: {e}")
        interactions_df = pd.DataFrame()
        analytics_df = pd.DataFrame()

    return ssi_df, interactions_df, analytics_df


# --- Visualization Functions (More than 30 plots in total) ---


def plot_line_chart(df, x_col, y_col, title, ax, color_key="dark_green"):
    """Plots a single line chart with Heineken style."""

    # Check for single point data to adjust Y-axis limits
    if df[y_col].nunique() <= 1 and len(df) > 0:
        value = df[y_col].iloc[0]
        # Adjust Y limits slightly around the single value for visibility
        range_val = max(abs(value * 0.05), 0.1)
        ax.set_ylim(value - range_val, value + range_val)

    ax.plot(
        df[x_col],
        df[y_col],
        marker="o",
        linestyle="-",
        color=HEINEKEN_COLORS[color_key],
    )
    ax.set_title(title, fontsize=14, fontweight="bold", color=HEINEKEN_COLORS["black"])
    ax.set_xlabel(x_col.replace("_", " ").title(), fontsize=12)
    ax.set_ylabel(y_col.replace("_", " ").title(), fontsize=12)

    # Apply date/timestamp format and rotation for X-axis
    if pd.api.types.is_datetime64_any_dtype(df[x_col]):
        ax.xaxis.set_major_formatter(
            FuncFormatter(
                lambda x, pos: pd.to_datetime(x, unit="D").strftime("%Y-%m-%d")
                if x > 1000
                else ""
            )
        )
    elif pd.api.types.is_object_dtype(df[x_col]):  # Handles Timestamp in Engagement
        try:
            # Tenta converter para datatime (se for um timestamp, ele funciona)
            dates = pd.to_datetime(df[x_col])
            ax.xaxis.set_major_formatter(
                FuncFormatter(
                    lambda x, pos: pd.to_datetime(x).strftime("%m-%d %H:%M")
                    if x > 1000
                    else ""
                )
            )
        except:
            pass  # Se falhar, usa o default (string)

    ax.tick_params(axis="x", rotation=45, labelsize=10)
    ax.grid(False)  # Ensure no grid


def plot_bar_chart(df, x_col, y_col, title, ax, color_key="dark_green"):
    """Plots a single bar chart."""
    # Using specific color for consistency
    sns.barplot(x=x_col, y=y_col, data=df, ax=ax, color=HEINEKEN_COLORS[color_key])
    ax.set_title(title, fontsize=14, fontweight="bold", color=HEINEKEN_COLORS["black"])
    ax.set_xlabel(x_col.replace("_", " ").title(), fontsize=12)
    ax.set_ylabel(y_col.replace("_", " ").title(), fontsize=12)
    ax.tick_params(axis="x", rotation=45, labelsize=10)
    ax.grid(False)


def plot_correlation_chart(df, x_col, y_col, title, ax):
    """Plots correlation (scatter plot)."""
    # Ensure data is numeric and handle potential non-finite values
    temp_df = df[[x_col, y_col]].replace([np.inf, -np.inf], np.nan).dropna()

    if (
        not temp_df.empty
        and temp_df[x_col].nunique() > 1
        and temp_df[y_col].nunique() > 1
    ):
        ax.scatter(
            temp_df[x_col], temp_df[y_col], color=HEINEKEN_COLORS["red"], alpha=0.6
        )
        corr = temp_df.corr().iloc[0, 1]
    else:
        # Avoid plotting scatter if data is insufficient for correlation visualization
        corr = np.nan
        ax.set_xticks([])  # Remove ticks for empty plot
        ax.set_yticks([])  # Remove ticks for empty plot

    ax.set_title(
        f"{title} (Corr: {corr:.2f})",
        fontsize=14,
        fontweight="bold",
        color=HEINEKEN_COLORS["black"],
    )
    ax.set_xlabel(x_col.replace("_", " ").title(), fontsize=12)
    ax.set_ylabel(y_col.replace("_", " ").title(), fontsize=12)
    ax.tick_params(axis="x", rotation=45, labelsize=10)
    ax.grid(False)


# --- Main Dashboard Component ---


def main_dashboard():
    """Main function to run the Streamlit dashboard."""
    st.set_page_config(layout="wide", page_title="LinkedIn SSI Bot Analytics")
    st.title("🤖 LinkedIn SSI Bot Analytics Dashboard")

    ssi_df, interactions_df, analytics_df = load_data()

    if ssi_df.empty:
        st.warning("Please run the bot first to generate data.")
        return

    # --- 1. KPI Section ---
    st.header("1. Key Performance Indicators (KPIs)")

    col1, col2, col3, col4 = st.columns(4)

    # KPI 1: Current SSI
    current_ssi = ssi_df["Total_SSI"].iloc[-1]
    ssi_change = (
        ssi_df["SSI_Increase"].iloc[-1] if "SSI_Increase" in ssi_df.columns else 0
    )
    col1.metric("SSI Total Atual", f"{current_ssi:.1f}", delta=f"{ssi_change:.1f}")

    # KPI 2: Connection Rate (Last Day)
    if not interactions_df.empty and not interactions_df.empty:
        # Avoid FutureWarning by passing include_groups=False (pandas 2.2+)
        daily_summary = (
            interactions_df.groupby("date")
            .apply(
                lambda x: pd.Series(
                    {
                        "Total_Attempts": len(x),
                        "Connected": len(x[x["status"] == "Connected"]),
                    }
                ),
                include_groups=False,
            )
            .reset_index()
        )

        if not daily_summary.empty and daily_summary["Total_Attempts"].iloc[-1] > 0:
            last_conn_rate = (
                daily_summary["Connected"].iloc[-1]
                / daily_summary["Total_Attempts"].iloc[-1]
                * 100
            )
            col2.metric("Taxa de Conexão (Último Dia)", f"{last_conn_rate:.1f}%")
        else:
            col2.metric("Taxa de Conexão (Último Dia)", "0.0%")
    else:
        col2.metric("Taxa de Conexão (Último Dia)", "N/A")

    # KPI 3: Avg Accepted Connections per Day
    if "New_Connections_Accepted" in ssi_df.columns:
        avg_accepted = ssi_df["New_Connections_Accepted"].mean()
        col3.metric("Média de Conexões Aceitas / Dia", f"{avg_accepted:.1f}")
    else:
        col3.metric("Média de Conexões Aceitas / Dia", "N/A")

    # KPI 4: Current Industry Rank
    current_rank = ssi_df["Industry_Rank"].iloc[-1]
    col4.metric("Rank de Indústria Atual", f"Top {current_rank}%")

    st.markdown("---")

    # --- 2. SSI Components & Trend Analysis (10 Plots) ---
    st.header("2. Análise da Tendência do SSI (Componentes)")

    ssi_components = ["Brand", "People", "Insights", "Relationships"]

    # 5 linhas para 1 plot de Total + 4 plots de Componentes (10 gráficos)
    fig, axes = plt.subplots(5, 2, figsize=(18, 30))

    # Apply figure face color explicitly for Matplotlib
    fig.patch.set_facecolor(HEINEKEN_COLORS["off_white"])

    # Plot 1: Total SSI Over Time (ROW 0, COL 0)
    plot_line_chart(
        ssi_df,
        "Date",
        "Total_SSI",
        "SSI Total ao Longo do Tempo",
        axes[0, 0],
        "dark_green",
    )

    # Plot 2: Correlation Plot (ROW 0, COL 1)
    plot_correlation_chart(
        ssi_df,
        "Connection_Limit",
        "Total_SSI",
        "Total SSI vs. Limite de Conexão",
        axes[0, 1],
    )

    # Plots 3-10: Individual Component Scores (Start at ROW 1)
    for i, comp in enumerate(ssi_components):
        # Line Chart (Left Column, starting row 1)
        plot_line_chart(
            ssi_df,
            "Date",
            comp,
            f"Componente SSI: {comp}",
            axes[i + 1, 0],
            "lime_green",
        )

        # Correlation (Right Column, starting row 1)
        plot_correlation_chart(
            ssi_df, comp, "Total_SSI", f"Total SSI vs. {comp}", axes[i + 1, 1]
        )

    # Aumentando hspace para evitar sobreposição de gráficos adjacentes
    plt.subplots_adjust(
        top=0.95, bottom=0.05, left=0.05, right=0.95, hspace=0.6, wspace=0.2
    )
    st.pyplot(fig)
    st.markdown("---")

    # --- 3. Interaction Metrics Analysis (8 Plots) ---
    st.header("3. Análise das Métricas de Interação (Limites e Perfis)")

    interaction_cols = [
        "Connection_Limit",
        "Follow_Limit",
        "Profiles_To_Scan",
        "Feed_Posts_Limit",
    ]

    fig, axes = plt.subplots(4, 2, figsize=(18, 20))
    fig.patch.set_facecolor(HEINEKEN_COLORS["off_white"])

    for i, col in enumerate(interaction_cols):
        # Plots 11-14: Interaction Limits Over Time
        plot_line_chart(
            ssi_df,
            "Date",
            col,
            f"Limite de Ação: {col.replace('_', ' ').title()}",
            axes[i, 0],
            "medium_dark_green",
        )

        # Plots 15-18: Correlation of Limits with SSI Total
        plot_correlation_chart(
            ssi_df,
            col,
            "Total_SSI",
            f"Total SSI vs. {col.replace('_', ' ').title()}",
            axes[i, 1],
        )

    plt.subplots_adjust(
        top=0.95, bottom=0.05, left=0.05, right=0.95, hspace=0.6, wspace=0.2
    )
    st.pyplot(fig)
    st.markdown("---")

    # --- 3B. Novo: Total Connections & Followers (4 Plots) ---
    st.header("3B. Análise de Conexões Totais e Followers")

    fig, axes = plt.subplots(2, 2, figsize=(18, 12))
    fig.patch.set_facecolor(HEINEKEN_COLORS["off_white"])

    # Plot: Total Connections Over Time
    plot_line_chart(
        ssi_df,
        "Date",
        "Total_Connections",
        "Conexões Totais (Histórico)",
        axes[0, 0],
        "dark_green",
    )

    # Plot: New Connections Accepted Per Day
    plot_line_chart(
        ssi_df,
        "Date",
        "New_Connections_Accepted",
        "Novas Conexões Aceitas por Dia",
        axes[0, 1],
        "lime_green",
    )

    # Plot: Total Followers Over Time
    plot_line_chart(
        ssi_df,
        "Date",
        "Total_Followers",
        "Followers Totais (Histórico)",
        axes[1, 0],
        "red",
    )

    # Plot: Correlation Connections vs SSI
    plot_correlation_chart(
        ssi_df,
        "Total_Connections",
        "Total_SSI",
        "Total SSI vs. Total de Conexões",
        axes[1, 1],
    )

    plt.subplots_adjust(
        top=0.95, bottom=0.05, left=0.05, right=0.95, hspace=0.6, wspace=0.2
    )
    st.pyplot(fig)
    st.markdown("---")

    # --- 4. Probability Metrics Analysis (6 Plots) ---
    st.header("4. Análise das Métricas de Probabilidade (Engajamento)")

    prob_cols = [
        "Group_Like_Prob",
        "Group_Comment_Prob",
        "Feed_Like_Prob",
        "Feed_Comment_Prob",
    ]

    fig, axes = plt.subplots(3, 2, figsize=(18, 15))
    fig.patch.set_facecolor(HEINEKEN_COLORS["off_white"])

    # Plots 19-20: Group Probabilities
    plot_line_chart(
        ssi_df,
        "Date",
        "Group_Like_Prob",
        "Prob. de Like em Grupos",
        axes[0, 0],
        "lime_green",
    )
    plot_line_chart(
        ssi_df,
        "Date",
        "Group_Comment_Prob",
        "Prob. de Comentário em Grupos",
        axes[0, 1],
        "red",
    )

    # Plots 21-22: Feed Probabilities
    plot_line_chart(
        ssi_df,
        "Date",
        "Feed_Like_Prob",
        "Prob. de Like no Feed",
        axes[1, 0],
        "medium_dark_green",
    )
    plot_line_chart(
        ssi_df,
        "Date",
        "Feed_Comment_Prob",
        "Prob. de Comentário no Feed",
        axes[1, 1],
        "dark_green",
    )

    # Plots 23-24: Correlation
    plot_correlation_chart(
        ssi_df,
        "Group_Comment_Prob",
        "SSI_Increase",
        "Aumento SSI vs. Prob. Comentário em Grupo",
        axes[2, 0],
    )
    plot_correlation_chart(
        ssi_df,
        "Feed_Like_Prob",
        "SSI_Increase",
        "Aumento SSI vs. Prob. Like no Feed",
        axes[2, 1],
    )

    plt.subplots_adjust(
        top=0.95, bottom=0.05, left=0.05, right=0.95, hspace=0.6, wspace=0.2
    )
    st.pyplot(fig)
    st.markdown("---")

    # --- 5. Engagement and Conversion Analysis (10 Plots) ---
    st.header("5. Análise de Conversão e Engajamento (DB Analytics)")

    if not interactions_df.empty:
        # Preparation for Conversion Analysis
        daily_interactions = (
            interactions_df.groupby("date")
            .apply(
                lambda x: pd.Series(
                    {
                        "total_attempts": len(x),
                        "connected": len(x[x["status"] == "Connected"]),
                        "followed": len(x[x["status"] == "Followed"]),
                        "visited": len(x[x["status"] == "Visited"]),
                        "sniper_attempts": len(x[x["source"] == "Sniper"]),
                        "group_attempts": len(x[x["source"] == "Group"]),
                        "reciprocator_connected": len(x[x["source"] == "Reciprocator"]),
                    }
                ),
                include_groups=False,
            )
            .reset_index()
        )

        daily_interactions["Conversion_Rate"] = (
            daily_interactions["connected"] / daily_interactions["total_attempts"]
        ) * 100

        # Merge with SSI data based on date
        daily_interactions["date"] = pd.to_datetime(daily_interactions["date"])
        merged_df = pd.merge(
            daily_interactions,
            ssi_df[["Date", "Total_SSI"]],
            left_on="date",
            right_on="Date",
            how="left",
        )

        fig, axes = plt.subplots(5, 2, figsize=(18, 25))
        fig.patch.set_facecolor(HEINEKEN_COLORS["off_white"])

        # Plots 25-27: Conversion and Attempts
        plot_line_chart(
            daily_interactions,
            "date",
            "total_attempts",
            "Tentativas Totais de Perfil por Dia",
            axes[0, 0],
            "dark_green",
        )
        plot_line_chart(
            daily_interactions,
            "date",
            "connected",
            "Conexões Enviadas por Dia",
            axes[0, 1],
            "lime_green",
        )
        plot_line_chart(
            daily_interactions,
            "date",
            "Conversion_Rate",
            "Taxa de Conversão Diária (%)",
            axes[1, 0],
            "red",
        )

        # Plot 28: Connection vs SSI
        plot_correlation_chart(
            merged_df.dropna(subset=["Total_SSI"]),
            "connected",
            "Total_SSI",
            "Conexões Enviadas vs. SSI Total",
            axes[1, 1],
        )

        # Plots 29-30: Source Analysis (Bar Chart)
        source_counts = interactions_df["source"].value_counts()
        plot_bar_chart(
            source_counts.reset_index(name="count"),
            "source",
            "count",
            "Interações por Fonte",
            axes[2, 0],
            "dark_green",
        )

        # Plots 31-32: Target Role Analysis (Top 5)
        top_roles = (
            interactions_df["headline"]
            .str.split(",")
            .str[0]
            .str.strip()
            .value_counts()
            .nlargest(5)
            .reset_index(name="count")
        )
        plot_bar_chart(
            top_roles,
            "headline",
            "count",
            "Top 5 Manchetes Alvo",
            axes[2, 1],
            "medium_dark_green",
        )

        # Plots 33-34: Analytics Dashboard Data
        if not analytics_df.empty:
            plot_line_chart(
                analytics_df,
                "timestamp",
                "profile_views",
                "Visualizações de Perfil (Dashboard)",
                axes[3, 0],
                "lime_green",
            )
            plot_line_chart(
                analytics_df,
                "timestamp",
                "post_impressions",
                "Impressões de Posts (Dashboard)",
                axes[3, 1],
                "dark_green",
            )
        else:
            axes[3, 0].set_title(
                "N/A: Profile Analytics data missing", fontsize=14, fontweight="bold"
            )
            axes[3, 1].set_title(
                "N/A: Profile Analytics data missing", fontsize=14, fontweight="bold"
            )
            axes[3, 0].grid(False)
            axes[3, 1].grid(False)

        # Plots 35-36: Correlation Analytics vs SSI
        if not analytics_df.empty and not ssi_df.empty:
            # Daily aggregation for analytics to merge with daily SSI
            daily_analytics = (
                analytics_df.groupby("date")
                .agg({"profile_views": "max", "post_impressions": "max"})
                .reset_index()
            )
            daily_analytics["date"] = pd.to_datetime(daily_analytics["date"])
            merged_analytics_ssi = pd.merge(
                daily_analytics,
                ssi_df[["Date", "Total_SSI", "SSI_Increase"]],
                left_on="date",
                right_on="Date",
                how="inner",
            )

            plot_correlation_chart(
                merged_analytics_ssi,
                "profile_views",
                "Total_SSI",
                "Total SSI vs. Visualizações de Perfil",
                axes[4, 0],
            )
            plot_correlation_chart(
                merged_analytics_ssi,
                "post_impressions",
                "SSI_Increase",
                "Aumento SSI vs. Impressões de Posts",
                axes[4, 1],
            )
        else:
            axes[4, 0].set_title(
                "N/A: Correlation Analytics missing data",
                fontsize=14,
                fontweight="bold",
            )
            axes[4, 1].set_title(
                "N/A: Correlation Analytics missing data",
                fontsize=14,
                fontweight="bold",
            )
            axes[4, 0].grid(False)
            axes[4, 1].grid(False)

        plt.subplots_adjust(
            top=0.95, bottom=0.05, left=0.05, right=0.95, hspace=0.6, wspace=0.2
        )
        st.pyplot(fig)

    else:
        st.info(
            "Nenhuma interação de perfil registrada no banco de dados SQLite ainda."
        )


# --- Run Streamlit ---
if __name__ == "__main__":
    main_dashboard()
