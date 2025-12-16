"""
KPI計算モジュール（現行データ構造対応版）
"""

import pandas as pd


# =====================================================
# KPI 計算
# =====================================================
def calculate_kpis(df, unrealized_df, capital):
    """
    総合KPIを計算
    - 売却済：Notion計算（実現損益）
    - 保有中：現在値ベース（損益）
    """

    # ==============================
    # 売却済トレード
    # ==============================
    closed_trades = df[df["ステータス"] == "売却済"].copy()

    total_trades = len(closed_trades)

    # 勝率
    if total_trades > 0:
        win_rate = (
            len(closed_trades[closed_trades["実現損益"] > 0])
            / total_trades
            * 100
        )
    else:
        win_rate = 0

    # 平均利益率・損失率
    profits = closed_trades[closed_trades["実現損益"] > 0]["増減率"]
    losses = closed_trades[closed_trades["実現損益"] < 0]["増減率"]

    avg_profit_rate = profits.mean() if not profits.empty else 0
    avg_loss_rate = losses.mean() if not losses.empty else 0

    # 実現損益
    realized_pnl = closed_trades["実現損益"].sum() if not closed_trades.empty else 0

    # ==============================
    # 保有中（評価損益）
    # ==============================
    unrealized_pnl = (
        unrealized_df["損益"].sum()
        if not unrealized_df.empty and "損益" in unrealized_df.columns
        else 0
    )

    # ==============================
    # KPI まとめ
    # ==============================
    kpis = {
        "トレード数": total_trades,
        "勝率": win_rate,
        "平均利益率": avg_profit_rate,
        "平均損失率": avg_loss_rate,
        "実現損益": realized_pnl,
        "保有中含み益": unrealized_pnl,
        "元本": capital,
        "総損益": realized_pnl + unrealized_pnl,
    }

    return kpis


# =====================================================
# 資金推移
# =====================================================
def calculate_equity_curve(df, unrealized_df, capital):
    """
    資金推移を計算
    """

    if df.empty:
        return pd.DataFrame()

    closed = df[df["ステータス"] == "売却済"].copy().sort_values("売付日")

    dates = []
    equity = []
    cumulative = 0

    for _, row in closed.iterrows():
        cumulative += row["実現損益"]
        dates.append(row["売付日"])
        equity.append(capital + cumulative)

    # 現在（保有中含む）
    unrealized_pnl = (
        unrealized_df["損益"].sum()
        if not unrealized_df.empty and "損益" in unrealized_df.columns
        else 0
    )

    current_equity = (
        equity[-1] + unrealized_pnl if equity else capital + unrealized_pnl
    )

    dates.append(pd.Timestamp.now())
    equity.append(current_equity)

    return pd.DataFrame(
        {
            "日付": dates,
            "資産": equity,
            "元本": capital,
        }
    )


# =====================================================
# トレード一覧テーブル
# =====================================================
def get_trade_summary_table(df, unrealized_df):
    """
    個別トレード一覧（表示用）
    """

    rows = []

    # --- 売却済 ---
    closed = df[df["ステータス"] == "売却済"].copy()
    for _, row in closed.iterrows():
        rows.append(
            {
                "銘柄名": row["銘柄名"],
                "証券コード": row["証券コード"],
                "ステータス": "売却済",
                "買付日": row["買付日"].strftime("%Y-%m-%d")
                if pd.notna(row["買付日"])
                else "",
                "売付日": row["売付日"].strftime("%Y-%m-%d")
                if pd.notna(row["売付日"])
                else "",
                "損益": row["実現損益"],
                "増減率": f"{row['増減率']:.2f}%",
            }
        )

    # --- 保有中 ---
    if not unrealized_df.empty:
        for _, row in unrealized_df.iterrows():
            rows.append(
                {
                    "銘柄名": row["銘柄名"],
                    "証券コード": row["証券コード"],
                    "ステータス": "保有中",
                    "買付日": row["買付日"].strftime("%Y-%m-%d")
                    if pd.notna(row["買付日"])
                    else "",
                    "売付日": "-",
                    "損益": row["損益"],
                    "増減率": f"{row['増減率']:.2f}%",
                }
            )

    return pd.DataFrame(rows)
