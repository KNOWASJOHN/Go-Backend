import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Application configuration"""
    
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    
    # OpenRouter AI
    OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
    OPENROUTER_MODEL = os.getenv('OPENROUTER_MODEL', 'google/gemini-2.0-flash-001')
    
    # Business Details
    BUSINESS_NAME = os.getenv('BUSINESS_NAME', 'Your Business Name')
    BUSINESS_ADDRESS = os.getenv('BUSINESS_ADDRESS', '123 Business Street, City, State - 123456')
    BUSINESS_PHONE = os.getenv('BUSINESS_PHONE', '+91-1234567890')
    BUSINESS_EMAIL = os.getenv('BUSINESS_EMAIL', 'info@yourbusiness.com')
    BUSINESS_GST = os.getenv('BUSINESS_GST', '22AAAAA0000A1Z5')
    
    # Payment Information
    DEFAULT_PAYMENT_METHOD = os.getenv('DEFAULT_PAYMENT_METHOD', 'UPI')
    DEFAULT_PAYEE_NAME = os.getenv('DEFAULT_PAYEE_NAME', BUSINESS_NAME)
    DEFAULT_UPI_ID = os.getenv('DEFAULT_UPI_ID', 'merchant@upi')
    BANK_NAME = os.getenv('BANK_NAME', 'N/A')
    BANK_ACCOUNT_NO = os.getenv('BANK_ACCOUNT_NO', 'N/A')
    BANK_IFSC = os.getenv('BANK_IFSC', 'N/A')
    
    # Tax Configuration
    GST_RATE = float(os.getenv('GST_RATE', '0.0'))
    
    # Invoice Settings
    INVOICE_PREFIX = os.getenv('INVOICE_PREFIX', 'INV')
    CURRENCY = os.getenv('CURRENCY', 'INR')
    CURRENCY_SYMBOL = os.getenv('CURRENCY_SYMBOL', 'Rs.')
    
    # File Paths
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    COUNTER_FILE = os.path.join(BASE_DIR, 'invoice_counter.txt')
