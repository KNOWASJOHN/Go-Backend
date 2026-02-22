"""
API Routes for Invoice Generation
"""

from flask import Blueprint, request, jsonify, send_file
from marshmallow import ValidationError
import io
from datetime import datetime

from app.schemas import InvoiceRequestSchema
from app.services.chat_parser import parse_chats, calculate_totals
from app.services.qr_generator import generate_upi_qr
from app.services.pdf_generator import generate_pdf
from app.utils.invoice_utils import get_next_invoice_number, format_date
from config import Config
import json
import os
import logging

# Create blueprint
api_bp = Blueprint('api', __name__, url_prefix='/api')

# In-memory notifications (for demo purposes)
NOTIFICATIONS = []

# Path for profile persistence
PROFILE_PATH = os.path.join(Config.BASE_DIR, 'business_profile.json')

def load_profile():
    if os.path.exists(PROFILE_PATH):
        try:
            with open(PROFILE_PATH, 'r') as f:
                return json.load(f)
        except:
            pass
    return {
        "business_name": Config.BUSINESS_NAME,
        "business_address": Config.BUSINESS_ADDRESS,
        "business_phone": Config.BUSINESS_PHONE,
        "business_email": Config.BUSINESS_EMAIL,
        "business_gst": Config.BUSINESS_GST,
        "default_payment_method": Config.DEFAULT_PAYMENT_METHOD,
        "default_upi_id": Config.DEFAULT_UPI_ID,
        "payee_name": Config.BUSINESS_NAME,
        "bank_name": Config.BANK_NAME,
        "bank_account_no": Config.BANK_ACCOUNT_NO,
        "bank_ifsc": Config.BANK_IFSC
    }

def save_profile(data):
    with open(PROFILE_PATH, 'w') as f:
        json.dump(data, f, indent=4)

# Initialize schema
invoice_schema = InvoiceRequestSchema()

@api_bp.route('/business-profile', methods=['GET', 'POST'])
def business_profile():
    if request.method == 'POST':
        data = request.json
        save_profile(data)
        return jsonify({"status": "success", "message": "Profile updated"})
    return jsonify(load_profile())

@api_bp.route('/upload-invoice', methods=['POST'])
def upload_invoice():
    """Endpoint to 'take' the PDF (save it to a static folder)"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    # Save to static/invoices
    upload_dir = os.path.join(Config.BASE_DIR, 'static', 'invoices')
    os.makedirs(upload_dir, exist_ok=True)
    
    filepath = os.path.join(upload_dir, file.filename)
    file.save(filepath)
    
    return jsonify({
        "status": "success",
        "url": f"/static/invoices/{file.filename}"
    })


@api_bp.route('/messages', methods=['POST'])
def receive_message():
    """Simple endpoint to log incoming messages with history"""
    try:
        if request.is_json:
            data = request.get_json()
            sender = data.get('sender', 'Unknown')
            message = data.get('message', '')
            history = data.get('history', [])
            
            logging.info(f"[Incoming Message] From: {sender}, Message: {message}")
            if history:
                logging.debug(f"Chat History Context ({len(history)} messages): {history}")
            
            print(f"\n[Incoming Message] From: {sender}")
            print(f"Message: {message}")
            if history:
                print(f"Chat History Context ({len(history)} messages):")
                for h in history:
                    print(f"  {h}")
            print("-" * 40)
        else:
            data = request.data.decode('utf-8')
            print(f"\n================ RECEIVING RAW DATA =================\n{data}\n================================================")
        return "OK", 200
    except Exception as e:
        print(f"Error receiving message: {e}")
        return str(e), 500


@api_bp.route('/generate-invoice', methods=['POST'])
def generate_invoice():
    """
    Generate PDF invoice from chat messages.
    
    Request JSON:
    {
        "chats": ["chat message 1", "chat message 2", ...],
        "upi_id": "merchant@paytm",
        "customer_name": "John Doe",
        "customer_phone": "+91-9876543210",  // optional
        "customer_email": "john@example.com",  // optional
        "payee_name": "Business Name"  // optional, defaults to config
    }
    
    Returns:
        PDF file as attachment
    """
    
    try:
        # Load profile for defaults
        profile = load_profile()
        
        # Validate request data
        json_data = request.json or {}
        if 'upi_id' not in json_data:
            json_data['upi_id'] = profile.get('default_upi_id', Config.DEFAULT_UPI_ID)
            
        try:
            data = invoice_schema.load(json_data)
        except ValidationError as err:
            return jsonify({
                'error': 'Validation failed',
                'details': err.messages
            }), 400
        
        # Extract chat messages
        chat_messages = data['chats']
        
        with open('debug_log.txt', 'a') as f:
            f.write(f"\n--- New Invoice Request {datetime.now()} ---\n")
            f.write(f"Customer: {data.get('customer_name')}\n")
            f.write(f"Chats: {json.dumps(chat_messages, indent=2)}\n")
        
        # Parse chats using AI
        try:
            items = parse_chats(chat_messages)
        except Exception as e:
            return jsonify({
                'error': 'Failed to parse chat messages',
                'details': str(e)
            }), 500
        
        # Check if items were extracted
        if not items:
            with open('debug_log.txt', 'a') as f:
                f.write("ERROR: No items extracted by Gemini\n")
            return jsonify({
                'error': 'No items found in chat messages',
                'details': 'Please ensure your chat messages contain item names and prices'
            }), 400
        
        with open('debug_log.txt', 'a') as f:
            f.write(f"Items Extracted: {json.dumps(items, indent=2)}\n")
        
        # Calculate totals
        totals = calculate_totals(items)
        
        # Generate invoice number
        invoice_number = get_next_invoice_number()
        
        # Prepare invoice data (combining profile and request)
        payee_name = data.get('payee_name') or profile.get('payee_name') or profile.get('business_name', Config.BUSINESS_NAME)
        invoice_data = {
            'invoice_number': invoice_number,
            'date': format_date(),
            'customer_name': data['customer_name'],
            'customer_phone': data.get('customer_phone', 'N/A'),
            'customer_email': data.get('customer_email', 'N/A'),
            'upi_id': data['upi_id'],
            'business_name': profile.get('business_name', Config.BUSINESS_NAME),
            'business_address': profile.get('business_address', Config.BUSINESS_ADDRESS),
            'business_phone': profile.get('business_phone', Config.BUSINESS_PHONE),
            'business_email': profile.get('business_email', Config.BUSINESS_EMAIL),
            'business_gst': profile.get('business_gst', Config.BUSINESS_GST),
            'payee_name': payee_name,
            'payment_method': profile.get('default_payment_method', Config.DEFAULT_PAYMENT_METHOD),
            'bank_name': profile.get('bank_name', Config.BANK_NAME),
            'bank_account_no': profile.get('bank_account_no', Config.BANK_ACCOUNT_NO),
            'bank_ifsc': profile.get('bank_ifsc', Config.BANK_IFSC)
        }
        
        # Generate UPI QR code
        qr_code_base64 = generate_upi_qr(
            upi_id=data['upi_id'],
            amount=totals['total'],
            payee_name=payee_name,
            invoice_number=invoice_number
        )
        
        # Generate PDF
        try:
            pdf_bytes = generate_pdf(
                invoice_data=invoice_data,
                items=items,
                totals=totals,
                qr_code_base64=qr_code_base64
            )
        except Exception as e:
            return jsonify({
                'error': 'Failed to generate PDF',
                'details': str(e)
            }), 500
        
        # Save to static/invoices
        upload_dir = os.path.join(Config.BASE_DIR, 'static', 'invoices')
        os.makedirs(upload_dir, exist_ok=True)
        filename = f"invoice_{invoice_number}.pdf"
        filepath = os.path.join(upload_dir, filename)
        with open(filepath, 'wb') as f:
            f.write(pdf_bytes)
            
        # Add to notifications
        item_names = [i.get('item', 'Item') for i in items]
        NOTIFICATIONS.append({
            "id": f"inv-{invoice_number}",
            "title": "New Invoice Generated",
            "message": f"Invoice {invoice_number} for {data['customer_name']} is ready.",
            "time": datetime.now().strftime("%H:%M"),
            "type": "invoice",
            "url": f"/static/invoices/{filename}",
            "order": {
                "id": f"ORD-{invoice_number}",
                "customer": data['customer_name'],
                "item": ", ".join(item_names) if len(item_names) <= 2 else f"{item_names[0]} + {len(item_names)-1} more",
                "status": "completed",
                "time": "Just now",
                "amount": totals['total'],
                "phone": data.get('customer_phone'),
                "quantity": sum(i.get('quantity', 1) for i in items),
                "raw_items": items
            }
        })

        pdf_buffer = io.BytesIO(pdf_bytes)
        pdf_buffer.seek(0)

        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'invoice_{invoice_number}.pdf'
        )
        
    except Exception as e:
        return jsonify({
            'error': 'Internal server error',
            'details': str(e)
        }), 500


@api_bp.route('/notifications', methods=['GET', 'DELETE'])
def get_notifications():
    global NOTIFICATIONS
    if request.method == 'DELETE':
        NOTIFICATIONS = []
        return jsonify({"status": "success"})
    return jsonify(NOTIFICATIONS)


@api_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'Invoice Generator API',
        'timestamp': datetime.now().isoformat()
    })


@api_bp.route('/test-parse', methods=['POST'])
def test_parse():
    """
    Test endpoint to parse chats without generating PDF.
    Useful for debugging chat parsing.
    
    Request JSON:
    {
        "chats": ["chat message 1", "chat message 2", ...]
    }
    
    Returns:
        JSON with parsed items and totals
    """
    
    try:
        data = request.json
        
        if not data or 'chats' not in data:
            return jsonify({
                'error': 'Missing chats field'
            }), 400
        
        # Parse chats
        items = parse_chats(data['chats'])
        
        # Calculate totals
        totals = calculate_totals(items)
        
        return jsonify({
            'items': items,
            'totals': totals
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500


@api_bp.route('/generate-invoice-direct', methods=['POST'])
def generate_invoice_direct():
    """
    Generate PDF invoice from manually provided items (no AI parsing).
    
    Request JSON:
    {
        "items": [{"item": "Pizza", "quantity": 2, "price": 500}, ...],
        "upi_id": "merchant@paytm",
        "customer_name": "John Doe",
        "customer_phone": "+91-9876543210",  // optional
        "customer_email": "john@example.com",  // optional
        "payee_name": "Business Name"  // optional
    }
    """
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No JSON body provided'}), 400

        # Validate required fields
        items_raw = data.get('items', [])
        if not items_raw:
            return jsonify({'error': 'No items provided'}), 400

        customer_name = data.get('customer_name', '').strip()
        upi_id = data.get('upi_id', '').strip()
        if not customer_name or not upi_id:
            return jsonify({'error': 'customer_name and upi_id are required'}), 400

        # Sanitize items
        items = []
        for i in items_raw:
            items.append({
                'item': str(i.get('item', 'Unknown')),
                'quantity': max(1, int(i.get('quantity', 1))),
                'price': float(i.get('price', 0))
            })

        # Calculate totals
        totals = calculate_totals(items)

        # Generate invoice number
        invoice_number = get_next_invoice_number()

        # Load profile
        profile = load_profile()
        
        # Prepare invoice data
        invoice_data = {
            'invoice_number': invoice_number,
            'date': format_date(),
            'customer_name': customer_name,
            'customer_phone': data.get('customer_phone', 'N/A'),
            'customer_email': data.get('customer_email', 'N/A'),
            'upi_id': upi_id,
            'business_name': profile.get('business_name', Config.BUSINESS_NAME),
            'business_address': profile.get('business_address', Config.BUSINESS_ADDRESS),
            'business_phone': profile.get('business_phone', Config.BUSINESS_PHONE),
            'business_email': profile.get('business_email', Config.BUSINESS_EMAIL),
            'business_gst': profile.get('business_gst', Config.BUSINESS_GST),
            'payee_name': data.get('payee_name') or profile.get('payee_name') or profile.get('business_name'),
            'payment_method': profile.get('default_payment_method', Config.DEFAULT_PAYMENT_METHOD),
            'bank_name': profile.get('bank_name', Config.BANK_NAME),
            'bank_account_no': profile.get('bank_account_no', Config.BANK_ACCOUNT_NO),
            'bank_ifsc': profile.get('bank_ifsc', Config.BANK_IFSC)
        }

        # Generate UPI QR code
        qr_code_base64 = generate_upi_qr(
            upi_id=upi_id,
            amount=totals['total'],
            payee_name=invoice_data['payee_name'],
            invoice_number=invoice_number
        )

        # Generate PDF
        pdf_bytes = generate_pdf(
            invoice_data=invoice_data,
            items=items,
            totals=totals,
            qr_code_base64=qr_code_base64
        )

        # Save to static/invoices
        upload_dir = os.path.join(Config.BASE_DIR, 'static', 'invoices')
        os.makedirs(upload_dir, exist_ok=True)
        filename = f"invoice_{invoice_number}.pdf"
        filepath = os.path.join(upload_dir, filename)
        with open(filepath, 'wb') as f:
            f.write(pdf_bytes)

        # Add to notifications
        item_names = [i.get('item', 'Item') for i in items]
        NOTIFICATIONS.append({
            "id": f"inv-{invoice_number}",
            "title": "New Invoice Generated",
            "message": f"Invoice {invoice_number} for {customer_name} is ready.",
            "time": datetime.now().strftime("%H:%M"),
            "type": "invoice",
            "url": f"/static/invoices/{filename}",
            "order": {
                "id": f"ORD-{invoice_number}",
                "customer": customer_name,
                "item": ", ".join(item_names) if len(item_names) <= 2 else f"{item_names[0]} + {len(item_names)-1} more",
                "status": "completed",
                "time": "Just now",
                "amount": totals['total'],
                "phone": data.get('customer_phone'),
                "quantity": sum(i.get('quantity', 1) for i in items),
                "raw_items": items
            }
        })

        pdf_buffer = io.BytesIO(pdf_bytes)
        pdf_buffer.seek(0)

        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'invoice_{invoice_number}.pdf'
        )

    except Exception as e:
        return jsonify({
            'error': 'Internal server error',
            'details': str(e)
        }), 500
