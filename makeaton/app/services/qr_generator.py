"""
QR Code Generator Service
Generates UPI payment QR codes for invoices.
"""

import qrcode
import io
import base64
from typing import Optional
from config import Config


def generate_upi_qr(
    upi_id: str,
    amount: float,
    payee_name: str,
    invoice_number: str,
    transaction_note: Optional[str] = None
) -> str:
    """
    Generate UPI payment QR code and return as base64 encoded image.
    
    Args:
        upi_id: UPI ID/VPA (e.g., merchant@paytm)
        amount: Payment amount
        payee_name: Name of the payee/merchant
        invoice_number: Invoice number for reference
        transaction_note: Optional transaction note
        
    Returns:
        Base64 encoded PNG image string (suitable for HTML img src)
    """
    
    # Create UPI deep link
    # Format: upi://pay?pa=UPI_ID&pn=NAME&am=AMOUNT&cu=CURRENCY&tn=NOTE
    
    if not transaction_note:
        transaction_note = f"Payment for Invoice {invoice_number}"
    
    upi_url = (
        f"upi://pay?"
        f"pa={upi_id}"
        f"&pn={payee_name}"
        f"&am={amount:.2f}"
        f"&cu={Config.CURRENCY}"
        f"&tn={transaction_note}"
    )
    
    # Generate QR code
    qr = qrcode.QRCode(
        version=1,  # Auto-size
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    
    qr.add_data(upi_url)
    qr.make(fit=True)
    
    # Create image
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to base64
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    img_base64 = base64.b64encode(buffer.getvalue()).decode()
    
    # Return as data URI for HTML embedding
    return f"data:image/png;base64,{img_base64}"


def get_upi_string(upi_id: str, amount: float, invoice_number: str) -> str:
    """
    Get the UPI payment string for reference/display.
    
    Args:
        upi_id: UPI ID
        amount: Payment amount
        invoice_number: Invoice number
        
    Returns:
        Formatted UPI payment string
    """
    return f"upi://pay?pa={upi_id}&am={amount:.2f}&tn=Invoice-{invoice_number}"
