from __future__ import annotations

from pathlib import Path
from html import escape
from datetime import datetime

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill
from PySide6.QtCore import QMarginsF, QSizeF
from PySide6.QtGui import QPageLayout, QPageSize, QPdfWriter, QTextDocument

from .paths import exports_dir


# QTextDocument lays out HTML in screen-style logical pixels (96 DPI).
# QPdfWriter defaults to a much higher print coordinate system. If the document
# page size is calculated using the writer's high DPI, the HTML becomes tiny.
# Keep the PDF high-resolution, but calculate QTextDocument's page size at 96 DPI.
_DOCUMENT_LAYOUT_DPI = 96
_PDF_OUTPUT_DPI = 1200


def _safe_name(name: str) -> str:
    for ch in '<>:"/\\|?*':
        name = name.replace(ch, "_")
    return name.strip() or "export"


def export_rows_excel(title: str, headers: list[str], rows: list[list], path: str | Path | None = None):
    if path is None:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = exports_dir() / f"{_safe_name(title)}_{stamp}.xlsx"
    path = Path(path)
    wb = Workbook()
    ws = wb.active
    ws.title = _safe_name(title)[:31]
    ws.sheet_view.rightToLeft = True
    ws.append(headers)
    for c in ws[1]:
        c.font = Font(bold=True)
        c.alignment = Alignment(horizontal="center")
        c.fill = PatternFill("solid", fgColor="DDEBF7")
    for row in rows:
        ws.append(row)
    for col in ws.columns:
        width = max(12, min(45, max(len(str(c.value or "")) for c in col) + 2))
        ws.column_dimensions[col[0].column_letter].width = width
        for c in col:
            c.alignment = Alignment(horizontal="right", vertical="center")
    wb.save(path)
    return path


def html_to_pdf(
    html: str,
    path: str | Path,
    *,
    landscape: bool = False,
    title: str = "Dental Lab",
):
    """Render RTL HTML to a correctly-scaled A4 PDF.

    The important detail is that QTextDocument is sized using a 96-DPI page
    rectangle, while QPdfWriter remains at high output resolution. This avoids
    the microscopic output produced when the document is laid out against the
    writer's 1200-DPI pixel rectangle.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    writer = QPdfWriter(str(path))
    writer.setResolution(_PDF_OUTPUT_DPI)
    writer.setTitle(title)
    writer.setCreator("Dental Lab Management System")

    orientation = (
        QPageLayout.Orientation.Landscape
        if landscape
        else QPageLayout.Orientation.Portrait
    )
    page_layout = QPageLayout(
        QPageSize(QPageSize.PageSizeId.A4),
        orientation,
        QMarginsF(10, 10, 10, 10),
        QPageLayout.Unit.Millimeter,
    )
    writer.setPageLayout(page_layout)

    doc = QTextDocument()
    doc.setDocumentMargin(0)
    doc.setHtml(html)

    # QTextDocument's HTML layout is based on screen-resolution logical pixels.
    # Do NOT use writer.resolution() here; that would make the page ~12.5x too
    # large in document units and shrink all content accordingly.
    logical_page = writer.pageLayout().paintRectPixels(_DOCUMENT_LAYOUT_DPI)
    doc.setPageSize(QSizeF(logical_page.size()))
    doc.print_(writer)
    return path


def export_table_pdf(title: str, headers: list[str], rows: list[list], path: str | Path | None = None):
    if path is None:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = exports_dir() / f"{_safe_name(title)}_{stamp}.pdf"

    # Wide reports are substantially more readable in landscape.
    landscape = len(headers) >= 6
    font_size = "9.5pt" if landscape else "10.5pt"
    cell_pad = "5px" if landscape else "7px"

    th = "".join(f"<th>{escape(str(h))}</th>" for h in headers)
    body = ""
    for index, row in enumerate(rows):
        bg = "#ffffff" if index % 2 == 0 else "#f8fafc"
        body += (
            f"<tr style='background:{bg}'>"
            + "".join(f"<td>{escape(str(v if v is not None else ''))}</td>" for v in row)
            + "</tr>"
        )

    empty = ""
    if not rows:
        empty = f"<tr><td colspan='{max(1, len(headers))}' style='text-align:center;color:#64748b'>لا توجد بيانات</td></tr>"

    html = f"""
    <html dir='rtl'>
    <head><meta charset='utf-8'>
    <style>
      body {{
        font-family:'Segoe UI','Tahoma','Arial';
        direction:rtl;
        color:#172033;
        font-size:{font_size};
        margin:0;
      }}
      .title {{
        font-size:20pt;
        font-weight:700;
        color:#0f172a;
        text-align:center;
        margin:0 0 14px 0;
      }}
      table {{
        border-collapse:collapse;
        width:100%;
      }}
      th, td {{
        border:1px solid #cbd5e1;
        padding:{cell_pad};
        text-align:right;
        vertical-align:middle;
      }}
      th {{
        background:#e2e8f0;
        color:#0f172a;
        font-weight:700;
      }}
    </style></head>
    <body>
      <div class='title'>{escape(title)}</div>
      <table>
        <thead><tr>{th}</tr></thead>
        <tbody>{body}{empty}</tbody>
      </table>
    </body></html>
    """
    return html_to_pdf(html, path, landscape=landscape, title=title)


def invoice_pdf(service, invoice_id: int, path: str | Path | None = None):
    inv, items, payments = service.invoice_detail(invoice_id)
    settings = service.settings()
    if path is None:
        path = exports_dir() / f"Invoice_{_safe_name(inv['invoice_no'])}.pdf"

    item_rows = ""
    for index, x in enumerate(items):
        bg = "#ffffff" if index % 2 == 0 else "#f8fafc"
        item_rows += f"""
        <tr style='background:{bg}'>
          <td>{escape(x['description'])}</td>
          <td>{x['quantity']:g}</td>
          <td>{x['unit_price']:.2f}</td>
          <td>{x['discount']:.2f}</td>
          <td>{x['line_total']:.2f}</td>
        </tr>
        """

    pay_rows = "".join(
        f"<tr><td>{escape(p['payment_date'])}</td><td>{p['amount']:.2f}</td><td>{escape(p.get('method') or '')}</td></tr>"
        for p in payments
    ) or "<tr><td colspan='3' style='text-align:center;color:#64748b'>لا توجد تحصيلات</td></tr>"

    lab_name = escape(settings.get('lab_name', 'Dental Lab'))
    lab_phone = escape(settings.get('lab_phone', ''))
    lab_address = escape(settings.get('lab_address', ''))
    footer = escape(settings.get('invoice_footer', ''))

    html = f"""
    <html dir='rtl'>
    <head><meta charset='utf-8'>
    <style>
      body {{
        font-family:'Segoe UI','Tahoma','Arial';
        direction:rtl;
        color:#172033;
        font-size:11pt;
        margin:0;
      }}
      .header {{
        border-bottom:2px solid #0f9d8c;
        padding-bottom:12px;
        margin-bottom:18px;
      }}
      .lab {{
        color:#0f172a;
        font-size:22pt;
        font-weight:700;
        margin-bottom:4px;
      }}
      .muted {{ color:#64748b; font-size:9.5pt; }}
      .invoice-title {{
        color:#0f172a;
        font-size:18pt;
        font-weight:700;
        margin:0 0 8px 0;
      }}
      .meta {{ margin:0 0 16px 0; }}
      table {{ border-collapse:collapse; width:100%; }}
      .grid th, .grid td {{
        border:1px solid #cbd5e1;
        padding:7px;
        text-align:right;
        vertical-align:middle;
      }}
      .grid th {{
        background:#e2e8f0;
        color:#0f172a;
        font-weight:700;
      }}
      .totals {{
        margin-top:16px;
        width:48%;
        margin-right:auto;
        border:1px solid #cbd5e1;
      }}
      .totals td {{ padding:7px; border-bottom:1px solid #e2e8f0; }}
      .totals tr:last-child td {{ border-bottom:0; }}
      .balance {{ color:#0f9d8c; font-weight:700; }}
      .section-title {{
        color:#0f172a;
        font-size:14pt;
        font-weight:700;
        margin:20px 0 8px 0;
      }}
      .footer {{
        text-align:center;
        color:#64748b;
        margin-top:28px;
        padding-top:10px;
        border-top:1px solid #e2e8f0;
      }}
    </style></head>
    <body>
      <div class='header'>
        <div class='lab'>{lab_name}</div>
        <div class='muted'>{lab_phone} &nbsp;&nbsp; {lab_address}</div>
      </div>

      <div class='invoice-title'>فاتورة رقم: {escape(inv['invoice_no'])}</div>
      <div class='meta'>
        <b>التاريخ:</b> {escape(inv['invoice_date'])}
        &nbsp;&nbsp;&nbsp;&nbsp;
        <b>الطبيب:</b> {escape(inv['doctor_name'])}
      </div>

      <table class='grid'>
        <thead><tr>
          <th>البيان</th><th>الكمية</th><th>سعر الوحدة</th><th>الخصم</th><th>الإجمالي</th>
        </tr></thead>
        <tbody>{item_rows}</tbody>
      </table>

      <table class='totals'>
        <tr><td><b>الإجمالي</b></td><td>{inv['total']:.2f} EGP</td></tr>
        <tr><td><b>المدفوع</b></td><td>{inv['paid']:.2f} EGP</td></tr>
        <tr><td><b>المتبقي</b></td><td class='balance'>{inv['balance']:.2f} EGP</td></tr>
      </table>

      <div class='section-title'>التحصيلات</div>
      <table class='grid'>
        <thead><tr><th>التاريخ</th><th>القيمة</th><th>الطريقة</th></tr></thead>
        <tbody>{pay_rows}</tbody>
      </table>

      <div class='footer'>{footer}</div>
    </body></html>
    """
    return html_to_pdf(html, path, landscape=False, title=f"Invoice {inv['invoice_no']}")
