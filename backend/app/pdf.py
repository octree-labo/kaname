"""見積書PDF生成（日本語・IPAフォント）。

未承認（draft/pending）は「仮」の透かしを、承認済みは社印の代わりに
プレースホルダー（赤丸＋「承認済」）を描画する。
実際の角印画像を使う場合は SEAL_IMAGE_PATH に画像ファイルを配置して差し替える。

罫線や項目配置は最小限の実装であり、正式な帳票デザインは別途フェーズで整える。
"""
from __future__ import annotations

import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from . import models

FONT_NAME = "IPAGothic"
_FONT_CANDIDATES = [
    "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf",
    "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf",
]

_font_registered = False


def _ensure_font() -> str:
    global _font_registered
    if _font_registered:
        return FONT_NAME
    for path in _FONT_CANDIDATES:
        try:
            pdfmetrics.registerFont(TTFont(FONT_NAME, path))
            _font_registered = True
            return FONT_NAME
        except Exception:
            continue
    # IPAフォントが見つからない場合は組み込みフォントにフォールバック（日本語は文字化けする）
    return "Helvetica"


def render_quotation_pdf(quotation: models.Quotation, partner: models.Partner | None) -> bytes:
    font = _ensure_font()
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    c.setFont(font, 18)
    c.drawCentredString(width / 2, height - 25 * mm, "見積書")

    c.setFont(font, 10)
    c.drawString(20 * mm, height - 35 * mm, f"見積番号: {quotation.quotation_no}")

    partner_label = partner.current_detail.name if partner and partner.current_detail else (
        partner.partner_code if partner else str(quotation.partner_id)
    )

    y = height - 48 * mm
    for label, value in [
        ("取引先", partner_label),
        ("見積日", quotation.quotation_date.isoformat()),
        ("有効期限", quotation.expiry_date.isoformat() if quotation.expiry_date else "-"),
        ("見積条件", quotation.condition_text or "-"),
        ("状態", _approval_label(quotation.approval_status)),
    ]:
        c.drawString(20 * mm, y, f"{label}：{value}")
        y -= 7 * mm

    y -= 4 * mm
    c.setFont(font, 9)
    headers = [("No", 20), ("商品コード", 32), ("商品名", 62), ("数量", 122), ("単価", 145), ("金額", 172)]
    for label, x in headers:
        c.drawString(x * mm, y, label)
    y -= 2 * mm
    c.line(20 * mm, y, 190 * mm, y)
    y -= 6 * mm

    total = 0
    for line in quotation.lines:
        product_code = getattr(line, "product_code", None) or str(line.product_id)
        product_name = getattr(line, "product_name", None) or ""
        c.drawString(20 * mm, y, str(line.line_no))
        c.drawString(32 * mm, y, product_code)
        c.drawString(62 * mm, y, product_name[:22])
        c.drawRightString(140 * mm, y, f"{line.quantity:,}" if line.quantity is not None else "-")
        c.drawRightString(165 * mm, y, f"{line.unit_price:,}" if line.unit_price is not None else "-")
        c.drawRightString(190 * mm, y, f"{line.amount:,}")
        total += line.amount
        y -= 6.5 * mm

    y -= 2 * mm
    c.line(20 * mm, y, 190 * mm, y)
    y -= 7 * mm
    c.setFont(font, 11)
    c.drawRightString(190 * mm, y, f"合計金額：{total:,} 円")

    is_approved = quotation.approval_status == models.ApprovalStatus.approved
    if not is_approved:
        c.saveState()
        c.setFont(font, 70)
        c.setFillColor(colors.Color(1, 0, 0, alpha=0.25))
        c.translate(width / 2, height / 2)
        c.rotate(30)
        c.drawCentredString(0, 0, "仮")
        c.restoreState()
    else:
        # 社印画像のプレースホルダー（実際の運用では画像ファイルに差し替える）
        c.saveState()
        seal_x, seal_y = width - 45 * mm, height - 40 * mm
        c.setStrokeColor(colors.red)
        c.setFillColor(colors.Color(1, 0, 0, alpha=0.15))
        c.circle(seal_x, seal_y, 14 * mm, stroke=1, fill=1)
        c.setFillColor(colors.red)
        c.setFont(font, 13)
        c.drawCentredString(seal_x, seal_y - 4, "承認済")
        c.restoreState()

    c.showPage()
    c.save()
    return buffer.getvalue()


def _approval_label(status: models.ApprovalStatus) -> str:
    return {
        models.ApprovalStatus.draft: "未承認（仮）",
        models.ApprovalStatus.pending: "承認待ち（仮）",
        models.ApprovalStatus.approved: "承認済み",
        models.ApprovalStatus.rejected: "却下",
    }.get(status, str(status))
