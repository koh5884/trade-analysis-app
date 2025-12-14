"""
トレード分析アプリ - 設定ファイル
"""

import os

# Notion API設定（環境変数から取得）
NOTION_TOKEN = os.getenv("NOTION_TOKEN", "YOUR_NOTION_TOKEN_HERE")

# NotionデータベースID（環境変数から取得）
DATABASE_IDS = {
    "japan_swing": os.getenv("JAPAN_SWING_DB_ID", "YOUR_JAPAN_SWING_DB_ID"),
    "japan_long": os.getenv("JAPAN_LONG_DB_ID", "YOUR_JAPAN_LONG_DB_ID"),
    "us_swing": os.getenv("US_SWING_DB_ID", "YOUR_US_SWING_DB_ID"),
    "us_long": os.getenv("US_LONG_DB_ID", "YOUR_US_LONG_DB_ID"),
}

# GitHub設定（環境変数から取得）
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "YOUR_GITHUB_TOKEN_HERE")
GITHUB_REPO = os.getenv("GITHUB_REPO", "username/repository")
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main")

# 元本設定
CAPITAL = {
    "japan": 100000,  # 日本株: 10万円
    "us": 500,     # 米国株: 500ドル
}

# データ保存先
DATA_DIR = "data"

# yfinance 設定
YFINANCE_SUFFIX = {
    "japan": ".T",  # 日本株は末尾に.Tを付与
    "us": "",       # 米国株はそのまま
}

# チャート設定
CHART_CONFIG = {
    "candle_width": 0.6,
    "entry_marker": "^",
    "exit_marker": "v",
    "current_marker": "*",
    "marker_size": 150,
    "lookback_days": 20,  # エントリー前後の表示日数
}