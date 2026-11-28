-- 仕入・売上で在庫数を増減させるための変更。
-- 1) 仕入明細・売上明細に倉庫を持たせる
-- 2) 在庫の受払（入庫・出庫）の履歴テーブル inventory_movements を作る
-- 3) 既にある確定済みの仕入・売上は「移行時の既存分」として履歴だけ作り、在庫数は変えない
--    （いまの在庫数は、これまでの仕入・売上を反映済みの数として扱う）
-- 何度流しても同じ結果になる。

ALTER TABLE purchase_lines ADD COLUMN IF NOT EXISTS warehouse_id BIGINT REFERENCES warehouses(id);
ALTER TABLE sales_lines    ADD COLUMN IF NOT EXISTS warehouse_id BIGINT REFERENCES warehouses(id);

CREATE TABLE IF NOT EXISTS inventory_movements (
  id                BIGSERIAL PRIMARY KEY,
  product_id        BIGINT NOT NULL REFERENCES products(id),
  warehouse_id      BIGINT NOT NULL REFERENCES warehouses(id),
  quantity          NUMERIC(14,3) NOT NULL,          -- 入庫はプラス、出庫はマイナス
  movement_type     VARCHAR(20) NOT NULL,            -- purchase（仕入）/ sales（売上）
  purchase_line_id  BIGINT REFERENCES purchase_lines(id),
  sales_line_id     BIGINT REFERENCES sales_lines(id),
  migrated          BOOLEAN NOT NULL DEFAULT FALSE,  -- 移行時の既存分（在庫数には反映していない）
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT chk_movement_source CHECK (
    (movement_type = 'purchase' AND purchase_line_id IS NOT NULL AND sales_line_id IS NULL) OR
    (movement_type = 'sales'    AND sales_line_id    IS NOT NULL AND purchase_line_id IS NULL)
  )
);
CREATE INDEX IF NOT EXISTS idx_inventory_movements_purchase_line ON inventory_movements(purchase_line_id);
CREATE INDEX IF NOT EXISTS idx_inventory_movements_sales_line    ON inventory_movements(sales_line_id);
CREATE INDEX IF NOT EXISTS idx_inventory_movements_product       ON inventory_movements(product_id, warehouse_id);

-- 既存の明細の倉庫は、いちばん古い倉庫にする
UPDATE purchase_lines SET warehouse_id = (SELECT MIN(id) FROM warehouses) WHERE warehouse_id IS NULL;
UPDATE sales_lines    SET warehouse_id = (SELECT MIN(id) FROM warehouses) WHERE warehouse_id IS NULL;

-- 既存の確定済み伝票の受払履歴（在庫数は変えない）
INSERT INTO inventory_movements (product_id, warehouse_id, quantity, movement_type, purchase_line_id, migrated)
SELECT pl.product_id, pl.warehouse_id, pl.quantity, 'purchase', pl.id, TRUE
FROM purchase_lines pl JOIN purchases p ON p.id = pl.purchase_id
WHERE p.status = 'confirmed' AND pl.quantity IS NOT NULL AND pl.warehouse_id IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM inventory_movements m WHERE m.purchase_line_id = pl.id);

INSERT INTO inventory_movements (product_id, warehouse_id, quantity, movement_type, sales_line_id, migrated)
SELECT sl.product_id, sl.warehouse_id, -sl.quantity, 'sales', sl.id, TRUE
FROM sales_lines sl JOIN sales s ON s.id = sl.sales_id
WHERE s.status = 'confirmed' AND sl.quantity IS NOT NULL AND sl.warehouse_id IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM inventory_movements m WHERE m.sales_line_id = sl.id);
