# 🎨 Frontend Usage Guide

## Access the Web Interface

Once your server is running, open your browser and navigate to:

```
http://localhost:5000
```

## Features

### 1. **Simple Chat Input**
- Type your order conversation naturally
- Each line is treated as a chat message
- The AI (Gemini 2.5 Pro) extracts items, quantities, and prices

### 2. **Customer Information**
- UPI ID (required) - for payment QR code
- Customer Name (required)
- Phone & Email (optional)

### 3. **Instant Invoice Generation**
- Click "Generate Invoice"
- AI processes your chat
- PDF downloads automatically

## Example Chat Input

```
I want 2 large pizzas
Each pizza costs 500 rupees
Also add 3 cold drinks at 50 each
And 1 garlic bread for 150
```

The AI will automatically understand:
- 2 × Pizza @ ₹500 = ₹1000
- 3 × Cold Drink @ ₹50 = ₹150
- 1 × Garlic Bread @ ₹150 = ₹150
- **Subtotal:** ₹1300
- **GST (18%):** ₹234
- **Total:** ₹1534

## Tips for Best Results

✅ **Do:**
- Mention quantities and prices clearly
- Use natural language
- Separate different items on new lines

❌ **Don't:**
- Use vague descriptions without prices
- Mix multiple items in one line without clarity

## Troubleshooting

**"API key expired"**
- Get a new free API key from: https://makersuite.google.com/app/apikey
- Update it in the `.env` file: `GEMINI_API_KEY=your-new-key`
- Restart the server

**"No items found"**
- Make sure chat includes both item names AND prices
- Try more explicit phrasing: "2 pizzas at 500 each"

**Server not responding**
- Check if `python run.py` is running
- Verify server is on http://localhost:5000

## Screenshots

The frontend features:
- 🎨 Beautiful gradient design
- 📱 Mobile responsive
- ⚡ Real-time processing feedback
- 📥 Automatic PDF download
- ✨ AI-powered extraction

Enjoy generating invoices effortlessly! 🎉
