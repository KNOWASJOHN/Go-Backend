"""
PDF Generator Service
Generates professional PDF invoices using ReportLab.
"""

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


def generate_pdf(
    invoice_data: Dict,
    items: List[Dict],
    totals: Dict,
    qr_code_base64: str
) -> bytes:
    """
    Generate PDF invoice from data using ReportLab.
    
    Args:
        invoice_data: Invoice metadata
        items: List of items
        totals: Calculated totals
        qr_code_base64: Base64 QR code
        
    Returns:
        PDF as bytes
    """
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                           rightMargin=50, leftMargin=50,
                           topMargin=50, bottomMargin=50)
    
    # Container for PDF elements
    elements = []
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=10
    )
    
    normal_style = styles['Normal']
    
    # Company Header
    company_name = Paragraph(f"<b>{invoice_data['business_name']}</b>", 
                            ParagraphStyle('CompanyName', parent=styles['Heading1'],
                                         fontSize=20, textColor=colors.HexColor('#2c3e50'),
                                         spaceAfter=5))
    elements.append(company_name)
    
    company_details = Paragraph(
        f"{invoice_data['business_address']}<br/>"
        f"Phone: {invoice_data['business_phone']} | Email: {invoice_data['business_email']}<br/>"
        f"GST: {invoice_data['business_gst']}",
        normal_style
    )
    elements.append(company_details)
    elements.append(Spacer(1, 20))
    
    # Invoice Title
    invoice_title = Paragraph("<b>INVOICE</b>", title_style)
    elements.append(invoice_title)
    elements.append(Spacer(1, 20))
    
    # Invoice Info Table (Bill To and Invoice Details side by side)
    info_data = [
        [
            Paragraph("<b>Bill To:</b>", heading_style),
            Paragraph("<b>Invoice Details:</b>", heading_style)
        ],
        [
            Paragraph(
                f"<b>{invoice_data['customer_name']}</b><br/>"
                f"Contact: {invoice_data.get('customer_phone', 'N/A')}<br/>"
                f"Email: {invoice_data.get('customer_email', 'N/A')}",
                normal_style
            ),
            Paragraph(
                f"<b>Invoice Number:</b> {invoice_data['invoice_number']}<br/>"
                f"<b>Date:</b> {invoice_data['date']}",
                normal_style
            )
        ]
    ]
    
    info_table = Table(info_data, colWidths=[3*inch, 3*inch])
    info_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8f9fa')),
        ('PADDING', (0, 0), (-1, -1), 10),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 30))
    
    # Items Table
    table_data = [
        ['#', 'Description', 'Qty', 'Rate', 'Amount']
    ]
    
    for idx, item in enumerate(items, 1):
        amount = item['quantity'] * item['price']
        table_data.append([
            str(idx),
            item['item'],
            str(item['quantity']),
            f"Rs.{item['price']:.2f}",
            f"Rs.{amount:.2f}"
        ])
    
    items_table = Table(table_data, colWidths=[0.5*inch, 2.5*inch, 0.8*inch, 1.2*inch, 1.2*inch])
    items_table.setStyle(TableStyle([
        # Header row styling
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('TOPPADDING', (0, 0), (-1, 0), 12),
        
        # Data rows styling
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # # column
        ('ALIGN', (2, 1), (2, -1), 'CENTER'),  # Qty column
        ('ALIGN', (3, 1), (-1, -1), 'RIGHT'),   # Rate and Amount columns
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('PADDING', (0, 1), (-1, -1), 8),
        
        # Grid
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#2c3e50')),
        ('LINEBELOW', (0, 0), (-1, 0), 2, colors.HexColor('#2c3e50')),
        
        # Alternating row colors
        *[('BACKGROUND', (0, i), (-1, i), colors.HexColor('#f8f9fa')) 
          for i in range(2, len(table_data), 2)]
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 30))
    
    # Totals Table (aligned to right)
    totals_data = [
        ['Subtotal:', f"Rs.{totals['subtotal']:.2f}"],
        [f"GST ({totals['gst_rate']:.0f}%):", f"Rs.{totals['gst']:.2f}"],
        ['TOTAL:', f"Rs.{totals['total']:.2f}"],
    ]
    
    totals_table = Table(totals_data, colWidths=[2*inch, 1.5*inch])
    totals_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 1), 'Helvetica'),
        ('FONTNAME', (0, 2), (-1, 2), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('LINEABOVE', (0, 0), (-1, 0), 1, colors.HexColor('#2c3e50')),
        ('LINEABOVE', (0, 2), (-1, 2), 2, colors.HexColor('#2c3e50')),
        ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor('#2c3e50')),
        ('TEXTCOLOR', (0, 2), (-1, 2), colors.whitesmoke),
        ('PADDING', (0, 2), (-1, 2), 10),
    ]))
    
    # Create a table to align totals to the right
    right_aligned = Table([[totals_table]], colWidths=[6.5*inch])
    right_aligned.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
    ]))
    elements.append(right_aligned)
    elements.append(Spacer(1, 30))
    
    # Payment Section
    payment_heading = Paragraph("<b>Payment Information</b>", heading_style)
    elements.append(payment_heading)
    
    payment_text = Paragraph("Scan the QR code below to pay via UPI:", normal_style)
    elements.append(payment_text)
    elements.append(Spacer(1, 10))
    
    # QR Code Image
    import base64
    qr_image_data = qr_code_base64.split(',')[1] if ',' in qr_code_base64 else qr_code_base64
    qr_image_bytes = BytesIO(base64.b64decode(qr_image_data))
    qr_img = Image(qr_image_bytes, width=2*inch, height=2*inch)
    
    # Center the QR code
    qr_table = Table([[qr_img]], colWidths=[6.5*inch])
    qr_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    elements.append(qr_table)
    elements.append(Spacer(1, 10))
    
    # UPI ID
    upi_text = Paragraph(
        f"<b>Payment Method:</b> UPI<br/>"
        f"<b>Payee Name:</b> {invoice_data.get('payee_name', invoice_data['business_name'])}<br/>"
        f"<b>UPI ID:</b> {invoice_data['upi_id']}<br/>"
        f"<b>Amount:</b> Rs.{totals['total']:.2f}",
        ParagraphStyle('UPI', parent=normal_style, alignment=TA_CENTER)
    )
    elements.append(upi_text)
    elements.append(Spacer(1, 30))
    
    # Thank You
    thank_you = Paragraph(
        "<b>Thank You for Your Business!</b>",
        ParagraphStyle('ThankYou', parent=styles['Heading2'],
                      fontSize=18, textColor=colors.HexColor('#2c3e50'),
                      alignment=TA_CENTER, spaceAfter=20)
    )
    elements.append(thank_you)
    
    # Footer
    footer = Paragraph(
        "This is a computer-generated invoice and does not require a signature.<br/>"
        f"For any queries, please contact us at {invoice_data['business_email']}",
        ParagraphStyle('Footer', parent=normal_style,
                      fontSize=9, textColor=colors.grey, alignment=TA_CENTER)
    )
    elements.append(footer)
    
    # Build PDF
    doc.build(elements)
    
    # Get PDF bytes
    pdf_bytes = buffer.getvalue()
    buffer.close()
    
    return pdf_bytes
