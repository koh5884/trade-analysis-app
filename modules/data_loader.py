"""
データ読み込み & 整形
"""

import pandas as pd
import os
from datetime import datetime
import yfinance as yf


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
    
    # 証券コードを文字列に変換（重要！）
    if '証券コード' in df.columns:
        df['証券コード'] = df['証券コード'].astype(str).str.replace('.0', '', regex=False)
    
    # 日付型に変換
    if '買付日' in df.columns:
        df['買付日'] = pd.to_datetime(df['買付日'], errors='coerce')
    if '売付日' in df.columns:
        df['売付日'] = pd.to_datetime(df['売付日'], errors='coerce')
    
    # NaN処理（数値項目のみ0で埋める）
    numeric_columns = ['売付単価', '売付約定代金', '実現損益', '増減率']
    for col in numeric_columns:
        if col in df.columns:
            df[col] = df[col].fillna(0)
    
    return df


def get_current_price(ticker_code, market):
    """yfinanceで現在価格を取得"""
    from datetime import datetime, timedelta
    import warnings
    warnings.filterwarnings('ignore')
    
    try:
        # 文字列に変換
        ticker_code = str(ticker_code).replace('.0', '')
        
        # 日本株の場合は.Tを付与
        if market == "japan":
            ticker_code = f"{ticker_code}.T"
        
        # yf.download() with start/end
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        df = yf.download(
            ticker_code,
            start=start_date,
            end=end_date,
            progress=False,
            threads=False
        )
        
        if df.empty:
            print(f"⚠️  {ticker_code} データが空です")
            return None
        
        # マルチインデックスの場合の処理
        if isinstance(df.columns, pd.MultiIndex):
            # ('Close', 'TICKER') の形式
            if 'Close' in df.columns.get_level_values(0):
                close_col = df['Close']
                # 最初の列を取得（ティッカーが複数の場合もある）
                if isinstance(close_col, pd.DataFrame):
                    close_price = close_col.iloc[-1, 0]
                else:
                    close_price = close_col.iloc[-1]
                
                if pd.notna(close_price):
                    print(f"✅ {ticker_code} 株価取得成功: {close_price:,.0f}円")
                    return float(close_price)
        else:
            # 通常のインデックスの場合
            if 'Close' in df.columns:
                close_price = df['Close'].iloc[-1]
                if pd.notna(close_price):
                    print(f"✅ {ticker_code} 株価取得成功: {close_price:,.0f}円")
                    return float(close_price)
        
        print(f"⚠️  {ticker_code} Closeカラムが見つかりません")
        return None
    
    except Exception as e:
        print(f"⚠️  {ticker_code} エラー: {str(e)}")
        return None


def calculate_unrealized_pnl(df, market):
    """保有中銘柄の含み損益を計算"""
    holding_trades = df[df['ステータス'] == '保有中'].copy()
    
    if holding_trades.empty:
        return pd.DataFrame()
    
    unrealized_pnl = []
    currency_symbol = "¥" if market == "japan" else "$"
    
    for idx, row in holding_trades.iterrows():
        ticker = row['証券コード']
        current_price = get_current_price(ticker, market)
        
        if current_price is None:
            print(f"⚠️  {row['銘柄名']}({ticker})の株価取得失敗")
            current_price = row['買付単価']  # 取得失敗時は買付単価を使用
        
        quantity = row['買付数量']
        purchase_price = row['買付単価']
        
        # 評価額と含み損益を計算
        current_value = current_price * quantity
        purchase_value = purchase_price * quantity
        pnl = current_value - purchase_value
        pnl_rate = (pnl / purchase_value * 100) if purchase_value > 0 else 0
        
        unrealized_pnl.append({
            '銘柄名': row['銘柄名'],
            '証券コード': ticker,
            '買付日': row['買付日'],
            '買付単価': purchase_price,
            '現在値': current_price,
            '数量': quantity,
            '買付金額': purchase_value,
            '評価額': current_value,
            '含み損益': pnl,
            '増減率': pnl_rate
        })
        
        print(f"✅ {row['銘柄名']}: 買付{currency_symbol}{purchase_price:,.2f} → 現在{currency_symbol}{current_price:,.2f} (含み損益: {currency_symbol}{pnl:+,.2f})")
    
    return pd.DataFrame(unrealized_pnl)


def filter_closed_trades(df):
    """売却済トレードのみ抽出"""
    return df[df['ステータス'] == '売却済'].copy()


def get_all_trades_with_status(df, market):
    """全トレード(売却済+保有中)を統合"""
    closed = filter_closed_trades(df)
    holding = calculate_unrealized_pnl(df, market)
    
    # 統合用に列を整える
    closed_formatted = closed[['銘柄名', '証券コード', '買付日', '売付日', '実現損益', '増減率']].copy()
    closed_formatted['ステータス'] = '売却済'
    closed_formatted['損益'] = closed_formatted['実現損益']
    
    if not holding.empty:
        holding_formatted = holding[['銘柄名', '証券コード', '買付日']].copy()
        holding_formatted['売付日'] = None
        holding_formatted['損益'] = holding['含み損益']
        holding_formatted['増減率'] = holding['増減率']
        holding_formatted['ステータス'] = '保有中'
        
        all_trades = pd.concat([closed_formatted, holding_formatted], ignore_index=True)
    else:
        all_trades = closed_formatted
    
    # 買付日でソート
    all_trades = all_trades.sort_values('買付日', ascending=True).reset_index(drop=True)
    
    return all_trades