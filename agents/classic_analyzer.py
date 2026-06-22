"""
Classic Technical Analyzer
Handles classic technical analysis based on SMA_150 and ATR with Hebrew output.
"""
import yfinance as yf
import pandas as pd
import talib
from typing import Dict, Optional, Tuple
from datetime import datetime
from .technical_config import (
    HISTORICAL_PERIOD, 
    INTERVAL, 
    SMA_PERIOD,
    RSI_PERIOD,
    BBANDS_PERIOD,
    BBANDS_STD_DEV
)
from .classic_config import (
    ATR_PERIOD,
    RESISTANCE_LOOKBACK,
    EXTENSION_THRESHOLD,
    ATR_WARNING_THRESHOLD,
    ATR_SEVERE_THRESHOLD,
    SMA_SLOPE_LOOKBACK,
    SMA_SLOPE_FLAT_THRESHOLD,
    MIN_DATA_POINTS
)


class ClassicAnalyzer:
    """
    Classic technical analysis agent that analyzes stocks based on SMA_150 and ATR.
    """
    
    def analyze(self, ticker: str) -> Tuple[pd.DataFrame, Optional[int], Optional[datetime]]:
        """
        Fetch historical data and calculate SMA_150 and ATR.
        Also attempts to fetch the next earnings date.
        
        Args:
            ticker: Stock ticker symbol (e.g., 'AAPL')
            
        Returns:
            Tuple containing:
            - DataFrame with at least 30 rows containing SMA_150 and ATR
            - Optional[int]: Days until next earnings report (None if not available)
            - Optional[datetime]: Next earnings date (None if not available)
        """
        # Fetch historical data based on configuration
        stock = yf.Ticker(ticker)
        df = stock.history(period=HISTORICAL_PERIOD, interval=INTERVAL)
        
        # Calculate days until earnings
        days_until_earnings = None
        next_earnings_date = None
        try:
            # Try to get earnings dates
            earnings_dates = stock.earnings_dates
            if earnings_dates is not None and not earnings_dates.empty:
                # Handle timezone awareness mismatch
                dates = earnings_dates.index
                if dates.tz is not None:
                    dates = dates.tz_localize(None)
                
                now = datetime.now()
                # Filter for future dates
                future_dates = dates[dates > now]
                if not future_dates.empty:
                    next_date = future_dates.min()
                    next_earnings_date = next_date
                    # Calculate difference in days
                    days_until_earnings = (next_date - now).days
        except Exception:
            # Silently fail if earnings data is unavailable
            pass
        
        # Reset index to have Date as a column (if needed)
        if isinstance(df.index, pd.DatetimeIndex):
            df = df.reset_index()
        
        # Check if we have enough data points
        if len(df) < MIN_DATA_POINTS:
            raise ValueError(f"Insufficient data points: {len(df)} < {MIN_DATA_POINTS} required for SMA_{SMA_PERIOD}")
        
        # Calculate technical indicators using TA-Lib
        # Simple Moving Average 150
        df['SMA_150'] = talib.SMA(df['Close'].values, timeperiod=SMA_PERIOD)
        
        # Average True Range
        df['ATR'] = talib.ATR(df['High'].values, df['Low'].values, df['Close'].values, timeperiod=ATR_PERIOD)
        
        # Bollinger Bands
        df['BB_Upper'], df['BB_Middle'], df['BB_Lower'] = talib.BBANDS(
            df['Close'].values, 
            timeperiod=BBANDS_PERIOD,
            nbdevup=BBANDS_STD_DEV,
            nbdevdn=BBANDS_STD_DEV,
            matype=0
        )
        
        # RSI
        df['RSI'] = talib.RSI(df['Close'].values, timeperiod=RSI_PERIOD)
        
        # Return at least the last 30 rows (for resistance calculation) and earnings info
        return df, days_until_earnings, next_earnings_date
    
    def analyze_classic(self, df: pd.DataFrame, days_until_earnings: Optional[int] = None, next_earnings_date: Optional[datetime] = None) -> Dict:
        """
        Perform classic technical analysis based on SMA_150 and ATR.
        
        Args:
            df: DataFrame with SMA_150 and ATR columns
            days_until_earnings: Days until next earnings report (optional)
            next_earnings_date: Next earnings date (optional)
            
        Returns:
            Dictionary with analysis results
        """
        if len(df) == 0:
            raise ValueError("DataFrame is empty")
        
        # Get the last row (most recent data)
        last_row = df.iloc[-1]
        current_price = last_row['Close']
        previous_close = df.iloc[-2]['Close'] if len(df) >= 2 else None
        sma_150 = last_row['SMA_150']
        
        # Check if we have valid SMA_150
        if pd.isna(sma_150):
            raise ValueError("SMA_150 is not available - insufficient historical data")
        
        daily_change_pct = None
        if previous_close is not None and pd.notna(previous_close) and previous_close != 0:
            daily_change_pct = ((current_price - previous_close) / previous_close) * 100

        # Determine trend (main direction)
        is_positive = current_price > sma_150
        
        # Calculate SMA slope
        sma_slope = self._calculate_sma_slope(df)
        
        # Calculate distance from SMA (percentage)
        distance_from_sma = ((current_price - sma_150) / sma_150) * 100
        
        # Check for extension (stretched)
        is_extended = abs(distance_from_sma) > EXTENSION_THRESHOLD
        
        # Calculate entry zone (only for positive stocks)
        entry_zone = None
        resistance = None
        if is_positive:
            resistance = self._find_local_resistance(df)
            if resistance is not None:
                entry_zone = {
                    'support': sma_150,
                    'resistance': resistance
                }
        
        # Calculate ATR as percentage of price
        atr_value = last_row.get('ATR')
        atr_pct = None
        atr_warning = None
        if pd.notna(atr_value) and current_price > 0:
            atr_pct = (atr_value / current_price) * 100
            if atr_pct >= ATR_SEVERE_THRESHOLD:
                atr_warning = 'severe'
            elif atr_pct >= ATR_WARNING_THRESHOLD:
                atr_warning = 'warning'
        
        # Determine status
        status = self._determine_status(is_positive, sma_slope, is_extended, distance_from_sma)
        open_gaps = self._detect_open_gaps(df, current_price)
        nearest_open_gap = open_gaps[0] if open_gaps else None
        gap_summary = {
            'open_count': len(open_gaps),
            'up_count': sum(1 for gap in open_gaps if gap['direction'] == 'up'),
            'down_count': sum(1 for gap in open_gaps if gap['direction'] == 'down'),
            'fill_rule': 'close'
        }
        
        return {
            'ticker': None,  # Will be set by caller
            'is_positive': is_positive,
            'current_price': current_price,
            'previous_close': previous_close,
            'daily_change_pct': daily_change_pct,
            'sma_150': sma_150,
            'sma_slope': sma_slope,
            'distance_from_sma': distance_from_sma,
            'is_extended': is_extended,
            'entry_zone': entry_zone,
            'resistance': resistance,
            'atr_pct': atr_pct,
            'atr_warning': atr_warning,
            'status': status,
            'has_unfilled_gap': len(open_gaps) > 0,
            'open_gaps': open_gaps,
            'nearest_open_gap': nearest_open_gap,
            'gap_summary': gap_summary,
            'days_until_earnings': days_until_earnings,
            'next_earnings_date': next_earnings_date
        }
    
    def _calculate_sma_slope(self, df: pd.DataFrame) -> str:
        """
        Calculate SMA slope direction.
        
        Args:
            df: DataFrame with SMA_150 column
            
        Returns:
            'rising', 'flat', or 'declining'
        """
        if len(df) < SMA_SLOPE_LOOKBACK + 1:
            return 'unknown'
        
        current_sma = df.iloc[-1]['SMA_150']
        past_sma = df.iloc[-(SMA_SLOPE_LOOKBACK + 1)]['SMA_150']
        
        if pd.isna(current_sma) or pd.isna(past_sma):
            return 'unknown'
        
        # Calculate percentage change
        slope_pct = ((current_sma - past_sma) / past_sma) * 100
        
        if abs(slope_pct) < SMA_SLOPE_FLAT_THRESHOLD:
            return 'flat'
        elif slope_pct < 0:
            return 'declining'
        else:
            return 'rising'
    
    def _find_local_resistance(self, df: pd.DataFrame) -> Optional[float]:
        """
        Find local resistance (maximum High in last RESISTANCE_LOOKBACK days).
        
        Args:
            df: DataFrame with High column
            
        Returns:
            Maximum High value or None if not found
        """
        if len(df) < RESISTANCE_LOOKBACK:
            lookback = len(df)
        else:
            lookback = RESISTANCE_LOOKBACK
        
        recent_data = df.tail(lookback)
        
        # Filter out NaN values
        valid_highs = recent_data['High'].dropna()
        
        if len(valid_highs) == 0:
            return None
        
        return valid_highs.max()
    
    def _determine_status(self, is_positive: bool, sma_slope: str, is_extended: bool, distance_from_sma: float) -> str:
        """
        Determine current status based on analysis.
        
        Args:
            is_positive: Whether price is above SMA_150
            sma_slope: Slope of SMA ('rising', 'flat', 'declining')
            is_extended: Whether price is extended (>20% from SMA)
            distance_from_sma: Distance from SMA as percentage
            
        Returns:
            Status string: 'breakout', 'stretched', 'breakdown', 'stagnation', 'accumulation'
        """
        if not is_positive:
            return 'breakdown'
        
        # If price is extended above SMA (more than 20% away)
        if is_extended and distance_from_sma > EXTENSION_THRESHOLD:
            return 'stretched'
        
        # If SMA slope is declining or flat, it's stagnation
        if sma_slope == 'declining' or sma_slope == 'flat':
            return 'stagnation'
        
        # If positive, rising slope, and not extended
        # Check if close to SMA (within 5%)
        if abs(distance_from_sma) < 5:  # Close to SMA
            return 'accumulation'
        else:
            return 'breakout'

    def _detect_open_gaps(self, df: pd.DataFrame, current_price: float, lookback: int = 120) -> list[dict]:
        """Detect open/partial price gaps with fill rule based on Close only."""
        required_columns = {'High', 'Low', 'Close'}
        if len(df) < 2 or not required_columns.issubset(df.columns):
            return []

        date_column = 'Date' if 'Date' in df.columns else ('Datetime' if 'Datetime' in df.columns else None)
        columns_to_use = ['High', 'Low', 'Close']
        if date_column:
            columns_to_use.append(date_column)

        data = df[columns_to_use].tail(lookback).reset_index(drop=True)
        gaps: list[dict] = []

        for idx in range(1, len(data)):
            prev_high = data.loc[idx - 1, 'High']
            prev_low = data.loc[idx - 1, 'Low']
            curr_high = data.loc[idx, 'High']
            curr_low = data.loc[idx, 'Low']

            if pd.isna(prev_high) or pd.isna(prev_low) or pd.isna(curr_high) or pd.isna(curr_low):
                continue

            prev_high = float(prev_high)
            prev_low = float(prev_low)
            curr_high = float(curr_high)
            curr_low = float(curr_low)

            direction = None
            zone_low = None
            zone_high = None
            gap_pct_base = None
            if curr_low > prev_high:
                direction = 'up'
                zone_low = prev_high
                zone_high = curr_low
                gap_pct_base = prev_high
            elif curr_high < prev_low:
                direction = 'down'
                zone_low = curr_high
                zone_high = prev_low
                gap_pct_base = prev_low

            if direction is None or zone_low is None or zone_high is None:
                continue

            gap_size_abs = zone_high - zone_low
            gap_size_pct = (gap_size_abs / gap_pct_base * 100) if gap_pct_base else 0.0

            future_close = data.loc[idx + 1:, 'Close'].dropna()
            future_low = data.loc[idx + 1:, 'Low'].dropna()
            future_high = data.loc[idx + 1:, 'High'].dropna()
            if direction == 'up':
                close_partial = bool((future_close <= zone_high).any()) if len(future_close) else False
                close_closed = bool((future_close <= zone_low).any()) if len(future_close) else False
                wick_partial = bool((future_low <= zone_high).any()) if len(future_low) else False
                wick_closed = bool((future_low <= zone_low).any()) if len(future_low) else False
            else:
                close_partial = bool((future_close >= zone_low).any()) if len(future_close) else False
                close_closed = bool((future_close >= zone_high).any()) if len(future_close) else False
                wick_partial = bool((future_high >= zone_low).any()) if len(future_high) else False
                wick_closed = bool((future_high >= zone_high).any()) if len(future_high) else False

            is_partial = close_partial or wick_partial
            is_closed = close_closed or wick_closed

            if is_closed:
                fill_status = 'closed'
            elif is_partial:
                fill_status = 'partial'
            else:
                fill_status = 'open'

            if fill_status == 'closed':
                continue

            zone_mid = (zone_low + zone_high) / 2
            distance_from_current_pct = (
                abs((current_price - zone_mid) / zone_mid) * 100 if zone_mid else None
            )
            gap_date = data.loc[idx, date_column] if date_column else None

            gaps.append({
                'direction': direction,
                'gap_date': gap_date,
                'zone_low': zone_low,
                'zone_high': zone_high,
                'gap_size_abs': gap_size_abs,
                'gap_size_pct': gap_size_pct,
                'fill_status': fill_status,
                'fill_rule': 'close',
                'distance_from_current_pct': distance_from_current_pct
            })

        gaps.sort(
            key=lambda gap: (
                gap['distance_from_current_pct']
                if gap['distance_from_current_pct'] is not None
                else float('inf')
            )
        )
        return gaps
    
    def format_output(self, ticker: str, analysis: Dict) -> str:
        """
        Format analysis output in Hebrew.
        
        Args:
            ticker: Stock ticker symbol
            analysis: Analysis dictionary from analyze_classic()
            
        Returns:
            Formatted Hebrew output string
        """
        lines = []
        
        # Line 1: Ticker and Price (Bold)
        # Format: TICKER_NAME - CURRENT_PRICE $
        lines.append(f"**{ticker}** - {analysis['current_price']:,.2f}$")
        
        # Line 2: Date
        date_str = self._get_hebrew_date()
        lines.append(f"\u200f📅 {date_str}")
        
        # Line 3: Earnings (if available)
        days_until = analysis.get('days_until_earnings')
        next_date = analysis.get('next_earnings_date')
        
        if days_until is not None:
            date_info = ""
            if next_date and isinstance(next_date, datetime):
                date_info = f" ({next_date.strftime('%d.%m.%Y')})"
            
            lines.append(f"\u200f⏳ ימים לדווח תוצאות: {days_until}{date_info}")
        
        # Entry zone or no entry message
        if analysis['is_positive']:
            distance = analysis['distance_from_sma']
            if analysis['entry_zone']:
                support = analysis['entry_zone']['support']
                resistance = analysis['entry_zone']['resistance']
                current_price = analysis['current_price']
                
                if current_price > resistance:
                    lines.append(f"\u200f**🎯 אזור כניסה טכני: נפרצה התנגדות ב-{resistance:,.2f}$. רמה זו משמשת כעת כתמיכה חדשה (Retest).**")
                else:
                    lines.append(f"\u200f**🎯 אזור כניסה טכני: {support:,.2f}$ - {resistance:,.2f}$ (הטווח שבין הממוצע לפריצה, ב-{distance:.1f}% מעל הממוצע)**")
            else:
                lines.append(f"\u200f**🎯 אזור כניסה טכני: {analysis['sma_150']:,.2f}$ - לא זוהתה התנגדות (הטווח שבין הממוצע לשיא, ב-{distance:.1f}% מעל הממוצע)**")
        else:
            distance = abs(analysis['distance_from_sma'])
            lines.append(f"\u200f**⛔ אין כניסה: המניה נסחרת מתחת לממוצע 150 ({analysis['sma_150']:,.2f}$, ב-{distance:.1f}% מתחת לקו).**")
        
        # Status with emoji
        status_emoji = {
            'breakout': '🚀',
            'stretched': '🚀',
            'breakdown': '💥',
            'stagnation': '⚠️',
            'accumulation': '📊'
        }
        status_text = {
            'breakout': 'פריצה',
            'stretched': 'מתוחה',
            'breakdown': 'שבירה',
            'stagnation': 'דשדוש',
            'accumulation': 'איסוף'
        }
        
        status = analysis['status']
        emoji = status_emoji.get(status, '📈')
        text = status_text.get(status, status)
        lines.append(f"\u200f{emoji} סטטוס נוכחי: {text}")
        
        # Explanation sentence
        explanation = self._generate_explanation(analysis)
        lines.append(f"\u200f{explanation}")
        
        # ATR warning / info - always show
        atr_pct = analysis.get('atr_pct')
        if atr_pct is not None:
            if analysis['atr_warning'] == 'severe':
                lines.append(f"\u200f⚠️ אזהרת סיכון: ATR גבוה מאוד ({atr_pct:.1f}%) - רכבת הרים, קזינו.")
            elif analysis['atr_warning'] == 'warning':
                lines.append(f"\u200f⚠️ אזהרת סיכון: ATR גבוה ({atr_pct:.1f}%) - תנודתיות מוגברת, להדק סטופים.")
            else:
                lines.append(f"\u200f✅ רמת סיכון: ATR תקין ({atr_pct:.1f}%) - תנודתיות רגילה.")

        # Instruction
        instruction = self._generate_instruction(analysis)
        lines.append(f"\u200f{instruction}")
        
        # Summary sentence
        summary = self._generate_summary(analysis)
        lines.append(f"\u200f{summary}")
        
        return "\n".join(lines)
    
    def _get_hebrew_date(self) -> str:
        """Get current date formatted in Hebrew."""
        now = datetime.now()
        day_name_en = now.strftime("%A")
        
        days_map = {
            'Sunday': 'יום ראשון',
            'Monday': 'יום שני',
            'Tuesday': 'יום שלישי',
            'Wednesday': 'יום רביעי',
            'Thursday': 'יום חמישי',
            'Friday': 'יום שישי',
            'Saturday': 'יום שבת'
        }
        
        day_he = days_map.get(day_name_en, day_name_en)
        date_str = now.strftime("%d.%m.%Y")
        
        return f"{date_str} {day_he}"

    def _generate_explanation(self, analysis: Dict) -> str:
        """Generate explanation sentence in Hebrew."""
        distance = analysis['distance_from_sma']
        slope = analysis['sma_slope']
        
        slope_text = {
            'rising': 'בשיפוע עולה',
            'flat': 'בשיפוע שטוח',
            'declining': 'בשיפוע יורד',
            'unknown': 'בשיפוע לא ידוע'
        }
        slope_desc = slope_text.get(slope, '')
        
        if analysis['is_positive']:
            if abs(distance) > EXTENSION_THRESHOLD:
                return f"המחיר נמצא מעל הממוצע 150, הממוצע {slope_desc}, אך המחיר רחוק {distance:.1f}% מהקו - טיסה לירח, סכנת גבהים."
            else:
                base_expl = f"המחיר נמצא מעל הממוצע 150, הממוצע {slope_desc}, המחיר במרחק {distance:.1f}% מהקו."
                if abs(distance) < 2:
                    return f"{base_expl} הממוצע משמש כרצפת ברזל."
                return base_expl
        else:
            return f"המחיר נמצא מתחת לממוצע 150, הממוצע {slope_desc}, המחיר במרחק {abs(distance):.1f}% מתחת לקו - סכין נופלת."
    
    def _generate_instruction(self, analysis: Dict) -> str:
        """Generate instruction in Hebrew."""
        status = analysis['status']
        is_extended = analysis['is_extended']
        
        if status == 'breakdown':
            return "📉 הוראה: להתרחק"
        elif status == 'stretched':
            return "📈 הוראה: לא לרדוף"
        elif status == 'stagnation':
            return "📈 הוראה: להמתין לתיקון"
        elif status == 'accumulation':
            return "📈 הוראה: איסוף"
        elif status == 'breakout':
            if is_extended:
                return "📈 הוראה: לא לרדוף"
            else:
                return "📈 הוראה: איסוף"
        else:
            return "📈 הוראה: להמתין"
    
    def _generate_summary(self, analysis: Dict) -> str:
        """Generate summary sentence in Hebrew."""
        status = analysis['status']
        
        if status == 'breakdown':
            return "המניה מתחת למים (תקרת בטון), אין כניסה עד חזרה מעל הממוצע עם שיפוע חיובי."
        elif status == 'stretched':
            return "המניה מתוחה מדי מהממוצע (טיסה לירח), מומלץ להמתין לתיקון או נשיקה לממוצע לפני כניסה."
        elif status == 'stagnation':
            return "המניה מעל הממוצע אך המגמה חלשה (חשד/זהירות), מומלץ להמתין לשיפוע חיובי או נשיקה לממוצע."
        elif status == 'accumulation':
            return "המניה נמצאת באזור איסוף מעל הממוצע (רצפת ברזל), שיפוע חיובי - אפשרות לכניסה באזור התמיכה."
        elif status == 'breakout':
            return "המניה בפריצה מעל הממוצע עם שיפוע חיובי - מגמה עולה, להדק סטופים בממוצע."
        else:
            return "יש להמתין לזיהוי מגמה ברורה."

