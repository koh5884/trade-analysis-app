"""
データ読み込み & 整形
"""

import pandas as pd
import os
from datetime import datetime, timedelta
import yfinance as yf
import warnings

warnings.filterwarnings("ignore")


def load_trade_data(data_dir, market, style):
    """
    CSVからトレードデータを読み込み
    market: 'japan' or 'us'
    style: 'swing' or 'long'
    """
    filename = f"{market}_{style}.csv"
    filepath = os.path.join(data_dir, filename)

    if not os.path.exists(filepath):
        return pd.DataFrame()

    df = pd.read_csv(filepath)

    # 証券コードを文字列に変換
    if "証券コード" in df.columns:
        df["証券コード"] = (
            df["証券コード"].astype(str).str.replace(".0", "", regex=False)
        )

    # 日付型
    for col in ["買付日", "売付日"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    # 数値NaN補完（売却済用）
    numeric_columns = ["売付単価", "売付約定代金", "実現損益", "増減率"]
    for col in numeric_columns:
        if col in df.columns:
            df[col] = df[col].fillna(0)

    # 増減率が未計算なら算出（売却済のみ）
    if {"実現損益", "買付約定代金", "増減率"}.issubset(df.columns):
        for idx, row in df.iterrows():
            if row["ステータス"] == "売却済":
                if row["買付約定代金"] > 0 and row["増減率"] == 0:
                    df.at[idx, "増減率"] = (
                        row["実現損益"] / row["買付約定代金"] * 100
                    )

    return df


# =====================================================
# 現在価格取得（できるだけリアルタイム）
# =====================================================
def get_current_price(ticker_code, market):
    """yfinanceで現在価格を取得（fast_info → 分足）"""
    try:
        ticker_code = str(ticker_code).replace(".0", "")
        if market == "japan":
            ticker_code = f"{ticker_code}.T"

        ticker = yf.Ticker(ticker_code)

        # ① fast_info（最優先）
        info = ticker.fast_info
        if info and "last_price" in info and info["last_price"] is not None:
            return float(info["last_price"])

        # ② 直近1日の1分足
        intraday = ticker.history(period="1d", interval="1m")
        if not intraday.empty:
            return float(intraday["Close"].iloc[-1])

        return None

    except Exception as e:
        print(f"⚠️ 現在値取得失敗 {ticker_code}: {e}")
        return None


# =====================================================
# 保有中トレードの評価損益計算
# =====================================================
def calculate_unrealized_pnl(df, market):
    """
    保有中銘柄のみ：
    (現在値 − 買付単価) × 買付数量
    """

    if df.empty or "ステータス" not in df.columns:
        return pd.DataFrame()

    holding = df[df["ステータス"] == "保有中"].copy()
    if holding.empty:
        return pd.DataFrame()

    records = []

    for _, row in holding.iterrows():
        ticker = row["証券コード"]
        quantity = row["買付数量"]
        buy_price = row["買付単価"]

        current_price = get_current_price(ticker, market)
        if current_price is None:
            current_price = buy_price  # フェイルセーフ

        buy_value = buy_price * quantity
        current_value = current_price * quantity
        pnl = current_value - buy_value
        pnl_rate = (pnl / buy_value * 100) if buy_value > 0 else 0

        records.append(
            {
                "銘柄名": row["銘柄名"],
                "証券コード": ticker,
                "買付日": row["買付日"],
                "買付単価": buy_price,
                "現在値": current_price,
                "数量": quantity,
                "買付金額": buy_value,
                "評価額": current_value,
                "含み損益": pnl,
                "増減率": pnl_rate,
            }
        )

    return pd.DataFrame(records)


# =====================================================
# 売却済フィルタ
# =====================================================
def filter_closed_trades(df):
    return df[df["ステータス"] == "売却済"].copy()


# =====================================================
# 売却済 + 保有中 を統合（表示用）
# =====================================================
def get_all_trades_with_status(df, market):
    closed = filter_closed_trades(df)
    holding = calculate_unrealized_pnl(df, market)

    # --- 売却済（Notion計算そのまま） ---
    closed_fmt = closed[
        ["銘柄名", "証券コード", "買付日", "売付日", "実現損益", "増減率"]
    ].copy()
    closed_fmt["ステータス"] = "売却済"
    closed_fmt["損益"] = closed_fmt["実現損益"]

    # --- 保有中（評価損益） ---
    if not holding.empty:
        holding_fmt = holding[
            ["銘柄名", "証券コード", "買付日", "含み損益", "増減率"]
        ].copy()
        holding_fmt["売付日"] = None
        holding_fmt["損益"] = holding_fmt["含み損益"]
        holding_fmt["ステータス"] = "保有中"

        all_trades = pd.concat([closed_fmt, holding_fmt], ignore_index=True)
    else:
        all_trades = closed_fmt

    # 買付日降順（新しい順）
    all_trades = (
        all_trades.sort_values("買付日", ascending=False)
        .reset_index(drop=True)
    )

    return all_trades
