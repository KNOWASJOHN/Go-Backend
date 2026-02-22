from typing import Dict, List
from datetime import datetime
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from config import Config
import base64

def generate_pdf(
    invoice_data: Dict,
    items: List[Dict],
    totals: Dict,
    qr_code_base64: str
) -> bytes:
    """Generates a premium PDF invoice with advanced styling."""
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    elements = []
    
    # --- STYLES ---
    styles = getSampleStyleSheet()
    
    # Modern Brand Color (Elegant Deep Blue/Slate)
    brand_color = colors.HexColor('#1e293b') # Slate 800
    accent_color = colors.HexColor('#3b82f6') # Blue 500
    text_muted = colors.HexColor('#64748b') # Slate 400
    
    header_style = ParagraphStyle(
        'HeaderStyle',
        parent=styles['Heading1'],
        fontSize=28,
        textColor=brand_color,
        fontName='Helvetica-Bold',
        spaceAfter=5
    )
    
    subheader_style = ParagraphStyle(
        'SubHeaderStyle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=text_muted,
        leading=14
    )
    
    invoice_title_style = ParagraphStyle(
        'InvoiceTitle',
        parent=styles['Heading1'],
        fontSize=36,
        textColor=brand_color,
        alignment=TA_RIGHT,
        fontName='Helvetica-Bold',
        leading=42,
        spaceAfter=10
    )
    
    right_small_style = ParagraphStyle(
        'RightSmall', 
        parent=styles['Normal'], 
        alignment=TA_RIGHT, 
        fontSize=11,
        leading=14
    )
    
    section_title_style = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=accent_color,
        fontName='Helvetica-Bold',
        spaceAfter=12,
        textTransform='uppercase'
    )
    
    # --- TOP SECTION (Logo & Invoice Info) ---
    business_name = invoice_data['business_name']
    
    top_data = [
        [
            [
                Paragraph(business_name, header_style),
                Paragraph(invoice_data['business_address'], subheader_style),
                Paragraph(f"Phone: {invoice_data['business_phone']}", subheader_style),
                Paragraph(f"GST: {invoice_data['business_gst']}", subheader_style),
            ],
            [
                Paragraph("INVOICE", invoice_title_style),
                Paragraph(f"<b>Number:</b> {invoice_data['invoice_number']}", right_small_style),
                Paragraph(f"<b>Date:</b> {invoice_data['date']}", right_small_style),
            ]
        ]
    ]
    
    top_table = Table(top_data, colWidths=[3.5*inch, 3.5*inch])
    top_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 20),
    ]))
    elements.append(top_table)
    elements.append(Spacer(1, 20))
    
    # --- BILL TO SECTION ---
    elements.append(Paragraph("Bill To", section_title_style))
    bill_to_data = [
        [
            Paragraph(
                f"<b>{invoice_data['customer_name']}</b><br/>"
                f"Contact: {invoice_data.get('customer_phone', 'N/A')}<br/>"
                f"Email: {invoice_data.get('customer_email', 'N/A')}",
                styles['Normal']
            )
        ]
    ]
    bill_to_table = Table(bill_to_data, colWidths=[7*inch])
    bill_to_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
        ('PADDING', (0, 0), (-1, -1), 15),
        ('ROUNDEDCORNERS', [10, 10, 10, 10]),
    ]))
    elements.append(bill_to_table)
    elements.append(Spacer(1, 30))
    
    # --- ITEMS TABLE ---
    table_data = [['#', 'Description', 'Quantity', 'Unit Price', 'Total']]
    for idx, item in enumerate(items, 1):
        line_total = item['quantity'] * item['price']
        table_data.append([
            str(idx),
            item['item'],
            str(item['quantity']),
            f"{Config.CURRENCY_SYMBOL}{item['price']:.2f}",
            f"{Config.CURRENCY_SYMBOL}{line_total:.2f}"
        ])
    
    # Adjust column widths
    items_table = Table(table_data, colWidths=[0.5*inch, 3.5*inch, 1*inch, 1*inch, 1*inch])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), brand_color),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('TOPPADDING', (0, 0), (-1, 0), 12),
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),
        ('ALIGN', (2, 1), (2, -1), 'CENTER'),
        ('ALIGN', (3, 1), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f1f5f9')]),
        ('GRID', (0, 0), (-1, 0), 0.5, colors.white),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 10),
        ('TOPPADDING', (0, 1), (-1, -1), 10),
    ]))
    elements.append(items_table)
    
    # --- SUMMARY SECTION ---
    summary_data = [
        ['', 'Subtotal:', f"{Config.CURRENCY_SYMBOL}{totals['subtotal']:.2f}"],
        ['', f"GST ({totals['gst_rate']}%):", f"{Config.CURRENCY_SYMBOL}{totals['gst']:.2f}"],
        ['', 'GRAND TOTAL:', f"{Config.CURRENCY_SYMBOL}{totals['total']:.2f}"]
    ]
    summary_table = Table(summary_data, colWidths=[4*inch, 1.5*inch, 1.5*inch])
    summary_table.setStyle(TableStyle([
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
        ('FONTNAME', (1, 0), (2, 1), 'Helvetica'),
        ('FONTNAME', (1, 2), (2, 2), 'Helvetica-Bold'),
        ('FONTSIZE', (1, 0), (2, 1), 10),
        ('FONTSIZE', (1, 2), (2, 2), 14),
        ('TEXTCOLOR', (1, 2), (2, 2), accent_color),
        ('TOPPADDING', (1, 0), (-1, -1), 5),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 40))
    
    # --- PAYMENT & QR SECTION ---
    elements.append(Paragraph("Payment Information", section_title_style))
    
    # QR code processing
    qr_image_data = qr_code_base64.split(',')[1] if ',' in qr_code_base64 else qr_code_base64
    qr_image_bytes = BytesIO(base64.b64decode(qr_image_data))
    qr_img = Image(qr_image_bytes, width=1.4*inch, height=1.4*inch)
    
    # Side by side Bank Details and QR
    payment_box_data = [
        [
            [
                Paragraph(f"<b>Pay To:</b> {invoice_data.get('payee_name', business_name)}", styles['Normal']),
                Paragraph(f"<b>UPI ID:</b> {invoice_data['upi_id']}", styles['Normal']),
                Paragraph(f"<b>Bank:</b> {invoice_data.get('bank_name', 'N/A')}", styles['Normal']),
                Paragraph(f"<b>A/C No:</b> {invoice_data.get('bank_account_no', 'N/A')}", styles['Normal']),
                Paragraph(f"<b>IFSC:</b> {invoice_data.get('bank_ifsc', 'N/A')}", styles['Normal']),
            ],
            [
                qr_img,
                Paragraph("Scan to Pay", ParagraphStyle('CenterLabel', parent=styles['Normal'], alignment=TA_CENTER, fontSize=8, textColor=text_muted))
            ]
        ]
    ]
    
    payment_box = Table(payment_box_data, colWidths=[4.5*inch, 2.5*inch])
    payment_box.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#eff6ff')),
        ('ROUNDEDCORNERS', [10, 10, 10, 10]),
        ('PADDING', (0, 0), (-1, -1), 15),
    ]))
    elements.append(payment_box)
    
    # --- FOOTER ---
    elements.append(Spacer(1, 60))
    footer_text = (
        "Thank you for choosing us! We appreciate your business.<br/>"
        "This is a digitally generated invoice. No signature required."
    )
    elements.append(Paragraph(footer_text, ParagraphStyle('Footer', parent=styles['Normal'], alignment=TA_CENTER, textColor=text_muted, fontSize=9)))
    
    # Build
    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
