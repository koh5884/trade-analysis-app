"""
チャート描画モジュール
"""

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np

# 日本語フォント設定
plt.rcParams['font.family'] = ['DejaVu Sans', 'Arial', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False


def plot_pnl_bar(df, market='japan'):
    """
    損益棒グラフ(トレード順)
    """
    closed = df[df['ステータス'] == '売却済'].copy()
    
    if closed.empty:
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.text(0.5, 0.5, 'No Data', ha='center', va='center', fontsize=14)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        return fig
    
    closed = closed.sort_values('売付日').reset_index(drop=True)
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # 色分け: プラスは緑、マイナスは赤
    colors = ['green' if x > 0 else 'red' for x in closed['実現損益']]
    
    ax.bar(range(len(closed)), closed['実現損益'], color=colors, alpha=0.7, edgecolor='black')
    
    ax.axhline(0, color='black', linewidth=0.8, linestyle='--')
    ax.set_xlabel('Trade Number', fontsize=12)
    currency = 'JPY' if market == 'japan' else 'USD'
    ax.set_ylabel(f'P&L ({currency})', fontsize=12)
    ax.set_title('Trade P&L', fontsize=14, fontweight='bold')
    ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    return fig


def plot_equity_curve(equity_df, market='japan'):
    """
    資金推移グラフ（現金 + 保有評価額の積み上げ）
    """
    if equity_df.empty:
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.text(0.5, 0.5, 'No Data', ha='center', va='center', fontsize=14)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        return fig
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    currency = 'JPY' if market == 'japan' else 'USD'
    
    # 元本ライン
    ax.axhline(equity_df['元本'].iloc[0], color='gray', linewidth=1.5, linestyle='--', label='Capital')
    
    # 資産推移
    ax.plot(equity_df['日付'], equity_df['資産'], marker='o', linewidth=2, color='blue', label='Total Assets')
    ax.fill_between(equity_df['日付'], equity_df['元本'].iloc[0], equity_df['資産'], alpha=0.3, color='blue')
    
    ax.set_xlabel('Date', fontsize=12)
    ax.set_ylabel(f'Assets ({currency})', fontsize=12)
    ax.set_title('Equity Curve', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(alpha=0.3)
    
    # 日付フォーマット
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.xticks(rotation=45)
    
    plt.tight_layout()
    return fig


def plot_win_loss_distribution(df):
    """
    勝ち負け分布（円グラフ）
    """
    closed = df[df['ステータス'] == '売却済'].copy()
    
    if closed.empty:
        fig, ax = plt.subplots(figsize=(6, 6))
        ax.text(0.5, 0.5, 'No Data', ha='center', va='center', fontsize=14)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        return fig
    
    wins = len(closed[closed['実現損益'] > 0])
    losses = len(closed[closed['実現損益'] < 0])
    breakeven = len(closed[closed['実現損益'] == 0])
    
    labels = []
    sizes = []
    colors = []
    
    if wins > 0:
        labels.append(f'Win ({wins})')
        sizes.append(wins)
        colors.append('green')
    
    if losses > 0:
        labels.append(f'Loss ({losses})')
        sizes.append(losses)
        colors.append('red')
    
    if breakeven > 0:
        labels.append(f'Even ({breakeven})')
        sizes.append(breakeven)
        colors.append('gray')
    
    fig, ax = plt.subplots(figsize=(7, 7))
    ax.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
    ax.set_title('Win/Loss Distribution', fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    return fig