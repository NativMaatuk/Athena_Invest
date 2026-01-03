"""
AthenaInvest Configuration
All sensitive keys should be read from environment variables.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Tickers list for initial analysis
TICKERS = ['AAPL', 'MSFT', 'GOOGL', 'LAES', 'NB', 'TSLA', 'NVDA', 'BTC-USD', 'ETH-USD']

# Scoring weights
WEIGHT_TECH = 0.4  # 40% weight for technical score
WEIGHT_FUND = 0.6  # 60% weight for fundamental score

# Trading thresholds
BUY_THRESHOLD = 7.5  # Minimum score for buy signal
SELL_THRESHOLD = 5.0  # Maximum score for sell signal

# LLM Configuration
LLM_MODEL = os.getenv('LLM_MODEL', 'gpt-4o')  # Default to 'gpt-4o' if not set

# API Keys (read from environment variables)
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')

# Webhooks (read from environment variables)
WEBHOOK_URL = os.getenv('WEBHOOK_URL')

