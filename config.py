import os

# Notion API設定（環境変数から取得）
NOTION_TOKEN = os.getenv("NOTION_TOKEN", "")  # ← 空にする

# NotionデータベースID（環境変数から取得）
DATABASE_IDS = {
    "japan_swing": os.getenv("JAPAN_SWING_DB_ID", ""),  # ← 空にする
    "japan_long": os.getenv("JAPAN_LONG_DB_ID", ""),
    "us_swing": os.getenv("US_SWING_DB_ID", ""),
    "us_long": os.getenv("US_LONG_DB_ID", ""),
}

# GitHub設定（環境変数から取得）
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")  # ← 空にする
GITHUB_REPO = os.getenv("GITHUB_REPO", "")
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main")

# 以下はそのまま
CAPITAL = {
    "japan": 100000,
    "us": 100,
}

DATA_DIR = "data"

YFINANCE_SUFFIX = {
    "japan": ".T",
    "us": "",
}

CHART_CONFIG = {
    "candle_width": 0.6,
    "entry_marker": "^",
    "exit_marker": "v",
    "current_marker": "*",
    "marker_size": 150,
    "lookback_days": 20,
}