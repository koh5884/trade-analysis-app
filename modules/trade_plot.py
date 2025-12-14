"""
個別トレードのローソク足チャート（約定価格対応版）
"""

import matplotlib.pyplot as plt
import yfinance as yf
import pandas as pd
from datetime import timedelta

# 日本語フォント設定
plt.rcParams["font.family"] = ["DejaVu Sans", "Arial", "sans-serif"]
plt.rcParams["axes.unicode_minus"] = False


def get_stock_data(ticker_code, start_date, end_date, market):
    """
    yfinanceで株価データ取得
    """
    try:
        ticker_code = str(ticker_code).replace(".0", "")
        if market == "japan":
            ticker_code = f"{ticker_code}.T"

        ticker = yf.Ticker(ticker_code)
        data = ticker.history(start=start_date, end=end_date)

        if data.empty:
            return None

        return data

    except Exception as e:
        print(f"❌ 株価取得エラー ({ticker_code}): {e}")
        return None


def plot_candlestick(ax, df):
    """
    ローソク足描画
    """
    width = 0.6
    df = df.reset_index(drop=True)

    for i in range(len(df)):
        o, h, l, c = df.loc[i, ["Open", "High", "Low", "Close"]]
        if pd.isna([o, h, l, c]).any():
            continue

        color = "red" if c >= o else "green"

        # ヒゲ
        ax.plot([i, i], [l, h], color="black", linewidth=1)

        # ボディ
        height = abs(c - o)
        bottom = min(o, c)

        if height == 0:
            ax.plot([i - width / 2, i + width / 2], [c, c], color="black")
        else:
            rect = plt.Rectangle(
                (i - width / 2, bottom),
                width,
                height,
                facecolor=color,
                edgecolor="black",
                alpha=0.85,
            )
            ax.add_patch(rect)


def plot_trade_chart(trade_row, market, lookback_days=20):
    """
    個別トレードのローソク足チャート（約定価格重視）
    """

    ticker_code = trade_row["証券コード"]
    entry_date = pd.to_datetime(trade_row["買付日"])
    exit_date = (
        pd.to_datetime(trade_row["売付日"])
        if pd.notna(trade_row["売付日"])
        else None
    )

    entry_price = trade_row["買付単価"]
    exit_price = trade_row["売付単価"]
    status = trade_row["ステータス"]

    # データ取得期間
    start_date = entry_date - timedelta(days=lookback_days + 10)
    end_date = (
        exit_date + timedelta(days=5)
        if exit_date
        else pd.Timestamp.now() + timedelta(days=1)
    )

    stock_data = get_stock_data(ticker_code, start_date, end_date, market)

    if stock_data is None:
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.text(0.5, 0.5, "株価データ取得失敗", ha="center", va="center")
        ax.axis("off")
        return fig

    fig, ax = plt.subplots(figsize=(14, 7))

    # ローソク足
    plot_candlestick(ax, stock_data)

    dates = stock_data.index
    x = list(range(len(stock_data)))

    # ========= エントリー =========
    entry_idx = dates.get_indexer([entry_date], method="nearest")[0]

    ax.axhline(
        entry_price,
        color="blue",
        linestyle="--",
        linewidth=1.2,
        alpha=0.7,
        label="Entry Price",
    )

    ax.scatter(
        entry_idx,
        entry_price,
        marker="^",
        s=160,
        color="blue",
        edgecolors="black",
        zorder=6,
    )

    # ========= エグジット =========
    if exit_date and pd.notna(exit_price):
        exit_idx = dates.get_indexer([exit_date], method="nearest")[0]

        ax.axhline(
            exit_price,
            color="orange",
            linestyle="--",
            linewidth=1.2,
            alpha=0.7,
            label="Exit Price",
        )

        ax.scatter(
            exit_idx,
            exit_price,
            marker="v",
            s=160,
            color="orange",
            edgecolors="black",
            zorder=6,
        )

    # ========= 保有中 =========
    if status == "保有中":
        current_price = stock_data.iloc[-1]["Close"]
        ax.scatter(
            len(stock_data) - 1,
            current_price,
            marker="*",
            s=260,
            color="gold",
            edgecolors="black",
            zorder=6,
            label="Current",
        )

    # ========= 軸・装飾 =========
    ax.set_ylabel("Price (JPY)" if market == "japan" else "Price (USD)")
    ax.set_title(f"{ticker_code} Trade Chart", fontweight="bold")
    ax.grid(alpha=0.3)
    ax.legend()

    step = max(1, len(x) // 10)
    ax.set_xticks(x[::step])
    ax.set_xticklabels(
        [dates[i].strftime("%Y-%m-%d") for i in x[::step]],
        rotation=45,
    )

    plt.tight_layout()
    return fig
