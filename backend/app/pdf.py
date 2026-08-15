"""見積書PDF生成。

未承認（draft/pending）は「仮」の透かしを、承認済みは社印の代わりに
プレースホルダー（赤丸＋「印」）を描画する。
実際の角印画像を使う場合は SEAL_IMAGE_PATH に画像ファイルを配置して差し替える。

罫線や項目配置は最小限の実装であり、正式な帳票デザインは別途フェーズで整える。
"""
from __future__ import annotations

import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from . import models


def render_quotation_pdf(quotation: models.Quotation, partner: models.Partner | None) -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 16)
    c.drawString(20 * mm, height - 25 * mm, f"Quotation {quotation.quotation_no}")

    c.setFont("Helvetica", 10)
    y = height - 40 * mm
    partner_label = partner.partner_code if partner else str(quotation.partner_id)
    for label, value in [
        ("Partner", partner_label),
        ("Date", quotation.quotation_date.isoformat()),
        ("Expiry", quotation.expiry_date.isoformat() if quotation.expiry_date else "-"),
        ("Status", quotation.approval_status.value),
    ]:
        c.drawString(20 * mm, y, f"{label}: {value}")
        y -= 6 * mm

    y -= 4 * mm
    c.setFont("Helvetica-Bold", 9)
    c.drawString(20 * mm, y, "Line")
    c.drawString(35 * mm, y, "Product ID")
    c.drawString(70 * mm, y, "Qty")
    c.drawString(95 * mm, y, "Unit Price")
    c.drawString(130 * mm, y, "Amount")
    y -= 5 * mm
    c.setFont("Helvetica", 9)
    for line in quotation.lines:
        c.drawString(20 * mm, y, str(line.line_no))
        c.drawString(35 * mm, y, str(line.product_id))
        c.drawRightString(85 * mm, y, str(line.quantity))
        c.drawRightString(120 * mm, y, str(line.unit_price))
        c.drawRightString(155 * mm, y, str(line.amount))
        y -= 6 * mm

    is_approved = quotation.approval_status == models.ApprovalStatus.approved
    if not is_approved:
        c.saveState()
        c.setFont("Helvetica-Bold", 80)
        c.setFillColor(colors.Color(1, 0, 0, alpha=0.25))
        c.translate(width / 2, height / 2)
        c.rotate(30)
        c.drawCentredString(0, 0, "DRAFT / 仮")
        c.restoreState()
    else:
        # 社印画像のプレースホルダー（実際の運用では画像ファイルに差し替える）
        c.saveState()
        seal_x, seal_y = width - 45 * mm, height - 45 * mm
        c.setStrokeColor(colors.red)
        c.setFillColor(colors.Color(1, 0, 0, alpha=0.15))
        c.circle(seal_x, seal_y, 12 * mm, stroke=1, fill=1)
        c.setFillColor(colors.red)
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(seal_x, seal_y - 3, "APPROVED")
        c.restoreState()

    c.showPage()
    c.save()
    return buffer.getvalue()
