"""
個別トレードのローソク足チャート
約定価格ベース（Entry / Exit）
"""

import matplotlib.pyplot as plt
import yfinance as yf
import pandas as pd
from datetime import timedelta

plt.rcParams["axes.unicode_minus"] = False


def get_stock_data(ticker_code, start_date, end_date, market):
    ticker_code = str(ticker_code).replace(".0", "")
    if market == "japan":
        ticker_code += ".T"

    ticker = yf.Ticker(ticker_code)
    df = ticker.history(start=start_date, end=end_date)

    return df if not df.empty else None


def plot_candlestick(ax, df):
    width = 0.6
    df = df.reset_index(drop=True)

    for i in range(len(df)):
        o, h, l, c = df.loc[i, ["Open", "High", "Low", "Close"]]

        color = "red" if c >= o else "green"

        ax.plot([i, i], [l, h], color="black", linewidth=1)

        ax.add_patch(
            plt.Rectangle(
                (i - width / 2, min(o, c)),
                width,
                abs(c - o),
                facecolor=color,
                edgecolor="black",
                alpha=0.8,
            )
        )


def plot_trade_chart(trade_row, market, lookback_days=20):
    ticker = trade_row["証券コード"]
    entry_date = pd.to_datetime(trade_row["買付日"])
    exit_date = pd.to_datetime(trade_row["売付日"]) if pd.notna(trade_row["売付日"]) else None

    entry_price = trade_row["買付単価"]
    exit_price = trade_row["売付単価"] if pd.notna(trade_row["売付単価"]) else None

    start = entry_date - timedelta(days=lookback_days + 10)
    end = exit_date + timedelta(days=5) if exit_date else pd.Timestamp.now()

    df = get_stock_data(ticker, start, end, market)

    if df is None:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "No data", ha="center", va="center")
        ax.axis("off")
        return fig

    fig, ax = plt.subplots(figsize=(14, 7))
    plot_candlestick(ax, df)

    dates = df.index
    entry_idx = dates.get_indexer([entry_date], method="nearest")[0]

    ax.scatter(
        entry_idx,
        entry_price,
        marker="^",
        s=200,
        color="blue",
        edgecolors="black",
        zorder=5,
        label="Entry (約定)",
    )
    ax.axhline(entry_price, color="blue", linestyle="--", alpha=0.5)

    if exit_date and exit_price is not None:
        exit_idx = dates.get_indexer([exit_date], method="nearest")[0]
        ax.scatter(
            exit_idx,
            exit_price,
            marker="v",
            s=200,
            color="orange",
            edgecolors="black",
            zorder=5,
            label="Exit (約定)",
        )
        ax.axhline(exit_price, color="orange", linestyle="--", alpha=0.5)

    ax.set_ylabel("Price (JPY)" if market == "japan" else "Price (USD)")
    ax.set_title(f"{ticker} Trade Chart")
    ax.legend()
    ax.grid(alpha=0.3)

    ax.set_xticks(range(0, len(df), max(1, len(df) // 10)))
    ax.set_xticklabels(
        [d.strftime("%Y-%m-%d") for d in dates[:: max(1, len(df) // 10)]],
        rotation=45,
    )

    plt.tight_layout()
    return fig
