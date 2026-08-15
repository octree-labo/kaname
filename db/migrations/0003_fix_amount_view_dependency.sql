-- ============================================================
-- マイグレーション 0003: 0002適用時に発生したビュー依存エラーの修正
--
-- purchase_lines.amount / sales_lines.amount は
-- v_purchase_remaining_for_payment / v_sales_remaining_for_receipt から
-- 直接参照されているため、型変更(NUMERIC(16,2)→NUMERIC(16,0))には
-- 事前にビューを削除し、変更後に再作成する必要がある。
-- schema.sql は最初からこの順序で書かれているため、新規構築では不要。
-- ============================================================

DROP VIEW IF EXISTS v_purchase_remaining_for_payment;
DROP VIEW IF EXISTS v_sales_remaining_for_receipt;

ALTER TABLE purchase_lines ALTER COLUMN amount TYPE NUMERIC(16,0);
ALTER TABLE sales_lines ALTER COLUMN amount TYPE NUMERIC(16,0);

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
