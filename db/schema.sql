-- ============================================================
-- 基幹業務システム DB設計（第1フェーズ）
-- 対象: 共通マスタ / 顧客管理 / 販売管理（見積〜支払）/ 在庫引当
-- PostgreSQL 15+ 想定
-- ============================================================

-- ------------------------------------------------------------
-- ENUM型
-- ------------------------------------------------------------
CREATE TYPE partner_type      AS ENUM ('customer', 'supplier', 'both');
CREATE TYPE approval_status   AS ENUM ('draft', 'pending', 'approved', 'rejected');
CREATE TYPE document_status   AS ENUM ('draft', 'confirmed', 'cancelled');
CREATE TYPE price_type        AS ENUM ('sales', 'purchase');
CREATE TYPE allocation_stage  AS ENUM ('quotation', 'order', 'sales');
CREATE TYPE user_role         AS ENUM ('owner', 'member');
CREATE TYPE user_status       AS ENUM ('pending', 'approved', 'rejected');
CREATE TYPE rounding_type     AS ENUM ('floor', 'ceil', 'round');

-- ------------------------------------------------------------
-- ユーザー（承認者・作成者の参照用、およびログインアカウント）
-- role: owner=オーナーメニュー利用可 / member=一般利用者
-- status: pending=アカウント申請中（未ログイン可） / approved=ログイン可 / rejected=却下
-- ------------------------------------------------------------
CREATE TABLE users (
  id             BIGSERIAL PRIMARY KEY,
  employee_code  VARCHAR(20)  UNIQUE NOT NULL,
  name           VARCHAR(100) NOT NULL,
  email          VARCHAR(255) UNIQUE NOT NULL,
  role           user_role    NOT NULL DEFAULT 'member',
  status         user_status  NOT NULL DEFAULT 'pending',
  is_active      BOOLEAN      NOT NULL DEFAULT TRUE,
  created_at     TIMESTAMPTZ  NOT NULL DEFAULT now(),
  updated_at     TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- ------------------------------------------------------------
-- 共通マスタ: 取引先
-- partners      = 識別情報（不変）
-- partner_details = 属性の時系列スナップショット（SCD Type2）
--   → 即時反映/日付指定反映、および変更履歴の参照を
--     「有効日(effective_date)付きの行を積み上げる」ことで実現する。
--     現在値は v_partner_current で取得。将来日付の行を先行登録
--     しておけば、その日を境に自動的に「現在値」が切り替わる。
-- ------------------------------------------------------------
CREATE TABLE partners (
  id            BIGSERIAL PRIMARY KEY,
  partner_code  VARCHAR(20) UNIQUE NOT NULL,
  partner_type  partner_type NOT NULL,
  -- 金額計算（数量×単価）の端数処理方法。伝票明細の作成時にこの値を
  -- そのままコピーして保持する（後でここを変更しても過去の伝票には影響しない）。
  rounding_type rounding_type NOT NULL DEFAULT 'round',
  is_active     BOOLEAN NOT NULL DEFAULT TRUE,
  created_by    BIGINT REFERENCES users(id),
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE partner_details (
  id                    BIGSERIAL PRIMARY KEY,
  partner_id            BIGINT NOT NULL REFERENCES partners(id),
  effective_date        DATE NOT NULL,        -- この日付から有効
  name                  VARCHAR(200) NOT NULL,
  name_kana             VARCHAR(200),
  representative_name   VARCHAR(100),
  postal_code           VARCHAR(10),
  address               VARCHAR(255),
  phone                 VARCHAR(20),
  fax                   VARCHAR(20),
  email                 VARCHAR(255),
  contact_person        VARCHAR(100),
  credit_limit          NUMERIC(14,2),        -- 与信限度額
  remarks               TEXT,                 -- 手入力特記事項（連携情報とは別管理）
  created_by            BIGINT REFERENCES users(id),
  created_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_partner_details_partner_effective
  ON partner_details(partner_id, effective_date DESC);

-- 基準日時点で有効な最新の属性（変更履歴ログとしても機能する）
CREATE VIEW v_partner_current AS
SELECT DISTINCT ON (partner_id) *
FROM partner_details
WHERE effective_date <= CURRENT_DATE
ORDER BY partner_id, effective_date DESC, id DESC;

-- ------------------------------------------------------------
-- 共通マスタ: 商品
-- ------------------------------------------------------------
CREATE TABLE products (
  id                   BIGSERIAL PRIMARY KEY,
  product_code         VARCHAR(30) UNIQUE NOT NULL,
  name                 VARCHAR(200) NOT NULL,
  category             VARCHAR(100),
  unit                 VARCHAR(20) NOT NULL,   -- 個, kg 等
  default_supplier_id  BIGINT REFERENCES partners(id),
  is_active            BOOLEAN NOT NULL DEFAULT TRUE,
  created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ------------------------------------------------------------
-- 共通マスタ: 単価
-- ------------------------------------------------------------
CREATE TABLE price_master (
  id                     BIGSERIAL PRIMARY KEY,
  price_type             price_type NOT NULL,
  partner_id             BIGINT REFERENCES partners(id),  -- NULL = 標準単価
  product_id             BIGINT NOT NULL REFERENCES products(id),
  unit_price             NUMERIC(14,2) NOT NULL,
  effective_start_date   DATE NOT NULL,
  effective_end_date     DATE,
  created_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_price_master_lookup
  ON price_master(price_type, product_id, partner_id, effective_start_date);

-- ------------------------------------------------------------
-- 倉庫 / 在庫
-- ------------------------------------------------------------
CREATE TABLE warehouses (
  id             BIGSERIAL PRIMARY KEY,
  warehouse_code VARCHAR(20) UNIQUE NOT NULL,
  name           VARCHAR(100) NOT NULL
);

CREATE TABLE inventory_stocks (
  id                BIGSERIAL PRIMARY KEY,
  product_id        BIGINT NOT NULL REFERENCES products(id),
  warehouse_id      BIGINT NOT NULL REFERENCES warehouses(id),
  quantity_on_hand  NUMERIC(14,3) NOT NULL DEFAULT 0,
  UNIQUE(product_id, warehouse_id)
);
-- inventory_allocations（見積/受注/売上時点の在庫引当）は
-- quotation_lines / order_lines / sales_lines を参照するため、
-- 本ファイル末尾（該当テーブル定義後）にまとめて定義する。
-- 発注残（＝入庫予定在庫）は v_purchase_order_remaining（下記）で算出する。

-- ============================================================
-- 販売管理チェーン: 見積 → 受注 → 発注 → 仕入 → 売上 → 入金 / 支払
-- 各明細は「1つ上位の明細」への任意(NULL可)の外部キーを持つ。
-- NULLの場合は「上位伝票なしの直接入力」を意味する。
-- 残数(残高)は SUM で都度算出し、テーブルには保持しない
--   （データ不整合を避けるため。件数が増えたら集計テーブル/マテビューを検討）。
-- ============================================================

-- ---------------- 見積 ----------------
CREATE TABLE quotations (
  id               BIGSERIAL PRIMARY KEY,
  quotation_no     VARCHAR(30) UNIQUE NOT NULL,
  partner_id       BIGINT NOT NULL REFERENCES partners(id),
  quotation_date   DATE NOT NULL,
  expiry_date      DATE,                  -- 見積期限
  condition_text   TEXT,                  -- 見積条件
  approval_status  approval_status NOT NULL DEFAULT 'draft',
  approved_by      BIGINT REFERENCES users(id),
  approved_at      TIMESTAMPTZ,
  created_by       BIGINT REFERENCES users(id),
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- 見積書PDFの「仮」印字/社印画像の出し分けは approval_status を参照して
-- アプリケーション層（PDF生成処理）で切り替える。

-- 明細の quantity/unit_price は両方揃っていれば amount を自動計算する
-- （取引先の rounding_type で端数処理し、その丸め方式を rounding_type 列に
-- スナップショットとして保持する。後で取引先マスタの丸め方式を変えても、
-- この明細の再計算には作成時点の rounding_type を使う）。
-- どちらか一方でも未入力の場合のみ amount を直接入力できる。
CREATE TABLE quotation_lines (
  id             BIGSERIAL PRIMARY KEY,
  quotation_id   BIGINT NOT NULL REFERENCES quotations(id),
  line_no        INT NOT NULL,
  product_id     BIGINT NOT NULL REFERENCES products(id),
  quantity       NUMERIC(14,3),
  unit_price     NUMERIC(14,2),
  amount         NUMERIC(16,0) NOT NULL,
  rounding_type  rounding_type NOT NULL,
  UNIQUE(quotation_id, line_no)
);

-- ---------------- 受注 ----------------
CREATE TABLE orders (
  id          BIGSERIAL PRIMARY KEY,
  order_no    VARCHAR(30) UNIQUE NOT NULL,
  partner_id  BIGINT NOT NULL REFERENCES partners(id),
  order_date  DATE NOT NULL,
  status      document_status NOT NULL DEFAULT 'confirmed',
  created_by  BIGINT REFERENCES users(id),
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE order_lines (
  id                  BIGSERIAL PRIMARY KEY,
  order_id            BIGINT NOT NULL REFERENCES orders(id),
  line_no             INT NOT NULL,
  quotation_line_id   BIGINT REFERENCES quotation_lines(id),  -- NULL可: 見積なし直接受注
  product_id          BIGINT NOT NULL REFERENCES products(id),
  quantity            NUMERIC(14,3),
  unit_price          NUMERIC(14,2),
  amount              NUMERIC(16,0) NOT NULL,
  rounding_type       rounding_type NOT NULL,
  UNIQUE(order_id, line_no)
);
CREATE INDEX idx_order_lines_quotation_line ON order_lines(quotation_line_id);

CREATE VIEW v_quotation_remaining AS
SELECT ql.id AS quotation_line_id, ql.quotation_id, ql.quantity AS quoted_qty,
       COALESCE(SUM(ol.quantity), 0) AS ordered_qty,
       GREATEST(ql.quantity - COALESCE(SUM(ol.quantity), 0), 0) AS remaining_qty
FROM quotation_lines ql
LEFT JOIN (order_lines ol JOIN orders o ON o.id = ol.order_id AND o.status <> 'cancelled')
       ON ol.quotation_line_id = ql.id
GROUP BY ql.id, ql.quotation_id, ql.quantity;

-- ---------------- 発注 ----------------
CREATE TABLE purchase_orders (
  id                  BIGSERIAL PRIMARY KEY,
  purchase_order_no   VARCHAR(30) UNIQUE NOT NULL,
  partner_id          BIGINT NOT NULL REFERENCES partners(id),  -- 仕入先
  order_date          DATE NOT NULL,
  status              document_status NOT NULL DEFAULT 'confirmed',
  created_by          BIGINT REFERENCES users(id),
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE purchase_order_lines (
  id                  BIGSERIAL PRIMARY KEY,
  purchase_order_id   BIGINT NOT NULL REFERENCES purchase_orders(id),
  line_no             INT NOT NULL,
  order_line_id       BIGINT REFERENCES order_lines(id),  -- NULL可: 受注なし直接発注
  product_id          BIGINT NOT NULL REFERENCES products(id),
  quantity            NUMERIC(14,3),
  unit_price          NUMERIC(14,2),
  amount              NUMERIC(16,0) NOT NULL,
  rounding_type       rounding_type NOT NULL,
  UNIQUE(purchase_order_id, line_no)
);
CREATE INDEX idx_po_lines_order_line ON purchase_order_lines(order_line_id);

CREATE VIEW v_order_remaining_for_purchase AS
SELECT ol.id AS order_line_id, ol.order_id, ol.quantity AS ordered_qty,
       COALESCE(SUM(pol.quantity), 0) AS purchase_ordered_qty,
       GREATEST(ol.quantity - COALESCE(SUM(pol.quantity), 0), 0) AS remaining_qty
FROM order_lines ol
LEFT JOIN (purchase_order_lines pol JOIN purchase_orders po ON po.id = pol.purchase_order_id AND po.status <> 'cancelled')
       ON pol.order_line_id = ol.id
GROUP BY ol.id, ol.order_id, ol.quantity;

-- ---------------- 仕入 ----------------
CREATE TABLE purchases (
  id             BIGSERIAL PRIMARY KEY,
  purchase_no    VARCHAR(30) UNIQUE NOT NULL,
  partner_id     BIGINT NOT NULL REFERENCES partners(id),
  purchase_date  DATE NOT NULL,
  status         document_status NOT NULL DEFAULT 'confirmed',
  created_by     BIGINT REFERENCES users(id),
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE purchase_lines (
  id                       BIGSERIAL PRIMARY KEY,
  purchase_id              BIGINT NOT NULL REFERENCES purchases(id),
  line_no                  INT NOT NULL,
  purchase_order_line_id   BIGINT REFERENCES purchase_order_lines(id),  -- NULL可: 発注なし直接仕入
  product_id               BIGINT NOT NULL REFERENCES products(id),
  quantity                 NUMERIC(14,3),
  unit_price               NUMERIC(14,2),
  amount                   NUMERIC(16,0) NOT NULL,
  rounding_type            rounding_type NOT NULL,
  UNIQUE(purchase_id, line_no)
);
CREATE INDEX idx_purchase_lines_po_line ON purchase_lines(purchase_order_line_id);

CREATE VIEW v_purchase_order_remaining AS
SELECT pol.id AS purchase_order_line_id, pol.purchase_order_id, pol.quantity AS ordered_qty,
       COALESCE(SUM(pl.quantity), 0) AS purchased_qty,
       GREATEST(pol.quantity - COALESCE(SUM(pl.quantity), 0), 0) AS remaining_qty  -- ≒ 入庫予定在庫
FROM purchase_order_lines pol
LEFT JOIN (purchase_lines pl JOIN purchases p ON p.id = pl.purchase_id AND p.status <> 'cancelled')
       ON pl.purchase_order_line_id = pol.id
GROUP BY pol.id, pol.purchase_order_id, pol.quantity;

-- ---------------- 売上 ----------------
CREATE TABLE sales (
  id          BIGSERIAL PRIMARY KEY,
  sales_no    VARCHAR(30) UNIQUE NOT NULL,
  partner_id  BIGINT NOT NULL REFERENCES partners(id),
  sales_date  DATE NOT NULL,
  status      document_status NOT NULL DEFAULT 'confirmed',
  created_by  BIGINT REFERENCES users(id),
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE sales_lines (
  id              BIGSERIAL PRIMARY KEY,
  sales_id        BIGINT NOT NULL REFERENCES sales(id),
  line_no         INT NOT NULL,
  order_line_id   BIGINT REFERENCES order_lines(id),  -- NULL可: 受注なし直接売上
  product_id      BIGINT NOT NULL REFERENCES products(id),
  quantity        NUMERIC(14,3),
  unit_price      NUMERIC(14,2),
  amount          NUMERIC(16,0) NOT NULL,
  rounding_type   rounding_type NOT NULL,
  UNIQUE(sales_id, line_no)
);
CREATE INDEX idx_sales_lines_order_line ON sales_lines(order_line_id);

CREATE VIEW v_order_remaining_for_sales AS
SELECT ol.id AS order_line_id, ol.order_id, ol.quantity AS ordered_qty,
       COALESCE(SUM(sl.quantity), 0) AS sold_qty,
       GREATEST(ol.quantity - COALESCE(SUM(sl.quantity), 0), 0) AS remaining_qty
FROM order_lines ol
LEFT JOIN (sales_lines sl JOIN sales s ON s.id = sl.sales_id AND s.status <> 'cancelled')
       ON sl.order_line_id = ol.id
GROUP BY ol.id, ol.order_id, ol.quantity;

-- 見積時点/受注時点/売上時点の在庫引当を独立管理
-- (3ステージのうちどれか1つだけを参照するようCHECK制約で強制)
CREATE TABLE inventory_allocations (
  id                 BIGSERIAL PRIMARY KEY,
  allocation_stage   allocation_stage NOT NULL,
  quotation_line_id  BIGINT REFERENCES quotation_lines(id),
  order_line_id      BIGINT REFERENCES order_lines(id),
  sales_line_id      BIGINT REFERENCES sales_lines(id),
  product_id         BIGINT NOT NULL REFERENCES products(id),
  warehouse_id       BIGINT REFERENCES warehouses(id),
  quantity           NUMERIC(14,3) NOT NULL,
  created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT chk_allocation_source CHECK (
    (allocation_stage = 'quotation' AND quotation_line_id IS NOT NULL AND order_line_id IS NULL AND sales_line_id IS NULL) OR
    (allocation_stage = 'order'     AND order_line_id     IS NOT NULL AND quotation_line_id IS NULL AND sales_line_id IS NULL) OR
    (allocation_stage = 'sales'     AND sales_line_id     IS NOT NULL AND quotation_line_id IS NULL AND order_line_id IS NULL)
  )
);

-- ---------------- 入金 ----------------
CREATE TABLE receipts (
  id              BIGSERIAL PRIMARY KEY,
  receipt_no      VARCHAR(30) UNIQUE NOT NULL,
  partner_id      BIGINT NOT NULL REFERENCES partners(id),
  receipt_date    DATE NOT NULL,
  payment_method  VARCHAR(30),
  status          document_status NOT NULL DEFAULT 'confirmed',
  created_by      BIGINT REFERENCES users(id),
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE receipt_lines (
  id              BIGSERIAL PRIMARY KEY,
  receipt_id      BIGINT NOT NULL REFERENCES receipts(id),
  line_no         INT NOT NULL,
  sales_line_id   BIGINT REFERENCES sales_lines(id),  -- NULL可: 売上なし直接入金
  amount          NUMERIC(16,2) NOT NULL,
  UNIQUE(receipt_id, line_no)
);
CREATE INDEX idx_receipt_lines_sales_line ON receipt_lines(sales_line_id);

CREATE VIEW v_sales_remaining_for_receipt AS
SELECT sl.id AS sales_line_id, sl.sales_id, sl.amount AS sales_amount,
       COALESCE(SUM(rl.amount), 0) AS received_amount,
       GREATEST(sl.amount - COALESCE(SUM(rl.amount), 0), 0) AS remaining_amount
FROM sales_lines sl
LEFT JOIN (receipt_lines rl JOIN receipts r ON r.id = rl.receipt_id AND r.status <> 'cancelled')
       ON rl.sales_line_id = sl.id
GROUP BY sl.id, sl.sales_id, sl.amount;

-- ---------------- 支払 ----------------
CREATE TABLE payments (
  id              BIGSERIAL PRIMARY KEY,
  payment_no      VARCHAR(30) UNIQUE NOT NULL,
  partner_id      BIGINT NOT NULL REFERENCES partners(id),
  payment_date    DATE NOT NULL,
  payment_method  VARCHAR(30),
  status          document_status NOT NULL DEFAULT 'confirmed',
  created_by      BIGINT REFERENCES users(id),
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE payment_lines (
  id                BIGSERIAL PRIMARY KEY,
  payment_id        BIGINT NOT NULL REFERENCES payments(id),
  line_no           INT NOT NULL,
  purchase_line_id  BIGINT REFERENCES purchase_lines(id),  -- NULL可: 仕入なし直接支払
  amount            NUMERIC(16,2) NOT NULL,
  UNIQUE(payment_id, line_no)
);
CREATE INDEX idx_payment_lines_purchase_line ON payment_lines(purchase_line_id);

CREATE VIEW v_purchase_remaining_for_payment AS
SELECT pl.id AS purchase_line_id, pl.purchase_id, pl.amount AS purchase_amount,
       COALESCE(SUM(payl.amount), 0) AS paid_amount,
       GREATEST(pl.amount - COALESCE(SUM(payl.amount), 0), 0) AS remaining_amount
FROM purchase_lines pl
LEFT JOIN (payment_lines payl JOIN payments pm ON pm.id = payl.payment_id AND pm.status <> 'cancelled')
       ON payl.purchase_line_id = pl.id
GROUP BY pl.id, pl.purchase_id, pl.amount;
