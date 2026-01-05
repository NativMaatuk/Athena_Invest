"""
Classic Analyzer Configuration
Configuration settings for the classic technical analysis agent.
"""
from .technical_config import SMA_PERIOD, HISTORICAL_PERIOD, INTERVAL

# ATR settings
ATR_PERIOD = 14  # Average True Range period (standard period)

# Resistance and entry zone settings
RESISTANCE_LOOKBACK = 30  # Days to look back for local resistance (High maximum)

# Extension settings
EXTENSION_THRESHOLD = 20.0  # Percentage threshold for extension (if price is more than 20% away from average)

# ATR risk thresholds (as percentage of price)
ATR_WARNING_THRESHOLD = 5.0  # Volatility warning threshold (ATR as % of price)
ATR_SEVERE_THRESHOLD = 8.0  # Severe risk warning threshold (ATR as % of price)

# SMA slope settings
SMA_SLOPE_LOOKBACK = 10  # Days to look back for SMA slope calculation
SMA_SLOPE_FLAT_THRESHOLD = 0.5  # Percentage change threshold to identify flat slope (< 0.5%)

# Data requirements
MIN_DATA_POINTS = 150  # Minimum data points required (for SMA_150 calculation)

