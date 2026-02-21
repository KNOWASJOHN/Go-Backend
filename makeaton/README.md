# Invoice Generator API

Flask API that generates PDF invoices from chat messages using AI parsing, with UPI QR code payment integration.

## Features

- 🤖 AI-powered chat parsing using Google Gemini 2.5 Pro (FREE!)
- 📄 Professional PDF invoice generation with ReportLab
- 💳 UPI QR code generation for seamless payments
- 🧮 Automatic GST (18%) calculation
- 🎨 Beautiful web interface included
- 📱 RESTful API with JSON input/output

## Quick Start

### 1. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   - Copy `.env.example` to `.env`
   - Get your free Gemini API key from: https://makersuite.google.com/app/apikey
   - Add the key to `.env`
   - Update business details

### 3. Run the server
   ```bash
   python run.py
   ```

The server starts at `http://localhost:5000`

## Web Interface

Open your browser and go to **http://localhost:5000** for a beautiful web interface where you can:

- ✍️ Type chat messages naturally
- 👤 Enter customer details
- 🎯 Generate invoices with one click
- 📥 Download PDF automatically

See [static/README.md](static/README.md) for frontend usage guide.

## API Endpoint

### POST `/api/generate-invoice`

**Request Body:**
```json
{
  "chats": [
    "I'll take 2 pizzas",
    "Each pizza is 500 rupees",
    "Also need 3 cold drinks at 50 each"
  ],
  "upi_id": "merchant@paytm",
  "customer_name": "John Doe",
  "customer_phone": "+91-9876543210",
  "customer_email": "john@example.com"
}
```

**Response:**
- PDF file download with `Content-Type: application/pdf`
- Filename: `invoice_INV-YYYYMM-XXXX.pdf`

## Example Usage

```bash
curl -X POST http://localhost:5000/api/generate-invoice \
  -H "Content-Type: application/json" \
  -d @sample_request.json \
  --output invoice.pdf
```

## Requirements

- Python 3.8+
- Google Gemini API key (Free tier available)
- WeasyPrint dependencies (GTK3 on Windows)

## License

MIT
