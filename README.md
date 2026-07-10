# 📚 book-cover-automation

ISBN から Amazon の表紙画像を自動取得して、Notion の「読みたい本」「読みたい漫画」など複数DB に自動入力するツールです。

毎週月曜 09:00 JST に GitHub Actions で自動実行されます。

---

## 📋 機能

- ✅ Notion DB から複数の本・漫画DBを全件取得
- ✅ **ISBN から Amazon URL を自動構築**（新機能）
- ✅ Amazon URL から ASIN を抽出
- ✅ Amazon から表紙画像 URL を構築
- ✅ Notion の「表紙」プロパティ（Files型）に自動入力
- ✅ 本・漫画など複数DB に対応
- ✅ スキップ・成功・失敗の件数をログ出力

---

## 🚀 セットアップ

### 1️⃣ リポジトリをクローン

```bash
git clone https://github.com/YOUR_USERNAME/book-cover-automation.git
cd book-cover-automation
```

### 2️⃣ Notion API トークンを取得

1. [Notion インテグレーション](https://www.notion.so/my-integrations) にアクセス
2. **新しいインテグレーション** を作成
3. **能力** で以下を有効化：
   - `content` → `read` ✓
   - `content` → `update` ✓
4. トークンをコピー（後で使用）

### 3️⃣ GitHub Secrets に登録

1. GitHub リポジトリ → **Settings** → **Secrets and variables** → **Actions**
2. **New repository secret** をクリック

| 名前 | 値 |
|---|---|
| `NOTION_TOKEN` | Notion API トークン |
| `NOTION_DB_BOOK` | 読みたい本DB の ID（16進数、ハイフンなし） |
| `NOTION_DB_MANGA` | 読みたい漫画DB の ID（16進数、ハイフンなし）※オプション |

**DB ID の確認方法：**
- Notion で DB を開く
- ブラウザ URL から ID を抽出
- 例：`https://www.notion.so/350fe35c0967807b9af1000b7698f35a?v=...` → `350fe35c0967807b9af1000b7698f35a`

### 4️⃣ ローカルテスト（オプション）

```bash
# 依存ライブラリをインストール
pip3 install notion-client requests

# 環境変数を設定
export NOTION_TOKEN="ntn_xxxxx..."
export NOTION_DB_BOOK="350fe35c0967807b9af1000b7698f35a"
export NOTION_DB_MANGA="4e6e632c38104b8b91beed975c434e13"  # オプション

# 実行
python3 cover_book.py
```

---

## ⏰ 実行スケジュール

| トリガー | 時刻 |
|---|---|
| 定期実行 | **毎週月曜 09:00 JST** |
| 手動実行 | いつでも（GitHub Actions → Workflow → Run workflow） |

---

## 📊 ログ出力例

```
=== 読みたい本・漫画DB 表紙画像自動入力 ===

📚 読みたい本DB を処理中...

  取得レコード数: 42

  [OK]   藍色炎舞
  [SKIP] プロレタリア文学（表紙あり）
  [SKIP] 世界大百科事典（ISBNなし or 形式不正）
  [OK]   思想の生活と死

  --- 読みたい本DB の結果 ---
    成功: 2 件
    スキップ: 40 件
    失敗: 0 件

📚 読みたい漫画DB を処理中...

  取得レコード数: 15

  [OK]   進撃の巨人 1巻
  [SKIP] 鬼滅の刃（表紙あり）

  --- 読みたい漫画DB の結果 ---
    成功: 1 件
    スキップ: 14 件
    失敗: 0 件

========================================
=== 全体の完了 ===
  成功: 3 件
  スキップ: 54 件
  失敗: 0 件

Notionを開いて表紙が表示されているか確認してください！
```

---

## 🔧 トラブルシューティング

### Q: 「実行に失敗しました」と出た

**A:** GitHub Actions のログを確認：
1. リポジトリ → **Actions** タブ
2. 失敗したワークフローをクリック
3. ログを確認（エラーメッセージを参照）

### Q: 一部の本の表紙が入らない

**A:** 以下を確認：
- Notion に **ISBN** が入力されているか
- ISBN が 10 ~ 13 桁の数字か（ハイフンは削除される）
- Amazon から画像が取得できるか（手動で URL アクセス）

### Q: Notion に「トークンが無効」と出た

**A:** 以下を確認：
- Secrets に登録した `NOTION_TOKEN` が正しいか
- トークンに余計なスペースがないか
- インテグレーションで DB へのアクセス許可があるか

### Q: 漫画DB を追加したい・変更したい

**A:** `cover_book.py` の以下を修正：

```python
DATABASES = []
if DB_BOOK_ID:
    DATABASES.append((DB_BOOK_ID, "読みたい本DB", "書名"))
if DB_MANGA_ID:
    DATABASES.append((DB_MANGA_ID, "読みたい漫画DB", "タイトル"))
```

- 第1要素：環境変数名（Secrets に登録したもの）
- 第2要素：ログ出力用の DB 名
- 第3要素：Notion DB のタイトルプロパティ名

---

## 📝 ファイル構成

```
book-cover-automation/
├── cover_book.py              # メインスクリプト
├── .github/
│   └── workflows/
│       └── cover_book.yml     # GitHub Actions ワークフロー
├── README.md                  # このファイル
└── .gitignore                 # Git 無視ファイル
```

---

## 📌 必要な Notion プロパティ

「読みたい本」「読みたい漫画」など全DB に共通で必須：

| プロパティ名 | 型 | 説明 |
|---|---|---|
| `書名` / `タイトル` | Title | 本・漫画のタイトル |
| `ISBN` | Rich text | 書籍の ISBN |
| `表紙` | Files | 表紙画像（自動入力） |

---

## 📄 ライセンス

MIT

---

## 💬 サポート

問題が発生した場合は、[Issues](https://github.com/YOUR_USERNAME/book-cover-automation/issues) で報告してください。

