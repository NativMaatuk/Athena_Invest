"""
AthenaInvest Configuration
All sensitive keys should be read from environment variables.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Tickers list for initial analysis
TICKERS = ['NVDA', 'GOOGL', 'TSLA', 'AMZN', 'AAPL', 'MSFT', 'META', 'META', 'AMD', 'PLTR', 'SPOT', 'INDO', 'HUSA', 'DXYZ', 'ORCL', 'ASTS', 'QCLS', 'LAES', 'NB', 'BTC-USD', 'ETH-USD', 'XRP-USD']

# Scoring weights
WEIGHT_TECH = 0.4  # 40% weight for technical score
WEIGHT_FUND = 0.6  # 60% weight for fundamental score

# Trading thresholds
BUY_THRESHOLD = 7.5  # Minimum score for buy signal
SELL_THRESHOLD = 5.0  # Maximum score for sell signal

# LLM Configuration
LLM_MODEL = os.getenv('LLM_MODEL', 'gpt-4o')  # Default to 'gpt-4o' if not set

# API Keys (read from environment variables)
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')

# Webhooks (read from environment variables)
WEBHOOK_URL = os.getenv('WEBHOOK_URL')

# Sector-based Webhooks
WEBHOOK_CRYPTO = os.getenv('WEBHOOK_CRYPTO')
WEBHOOK_TECH = os.getenv('WEBHOOK_TECH')
WEBHOOK_ENERGY = os.getenv('WEBHOOK_ENERGY')
WEBHOOK_HEALTH = os.getenv('WEBHOOK_HEALTH')
WEBHOOK_FINANCE = os.getenv('WEBHOOK_FINANCE')
WEBHOOK_CONSUMER = os.getenv('WEBHOOK_CONSUMER')
WEBHOOK_FEAR_AND_GREED = os.getenv('WEBHOOK_FEAR_AND_GREED') # Market Sentiment / General Info

# Sector to Webhook Mapping
# Maps yfinance sector names to the corresponding webhook URL variable
SECTOR_CHANNEL_MAP = {
    # Crypto
    'Crypto': WEBHOOK_CRYPTO,
    
    # Tech Titans (Technology, Communication Services)
    'Technology': WEBHOOK_TECH,
    'Communication Services': WEBHOOK_TECH,
    
    # Energy & Industrial (Energy, Utilities, Industrials, Basic Materials)
    'Energy': WEBHOOK_ENERGY,
    'Utilities': WEBHOOK_ENERGY,
    'Industrials': WEBHOOK_ENERGY,
    'Basic Materials': WEBHOOK_ENERGY,
    
    # Healthcare & Bio
    'Healthcare': WEBHOOK_HEALTH,
    
    # Finance & Real Estate
    'Financial Services': WEBHOOK_FINANCE,
    'Real Estate': WEBHOOK_FINANCE,
    
    # Consumer Market
    'Consumer Cyclical': WEBHOOK_CONSUMER,
    'Consumer Defensive': WEBHOOK_CONSUMER,
}

# Fallback to general webhook if specific one is missing
for sector, url in SECTOR_CHANNEL_MAP.items():
    if not url:
        SECTOR_CHANNEL_MAP[sector] = WEBHOOK_URL

# Hebrew Sector Mapping
SECTOR_HEBREW_MAP = {
    'Crypto': 'קריפטו',
    'Technology': 'טכנולוגיה',
    'Communication Services': 'שירותי תקשורת',
    'Energy': 'אנרגיה',
    'Utilities': 'תשתיות',
    'Industrials': 'תעשייה',
    'Basic Materials': 'חומרי גלם',
    'Healthcare': 'בריאות',
    'Financial Services': 'פיננסים',
    'Real Estate': 'נדל"ן',
    'Consumer Cyclical': 'צריכה מחזורית',
    'Consumer Defensive': 'צריכה בסיסית'
}
