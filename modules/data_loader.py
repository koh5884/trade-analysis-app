"""
データ読み込み & 整形
"""

import pandas as pd
import os
import yfinance as yf
import warnings
from datetime import datetime, timedelta

warnings.filterwarnings("ignore")


# =====================================================
# CSV 読み込み
# =====================================================
def load_trade_data(data_dir, market, style):
    filename = f"{market}_{style}.csv"
    filepath = os.path.join(data_dir, filename)

    if not os.path.exists(filepath):
        return pd.DataFrame()

    df = pd.read_csv(filepath)

    # 証券コードを文字列化
    if "証券コード" in df.columns:
        df["証券コード"] = df["証券コード"].astype(str).str.replace(".0", "", regex=False)

    # 日付型
    for col in ["買付日", "売付日"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    # 数値 NaN 補完（売却済用）
    for col in ["売付単価", "売付約定代金", "実現損益", "増減率"]:
        if col in df.columns:
            df[col] = df[col].fillna(0)

    # 売却済の増減率補完
    if {"ステータス", "実現損益", "買付約定代金", "増減率"}.issubset(df.columns):
        for idx, row in df.iterrows():
            if row["ステータス"] == "売却済":
                if row["買付約定代金"] > 0 and row["増減率"] == 0:
                    df.at[idx, "増減率"] = row["実現損益"] / row["買付約定代金"] * 100

    return df


# =====================================================
# 現在価格取得
# =====================================================
def get_current_price(ticker_code, market):
    try:
        ticker_code = str(ticker_code).replace(".0", "")
        if market == "japan":
            ticker_code = f"{ticker_code}.T"

        ticker = yf.Ticker(ticker_code)

        info = ticker.fast_info
        if info and info.get("last_price") is not None:
            return float(info["last_price"])

        intraday = ticker.history(period="1d", interval="1m")
        if not intraday.empty:
            return float(intraday["Close"].iloc[-1])

        return None

    except Exception:
        return None


# =====================================================
# 保有中 評価損益
# =====================================================
def calculate_unrealized_pnl(df, market):
    holding = df[df["ステータス"] == "保有中"].copy()
    if holding.empty:
        return pd.DataFrame()

    records = []

    for _, row in holding.iterrows():
        current_price = get_current_price(row["証券コード"], market)
        if current_price is None:
            current_price = row["買付単価"]

        qty = row["買付数量"]
        buy_price = row["買付単価"]

        pnl = (current_price - buy_price) * qty
        pnl_rate = (pnl / (buy_price * qty) * 100) if qty > 0 else 0

        records.append(
            {
                "銘柄名": row["銘柄名"],
                "証券コード": row["証券コード"],
                "ステータス": "保有中",
                "買付日": row["買付日"],
                "売付日": None,
                "買付単価": buy_price,
                "売付単価": None,
                "買付数量": qty,
                "損益": pnl,
                "増減率": pnl_rate,
            }
        )

    return pd.DataFrame(records)


# =====================================================
# 売却済 + 保有中 統合
# =====================================================
def get_all_trades_with_status(df, market):
    # --- 売却済 ---
    closed = df[df["ステータス"] == "売却済"].copy()
    closed_fmt = closed[
        [
            "銘柄名",
            "証券コード",
            "ステータス",
            "買付日",
            "売付日",
            "買付単価",
            "売付単価",
            "買付数量",
            "実現損益",
            "増減率",
        ]
    ].copy()
    closed_fmt["損益"] = closed_fmt["実現損益"]
    closed_fmt.drop(columns=["実現損益"], inplace=True)

    # --- 保有中 ---
    holding_fmt = calculate_unrealized_pnl(df, market)

    # --- 結合 ---
    all_trades = pd.concat([closed_fmt, holding_fmt], ignore_index=True)

    # --- 表示順を完全固定 ---
    display_columns = [
        "銘柄名",
        "証券コード",
        "ステータス",
        "買付日",
        "売付日",
        "買付単価",
        "売付単価",
        "買付数量",
        "損益",
        "増減率",
    ]

    all_trades = all_trades[display_columns]

    # 買付日 降順
    all_trades = all_trades.sort_values("買付日", ascending=False).reset_index(drop=True)

    return all_trades
