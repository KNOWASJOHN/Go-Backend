import json
from typing import List, Dict
from google import genai
from google.genai import types
from config import Config

def parse_chats(chat_messages: List[str]) -> List[Dict]:
    """
    Extracts structured purchase data using Gemini's Constrained Output.
    """
    if not Config.GEMINI_API_KEY:
        raise Exception("API Key missing. Check your .env file.")

    client = genai.Client(api_key=Config.GEMINI_API_KEY)
    
    # Contextualize messages with indices to help Gemini distinguish separate lines
    chat_context = "\n".join([f"Msg {i}: {msg}" for i, msg in enumerate(chat_messages)])

    # Define the exact structure Gemini MUST return
    response_schema = {
        "type": "ARRAY",
        "items": {
            "type": "OBJECT",
            "properties": {
                "item": {"type": "STRING", "description": "The name of the product"},
                "quantity": {"type": "INTEGER", "description": "Number of units"},
                "price": {"type": "NUMBER", "description": "Price per single unit in INR"}
            },
            "required": ["item", "quantity", "price"]
        }
    }

    prompt = f"""
    You are a logistics assistant. Extract items, quantities, and unit prices from these chats.
    Rules:
    1. If quantity is missing, use 1.
    2. If the user mentions a total price for multiple items, divide it to get the unit price.
    3. Ignore conversational filler; only extract actual orders.

    Chat History:
    {chat_context}
    """

    try:
        # Use 'gemini-2.0-flash' for speed/cost or 'gemini-2.0-pro' for complex reasoning
        response = client.models.generate_content(
            model=Config.GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=response_schema,
                temperature=0.1,  # Low temperature for high consistency
            )
        )

        # Gemini now returns a clean JSON string directly
        items = json.loads(response.text)
        
        # Final safety validation
        return [
            {
                "item": str(i.get("item", "Unknown")),
                "quantity": max(1, int(i.get("quantity", 1))),
                "price": float(i.get("price", 0.0))
            } 
            for i in items
        ]

    except Exception as e:
        print(f"Extraction Error: {e}")
        return []

def calculate_totals(items: List[Dict]) -> Dict:
    """
    Calculates the financial breakdown of the extracted items.
    """
    subtotal = sum(item['quantity'] * item['price'] for item in items)
    gst_rate = getattr(Config, 'GST_RATE', 0.18) # Default to 18% if missing
    gst_amount = subtotal * gst_rate
    
    return {
        'items': items,
        'subtotal': round(subtotal, 2),
        'gst': round(gst_amount, 2),
        'gst_rate': gst_rate * 100,
        'total': round(subtotal + gst_amount, 2)
    }