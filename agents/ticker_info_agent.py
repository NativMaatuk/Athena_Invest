import yfinance as yf
from typing import Dict, Optional
import yfinance as yf
from config import SECTOR_HEBREW_MAP
from deep_translator import GoogleTranslator

class TickerInfoAgent:
    """
    Agent responsible for fetching descriptive information about a ticker,
    specifically its sector and a brief business summary, with Hebrew translation.
    """
    
    def __init__(self):
        self.translator = GoogleTranslator(source='auto', target='iw')

    def get_ticker_info(self, ticker: str) -> Dict[str, str]:
        """
        Fetches sector, industry, and a one-sentence business summary for the given ticker,
        translated to Hebrew.

        Args:
            ticker: Stock ticker symbol (e.g., 'AAPL')

        Returns:
            Dictionary containing:
            - 'sector': The sector of the company in Hebrew.
            - 'industry': The industry of the company in Hebrew.
            - 'summary': A one-sentence summary of what the business does in Hebrew.
        """
        try:
            # Handle crypto tickers specifically if needed, or rely on yfinance
            # yfinance handles 'BTC-USD' correctly but sector might be different.
            
            t = yf.Ticker(ticker)
            info = t.info
            
            sector = info.get('sector', 'Unknown')
            industry = info.get('industry', 'Unknown')
            # For crypto, yfinance often puts 'Financial Services' or similar, or sometimes nothing.
            if 'quoteType' in info and info['quoteType'] == 'CRYPTOCURRENCY':
                 sector = 'Crypto'
                 industry = 'Crypto'
            
            summary_text = info.get('longBusinessSummary', '')
            
            # Market Cap
            market_cap_raw = info.get('marketCap')
            market_cap_str = self._format_market_cap(market_cap_raw)

            if not summary_text:
                 summary_text = "No summary available."

            # Use free translation service
            result = self._translate_info(ticker, sector, industry, summary_text)
            result['sector_en'] = sector
            result['industry_en'] = industry
            result['market_cap'] = market_cap_str
            return result

        except Exception as e:
            print(f"Error fetching info for {ticker}: {e}")
            return {
                'sector': 'לא ידוע',
                'industry': 'לא ידוע',
                'summary': 'לא ניתן היה לשלוף מידע.',
                'sector_en': 'Unknown',
                'industry_en': 'Unknown',
                'market_cap': 'N/A'
            }

    def _format_market_cap(self, market_cap: Optional[int]) -> str:
        """Formats market cap into readable string (T, B, M)."""
        if not market_cap:
            return "N/A"
        
        try:
            val = float(market_cap)
            if val >= 1_000_000_000_000:
                return f"${val / 1_000_000_000_000:.2f}T"
            elif val >= 1_000_000_000:
                return f"${val / 1_000_000_000:.2f}B"
            elif val >= 1_000_000:
                return f"${val / 1_000_000:.2f}M"
            else:
                return f"${val:,.0f}"
        except:
            return "N/A"

    def _translate_info(self, ticker: str, sector: str, industry: str, summary_text: str) -> Dict[str, str]:
        """
        Uses deep_translator (Google Translate) for free translation.
        """
        try:
            # 1. Translate Sector (use static map first, then translator)
            hebrew_sector = SECTOR_HEBREW_MAP.get(sector)
            if not hebrew_sector and sector != 'Unknown':
                 hebrew_sector = self.translator.translate(sector)
            if not hebrew_sector:
                 hebrew_sector = sector

            # 2. Translate Industry
            hebrew_industry = industry
            if industry != 'Unknown':
                try:
                    hebrew_industry = self.translator.translate(industry)
                except:
                    pass
            
            # 3. Translate Summary (First sentence only to keep it short and reliable)
            first_sentence = self._extract_first_sentence(summary_text)
            hebrew_summary = first_sentence
            if first_sentence:
                 try:
                     # Limit length for translation stability
                     hebrew_summary = self.translator.translate(first_sentence[:450]) 
                 except:
                     pass

            return {
                'sector': hebrew_sector,
                'industry': hebrew_industry,
                'summary': hebrew_summary
            }
        except Exception as e:
            print(f"⚠️ Free translation failed for {ticker}: {e}")
            return {
                'sector': SECTOR_HEBREW_MAP.get(sector, sector),
                'industry': industry,
                'summary': self._extract_first_sentence(summary_text)
            }

    def _extract_first_sentence(self, text: str) -> str:
        """
        Extracts the first sentence from the text.
        """
        if not text:
            return ""
        
        if ". " in text:
            return text.split(". ")[0] + "."
        return text