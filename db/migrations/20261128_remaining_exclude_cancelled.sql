-- 残数ビューで、取り消し（cancelled）された下位伝票の数量・金額を数えないようにする。
-- 以前は取り消した受注・売上なども残数から差し引かれ、残数が実際より少なく出ていた。
-- schema.sql の同名ビューと同じ定義。何度流しても同じ結果になる（CREATE OR REPLACE）。

CREATE OR REPLACE VIEW v_quotation_remaining AS
SELECT ql.id AS quotation_line_id, ql.quotation_id, ql.quantity AS quoted_qty,
       COALESCE(SUM(ol.quantity), 0) AS ordered_qty,
       GREATEST(ql.quantity - COALESCE(SUM(ol.quantity), 0), 0) AS remaining_qty
FROM quotation_lines ql
LEFT JOIN (order_lines ol JOIN orders o ON o.id = ol.order_id AND o.status <> 'cancelled')
       ON ol.quotation_line_id = ql.id
GROUP BY ql.id, ql.quotation_id, ql.quantity;

CREATE OR REPLACE VIEW v_order_remaining_for_purchase AS
SELECT ol.id AS order_line_id, ol.order_id, ol.quantity AS ordered_qty,
       COALESCE(SUM(pol.quantity), 0) AS purchase_ordered_qty,
       GREATEST(ol.quantity - COALESCE(SUM(pol.quantity), 0), 0) AS remaining_qty
FROM order_lines ol
LEFT JOIN (purchase_order_lines pol JOIN purchase_orders po ON po.id = pol.purchase_order_id AND po.status <> 'cancelled')
       ON pol.order_line_id = ol.id
GROUP BY ol.id, ol.order_id, ol.quantity;

CREATE OR REPLACE VIEW v_purchase_order_remaining AS
SELECT pol.id AS purchase_order_line_id, pol.purchase_order_id, pol.quantity AS ordered_qty,
       COALESCE(SUM(pl.quantity), 0) AS purchased_qty,
       GREATEST(pol.quantity - COALESCE(SUM(pl.quantity), 0), 0) AS remaining_qty  -- ≒ 入庫予定在庫
FROM purchase_order_lines pol
LEFT JOIN (purchase_lines pl JOIN purchases p ON p.id = pl.purchase_id AND p.status <> 'cancelled')
       ON pl.purchase_order_line_id = pol.id
GROUP BY pol.id, pol.purchase_order_id, pol.quantity;

CREATE OR REPLACE VIEW v_order_remaining_for_sales AS
SELECT ol.id AS order_line_id, ol.order_id, ol.quantity AS ordered_qty,
       COALESCE(SUM(sl.quantity), 0) AS sold_qty,
       GREATEST(ol.quantity - COALESCE(SUM(sl.quantity), 0), 0) AS remaining_qty
FROM order_lines ol
LEFT JOIN (sales_lines sl JOIN sales s ON s.id = sl.sales_id AND s.status <> 'cancelled')
       ON sl.order_line_id = ol.id
GROUP BY ol.id, ol.order_id, ol.quantity;

CREATE OR REPLACE VIEW v_sales_remaining_for_receipt AS
SELECT sl.id AS sales_line_id, sl.sales_id, sl.amount AS sales_amount,
       COALESCE(SUM(rl.amount), 0) AS received_amount,
       GREATEST(sl.amount - COALESCE(SUM(rl.amount), 0), 0) AS remaining_amount
FROM sales_lines sl
LEFT JOIN (receipt_lines rl JOIN receipts r ON r.id = rl.receipt_id AND r.status <> 'cancelled')
       ON rl.sales_line_id = sl.id
GROUP BY sl.id, sl.sales_id, sl.amount;

CREATE OR REPLACE VIEW v_purchase_remaining_for_payment AS
SELECT pl.id AS purchase_line_id, pl.purchase_id, pl.amount AS purchase_amount,
       COALESCE(SUM(payl.amount), 0) AS paid_amount,
       GREATEST(pl.amount - COALESCE(SUM(payl.amount), 0), 0) AS remaining_amount
FROM purchase_lines pl
LEFT JOIN (payment_lines payl JOIN payments pm ON pm.id = payl.payment_id AND pm.status <> 'cancelled')
       ON payl.purchase_line_id = pl.id
GROUP BY pl.id, pl.purchase_id, pl.amount;
