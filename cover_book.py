"""
cover_book.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
読みたい本DB・読みたい漫画DB の全レコードを対象に、
ISBN → Amazon URL → ASIN → Amazon画像URL を自動構築し
Notion の「表紙」プロパティ（Files型）に書き込む。

【処理フロー】
1. ISBN から Amazon URL を構築
2. Amazon URL から ASIN を抽出
3. ASIN から 画像URL を取得
4. Notion の「表紙」に書き込み

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
DB_BOOK_ID   = os.environ.get("NOTION_DB_BOOK")
DB_MANGA_ID  = os.environ.get("NOTION_DB_MANGA")

if not NOTION_TOKEN:
    raise ValueError("❌ 環境変数 NOTION_TOKEN が設定されていません。")

if not DB_BOOK_ID and not DB_MANGA_ID:
    raise ValueError(
        "❌ 環境変数が設定されていません。\n"
        "  NOTION_DB_BOOK または NOTION_DB_MANGA を設定してください。"
    )

# DB定義：(DATABASE_ID, DB名, タイトルプロパティ名)
DATABASES = []
if DB_BOOK_ID:
    DATABASES.append((DB_BOOK_ID, "読みたい本DB", "書名"))
if DB_MANGA_ID:
    DATABASES.append((DB_MANGA_ID, "読みたい漫画DB", "タイトル"))

notion = Client(auth=NOTION_TOKEN)


# ── 1. ISBNからAmazon URLを構築 ──────────────────
def search_amazon_url_by_isbn(isbn: str) -> Optional[str]:
    """
    ISBNからAmazon Japan URLを構築
    ISBN-10 / ISBN-13 両対応
    """
    if not isbn or len(isbn) < 10:
        return None
    # ISBN（ハイフン削除）
    clean_isbn = isbn.replace("-", "").strip()
    if not clean_isbn.isdigit() or len(clean_isbn) not in [10, 13]:
        return None
    # Amazon Japan のURLを構築
    url = f"https://www.amazon.co.jp/dp/{clean_isbn}"
    return url


# ── 2. ASINをAmazon URLから抽出 ──────────────────
def extract_asin(amazon_url: str) -> Optional[str]:
    """
    Amazon URL から ASIN（10桁の英数字）を抽出
    """
    if not amazon_url:
        return None
    match = re.search(r"/(?:dp|gp/product)/([A-Z0-9]{10})", amazon_url)
    return match.group(1) if match else None


# ── 3. ASINからAmazon画像URLを組み立て ───────────
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
    return url_fallback


# ── 4. Notionの特定DBの全レコードを取得 ──────────
def fetch_pages_from_db(database_id: str) -> list:
    """
    指定DBの全レコードを取得（ページネーション対応）
    """
    results = []
    cursor = None
    # database_id をハイフンなしに正規化
    normalized_db_id = database_id.replace("-", "")
    
    while True:
        try:
            kwargs = {"database_id": normalized_db_id}
            if cursor:
                kwargs["start_cursor"] = cursor
            
            res = notion.databases.query(**kwargs)
            results.extend(res.get("results", []))
            
            if not res.get("has_more"):
                break
            cursor = res.get("next_cursor")
            time.sleep(0.3)
        except Exception as e:
            print(f"[エラー] DB 取得に失敗: {e}")
            break
    
    return results


# ── 5. Notionの「表紙」プロパティに画像URLを書き込む ──
def set_cover(page_id: str, image_url: str):
    """
    Notion ページの「表紙」プロパティに外部画像URLを設定
    """
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
    print("=== 読みたい本・漫画DB 表紙画像自動入力 ===\n")
    
    total_ok = 0
    total_skip = 0
    total_error = 0
    
    for db_id, db_name, title_prop in DATABASES:
        print(f"\n📚 {db_name} を処理中...\n")
        
        pages = fetch_pages_from_db(db_id)
        print(f"  取得レコード数: {len(pages)}\n")
        
        ok_count = 0
        skip_count = 0
        error_count = 0
        
        for page in pages:
            props = page["properties"]
            page_id = page["id"]
            
            # タイトルを取得
            title_list = props.get(title_prop, {}).get("title", [])
            title = title_list[0]["plain_text"] if title_list else "(タイトルなし)"
            
            # すでに表紙が入っているレコードはスキップ
            existing = props.get("表紙", {}).get("files", [])
            if existing:
                print(f"  [SKIP] {title}（表紙あり）")
                skip_count += 1
                continue
            
            # ISBN から Amazon URL を検索・構築
            isbn = props.get("ISBN", {}).get("rich_text", [])
            isbn_text = isbn[0]["plain_text"] if isbn else ""
            
            amazon_url = search_amazon_url_by_isbn(isbn_text)
            if not amazon_url:
                print(f"  [SKIP] {title}（ISBNなし or 形式不正）")
                skip_count += 1
                continue
            
            # Amazon URL から ASIN 抽出
            asin = extract_asin(amazon_url)
            if not asin:
                print(f"  [SKIP] {title}（ASIN取得失敗）")
                skip_count += 1
                continue
            
            # Amazon画像URLを構築
            cover_url = get_cover_url(asin)
            
            # Notionに書き込み
            try:
                set_cover(page_id, cover_url)
                print(f"  [OK]   {title}")
                ok_count += 1
            except Exception as e:
                print(f"  [ERR]  {title}: {e}")
                error_count += 1
            
            time.sleep(0.4)
        
        print(f"\n  --- {db_name} の結果 ---")
        print(f"    成功: {ok_count} 件")
        print(f"    スキップ: {skip_count} 件")
        print(f"    失敗: {error_count} 件")
        
        total_ok += ok_count
        total_skip += skip_count
        total_error += error_count
    
    print(f"\n{'='*40}")
    print(f"=== 全体の完了 ===")
    print(f"  成功: {total_ok} 件")
    print(f"  スキップ: {total_skip} 件")
    print(f"  失敗: {total_error} 件")
    print(f"\nNotionを開いて表紙が表示されているか確認してください！")


if __name__ == "__main__":
    main()