"""
KPI計算モジュール
"""

import pandas as pd
import numpy as np


def calculate_kpis(df, unrealized_df, capital):
    """
    総合KPIを計算
    
    Parameters:
    - df: 全トレードデータ
    - unrealized_df: 保有中銘柄の評価損益
    - capital: 元本
    
    Returns:
    - dict: KPI辞書
    """
    
    # 売却済トレード
    closed_trades = df[df['ステータス'] == '売却済'].copy()
    
    # トレード数
    total_trades = len(closed_trades)
    
    # 勝率
    if total_trades > 0:
        winning_trades = closed_trades[closed_trades['実現損益'] > 0]
        win_rate = len(winning_trades) / total_trades * 100
    else:
        win_rate = 0
    
    # 平均利益率・平均損失率
    if not closed_trades.empty:
        profits = closed_trades[closed_trades['実現損益'] > 0]['増減率']
        losses = closed_trades[closed_trades['実現損益'] < 0]['増減率']
        
        avg_profit_rate = profits.mean() if len(profits) > 0 else 0
        avg_loss_rate = losses.mean() if len(losses) > 0 else 0
    else:
        avg_profit_rate = 0
        avg_loss_rate = 0
    
    # 実現損益
    realized_pnl = closed_trades['実現損益'].sum() if not closed_trades.empty else 0
    
    # 保有中含み損益
    unrealized_pnl = unrealized_df['含み損益'].sum() if not unrealized_df.empty else 0
    unrealized_value = unrealized_df['評価額'].sum() if not unrealized_df.empty else 0
    
    # 総資産
    cash = capital + realized_pnl - (unrealized_df['買付金額'].sum() if not unrealized_df.empty else 0)
    total_assets = cash + unrealized_value
    
    kpis = {
        "トレード数": total_trades,
        "勝率": win_rate,
        "平均利益率": avg_profit_rate,
        "平均損失率": avg_loss_rate,
        "実現損益": realized_pnl,
        "保有中含み益": unrealized_pnl,
        "元本": capital,
        "現金": cash,
        "保有評価額": unrealized_value,
        "総資産": total_assets,
        "総損益": realized_pnl + unrealized_pnl,
    }
    
    return kpis


def calculate_equity_curve(df, unrealized_df, capital):
    """
    資金推移を計算
    
    Returns:
    - pd.DataFrame: 日付ごとの資金推移
    """
    
    if df.empty:
        return pd.DataFrame()
    
    # 売却済トレードを日付順に並べる
    closed = df[df['ステータス'] == '売却済'].copy()
    
    if closed.empty:
        dates = [pd.Timestamp.now()]
        equity = [capital]
    else:
        closed = closed.sort_values('売付日')
        
        dates = []
        equity = []
        cumulative_pnl = 0
        
        for idx, row in closed.iterrows():
            cumulative_pnl += row['実現損益']
            dates.append(row['売付日'])
            equity.append(capital + cumulative_pnl)
    
    # 現在の資産を追加
    if not unrealized_df.empty:
        unrealized_pnl = unrealized_df['含み損益'].sum()
        current_equity = equity[-1] + unrealized_pnl if equity else capital + unrealized_pnl
    else:
        current_equity = equity[-1] if equity else capital
    
    dates.append(pd.Timestamp.now())
    equity.append(current_equity)
    
    equity_df = pd.DataFrame({
        '日付': dates,
        '資産': equity,
        '元本': capital
    })
    
    return equity_df


def get_trade_summary_table(df, unrealized_df):
    """
    トレード一覧テーブル用のデータを生成
    
    Returns:
    - pd.DataFrame: 表示用テーブル
    """
    
    summary = []
    
    # 売却済
    closed = df[df['ステータス'] == '売却済'].copy()
    for idx, row in closed.iterrows():
        summary.append({
            '銘柄名': row['銘柄名'],
            '証券コード': row['証券コード'],
            'ステータス': '売却済',
            '買付日': row['買付日'].strftime('%Y-%m-%d') if pd.notna(row['買付日']) else '',
            '売付日': row['売付日'].strftime('%Y-%m-%d') if pd.notna(row['売付日']) else '',
            '損益': row['実現損益'],
            '増減率': f"{row['増減率']:.2f}%"
        })
    
    # 保有中
    for idx, row in unrealized_df.iterrows():
        summary.append({
            '銘柄名': row['銘柄名'],
            '証券コード': row['証券コード'],
            'ステータス': '保有中',
            '買付日': row['買付日'].strftime('%Y-%m-%d') if pd.notna(row['買付日']) else '',
            '売付日': '-',
            '損益': row['含み損益'],
            '増減率': f"{row['増減率']:.2f}%"
        })
    
    return pd.DataFrame(summary)
