-- ============================================================
-- マイグレーション 0002: 金額の端数処理（丸め区分）対応
--
-- - 取引先(partners)に rounding_type（切り捨て/切り上げ/四捨五入）を追加
-- - 見積/受注/発注/仕入/売上の明細: quantity/unit_price を任意入力化し、
--   amount を整数化(NUMERIC(16,0))、rounding_type をスナップショットとして追加
--   （数量・単価が両方揃っている場合のみ自動計算、どちらか欠けている場合は
--   amount を直接入力する）
--
-- 既存明細の rounding_type は、紐づく伝票の取引先が「現時点で」設定している
-- 丸め区分で暫定的にバックフィルする（過去の実際の計算方法を遡って復元する
-- 手段がないため。以後の変更はすべて作成時点の値がスナップショットされる）。
-- ============================================================

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'rounding_type') THEN
    CREATE TYPE rounding_type AS ENUM ('floor', 'ceil', 'round');
  END IF;
END $$;

ALTER TABLE partners ADD COLUMN IF NOT EXISTS rounding_type rounding_type NOT NULL DEFAULT 'round';

-- purchase_lines.amount / sales_lines.amount は v_purchase_remaining_for_payment /
-- v_sales_remaining_for_receipt から参照されているため、型変更の前に一旦削除する
-- （末尾で再作成する）。
DROP VIEW IF EXISTS v_purchase_remaining_for_payment;
DROP VIEW IF EXISTS v_sales_remaining_for_receipt;

-- ---------------- 見積明細 ----------------
ALTER TABLE quotation_lines ALTER COLUMN quantity DROP NOT NULL;
ALTER TABLE quotation_lines ALTER COLUMN unit_price DROP NOT NULL;
ALTER TABLE quotation_lines ADD COLUMN IF NOT EXISTS rounding_type rounding_type;
UPDATE quotation_lines ql SET rounding_type = p.rounding_type
  FROM quotations q JOIN partners p ON p.id = q.partner_id
  WHERE ql.quotation_id = q.id AND ql.rounding_type IS NULL;
ALTER TABLE quotation_lines ALTER COLUMN rounding_type SET NOT NULL;
ALTER TABLE quotation_lines ALTER COLUMN amount TYPE NUMERIC(16,0);

-- ---------------- 受注明細 ----------------
ALTER TABLE order_lines ALTER COLUMN quantity DROP NOT NULL;
ALTER TABLE order_lines ALTER COLUMN unit_price DROP NOT NULL;
ALTER TABLE order_lines ADD COLUMN IF NOT EXISTS rounding_type rounding_type;
UPDATE order_lines ol SET rounding_type = p.rounding_type
  FROM orders o JOIN partners p ON p.id = o.partner_id
  WHERE ol.order_id = o.id AND ol.rounding_type IS NULL;
ALTER TABLE order_lines ALTER COLUMN rounding_type SET NOT NULL;
ALTER TABLE order_lines ALTER COLUMN amount TYPE NUMERIC(16,0);

-- ---------------- 発注明細 ----------------
ALTER TABLE purchase_order_lines ALTER COLUMN quantity DROP NOT NULL;
ALTER TABLE purchase_order_lines ALTER COLUMN unit_price DROP NOT NULL;
ALTER TABLE purchase_order_lines ADD COLUMN IF NOT EXISTS rounding_type rounding_type;
UPDATE purchase_order_lines pol SET rounding_type = p.rounding_type
  FROM purchase_orders po JOIN partners p ON p.id = po.partner_id
  WHERE pol.purchase_order_id = po.id AND pol.rounding_type IS NULL;
ALTER TABLE purchase_order_lines ALTER COLUMN rounding_type SET NOT NULL;
ALTER TABLE purchase_order_lines ALTER COLUMN amount TYPE NUMERIC(16,0);

-- ---------------- 仕入明細 ----------------
ALTER TABLE purchase_lines ALTER COLUMN quantity DROP NOT NULL;
ALTER TABLE purchase_lines ALTER COLUMN unit_price DROP NOT NULL;
ALTER TABLE purchase_lines ADD COLUMN IF NOT EXISTS rounding_type rounding_type;
UPDATE purchase_lines pl SET rounding_type = p.rounding_type
  FROM purchases pu JOIN partners p ON p.id = pu.partner_id
  WHERE pl.purchase_id = pu.id AND pl.rounding_type IS NULL;
ALTER TABLE purchase_lines ALTER COLUMN rounding_type SET NOT NULL;
ALTER TABLE purchase_lines ALTER COLUMN amount TYPE NUMERIC(16,0);

-- ---------------- 売上明細 ----------------
ALTER TABLE sales_lines ALTER COLUMN quantity DROP NOT NULL;
ALTER TABLE sales_lines ALTER COLUMN unit_price DROP NOT NULL;
ALTER TABLE sales_lines ADD COLUMN IF NOT EXISTS rounding_type rounding_type;
UPDATE sales_lines sl SET rounding_type = p.rounding_type
  FROM sales s JOIN partners p ON p.id = s.partner_id
  WHERE sl.sales_id = s.id AND sl.rounding_type IS NULL;
ALTER TABLE sales_lines ALTER COLUMN rounding_type SET NOT NULL;
ALTER TABLE sales_lines ALTER COLUMN amount TYPE NUMERIC(16,0);

-- 冒頭で削除した2ビューを再作成する
CREATE VIEW v_sales_remaining_for_receipt AS
SELECT sl.id AS sales_line_id, sl.sales_id, sl.amount AS sales_amount,
       COALESCE(SUM(rl.amount), 0) AS received_amount,
       GREATEST(sl.amount - COALESCE(SUM(rl.amount), 0), 0) AS remaining_amount
FROM sales_lines sl
LEFT JOIN receipt_lines rl ON rl.sales_line_id = sl.id
GROUP BY sl.id, sl.sales_id, sl.amount;

CREATE VIEW v_purchase_remaining_for_payment AS
SELECT pl.id AS purchase_line_id, pl.purchase_id, pl.amount AS purchase_amount,
       COALESCE(SUM(payl.amount), 0) AS paid_amount,
       GREATEST(pl.amount - COALESCE(SUM(payl.amount), 0), 0) AS remaining_amount
FROM purchase_lines pl
LEFT JOIN payment_lines payl ON payl.purchase_line_id = pl.id
GROUP BY pl.id, pl.purchase_id, pl.amount;
