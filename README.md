# kaname — 基幹業務システム

全業務をカバーする統合基幹業務システム（ERP）。第1フェーズとして、共通マスタ／顧客管理／販売管理チェーン（見積〜支払）／在庫引当を実装している。

本番: **https://kaname.ajesta.work/**（Google OAuth認証、許可アカウントのみ）

機能一覧の全体像は [`基幹業務システム機能一覧.md`](./基幹業務システム機能一覧.md) を参照。

## 技術スタック

| レイヤー | 技術 |
|---|---|
| フロントエンド | Next.js（App Router, TypeScript） |
| バックエンド | Python（FastAPI + SQLAlchemy） |
| データベース | PostgreSQL |
| API | REST / OpenAPI |
| 認証 | Google OAuth（許可メールアドレスのみ） |

## ディレクトリ構成

```
db/       DB設計（schema.sql, ER図・設計方針）
api/      OpenAPI仕様の骨子
backend/  FastAPI アプリケーション
frontend/ Next.js アプリケーション
```

各ディレクトリの詳細:

- **`db/schema.sql`** — PostgreSQL DDL（テーブル・ビュー・ENUM一式）。テーブル定義の正本。
- **`db/db_design.md`** — ER図と設計方針（取引先マスタの時系列管理、伝票チェーンの残数管理ロジック等）
- **`api/openapi.yaml`** — 設計時点のAPI骨子（実際のAPIは起動中のバックエンドが `/openapi.json` として自動生成する方が最新）
- **`backend/app/`** — `models.py`（ORM）, `schemas.py`（Pydantic）, `routers/`（エンドポイント）, `security.py`（Google OAuth・セッション認証）
- **`frontend/app/`** — 画面（App Router）。`(app)/` 配下が認証必須のダッシュボード、`login/` がログイン画面

## 業務フローの要点

見積 → 受注 → 発注 → 仕入 → 売上 → 入金 / 支払 の各伝票は、上位明細への任意リンクと残数管理で連携している（例: 見積10個のうち7個を受注確定すると見積残3を自動算出）。詳細は `db/db_design.md` を参照。

## セットアップ（ローカル開発）

前提: PostgreSQL 15+, Python 3.12+, Node.js 22+

### 1. データベース

```bash
sudo -u postgres psql -c "CREATE USER kaname WITH PASSWORD 'kaname';"
sudo -u postgres psql -c "CREATE DATABASE kaname OWNER kaname;"
```

### 2. バックエンド

```bash
cd backend
python3 -m venv venv
./venv/bin/pip install -r requirements.txt

cp .env.example .env
# .env を編集: GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET 等を設定

./venv/bin/python scripts/init_db.py   # schema.sql を適用
./venv/bin/uvicorn app.main:app --reload --port 8000
```

### 3. フロントエンド

```bash
cd frontend
npm install

cp .env.local.example .env.local
# NEXT_PUBLIC_API_BASE_URL をバックエンドのURLに合わせて編集

npm run dev
```

### サンプルデータ

各テーブル100件規模のデモデータを投入する場合:

```bash
cd backend
./venv/bin/pip install -r requirements-dev.txt
source .env && ./venv/bin/python scripts/seed_demo_data.py
```

見積残・受注残などの消込ロジックを踏まえた、リンク付き/直接入力混在のデータが生成される。

## 認証

Google OAuthでログインし、`ALLOWED_EMAILS`（`.env`、カンマ区切り）に含まれるメールアドレスのみアクセスできる。認証の実体はバックエンドのセッションCookieが担い、フロントエンドの `proxy.ts` はUX目的の簡易リダイレクトのみ行う。

## 本番構成

`kaname.ajesta.work` は nginx リバースプロキシ配下で以下の2つの systemd サービスとして稼働している（フロント/バックエンドを同一オリジンにまとめ、`/api/` `/auth/` のみバックエンドへプロキシ）。

- `kaname-backend.service` — gunicorn + uvicorn worker（`127.0.0.1:8010`）
- `kaname-frontend.service` — Next.js本番サーバー（`127.0.0.1:3001`）

SSL証明書はCertbotで発行・自動更新。
