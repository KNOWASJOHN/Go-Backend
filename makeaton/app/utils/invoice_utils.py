"""
Utility functions for invoice generation
"""

import os
from datetime import datetime
from threading import Lock
from config import Config

# Thread lock for counter file access
counter_lock = Lock()


def get_next_invoice_number() -> str:
    """
    Generate next invoice number in format: INV-YYYYMM-XXXX
    
    Returns:
        Invoice number string
    """
    with counter_lock:
        # Get current year-month
        now = datetime.now()
        current_period = now.strftime("%Y%m")
        
        # Read current counter
        counter_file = Config.COUNTER_FILE
        
        if os.path.exists(counter_file):
            with open(counter_file, 'r') as f:
                content = f.read().strip()
                if content:
                    parts = content.split('-')
                    if len(parts) == 2:
                        last_period, last_counter = parts
                        
                        # Reset counter if new month
                        if last_period == current_period:
                            counter = int(last_counter) + 1
                        else:
                            counter = 1
                    else:
                        counter = 1
                else:
                    counter = 1
        else:
            counter = 1
        
        # Write new counter
        with open(counter_file, 'w') as f:
            f.write(f"{current_period}-{counter}")
        
        # Format invoice number
        invoice_number = f"{Config.INVOICE_PREFIX}-{current_period}-{counter:04d}"
        
        return invoice_number


def format_date(date: datetime = None) -> str:
    """
    Format date for invoice display.
    
    Args:
        date: datetime object (uses current if None)
        
    Returns:
        Formatted date string
    """
    if date is None:
        date = datetime.now()
    
    return date.strftime("%d %B %Y")
