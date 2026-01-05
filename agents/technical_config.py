"""
Technical Analyzer Configuration
Configuration settings for the technical analysis agent.
"""

# Data fetching settings
HISTORICAL_PERIOD = "1y"  # Historical data period (1 year - needed for SMA_150 which requires 150 data points)
INTERVAL = "1d"  # Data interval (daily)

# Indicator periods
SMA_PERIOD = 150  # Simple Moving Average period
EMA_PERIOD = 50  # Exponential Moving Average period
RSI_PERIOD = 14  # Relative Strength Index period
CCI_PERIOD = 20  # Commodity Channel Index period
BBANDS_PERIOD = 20  # Bollinger Bands period
VOLUME_MA_PERIOD = 20  # Volume Moving Average period

# Bollinger Bands settings
BBANDS_STD_DEV = 2  # Standard deviation multiplier for Bollinger Bands

# SMA Crossover threshold
SMA_CROSSOVER_PCT = 5.0  # Percentage threshold for SMA crossover scoring

# Scoring weights (points) - Updated for 10-point system
SCORE_SMA_CROSSOVER = 3.0  # Points for price near SMA (0% < deviation <= SMA_CROSSOVER_PCT)
SCORE_SMA_ESTABLISHED = 1.0  # Points for price well above SMA (deviation > SMA_CROSSOVER_PCT)
SCORE_EMA_ABOVE = 2.0  # Points for price above EMA
SCORE_RSI_OPTIMAL = 2.0  # Points for RSI in optimal range (40-65)
SCORE_VOLUME_HIGH = 1.0  # Points for volume above average
SCORE_CCI_STRONG = 2.0  # Points for CCI in strong range (100-200)

# Penalties
PENALTY_RSI_EXTREME = -2.0  # Penalty for RSI overbought (>70) or oversold (<30)
PENALTY_BBANDS_OVEREXTENDED = -2.0  # Penalty for price above upper Bollinger Band

# RSI thresholds (updated)
RSI_OPTIMAL_LOW = 40  # RSI optimal lower threshold
RSI_OPTIMAL_HIGH = 65  # RSI optimal upper threshold
RSI_OVERSOLD = 30  # RSI oversold threshold
RSI_OVERBOUGHT = 70  # RSI overbought threshold

# CCI thresholds
CCI_STRONG_LOW = 100  # CCI strong lower threshold
CCI_STRONG_HIGH = 200  # CCI strong upper threshold

# Maximum score
MAX_SCORE = 10.0

