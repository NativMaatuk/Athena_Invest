"""
Technical Analyzer
Handles technical analysis using indicators and scoring.
"""
import yfinance as yf
import pandas as pd
import talib
from .technical_config import (
    HISTORICAL_PERIOD,
    INTERVAL,
    SMA_PERIOD,
    EMA_PERIOD,
    RSI_PERIOD,
    CCI_PERIOD,
    BBANDS_PERIOD,
    VOLUME_MA_PERIOD,
    BBANDS_STD_DEV,
    SCORE_SMA_CROSSOVER,
    SCORE_SMA_ESTABLISHED,
    SCORE_EMA_ABOVE,
    SCORE_RSI_OPTIMAL,
    SCORE_VOLUME_HIGH,
    SCORE_CCI_STRONG,
    PENALTY_RSI_EXTREME,
    PENALTY_BBANDS_OVEREXTENDED,
    RSI_OPTIMAL_LOW,
    RSI_OPTIMAL_HIGH,
    RSI_OVERSOLD,
    RSI_OVERBOUGHT,
    CCI_STRONG_LOW,
    CCI_STRONG_HIGH,
    MAX_SCORE,
    SMA_CROSSOVER_PCT
)


class TechnicalAnalyzer:
    """
    Technical analysis agent that calculates indicators and scores.
    """
    
    def analyze(self, ticker: str) -> pd.DataFrame:
        """
        Fetch historical data and calculate technical indicators.
        
        Args:
            ticker: Stock ticker symbol (e.g., 'AAPL')
            
        Returns:
            DataFrame with the last two rows containing all indicators
        """
        # Fetch historical data based on configuration
        stock = yf.Ticker(ticker)
        df = stock.history(period=HISTORICAL_PERIOD, interval=INTERVAL)
        
        # Reset index to have Date as a column (if needed)
        if isinstance(df.index, pd.DatetimeIndex):
            df = df.reset_index()
        
        # Calculate technical indicators using TA-Lib
        # Simple Moving Average
        df['SMA_150'] = talib.SMA(df['Close'].values, timeperiod=SMA_PERIOD)
        
        # Exponential Moving Average
        df['EMA_50'] = talib.EMA(df['Close'].values, timeperiod=EMA_PERIOD)
        
        # Relative Strength Index
        df['RSI'] = talib.RSI(df['Close'].values, timeperiod=RSI_PERIOD)
        
        # Commodity Channel Index
        df['CCI'] = talib.CCI(df['High'].values, df['Low'].values, df['Close'].values, timeperiod=CCI_PERIOD)
        
        # Bollinger Bands
        bb_upper, bb_middle, bb_lower = talib.BBANDS(
            df['Close'].values,
            timeperiod=BBANDS_PERIOD,
            nbdevup=BBANDS_STD_DEV,
            nbdevdn=BBANDS_STD_DEV,
            matype=0
        )
        df['BBands_Upper'] = bb_upper
        df['BBands_Middle'] = bb_middle
        df['BBands_Lower'] = bb_lower
        
        # Calculate volume moving average
        df['Volume_MA_20'] = df['Volume'].rolling(window=VOLUME_MA_PERIOD).mean()
        
        # Return the last two rows
        return df.tail(2)
    
    def calculate_score(self, data_frame: pd.DataFrame) -> tuple[float, str]:
        """
        Calculate technical score based on indicators.
        
        Args:
            data_frame: DataFrame with at least the last row containing indicators
            
        Returns:
            Tuple of (score: float between 0-MAX_SCORE, summary: str)
        """
        # Get the last row (most recent data)
        last_row = data_frame.iloc[-1]
        
        # Initialize base score and tracking
        score = 0.0
        summary_parts = []
        added_points = []
        penalties = []
        
        # SMA 150 - Complex logic with deviation calculation
        if pd.notna(last_row['SMA_150']):
            if last_row['Close'] > last_row['SMA_150']:
                # Calculate deviation percentage
                deviation_pct = ((last_row['Close'] - last_row['SMA_150']) / last_row['SMA_150']) * 100
                
                if 0 < deviation_pct <= SMA_CROSSOVER_PCT:
                    # Near crossover - reward entry point
                    score += SCORE_SMA_CROSSOVER
                    added_points.append(SCORE_SMA_CROSSOVER)
                    summary_parts.append(f"✓ Price near SMA_{SMA_PERIOD} (deviation: {deviation_pct:.2f}%) - Crossover entry (+{SCORE_SMA_CROSSOVER} points)")
                elif deviation_pct > SMA_CROSSOVER_PCT:
                    # Well above - established trend
                    score += SCORE_SMA_ESTABLISHED
                    added_points.append(SCORE_SMA_ESTABLISHED)
                    summary_parts.append(f"✓ Price well above SMA_{SMA_PERIOD} (deviation: {deviation_pct:.2f}%) - Established trend (+{SCORE_SMA_ESTABLISHED} point)")
            else:
                summary_parts.append(f"✗ Price not above SMA_{SMA_PERIOD}")
        else:
            summary_parts.append(f"✗ SMA_{SMA_PERIOD} not available")
        
        # EMA 50 check
        if pd.notna(last_row['EMA_50']) and last_row['Close'] > last_row['EMA_50']:
            score += SCORE_EMA_ABOVE
            added_points.append(SCORE_EMA_ABOVE)
            summary_parts.append(f"✓ Price above EMA_{EMA_PERIOD} (+{SCORE_EMA_ABOVE} points)")
        else:
            summary_parts.append(f"✗ Price not above EMA_{EMA_PERIOD}")
        
        # RSI check - Optimal range (40-65)
        if pd.notna(last_row['RSI']):
            rsi_value = last_row['RSI']
            if RSI_OPTIMAL_LOW <= rsi_value <= RSI_OPTIMAL_HIGH:
                score += SCORE_RSI_OPTIMAL
                added_points.append(SCORE_RSI_OPTIMAL)
                summary_parts.append(f"✓ RSI in optimal range ({rsi_value:.2f}) (+{SCORE_RSI_OPTIMAL} points)")
            elif rsi_value > RSI_OVERBOUGHT or rsi_value < RSI_OVERSOLD:
                # Extreme RSI - apply penalty
                score += PENALTY_RSI_EXTREME
                penalties.append(PENALTY_RSI_EXTREME)
                if rsi_value > RSI_OVERBOUGHT:
                    summary_parts.append(f"✗ RSI overbought ({rsi_value:.2f} > {RSI_OVERBOUGHT}) ({PENALTY_RSI_EXTREME} points)")
                else:
                    summary_parts.append(f"✗ RSI oversold ({rsi_value:.2f} < {RSI_OVERSOLD}) ({PENALTY_RSI_EXTREME} points)")
            else:
                summary_parts.append(f"✗ RSI outside optimal range ({rsi_value:.2f})")
        else:
            summary_parts.append("✗ RSI not available")
        
        # Volume check
        if pd.notna(last_row['Volume']) and pd.notna(last_row['Volume_MA_20']):
            if last_row['Volume'] > last_row['Volume_MA_20']:
                score += SCORE_VOLUME_HIGH
                added_points.append(SCORE_VOLUME_HIGH)
                summary_parts.append(f"✓ Volume above {VOLUME_MA_PERIOD}-day average (+{SCORE_VOLUME_HIGH} point)")
            else:
                summary_parts.append(f"✗ Volume below {VOLUME_MA_PERIOD}-day average")
        else:
            summary_parts.append("✗ Volume data not available")
        
        # CCI check - Strong range (100-200)
        if pd.notna(last_row['CCI']):
            cci_value = last_row['CCI']
            if CCI_STRONG_LOW <= cci_value <= CCI_STRONG_HIGH:
                score += SCORE_CCI_STRONG
                added_points.append(SCORE_CCI_STRONG)
                summary_parts.append(f"✓ CCI in strong range ({cci_value:.2f}) (+{SCORE_CCI_STRONG} points)")
            else:
                summary_parts.append(f"✗ CCI outside strong range ({cci_value:.2f})")
        else:
            summary_parts.append("✗ CCI not available")
        
        # Bollinger Bands penalty - Overextended
        if pd.notna(last_row['BBands_Upper']) and last_row['Close'] > last_row['BBands_Upper']:
            score += PENALTY_BBANDS_OVEREXTENDED
            penalties.append(PENALTY_BBANDS_OVEREXTENDED)
            summary_parts.append(f"✗ Price above upper Bollinger Band - Overextended ({PENALTY_BBANDS_OVEREXTENDED} points)")
        
        # Ensure score is at least 0
        score = max(0.0, score)
        
        # Create detailed summary
        total_added = sum(added_points)
        total_penalties = sum(penalties)
        
        summary = f"Technical Score: {score:.2f}/{MAX_SCORE}\n"
        summary += f"Points Added: +{total_added:.1f} | Penalties: {total_penalties:.1f} | Final Score: {score:.2f}\n\n"
        summary += "\n".join(summary_parts)
        
        return score, summary

