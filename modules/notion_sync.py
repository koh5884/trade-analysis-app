"""
Notion API からデータ取得 & GitHub同期
"""

import requests
import json
import os
import pandas as pd
from datetime import datetime
import base64


def fetch_notion_database(token, database_id):
    """NotionデータベースからデータをJSON形式で取得"""
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    
    all_results = []
    has_more = True
    start_cursor = None
    
    while has_more:
        payload = {"page_size": 100}
        if start_cursor:
            payload["start_cursor"] = start_cursor
            
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code != 200:
            raise Exception(f"Notion API エラー: {response.status_code} - {response.text}")
        
        data = response.json()
        all_results.extend(data.get("results", []))
        has_more = data.get("has_more", False)
        start_cursor = data.get("next_cursor")
    
    return all_results


def extract_property_value(prop):
    """Notionプロパティから値を抽出"""
    prop_type = prop.get("type")
    
    if prop_type == "title":
        return prop["title"][0]["plain_text"] if prop["title"] else ""
    elif prop_type == "rich_text":
        return prop["rich_text"][0]["plain_text"] if prop["rich_text"] else ""
    elif prop_type == "number":
        return prop["number"]
    elif prop_type == "select":
        return prop["select"]["name"] if prop["select"] else ""
    elif prop_type == "date":
        return prop["date"]["start"] if prop["date"] else None
    elif prop_type == "formula":
        # 数式プロパティの値を取得
        formula = prop.get("formula", {})
        formula_type = formula.get("type")
        if formula_type == "number":
            return formula.get("number")
        elif formula_type == "string":
            # stringの場合、数値に変換を試みる
            string_val = formula.get("string")
            if string_val is None:
                return None
            try:
                # 文字列を数値に変換
                return float(string_val)
            except (ValueError, TypeError):
                return string_val
        elif formula_type == "boolean":
            return formula.get("boolean")
        elif formula_type == "date":
            date_obj = formula.get("date")
            return date_obj.get("start") if date_obj else None
        else:
            return None
    else:
        return None


def parse_notion_data(raw_data):
    """Notionの生データをDataFrameに変換"""
    records = []
    
    for page in raw_data:
        props = page["properties"]
        
        # デバッグ: プロパティ名を表示
        if not records:  # 最初の1件だけ表示
            print("📋 Notionプロパティ名一覧:")
            for key in props.keys():
                prop_type = props[key].get("type")
                print(f"  - {key}: {prop_type}")
        
        record = {
            "銘柄名": extract_property_value(props.get("銘柄名", {})),
            "証券コード": extract_property_value(props.get("証券コード", {})),
            "ステータス": extract_property_value(props.get("ステータス", {})),
            "買付日": extract_property_value(props.get("買付日", {})),
            "売付日": extract_property_value(props.get("売付日", {})),
            "買付単価": extract_property_value(props.get("買付単価", {})),
            "売付単価": extract_property_value(props.get("売付単価", {})),
            "買付数量": extract_property_value(props.get("買付数量", {})),
            "買付約定代金": extract_property_value(props.get("買付約定代金", {})),
            "売付約定代金": extract_property_value(props.get("売付約定代金", {})),
            # 「実現損益」または「評価損益」を試す
            "実現損益": extract_property_value(props.get("実現損益", props.get("評価損益", {}))),
            # 「増減率」がない場合はNone
            "増減率": extract_property_value(props.get("増減率", {})),
        }
        
        # デバッグ: 最初の1件の実現損益と増減率を表示
        if not records:
            print(f"🔍 1件目のデータ:")
            print(f"  - 実現損益: {record['実現損益']} (type: {type(record['実現損益'])})")
            print(f"  - 増減率: {record['増減率']} (type: {type(record['増減率'])})")
            
            # 生データも表示
            if "実現損益" in props:
                print(f"  - 実現損益(生データ): {props['実現損益']}")
            if "増減率" in props:
                print(f"  - 増減率(生データ): {props['増減率']}")
        
        records.append(record)
    
    return pd.DataFrame(records)


def sync_to_github(token, repo, branch, file_path, content, commit_message):
    """GitHubにファイルをコミット"""
    url = f"https://api.github.com/repos/{repo}/contents/{file_path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # 既存ファイルのSHA取得
    response = requests.get(url, headers=headers, params={"ref": branch})
    sha = response.json().get("sha") if response.status_code == 200 else None
    
    # Base64エンコード
    content_bytes = content.encode("utf-8")
    content_base64 = base64.b64encode(content_bytes).decode("utf-8")
    
    # コミット
    payload = {
        "message": commit_message,
        "content": content_base64,
        "branch": branch
    }
    if sha:
        payload["sha"] = sha
    
    response = requests.put(url, headers=headers, json=payload)
    
    if response.status_code not in [200, 201]:
        raise Exception(f"GitHub API エラー: {response.status_code} - {response.text}")
    
    return response.json()


def sync_all_databases(notion_token, db_ids, github_token, github_repo, github_branch, data_dir):
    """全データベースを同期"""
    os.makedirs(data_dir, exist_ok=True)
    
    datasets = {
        "japan_swing": "日本スイング",
        "japan_long": "日本長期",
        "us_swing": "米国スイング",
        "us_long": "米国長期",
    }
    
    results = {}
    
    for key, name in datasets.items():
        db_id = db_ids.get(key)
        if not db_id or db_id.startswith("YOUR_"):
            print(f"⚠️  {name} のDB IDが設定されていません")
            continue
        
        print(f"🔄 {name} を同期中...")
        
        # Notionから取得
        raw_data = fetch_notion_database(notion_token, db_id)
        df = parse_notion_data(raw_data)
        
        # ローカルに保存
        csv_path = os.path.join(data_dir, f"{key}.csv")
        json_path = os.path.join(data_dir, f"{key}.json")
        
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        df.to_json(json_path, orient="records", force_ascii=False, indent=2)
        
        # GitHubに同期
        try:
            sync_to_github(
                github_token, 
                github_repo, 
                github_branch,
                f"data/{key}.csv",
                df.to_csv(index=False),
                f"Update {name} data - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
            sync_to_github(
                github_token,
                github_repo,
                github_branch,
                f"data/{key}.json",
                df.to_json(orient="records", force_ascii=False, indent=2),
                f"Update {name} JSON - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
            print(f"✅ {name} 同期完了 ({len(df)}件)")
        except Exception as e:
            print(f"❌ GitHub同期エラー ({name}): {e}")
        
        results[key] = df
    
    return results