"""
個別トレードのローソク足チャート（約定価格 + 当日OHLC対応）
"""

import matplotlib.pyplot as plt
import yfinance as yf
import pandas as pd
from datetime import timedelta

plt.rcParams["font.family"] = ["DejaVu Sans", "Arial", "sans-serif"]
plt.rcParams["axes.unicode_minus"] = False


def get_stock_data(ticker_code, start_date, end_date, market, include_today=False):
    """
    日足 +（必要なら）当日OHLCを合成
    """
    ticker_code = str(ticker_code).replace(".0", "")
    if market == "japan":
        ticker_code = f"{ticker_code}.T"

    ticker = yf.Ticker(ticker_code)

    # === 日足 ===
    daily = ticker.history(
        start=start_date,
        end=end_date,
        interval="1d",
        auto_adjust=False,
    )

    if daily.empty:
        return None

    if daily.index.tz is not None:
        daily.index = daily.index.tz_localize(None)

    # === 当日足（保有中のみ）===
    if include_today:
        intraday = ticker.history(
            period="1d",
            interval="1m",
            auto_adjust=False,
        )

        if not intraday.empty:
            if intraday.index.tz is not None:
                intraday.index = intraday.index.tz_localize(None)

            today = intraday.index[-1].normalize()

            o = intraday.iloc[0]["Open"]
            h = intraday["High"].max()
            l = intraday["Low"].min()
            c = intraday.iloc[-1]["Close"]
            v = intraday["Volume"].sum()

            daily.loc[today] = [o, h, l, c, v, None, None]

    return daily.sort_index()


def plot_candlestick(ax, df):
    width = 0.6
    df = df.reset_index(drop=True)

    for i in range(len(df)):
        o, h, l, c = df.loc[i, ["Open", "High", "Low", "Close"]]

        if pd.isna([o, h, l, c]).any():
            continue

        color = "red" if c >= o else "green"
        ax.plot([i, i], [l, h], color="black", linewidth=1)

        bottom = min(o, c)
        height = abs(c - o)

        if height == 0:
            ax.plot([i - width / 2, i + width / 2], [c, c], color="black")
        else:
            ax.add_patch(
                plt.Rectangle(
                    (i - width / 2, bottom),
                    width,
                    height,
                    facecolor=color,
                    edgecolor="black",
                    alpha=0.8,
                )
            )


def plot_trade_chart(trade_row, market, lookback_days=20):
    ticker = trade_row["証券コード"]
    entry_date = pd.to_datetime(trade_row["買付日"]).normalize()
    exit_date = (
        pd.to_datetime(trade_row["売付日"]).normalize()
        if pd.notna(trade_row["売付日"])
        else None
    )

    entry_price = trade_row["買付単価"]
    exit_price = trade_row["売付単価"] if exit_date is not None else None
    status = trade_row["ステータス"]

    start = entry_date - timedelta(days=lookback_days + 10)
    end = pd.Timestamp.today() + timedelta(days=1)

    stock = get_stock_data(
        ticker,
        start,
        end,
        market,
        include_today=(status == "保有中"),
    )

    if stock is None:
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.text(0.5, 0.5, "No price data", ha="center", va="center")
        ax.axis("off")
        return fig

    fig, ax = plt.subplots(figsize=(14, 7))
    plot_candlestick(ax, stock)

    dates = stock.index

    entry_idx = dates.get_indexer([entry_date], method="nearest")[0]
    ax.scatter(entry_idx, entry_price, marker="^", s=220,
               color="blue", edgecolors="black", zorder=5, label="Entry")
    ax.axhline(entry_price, color="blue", linestyle="--", alpha=0.4)

    if exit_date is not None and exit_price is not None:
        exit_idx = dates.get_indexer([exit_date], method="nearest")[0]
        ax.scatter(exit_idx, exit_price, marker="v", s=220,
                   color="orange", edgecolors="black", zorder=5, label="Exit")
        ax.axhline(exit_price, color="orange", linestyle="--", alpha=0.4)

    if status == "保有中":
        ax.scatter(
            len(stock) - 1,
            stock.iloc[-1]["Close"],
            marker="*",
            s=320,
            color="gold",
            edgecolors="black",
            zorder=6,
            label="Current",
        )

    ax.set_ylabel("Price (JPY)" if market == "japan" else "Price (USD)")
    ax.set_title(f"{ticker} Trade Chart", fontsize=14, fontweight="bold")
    ax.legend()
    ax.grid(alpha=0.3)

    step = max(1, len(stock) // 10)
    ax.set_xticks(range(0, len(stock), step))
    ax.set_xticklabels(
        [dates[i].strftime("%Y-%m-%d") for i in range(0, len(stock), step)],
        rotation=45,
    )

    plt.tight_layout()
    return fig
