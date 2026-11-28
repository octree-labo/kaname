"""伝票チェーン・残数・引当の動作確認スクリプト（空のテスト用 DB で実行する）。

使い方（本番 DB では絶対に実行しないこと。データを作るため）:
    createdb kaname_test
    DATABASE_URL=postgresql+psycopg://.../kaname_test python scripts/init_db.py
    DATABASE_URL=postgresql+psycopg://.../kaname_test python tests/check_document_chain.py

pytest を入れていない環境でも動くように、素の assert で書いている。
"""
from __future__ import annotations

import os
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

if not os.environ.get("DATABASE_URL", "").rstrip("/").endswith("_test"):
    sys.exit("DATABASE_URL がテスト用 DB（名前が _test で終わる）を指していません。中止します。")

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app import models  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.security import SessionUser, get_current_user, get_viewer  # noqa: E402

USER = SessionUser(id=None, email="test@example.com", name="test", role="owner")
app.dependency_overrides[get_current_user] = lambda: USER
app.dependency_overrides[get_viewer] = lambda: USER
client = TestClient(app)


def api(method: str, path: str, expect: int = 200, **kw):
    res = client.request(method, "/api" + path, **kw)
    assert res.status_code == expect, f"{method} {path} -> {res.status_code}: {res.text}"
    return res.json()


def setup_masters() -> dict:
    with SessionLocal() as db:
        db.execute(text(
            "TRUNCATE inventory_movements, inventory_allocations, receipt_lines, receipts, payment_lines, payments, sales_lines, sales, "
            "purchase_lines, purchases, purchase_order_lines, purchase_orders, order_lines, orders, "
            "quotation_lines, quotations, price_master, inventory_stocks, warehouses, products, "
            "partner_details, partners RESTART IDENTITY CASCADE"
        ))
        db.commit()
    cust = api("POST", "/partners", 201, json={"partnerType": "customer", "roundingType": "floor",
               "detail": {"name": "テスト得意先", "effectiveDate": "2020-01-01"}})
    cust2 = api("POST", "/partners", 201, json={"partnerType": "customer", "roundingType": "floor",
                "detail": {"name": "別の得意先", "effectiveDate": "2020-01-01"}})
    supp = api("POST", "/partners", 201, json={"partnerType": "supplier", "roundingType": "floor",
               "detail": {"name": "テスト仕入先", "effectiveDate": "2020-01-01"}})
    p1 = api("POST", "/products", 201, json={"name": "商品A", "unit": "個"})
    p2 = api("POST", "/products", 201, json={"name": "商品B", "unit": "個"})
    with SessionLocal() as db:
        wh = models.Warehouse(warehouse_code="W1", name="本社倉庫")
        db.add(wh)
        db.flush()
        db.add(models.InventoryStock(product_id=p1["id"], warehouse_id=wh.id, quantity_on_hand=Decimal(100)))
        db.commit()
    return {"cust": cust["id"], "cust2": cust2["id"], "supp": supp["id"], "p1": p1["id"], "p2": p2["id"]}


def main() -> None:
    m = setup_masters()
    print("masters ok")

    # --- 見積 → 受注（一部）→ 見積全体の受注確定で二重受注しない ---
    q = api("POST", "/quotations", 201, json={"partnerId": m["cust"], "quotationDate": "2026-11-01", "lines": [
        {"productId": m["p1"], "quantity": 10, "unitPrice": 100},
        {"productId": m["p2"], "quantity": 5, "unitPrice": 200},
    ]})
    q_lines = api("GET", f"/quotations/{q['id']}/lines")
    ql1, ql2 = q_lines[0]["id"], q_lines[1]["id"]
    o1 = api("POST", f"/quotations/{q['id']}/confirm-orders", 201, json={
        "mode": "selected_lines", "lineSelections": [{"quotationLineId": ql1, "quantity": 7}]})
    o2 = api("POST", f"/quotations/{q['id']}/confirm-orders", 201, json={"mode": "whole_document"})
    o2_detail = api("GET", f"/orders/{o2['id']}")
    qtys = sorted((Decimal(str(l["quantity"])), l["productId"]) for l in o2_detail["lines"])
    assert qtys == [(Decimal(3), m["p1"]), (Decimal(5), m["p2"])], qtys
    api("POST", f"/quotations/{q['id']}/confirm-orders", 400, json={"mode": "whole_document"})
    print("confirm-orders uses remaining ok")

    # --- 取り消した受注は見積残に戻る ---
    api("PATCH", f"/orders/{o2['id']}", json={"status": "cancelled"})
    rem = {l["id"]: Decimal(str(l["remainingQty"])) for l in api("GET", f"/quotations/{q['id']}/lines")}
    assert rem[ql1] == 3 and rem[ql2] == 5, rem
    print("cancelled order restores quotation remaining ok")

    # --- 上位明細の検証 ---
    o1_line = api("GET", f"/orders/{o1['id']}")["lines"][0]["id"]
    api("POST", "/sales", 400, json={"partnerId": m["cust2"], "salesDate": "2026-11-05", "lines": [
        {"productId": m["p1"], "quantity": 1, "unitPrice": 100, "orderLineId": o1_line}]})  # 別の得意先
    api("POST", "/sales", 400, json={"partnerId": m["cust"], "salesDate": "2026-11-05", "lines": [
        {"productId": m["p2"], "quantity": 1, "unitPrice": 100, "orderLineId": o1_line}]})  # 別の商品
    api("POST", "/sales", 400, json={"partnerId": m["cust"], "salesDate": "2026-11-05", "lines": [
        {"productId": m["p1"], "quantity": 1, "unitPrice": 100, "orderLineId": 999999}]})  # 存在しない
    api("POST", "/sales", 400, json={"partnerId": m["cust"], "salesDate": "2026-11-05", "lines": [
        {"productId": m["p1"], "quantity": 1, "unitPrice": 100, "orderLineId": api("GET", f"/orders/{o2['id']}")["lines"][0]["id"]}]})  # 取消済み
    api("POST", "/sales", 400, json={"partnerId": m["cust"], "salesDate": "2026-11-05", "lines": []})  # 明細なし
    print("upstream validation ok")

    # --- 残のある上位明細の一覧 ---
    open_for_sales = api("GET", "/open-lines/order_for_sales", params={"partner_id": m["cust"]})
    assert [(l["lineId"], Decimal(str(l["remainingQty"]))) for l in open_for_sales] == [(o1_line, Decimal(7))], open_for_sales
    assert api("GET", "/open-lines/order_for_sales", params={"partner_id": m["cust2"]}) == []
    api("GET", "/open-lines/unknown", 404)

    s = api("POST", "/sales", 201, json={"partnerId": m["cust"], "salesDate": "2026-11-06", "lines": [
        {"productId": m["p1"], "quantity": 4, "unitPrice": 100, "orderLineId": o1_line}]})
    open_for_sales = api("GET", "/open-lines/order_for_sales", params={"partner_id": m["cust"]})
    assert Decimal(str(open_for_sales[0]["remainingQty"])) == 3, open_for_sales
    s_line = api("GET", f"/sales/{s['id']}")["lines"][0]["id"]
    open_recv = api("GET", "/open-lines/sales", params={"partner_id": m["cust"]})
    assert open_recv[0]["lineId"] == s_line and Decimal(str(open_recv[0]["remainingAmount"])) == 400, open_recv
    api("POST", "/receipts", 201, json={"partnerId": m["cust"], "receiptDate": "2026-11-10", "lines": [
        {"amount": 150, "salesLineId": s_line}]})
    open_recv = api("GET", "/open-lines/sales", params={"partner_id": m["cust"]})
    assert Decimal(str(open_recv[0]["remainingAmount"])) == 250, open_recv
    api("POST", "/receipts", 400, json={"partnerId": m["cust2"], "receiptDate": "2026-11-10", "lines": [
        {"amount": 10, "salesLineId": s_line}]})
    print("open lines ok")

    # --- 発注（受注→発注は取引先が違ってよい）と入荷予定 ---
    po = api("POST", "/purchase-orders", 201, json={"partnerId": m["supp"], "orderDate": "2026-11-02", "lines": [
        {"productId": m["p1"], "quantity": 30, "unitPrice": 60, "orderLineId": o1_line}]})
    po_line = api("GET", f"/purchase-orders/{po['id']}")["lines"][0]["id"]
    pu = api("POST", "/purchases", 201, json={"partnerId": m["supp"], "purchaseDate": "2026-11-08", "lines": [
        {"productId": m["p1"], "quantity": 10, "unitPrice": 60, "purchaseOrderLineId": po_line}]})

    # --- 引当と使える見込み ---
    api("POST", "/inventory/allocations", 201, json={"allocationStage": "quotation", "quotationLineId": ql1,
        "productId": m["p1"], "quantity": 10})   # 見積残は 3 → 3 だけ数える
    api("POST", "/inventory/allocations", 201, json={"allocationStage": "order", "orderLineId": o1_line,
        "productId": m["p1"], "quantity": 7})    # 売上にしていない残は 3 → 3 だけ数える
    api("POST", "/inventory/allocations", 201, json={"allocationStage": "sales", "salesLineId": s_line,
        "productId": m["p1"], "quantity": 4})    # 売上は確定済みで在庫数が減っているので数えない
    api("POST", "/inventory/allocations", 400, json={"allocationStage": "order", "orderLineId": o1_line,
        "productId": m["p2"], "quantity": 1})    # 商品が違う
    api("POST", "/inventory/allocations", 400, json={"allocationStage": "order", "productId": m["p1"], "quantity": 1})
    avail = {a["productId"]: a for a in api("GET", "/inventory/availability")}
    a1 = avail[m["p1"]]
    got = tuple(Decimal(str(a1[k])) for k in ("onHand", "allocated", "incoming", "available"))
    # 在庫 100 − 売上 4 + 仕入 10 = 106、引当 3 + 3 = 6、入荷予定 30 − 10 = 20
    assert got == (Decimal(106), Decimal(6), Decimal(20), Decimal(120)), got
    print("availability ok")

    # --- 更新で上位明細と商品が食い違わない ---
    s_detail = api("GET", f"/sales/{s['id']}")
    api("PATCH", f"/sales/{s['id']}", 400, json={"lines": [{"id": s_detail["lines"][0]["id"], "productId": m["p2"]}]})
    api("PATCH", f"/sales/{s['id']}", 400, json={"partnerId": m["cust2"]})
    # 上位の受注を取り消したあとでも、この売上は取り消せる
    api("PATCH", f"/orders/{o1['id']}", json={"status": "cancelled"})
    api("PATCH", f"/sales/{s['id']}", json={"status": "cancelled"})
    print("update validation ok")

    # --- 在庫の受払 ---
    def stock(product_id: int, warehouse_code: str = "W1") -> Decimal:
        rows = api("GET", "/inventory/stocks", params={"product_id": product_id})
        return sum((Decimal(str(r["quantityOnHand"])) for r in rows if r["warehouseCode"] == warehouse_code), Decimal(0))

    assert stock(m["p1"]) == 110, stock(m["p1"])  # 売上 4 を取り消したので 106 + 4
    pu_line = api("GET", f"/purchases/{pu['id']}")["lines"][0]
    assert pu_line["warehouseId"] is not None
    api("PATCH", f"/purchases/{pu['id']}", json={"lines": [{"id": pu_line["id"], "quantity": 12}]})
    assert stock(m["p1"]) == 112, stock(m["p1"])  # 仕入を 10 → 12 に訂正
    with SessionLocal() as db:
        db.add(models.Warehouse(warehouse_code="W2", name="第二倉庫"))
        db.commit()
        w2 = db.query(models.Warehouse).filter_by(warehouse_code="W2").one().id
    api("PATCH", f"/purchases/{pu['id']}", json={"lines": [{"id": pu_line["id"], "warehouseId": w2}]})
    assert stock(m["p1"]) == 100 and stock(m["p1"], "W2") == 12, (stock(m["p1"]), stock(m["p1"], "W2"))
    api("PATCH", f"/purchases/{pu['id']}", 400, json={"lines": [{"id": pu_line["id"], "warehouseId": 999999}]})
    s2 = api("POST", "/sales", 201, json={"partnerId": m["cust"], "salesDate": "2026-11-20", "lines": [
        {"productId": m["p2"], "quantity": 5, "unitPrice": 200, "warehouseId": w2}]})
    assert stock(m["p2"], "W2") == -5, stock(m["p2"], "W2")  # 在庫がなくても売上は登録でき、マイナスになる
    api("PATCH", f"/sales/{s2['id']}", json={"status": "draft"})
    assert stock(m["p2"], "W2") == 0
    api("PATCH", f"/sales/{s2['id']}", json={"status": "confirmed"})
    assert stock(m["p2"], "W2") == -5
    moves = api("GET", "/inventory/movements", params={"product_id": m["p1"]})
    assert sum(Decimal(str(x["quantity"])) for x in moves) == Decimal(12), moves  # p1 の受払の合計 = +12（売上は取消済み）
    assert moves[0]["documentNo"] == pu["purchaseNo"], moves[0]
    api("POST", "/quotations", 201, json={"partnerId": m["cust"], "quotationDate": "2026-11-21", "lines": [
        {"productId": m["p1"], "quantity": 1, "unitPrice": 1}]})  # 見積は在庫を動かさない
    assert stock(m["p1"]) == 100
    print("inventory movements ok")

    print("ALL OK")


if __name__ == "__main__":
    main()
