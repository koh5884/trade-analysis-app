"""
個別トレードのローソク足チャート（約定価格ベース）
"""

import matplotlib.pyplot as plt
import yfinance as yf
import pandas as pd
from datetime import timedelta

# 日本語フォント設定
plt.rcParams["font.family"] = ["DejaVu Sans", "Arial", "sans-serif"]
plt.rcParams["axes.unicode_minus"] = False


def get_stock_data(ticker_code, start_date, end_date, market):
    """yfinanceで株価データ取得（timezone問題完全回避）"""
    try:
        ticker_code = str(ticker_code).replace(".0", "")
        if market == "japan":
            ticker_code = f"{ticker_code}.T"

        data = yf.Ticker(ticker_code).history(
            start=start_date,
            end=end_date,
            auto_adjust=False,
        )

        if data.empty:
            return None

        # timezone を完全に除去（Streamlit Cloud 対策）
        if data.index.tz is not None:
            data.index = data.index.tz_localize(None)

        return data

    except Exception as e:
        print(f"❌ 株価取得エラー ({ticker_code}): {e}")
        return None


def plot_candlestick(ax, df):
    """ローソク足描画（index=0,1,2... ベース）"""
    width = 0.6
    df = df.reset_index(drop=True)

    for i in range(len(df)):
        o, h, l, c = df.loc[i, ["Open", "High", "Low", "Close"]]

        if pd.isna([o, h, l, c]).any():
            continue

        # 陽線: 赤 / 陰線: 緑（日本式）
        color = "red" if c >= o else "green"

        # ヒゲ
        ax.plot([i, i], [l, h], color="black", linewidth=1)

        # ボディ
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
    """
    個別トレードチャート
    ・X軸：最寄り営業日
    ・Y軸：Notionの約定価格（絶対にズレない）
    """

    # ===== トレード情報 =====
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

    # ===== 株価取得期間 =====
    start = entry_date - timedelta(days=lookback_days + 10)
    end = exit_date + timedelta(days=5) if exit_date else pd.Timestamp.today()

    stock = get_stock_data(ticker, start, end, market)

    if stock is None:
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.text(0.5, 0.5, "No price data", ha="center", va="center")
        ax.axis("off")
        return fig

    # ===== 描画 =====
    fig, ax = plt.subplots(figsize=(14, 7))
    plot_candlestick(ax, stock)

    dates = stock.index

    # ===== エントリー（約定価格）=====
    entry_idx = dates.get_indexer([entry_date], method="nearest")[0]
    ax.scatter(
        entry_idx,
        entry_price,
        marker="^",
        s=220,
        color="blue",
        edgecolors="black",
        zorder=6,
        label="Entry (約定)",
    )
    ax.axhline(entry_price, color="blue", linestyle="--", alpha=0.4)

    # ===== エグジット（約定価格）=====
    if exit_date is not None and exit_price is not None:
        exit_idx = dates.get_indexer([exit_date], method="nearest")[0]
        ax.scatter(
            exit_idx,
            exit_price,
            marker="v",
            s=220,
            color="orange",
            edgecolors="black",
            zorder=6,
            label="Exit (約定)",
        )
        ax.axhline(exit_price, color="orange", linestyle="--", alpha=0.4)

        # エントリー → エグジット線（分析的に超重要）
        ax.plot(
            [entry_idx, exit_idx],
            [entry_price, exit_price],
            color="gray",
            linestyle=":",
            linewidth=2,
            alpha=0.7,
        )

    # ===== 保有中 =====
    if status == "保有中":
        ax.scatter(
            len(stock) - 1,
            stock.iloc[-1]["Close"],
            marker="*",
            s=320,
            color="gold",
            edgecolors="black",
            zorder=7,
            label="Current",
        )

    # ===== 軸・装飾 =====
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
