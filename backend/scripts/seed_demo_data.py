"""デモ用サンプルデータ投入スクリプト。

各テーブルに概ね100件規模のデータを、業務ルール
（見積残・受注残・発注残・売上残・仕入残の消込ロジック、直接入力の混在）
に沿った形で生成する。既存データがある状態での再実行は想定していない
（複数回実行すると重複データが増える）。

実行:
  cd backend && source .env && ./venv/bin/python scripts/seed_demo_data.py
"""
from __future__ import annotations

import pathlib
import random
import sys
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from faker import Faker  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app import models  # noqa: E402
from app.database import SessionLocal  # noqa: E402

fake = Faker("ja_JP")
Faker.seed(42)
random.seed(42)

TODAY = date(2026, 8, 15)


def q3(value) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.001"))


def q2(value) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"))


def random_date(start: date, end: date) -> date:
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, max(delta, 0)))


PRODUCT_CATALOG = {
    "オフィス家具": {
        "unit": "台",
        "price_range": (8000, 80000),
        "items": ["オフィスチェア", "スチールデスク", "書庫", "パーティション", "ロッカー", "会議テーブル", "応接ソファ"],
    },
    "OA機器": {
        "unit": "台",
        "price_range": (15000, 250000),
        "items": ["レーザープリンター", "複合機", "シュレッダー", "プロジェクター", "電子ホワイトボード", "ラミネーター"],
    },
    "事務用品": {
        "unit": "個",
        "price_range": (100, 3000),
        "items": ["ファイルボックス", "バインダー", "クリアフォルダ", "電卓", "ホッチキス", "はさみ", "印鑑パッド"],
    },
    "消耗品": {
        "unit": "箱",
        "price_range": (500, 12000),
        "items": ["コピー用紙", "トナーカートリッジ", "インクカートリッジ", "封筒", "付箋セット", "ボールペン"],
    },
    "IT機器": {
        "unit": "台",
        "price_range": (25000, 300000),
        "items": ["ノートPC", "デスクトップPC", "液晶モニター", "ワイヤレスキーボード", "外付けHDD", "Webカメラ"],
    },
}

PAYMENT_METHODS = ["銀行振込", "現金", "口座振替", "クレジットカード"]


def main() -> None:
    db = SessionLocal()

    admin = db.execute(
        select(models.User).where(models.User.role == models.UserRole.owner).order_by(models.User.id)
    ).scalars().first()
    if admin is None:
        raise SystemExit(
            "オーナーユーザーが見つかりません。先に一度オーナーとしてログインするか、"
            "db/migrations/0001_add_user_roles.sql で既存ユーザーをオーナーへ昇格させてください。"
        )

    # ------------------------------------------------------------
    # 倉庫
    # ------------------------------------------------------------
    warehouses = []
    for code, name in [("WH001", "本社倉庫"), ("WH002", "東京倉庫"), ("WH003", "大阪倉庫")]:
        wh = models.Warehouse(warehouse_code=code, name=name)
        db.add(wh)
        warehouses.append(wh)
    db.flush()

    # ------------------------------------------------------------
    # 取引先 100件
    # ------------------------------------------------------------
    partners: list[models.Partner] = []
    used_names: set[str] = set()
    for i in range(1, 101):
        name = fake.company()
        while name in used_names:
            name = fake.company()
        used_names.add(name)

        partner_type = random.choices(["customer", "supplier", "both"], weights=[55, 30, 15])[0]
        partner = models.Partner(
            partner_code=f"P{i:04d}",
            partner_type=partner_type,
            created_by=admin.id,
        )
        db.add(partner)
        db.flush()

        credit_limit = q2(random.randint(5, 50) * 100000) if partner_type in ("customer", "both") else None
        detail = models.PartnerDetail(
            partner_id=partner.id,
            effective_date=random_date(date(2025, 4, 1), date(2026, 6, 1)),
            name=name,
            representative_name=fake.name(),
            postal_code=fake.zipcode(),
            address=fake.address(),
            phone=fake.phone_number(),
            email=fake.company_email(),
            contact_person=fake.name(),
            credit_limit=credit_limit,
            remarks=random.choice([None, None, None, "支払サイト要相談", "大口取引先", "新規開拓案件"]),
            created_by=admin.id,
        )
        db.add(detail)
        partners.append(partner)

    db.flush()

    customers = [p for p in partners if p.partner_type in ("customer", "both")]
    suppliers = [p for p in partners if p.partner_type in ("supplier", "both")]

    # ------------------------------------------------------------
    # 商品 100件
    # ------------------------------------------------------------
    products: list[models.Product] = []
    catalog_items = []
    for category, info in PRODUCT_CATALOG.items():
        for item in info["items"]:
            catalog_items.append((category, item, info["unit"], info["price_range"]))

    idx = 1
    while len(products) < 100:
        for category, item, unit, price_range in catalog_items:
            if len(products) >= 100:
                break
            model_no = f"{random.choice('ABCDEFGH')}{random.randint(100, 999)}"
            product = models.Product(
                product_code=f"PR{idx:04d}",
                name=f"{item} {model_no}",
                category=category,
                unit=unit,
                default_supplier_id=random.choice(suppliers).id if random.random() < 0.7 else None,
            )
            db.add(product)
            db.flush()
            product.price_range = price_range  # type: ignore[attr-defined]
            products.append(product)
            idx += 1

    # ------------------------------------------------------------
    # 単価マスタ 約110件
    # ------------------------------------------------------------
    price_by_product: dict[int, Decimal] = {}
    for product in products:
        low, high = product.price_range  # type: ignore[attr-defined]
        unit_price = q2(random.randint(low, high))
        db.add(
            models.PriceMaster(
                price_type=models.PriceType.sales,
                partner_id=None,
                product_id=product.id,
                unit_price=unit_price,
                effective_start_date=date(2025, 4, 1),
            )
        )
        price_by_product[product.id] = unit_price

    for product in random.sample(products, 20):
        low, _ = product.price_range  # type: ignore[attr-defined]
        db.add(
            models.PriceMaster(
                price_type=models.PriceType.purchase,
                partner_id=product.default_supplier_id,
                product_id=product.id,
                unit_price=q2(int(low * 0.6)),
                effective_start_date=date(2025, 4, 1),
            )
        )
    db.flush()

    def line_price(product: models.Product) -> Decimal:
        base = price_by_product[product.id]
        variance = Decimal(random.uniform(0.95, 1.05)).quantize(Decimal("0.01"))
        return q2(base * variance)

    # ------------------------------------------------------------
    # 見積 100件 + 明細
    # ------------------------------------------------------------
    quotations: list[models.Quotation] = []
    quotation_line_remaining: dict[int, Decimal] = {}
    quotation_lines_all: list[models.QuotationLine] = []

    for i in range(1, 101):
        partner = random.choice(customers)
        quotation_date = random_date(date(2026, 1, 5), TODAY)
        approval_status = random.choices(
            [models.ApprovalStatus.approved, models.ApprovalStatus.pending, models.ApprovalStatus.draft, models.ApprovalStatus.rejected],
            weights=[55, 15, 20, 10],
        )[0]

        quotation = models.Quotation(
            quotation_no=f"Q{i:06d}",
            partner_id=partner.id,
            quotation_date=quotation_date,
            expiry_date=quotation_date + timedelta(days=30) if random.random() < 0.8 else None,
            condition_text=random.choice([None, None, "送料別途", "納期別途相談", "初回取引につき前払い"]),
            approval_status=approval_status,
            created_by=admin.id,
        )
        if approval_status == models.ApprovalStatus.approved:
            quotation.approved_by = admin.id
            quotation.approved_at = datetime.combine(
                quotation_date + timedelta(days=random.randint(0, 3)), datetime.min.time(), tzinfo=timezone.utc
            )
        db.add(quotation)
        db.flush()

        for line_no in range(1, random.randint(1, 4) + 1):
            product = random.choice(products)
            quantity = q3(random.randint(1, 50))
            unit_price = line_price(product)
            line = models.QuotationLine(
                quotation_id=quotation.id,
                line_no=line_no,
                product_id=product.id,
                quantity=quantity,
                unit_price=unit_price,
                amount=q2(quantity * unit_price),
            )
            db.add(line)
            db.flush()
            quotation_line_remaining[line.id] = quantity
            quotation_lines_all.append(line)

        quotations.append(quotation)

    db.flush()

    approved_quotation_lines = [
        line for line in quotation_lines_all if line.quotation.approval_status == models.ApprovalStatus.approved
    ]

    # ------------------------------------------------------------
    # 受注 100件 + 明細（見積連携 or 直接入力）
    # ------------------------------------------------------------
    orders: list[models.Order] = []
    order_line_remaining_purchase: dict[int, Decimal] = {}
    order_line_remaining_sales: dict[int, Decimal] = {}
    order_lines_all: list[models.OrderLine] = []

    linkable_lines = [line for line in approved_quotation_lines if quotation_line_remaining[line.id] > 0]
    random.shuffle(linkable_lines)

    for i in range(1, 101):
        use_link = linkable_lines and random.random() < 0.65
        if use_link:
            q_line = linkable_lines.pop()
            partner_id = q_line.quotation.partner_id
            order_date = q_line.quotation.quotation_date + timedelta(days=random.randint(1, 14))
            remaining = quotation_line_remaining[q_line.id]
            qty = remaining if random.random() < 0.5 else q3(remaining * Decimal(random.uniform(0.3, 0.9)))
            qty = min(qty, remaining)
            quotation_line_remaining[q_line.id] -= qty
            product_id = q_line.product_id
            unit_price = q_line.unit_price
        else:
            partner = random.choice(customers)
            partner_id = partner.id
            order_date = random_date(date(2026, 1, 1), TODAY)
            product = random.choice(products)
            product_id = product.id
            qty = q3(random.randint(1, 30))
            unit_price = line_price(product)

        status = random.choices(
            [models.DocumentStatus.confirmed, models.DocumentStatus.draft, models.DocumentStatus.cancelled],
            weights=[85, 8, 7],
        )[0]

        order = models.Order(
            order_no=f"SO{i:06d}",
            partner_id=partner_id,
            order_date=order_date,
            status=status,
            created_by=admin.id,
        )
        db.add(order)
        db.flush()

        line = models.OrderLine(
            order_id=order.id,
            line_no=1,
            quotation_line_id=q_line.id if use_link else None,
            product_id=product_id,
            quantity=qty,
            unit_price=unit_price,
            amount=q2(qty * unit_price),
        )
        db.add(line)
        db.flush()
        order_line_remaining_purchase[line.id] = qty
        order_line_remaining_sales[line.id] = qty
        order_lines_all.append(line)
        orders.append(order)

    db.flush()

    # ------------------------------------------------------------
    # 発注 100件 + 明細（受注連携 or 直接入力）
    # ------------------------------------------------------------
    purchase_orders: list[models.PurchaseOrder] = []
    purchase_order_line_remaining: dict[int, Decimal] = {}
    purchase_order_lines_all: list[models.PurchaseOrderLine] = []

    po_linkable = [line for line in order_lines_all if order_line_remaining_purchase[line.id] > 0]
    random.shuffle(po_linkable)

    for i in range(1, 101):
        use_link = po_linkable and random.random() < 0.6
        if use_link:
            o_line = po_linkable.pop()
            product = next(p for p in products if p.id == o_line.product_id)
            supplier = None
            if product.default_supplier_id:
                supplier = next((s for s in suppliers if s.id == product.default_supplier_id), None)
            supplier = supplier or random.choice(suppliers)
            order_date = o_line.order.order_date + timedelta(days=random.randint(0, 7))
            remaining = order_line_remaining_purchase[o_line.id]
            qty = remaining if random.random() < 0.6 else q3(remaining * Decimal(random.uniform(0.3, 0.9)))
            qty = min(qty, remaining)
            order_line_remaining_purchase[o_line.id] -= qty
            product_id = o_line.product_id
            unit_price = q2(o_line.unit_price * Decimal("0.7"))
        else:
            supplier = random.choice(suppliers)
            product = random.choice(products)
            product_id = product.id
            order_date = random_date(date(2026, 1, 1), TODAY)
            qty = q3(random.randint(5, 100))
            unit_price = q2(price_by_product[product.id] * Decimal("0.7"))

        status = random.choices(
            [models.DocumentStatus.confirmed, models.DocumentStatus.draft, models.DocumentStatus.cancelled],
            weights=[85, 8, 7],
        )[0]

        po = models.PurchaseOrder(
            purchase_order_no=f"PO{i:06d}",
            partner_id=supplier.id,
            order_date=order_date,
            status=status,
            created_by=admin.id,
        )
        db.add(po)
        db.flush()

        line = models.PurchaseOrderLine(
            purchase_order_id=po.id,
            line_no=1,
            order_line_id=o_line.id if use_link else None,
            product_id=product_id,
            quantity=qty,
            unit_price=unit_price,
            amount=q2(qty * unit_price),
        )
        db.add(line)
        db.flush()
        purchase_order_line_remaining[line.id] = qty
        purchase_order_lines_all.append(line)
        purchase_orders.append(po)

    db.flush()

    # ------------------------------------------------------------
    # 仕入 100件 + 明細（発注連携 or 直接入力）
    # ------------------------------------------------------------
    purchases: list[models.Purchase] = []
    purchase_line_remaining: dict[int, Decimal] = {}
    purchase_lines_all: list[models.PurchaseLine] = []

    purchase_linkable = [line for line in purchase_order_lines_all if purchase_order_line_remaining[line.id] > 0]
    random.shuffle(purchase_linkable)

    for i in range(1, 101):
        use_link = purchase_linkable and random.random() < 0.6
        if use_link:
            po_line = purchase_linkable.pop()
            partner_id = po_line.purchase_order.partner_id
            purchase_date = po_line.purchase_order.order_date + timedelta(days=random.randint(1, 10))
            remaining = purchase_order_line_remaining[po_line.id]
            qty = remaining if random.random() < 0.7 else q3(remaining * Decimal(random.uniform(0.3, 0.9)))
            qty = min(qty, remaining)
            purchase_order_line_remaining[po_line.id] -= qty
            product_id = po_line.product_id
            unit_price = po_line.unit_price
        else:
            supplier = random.choice(suppliers)
            partner_id = supplier.id
            purchase_date = random_date(date(2026, 1, 1), TODAY)
            product = random.choice(products)
            product_id = product.id
            qty = q3(random.randint(5, 100))
            unit_price = q2(price_by_product[product.id] * Decimal("0.7"))

        status = random.choices(
            [models.DocumentStatus.confirmed, models.DocumentStatus.draft],
            weights=[92, 8],
        )[0]

        purchase = models.Purchase(
            purchase_no=f"PU{i:06d}",
            partner_id=partner_id,
            purchase_date=purchase_date,
            status=status,
            created_by=admin.id,
        )
        db.add(purchase)
        db.flush()

        line = models.PurchaseLine(
            purchase_id=purchase.id,
            line_no=1,
            purchase_order_line_id=po_line.id if use_link else None,
            product_id=product_id,
            quantity=qty,
            unit_price=unit_price,
            amount=q2(qty * unit_price),
        )
        db.add(line)
        db.flush()
        purchase_line_remaining[line.id] = line.amount
        purchase_lines_all.append(line)
        purchases.append(purchase)

    db.flush()

    # ------------------------------------------------------------
    # 売上 100件 + 明細（受注連携 or 直接入力）
    # ------------------------------------------------------------
    sales_list: list[models.Sales] = []
    sales_line_remaining: dict[int, Decimal] = {}
    sales_lines_all: list[models.SalesLine] = []

    sales_linkable = [line for line in order_lines_all if order_line_remaining_sales[line.id] > 0]
    random.shuffle(sales_linkable)

    for i in range(1, 101):
        use_link = sales_linkable and random.random() < 0.6
        if use_link:
            o_line = sales_linkable.pop()
            partner_id = o_line.order.partner_id
            sales_date = o_line.order.order_date + timedelta(days=random.randint(1, 14))
            remaining = order_line_remaining_sales[o_line.id]
            qty = remaining if random.random() < 0.7 else q3(remaining * Decimal(random.uniform(0.3, 0.9)))
            qty = min(qty, remaining)
            order_line_remaining_sales[o_line.id] -= qty
            product_id = o_line.product_id
            unit_price = o_line.unit_price
        else:
            partner = random.choice(customers)
            partner_id = partner.id
            sales_date = random_date(date(2026, 1, 1), TODAY)
            product = random.choice(products)
            product_id = product.id
            qty = q3(random.randint(1, 30))
            unit_price = line_price(product)

        status = random.choices(
            [models.DocumentStatus.confirmed, models.DocumentStatus.draft],
            weights=[92, 8],
        )[0]

        sales = models.Sales(
            sales_no=f"SA{i:06d}",
            partner_id=partner_id,
            sales_date=sales_date,
            status=status,
            created_by=admin.id,
        )
        db.add(sales)
        db.flush()

        line = models.SalesLine(
            sales_id=sales.id,
            line_no=1,
            order_line_id=o_line.id if use_link else None,
            product_id=product_id,
            quantity=qty,
            unit_price=unit_price,
            amount=q2(qty * unit_price),
        )
        db.add(line)
        db.flush()
        sales_line_remaining[line.id] = line.amount
        sales_lines_all.append(line)
        sales_list.append(sales)

    db.flush()

    # ------------------------------------------------------------
    # 入金 100件 + 明細（売上連携 or 直接入力）
    # ------------------------------------------------------------
    receipts: list[models.Receipt] = []
    receipt_linkable = [line for line in sales_lines_all if sales_line_remaining[line.id] > 0]
    random.shuffle(receipt_linkable)

    for i in range(1, 101):
        use_link = receipt_linkable and random.random() < 0.6
        if use_link:
            s_line = receipt_linkable.pop()
            partner_id = s_line.sales.partner_id
            receipt_date = s_line.sales.sales_date + timedelta(days=random.randint(5, 45))
            remaining = sales_line_remaining[s_line.id]
            amount = remaining if random.random() < 0.75 else q2(remaining * Decimal(random.uniform(0.3, 0.9)))
            amount = min(amount, remaining)
            sales_line_remaining[s_line.id] -= amount
        else:
            partner = random.choice(customers)
            partner_id = partner.id
            receipt_date = random_date(date(2026, 1, 1), TODAY)
            amount = q2(random.randint(5000, 300000))

        receipt = models.Receipt(
            receipt_no=f"RC{i:06d}",
            partner_id=partner_id,
            receipt_date=receipt_date,
            payment_method=random.choice(PAYMENT_METHODS),
            status=models.DocumentStatus.confirmed,
            created_by=admin.id,
        )
        db.add(receipt)
        db.flush()

        db.add(
            models.ReceiptLine(
                receipt_id=receipt.id,
                line_no=1,
                sales_line_id=s_line.id if use_link else None,
                amount=amount,
            )
        )
        receipts.append(receipt)

    db.flush()

    # ------------------------------------------------------------
    # 支払 100件 + 明細（仕入連携 or 直接入力）
    # ------------------------------------------------------------
    payments: list[models.Payment] = []
    payment_linkable = [line for line in purchase_lines_all if purchase_line_remaining[line.id] > 0]
    random.shuffle(payment_linkable)

    for i in range(1, 101):
        use_link = payment_linkable and random.random() < 0.6
        if use_link:
            p_line = payment_linkable.pop()
            partner_id = p_line.purchase.partner_id
            payment_date = p_line.purchase.purchase_date + timedelta(days=random.randint(5, 45))
            remaining = purchase_line_remaining[p_line.id]
            amount = remaining if random.random() < 0.75 else q2(remaining * Decimal(random.uniform(0.3, 0.9)))
            amount = min(amount, remaining)
            purchase_line_remaining[p_line.id] -= amount
        else:
            supplier = random.choice(suppliers)
            partner_id = supplier.id
            payment_date = random_date(date(2026, 1, 1), TODAY)
            amount = q2(random.randint(5000, 300000))

        payment = models.Payment(
            payment_no=f"PM{i:06d}",
            partner_id=partner_id,
            payment_date=payment_date,
            payment_method=random.choice(PAYMENT_METHODS),
            status=models.DocumentStatus.confirmed,
            created_by=admin.id,
        )
        db.add(payment)
        db.flush()

        db.add(
            models.PaymentLine(
                payment_id=payment.id,
                line_no=1,
                purchase_line_id=p_line.id if use_link else None,
                amount=amount,
            )
        )
        payments.append(payment)

    db.flush()

    # ------------------------------------------------------------
    # 在庫現在数（100件規模）/ 在庫引当（100件規模）
    # ------------------------------------------------------------
    stock_rows = 0
    for product in products:
        chosen_warehouses = random.sample(warehouses, k=1 if random.random() < 0.7 else 2)
        for wh in chosen_warehouses:
            db.add(
                models.InventoryStock(
                    product_id=product.id,
                    warehouse_id=wh.id,
                    quantity_on_hand=q3(random.randint(0, 500)),
                )
            )
            stock_rows += 1
    db.flush()

    allocation_rows = 0
    allocation_pool = [
        (models.AllocationStage.quotation, quotation_lines_all),
        (models.AllocationStage.order, order_lines_all),
        (models.AllocationStage.sales, sales_lines_all),
    ]
    while allocation_rows < 100:
        stage, pool = random.choice(allocation_pool)
        line = random.choice(pool)
        kwargs = {
            "allocation_stage": stage,
            "product_id": line.product_id,
            "warehouse_id": random.choice(warehouses).id,
            "quantity": q3(min(line.quantity, Decimal(random.randint(1, 20)))),
        }
        if stage == models.AllocationStage.quotation:
            kwargs["quotation_line_id"] = line.id
        elif stage == models.AllocationStage.order:
            kwargs["order_line_id"] = line.id
        else:
            kwargs["sales_line_id"] = line.id
        db.add(models.InventoryAllocation(**kwargs))
        allocation_rows += 1
    db.flush()

    db.commit()

    print(f"partners={len(partners)} products={len(products)} quotations={len(quotations)} "
          f"orders={len(orders)} purchase_orders={len(purchase_orders)} purchases={len(purchases)} "
          f"sales={len(sales_list)} receipts={len(receipts)} payments={len(payments)} "
          f"inventory_stocks={stock_rows} inventory_allocations={allocation_rows}")


if __name__ == "__main__":
    main()
