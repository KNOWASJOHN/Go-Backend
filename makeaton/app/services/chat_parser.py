import json
import re
import time
import requests
from typing import List, Dict
from datetime import datetime
from config import Config

def parse_chats(chat_messages: List[str]) -> List[Dict]:
    """
    Extracts structured purchase data using OpenRouter AI (Gemini 2.0 Flash) with a high-precision prompt.
    """
    if not Config.OPENROUTER_API_KEY:
        raise Exception("OpenRouter API Key missing. Check your .env file.")

    # Contextualize messages
    chat_context = "\n".join([f"Msg {i}: {msg}" for i, msg in enumerate(chat_messages)])

    system_prompt = """You are a highly accurate Billing Assistant. Your goal is to convert informal chat messages into a structured JSON invoice.
System Prompting and Regex Extraction:
1. Identify all products/items being ordered. NEVER combine different items (e.g., "pizza and coke") into one line. Each must be a separate object.
2. CONSOLIDATE: If the same item appears multiple times in the history (e.g., mentioned in two different messages), combine them into a single entry with the summed quantity.
3. CURRENT ORDER ONLY: The history might contain old orders. If you see a system message like "Your order has been placed!", treat messages BEFORE it as potentially separate. However, if the user is refining the same order, consolidate. Use your best judgment to provide a final, deduplicated list of what the user wants NOW.
4. For each item, extract the EXACT quantity. If none specify, default to 1.
5. Determine the UNIT PRICE (price for 1 unit) of each item:
   - If the user says "5 pizzas for 1000", the unit price is 200 (1000/5).
   - If the user says "2 burgers 150 each", the unit price is 150.
   - If the user provides a list of items and then a "Total", and no individual prices are mentioned, distribute the total sum among the items proportionally or equally.
   - If multiple prices are mentioned, the most recent or the one explicitly labeled 'total' is the final amount.
4. Output MUST be ONLY a JSON array of objects. NO EXPLANATIONS. NO MARKDOWN.
5. Keys: "item" (string), "quantity" (integer), "price" (float).
"""

    prompt = f"Convert this chat history into a JSON billing array:\n\n{chat_context}"

    items = []
    
    # Try OpenRouter with Retry
    max_retries = 1
    for attempt in range(max_retries + 1):
        try:
            print(f"\n[OpenRouter] Extraction attempt {attempt+1}...")
            
            response = requests.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {Config.OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "http://localhost:3000", # Required by OpenRouter for some models
                    "X-Title": "TRNDO-AI Billing Assistant"
                },
                data=json.dumps({
                    "model": Config.OPENROUTER_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.1,
                    "max_tokens": 1000
                }),
                timeout=30
            )
            
            if response.status_code != 200:
                print(f"OpenRouter Error: {response.status_code} - {response.text}")
                if response.status_code == 429 and attempt < max_retries:
                    time.sleep(2)
                    continue
                break

            result = response.json()
            content = result['choices'][0]['message']['content'].strip()
            
            # Extract JSON array using regex in case of prefix/suffix noise
            json_match = re.search(r'\[\s*{.*}\s*\]', content, re.DOTALL)
            if json_match:
                content = json_match.group(0)
            
            print(f"\n[AI Result]: {content}")
            
            data = json.loads(content)
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                # Handle cases where model wraps it in an object
                for val in data.values():
                    if isinstance(val, list):
                        items = val
                        break
            
            if items:
                print(f"[Success] Extracted {len(items)} items via AI.")
                break 
                
        except Exception as e:
            print(f"Extraction Error (Attempt {attempt+1}): {e}")
            if attempt < max_retries:
                time.sleep(2)
                continue
            break

    # Regex Fallback if AI really fails
    if not items:
        print("[Fallback] AI failed. Using Regex extraction...")
        chat_text = " ".join(chat_messages)
        
        # Total price extraction (looks for "1000 rs", "1000 rps", "1000 rupees")
        price_match = re.search(r'(\d+(?:,\d+)?)\s*(?:rps|rs|inr|rupees|bucks|total)', chat_text, re.I)
        total_price = float(price_match.group(1).replace(',', '')) if price_match else 0
        
        # Item extraction: "qty item" or "item qty"
        found_products = []
        for msg in chat_messages:
            clean_msg = re.sub(r'\[.*?\] \w+ \(.*?\): ', '', msg)
            if any(x in clean_msg.lower() for x in ["placed", "hello", "hi", "how much", "total"]):
                continue
            
            # Simple match for "2 pizza" or "pizza 2"
            parts = re.findall(r'(\d+)\s+([a-zA-Z\s]{3,20})|([a-zA-Z\s]{3,20})\s+(\d+)', clean_msg)
            for p in parts:
                q = int(p[0] or p[3])
                n = (p[1] or p[2]).strip()
                if len(n) > 2:
                    found_products.append({"name": n.title(), "qty": q})
        
        if found_products:
            # Distribute total price among items
            price_per_item = total_price / len(found_products) if total_price > 0 else 100.0
            for itm in found_products:
                items.append({
                    "item": itm["name"],
                    "quantity": itm["qty"],
                    "price": round(price_per_item / itm["qty"], 2) if itm["qty"] > 0 else price_per_item
                })
        else:
            items = [{"item": "Order Items", "quantity": 1, "price": total_price or 100.0}]

    # Final cleansing & Deduplication
    deduplicated = {}
    for i in items:
        if not isinstance(i, dict): continue
        name = str(i.get("item", "Custom Item")).strip().title()
        qty = int(i.get("quantity", 1))
        price = float(i.get("price", 0.0))
        
        if name in deduplicated:
            # If item exists, add quantity and use the newest price (or average)
            deduplicated[name]['quantity'] += qty
            if price > 0: deduplicated[name]['price'] = price
        else:
            deduplicated[name] = {"item": name, "quantity": qty, "price": price}

    return list(deduplicated.values())

def calculate_totals(items: List[Dict]) -> Dict:
    """Calculates subtotal, GST, and grand total."""
    subtotal = sum(i['quantity'] * i['price'] for i in items)
    gst_rate = Config.GST_RATE
    gst_amount = subtotal * gst_rate
    
    return {
        'items': items,
        'subtotal': round(subtotal, 2),
        'gst': round(gst_amount, 2),
        'gst_rate': int(gst_rate * 100),
        'total': round(subtotal + gst_amount, 2)
    }