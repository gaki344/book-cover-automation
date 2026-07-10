"""
cover_book.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
読みたい本DB の全レコードを対象に、
Amazon URL → ASIN → Amazon画像URL を構築し
Notion の「表紙」プロパティ（Files型）に書き込む。

画像取得方式: AmazonのASINから画像URLを直接組み立て
  https://m.media-amazon.com/images/P/{ASIN}.01.LZZZZZZZ.jpg

■ 必要ライブラリ（初回のみ）
    pip3 install notion-client requests

■ 実行
    python3 cover_book.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import re
import time
import os
from typing import Optional
import requests
from notion_client import Client

# ─── 設定 ────────────────────────────────────────
# 環境変数から読み込む
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
DATABASE_ID  = os.environ.get("NOTION_DB_BOOK")

if not NOTION_TOKEN or not DATABASE_ID:
    raise ValueError(
        "❌ 環境変数が設定されていません。\n"
        "  NOTION_TOKEN と NOTION_DB_BOOK を設定してください。"
    )

notion = Client(auth=NOTION_TOKEN)


# ── 1. ASINをAmazon URLから抽出 ──────────────────
def extract_asin(amazon_url: str) -> Optional[str]:
    if not amazon_url:
        return None
    match = re.search(r"/(?:dp|gp/product)/([A-Z0-9]{10})", amazon_url)
    return match.group(1) if match else None


# ── 2. ASINからAmazon画像URLを組み立て ───────────
def get_cover_url(asin: str) -> Optional[str]:
    """
    AmazonはASINさえあれば画像URLが決まった形式で構築できる。
    LZZZZZZZ = 大サイズ画像
    """
    url = f"https://m.media-amazon.com/images/P/{asin}.01.LZZZZZZZ.jpg"
    try:
        res = requests.head(url, timeout=10, allow_redirects=True)
        # 200かつ画像であれば有効
        content_type = res.headers.get("content-type", "")
        if res.status_code == 200 and "image" in content_type:
            return url
    except Exception as e:
        print(f"  [画像確認エラー] {asin}: {e}")
    # サイズ違いのフォールバック
    url_fallback = f"https://m.media-amazon.com/images/P/{asin}.01.MZZZZZZZ.jpg"
    return url_fallback  # 確認できなくてもURLとして返す（Notionが表示できるか試す）


# ── 3. Notionの全レコードを取得 ──────────────────
def fetch_all_pages() -> list:
    results = []
    cursor = None
    while True:
        kwargs = {
            "filter": {"value": "page", "property": "object"},
            "sort": {"direction": "ascending", "timestamp": "last_edited_time"},
        }
        if cursor:
            kwargs["start_cursor"] = cursor
        res = notion.search(**kwargs)
        for page in res["results"]:
            parent = page.get("parent", {})
            db_id = parent.get("database_id", "").replace("-", "")
            ds_id = parent.get("data_source_id", "").replace("-", "")
            target = DATABASE_ID.replace("-", "")
            if db_id == target or ds_id == target:
                results.append(page)
        if not res.get("has_more"):
            break
        cursor = res["next_cursor"]
        time.sleep(0.3)
    return results


# ── 4. Notionの「表紙」プロパティに画像URLを書き込む ──
def set_cover(page_id: str, image_url: str):
    notion.pages.update(
        page_id=page_id,
        properties={
            "表紙": {
                "files": [
                    {
                        "type": "external",
                        "name": "cover",
                        "external": {"url": image_url},
                    }
                ]
            }
        },
    )


# ── メイン処理 ───────────────────────────────────
def main():
    print("=== 読みたい本DB 表紙画像自動入力 ===\n")

    pages = fetch_all_pages()
    print(f"取得レコード数: {len(pages)}\n")

    ok_count    = 0
    skip_count  = 0
    error_count = 0

    for page in pages:
        props      = page["properties"]
        page_id    = page["id"]
        title_list = props.get("書名", {}).get("title", [])
        title      = title_list[0]["plain_text"] if title_list else "(タイトルなし)"

        # すでに表紙が入っているレコードはスキップ
        existing = props.get("表紙", {}).get("files", [])
        if existing:
            print(f"[SKIP] {title}（表紙あり）")
            skip_count += 1
            continue

        # Amazon URL から ASIN 抽出
        amazon_url = props.get("Amazon URL", {}).get("url", "")
        asin = extract_asin(amazon_url)
        if not asin:
            print(f"[SKIP] {title}（Amazon URLなし or ASIN取得不可）")
            skip_count += 1
            continue

        # Amazon画像URLを構築
        cover_url = get_cover_url(asin)

        # Notionに書き込み
        try:
            set_cover(page_id, cover_url)
            print(f"[OK]   {title}")
            ok_count += 1
        except Exception as e:
            print(f"[ERR]  {title}: {e}")
            error_count += 1

        time.sleep(0.4)

    print(f"\n=== 完了 ===")
    print(f"  成功: {ok_count} 件")
    print(f"  スキップ: {skip_count} 件")
    print(f"  失敗: {error_count} 件")
    print(f"\nNotionを開いて表紙が表示されているか確認してください！")


if __name__ == "__main__":
    main()