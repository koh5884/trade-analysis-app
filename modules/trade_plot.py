"""
個別トレードのローソク足チャート
"""

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import yfinance as yf
import pandas as pd
from datetime import timedelta

# 日本語フォント設定
plt.rcParams['font.family'] = ['DejaVu Sans', 'Arial', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False


def get_stock_data(ticker_code, start_date, end_date, market):
    """
    yfinanceで株価データ取得
    """
    try:
        # 文字列に変換
        ticker_code = str(ticker_code).replace('.0', '')
        
        # 日本株の場合は.Tを付与
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
    ローソク足を描画
    """
    if df.empty:
        return
    
    width = 0.6
    
    # リセットされたインデックスを使用
    df_reset = df.reset_index(drop=True)
    
    for i in range(len(df_reset)):
        open_price = df_reset.loc[i, 'Open']
        close_price = df_reset.loc[i, 'Close']
        high_price = df_reset.loc[i, 'High']
        low_price = df_reset.loc[i, 'Low']
        
        # NaNチェック（スカラー値として確認）
        if any(pd.isna(x) for x in [open_price, close_price, high_price, low_price]):
            continue
        
        # 陽線: 赤、陰線: 緑
        color = 'red' if close_price >= open_price else 'green'
        
        # ヒゲ（高値-安値）
        ax.plot([i, i], [low_price, high_price], color='black', linewidth=1)
        
        # ボディ
        body_height = abs(close_price - open_price)
        body_bottom = min(open_price, close_price)
        
        if body_height == 0:
            # 十字線
            ax.plot([i - width/2, i + width/2], [close_price, close_price], color='black', linewidth=1)
        else:
            rect = plt.Rectangle((i - width/2, body_bottom), width, body_height,
                                facecolor=color, edgecolor='black', linewidth=0.8, alpha=0.8)
            ax.add_patch(rect)


def plot_trade_chart(trade_row, market, lookback_days=20):
    """
    個別トレードのチャートを描画
    
    Parameters:
    - trade_row: トレード行データ（Series）
    - market: 'japan' or 'us'
    - lookback_days: エントリー前後の表示日数
    """
    
    ticker_code = trade_row['証券コード']
    entry_date = pd.to_datetime(trade_row['買付日'])
    exit_date = pd.to_datetime(trade_row['売付日']) if pd.notna(trade_row['売付日']) else None
    status = trade_row['ステータス']
    
    # データ取得範囲
    start_date = entry_date - timedelta(days=lookback_days + 10)
    if exit_date:
        end_date = exit_date + timedelta(days=5)
    else:
        end_date = pd.Timestamp.now() + timedelta(days=1)
    
    # 株価データ取得
    stock_data = get_stock_data(ticker_code, start_date, end_date, market)
    
    if stock_data is None or stock_data.empty:
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.text(0.5, 0.5, f'Failed to fetch stock data\nTicker: {ticker_code}',
                ha='center', va='center', fontsize=14)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        return fig
    
    # チャート描画
    fig, ax = plt.subplots(figsize=(14, 7))
    
    # ローソク足
    plot_candlestick(ax, stock_data)
    
    # エントリー・エグジット・保有中マーカー
    x_indices = list(range(len(stock_data)))
    dates = stock_data.index
    
    # エントリーマーカー
    entry_idx = None
    for i, date in enumerate(dates):
        if date.date() >= entry_date.date():
            entry_idx = i
            break
    
    if entry_idx is not None:
        entry_price = stock_data.iloc[entry_idx]['Close']
        ax.scatter(entry_idx, entry_price, marker='^', s=200, color='blue', 
                   zorder=5, label='Entry', edgecolors='black', linewidths=1.5)
    
    # エグジットマーカー
    if exit_date:
        exit_idx = None
        for i, date in enumerate(dates):
            if date.date() >= exit_date.date():
                exit_idx = i
                break
        
        if exit_idx is not None:
            exit_price = stock_data.iloc[exit_idx]['Close']
            ax.scatter(exit_idx, exit_price, marker='v', s=200, color='orange',
                       zorder=5, label='Exit', edgecolors='black', linewidths=1.5)
    
    # 保有中マーカー
    if status == '保有中':
        current_price = stock_data.iloc[-1]['Close']
        ax.scatter(len(stock_data) - 1, current_price, marker='*', s=300, color='gold',
                   zorder=5, label='Current', edgecolors='black', linewidths=1.5)
    
    # 軸設定
    ax.set_xlabel('Date', fontsize=12)
    ax.set_ylabel('Price (JPY)' if market == 'japan' else 'Price (USD)', fontsize=12)
    
    # タイトルは英語のみ（文字化け回避）
    ticker_display = ticker_code.replace('.T', '')
    ax.set_title(f"{ticker_display} - Chart", fontsize=14, fontweight='bold')
    ax.legend(loc='upper left')
    ax.grid(alpha=0.3)
    
    # X軸の日付表示
    step = max(1, len(stock_data) // 10)
    ax.set_xticks(x_indices[::step])
    ax.set_xticklabels([dates[i].strftime('%Y-%m-%d') for i in x_indices[::step]], rotation=45)
    
    plt.tight_layout()
    return fig