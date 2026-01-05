import requests
import time
from typing import List, Dict, Optional
from config import WEBHOOK_URL

class BaseDiscordNotifier:
    """
    Base class for handling raw Discord webhook interactions.
    """
    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url or WEBHOOK_URL
        if not self.webhook_url:
             # It is possible to initialize without a URL if it will be provided per message,
             # but for now we'll warn or allow it, but send_message will fail if not set.
             pass

    def send_raw_message(self, content: str, webhook_url: Optional[str] = None) -> bool:
        """
        Sends a plain text message to Discord.
        """
        target_url = webhook_url or self.webhook_url
        if not target_url:
            print("Error: No webhook URL provided.")
            return False

        try:
            response = requests.post(
                target_url,
                json={"content": content},
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"Error sending Discord message: {e}")
            return False

class ClassicAnalysisNotifier(BaseDiscordNotifier):
    """
    Specialized notifier for Classic Technical Analysis.
    Handles formatting and including sector/business info.
    """
    
    def send_analysis_message(self, ticker: str, content: str, is_positive: bool, 
                              sector: str = None, industry: str = None, summary: str = None, 
                              market_cap: str = None, webhook_url: Optional[str] = None) -> bool:
        """
        Sends the analysis as a formatted text message.
        """
        formatted_message = self._beautify_content(content, is_positive, sector, industry, summary, market_cap)

        target_url = webhook_url or self.webhook_url
        if not target_url:
             print(f"Error: No webhook URL configured for {ticker} (Sector: {sector})")
             return False

        try:
            response = requests.post(
                target_url,
                json={
                    "content": formatted_message
                },
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            time.sleep(2.0) # Slight delay
            return True
        except Exception as e:
            print(f"Error sending Discord analysis for {ticker}: {e}")
            return False

    def _beautify_content(self, content: str, is_positive: bool, sector: str = None, industry: str = None, summary: str = None, market_cap: str = None) -> str:
        """
        Parses raw analysis output and reformats it into high-end Discord Markdown.
        Adds Sector, Industry and Summary info if available.
        """
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        if not lines:
            return content

        # 1. Header with visual status indicator
        # Raw: "**TICKER** - 123.45$" -> Target: "# 🟢 TICKER - 123.45$"
        status_icon = "🟢" if is_positive else "🔴"
        header_line = lines[0].replace('**', '')
        header = f"# {status_icon} {header_line}"
        
        # 2. Body processing
        formatted_lines = []
        
        # Find and add Date/Earnings line FIRST (User request)
        date_line_idx = -1
        for i in range(1, len(lines)):
            if "📅" in lines[i] or "⏳" in lines[i]:
                formatted_lines.append(f"> *{lines[i]}*")
                date_line_idx = i
                break

        # Add Sector, Industry, Market Cap and Summary immediately after header (or date)
        if sector or industry or summary or market_cap:
            if market_cap:
                formatted_lines.append(f"> 💰 **שווי שוק:** {market_cap}")
            if sector:
                formatted_lines.append(f"> 🏢 **סקטור:** {sector}")
            if industry:
                formatted_lines.append(f"> 🏭 **תעשייה:** {industry}")
            if summary:
                formatted_lines.append(f"> ℹ️ **עיסוק:** {summary}")
            
            # Spacing removed per user request
        
        # We skip line 0 (header)
        for i in range(1, len(lines)):
            if i == date_line_idx:
                continue

            line = lines[i]
            
            # Date/Earnings -> Italic quote
            if "📅" in line or "⏳" in line:
                formatted_lines.append(f"> *{line}*")
            
            # Entry/No Entry (Major Signal) -> Subheader style
            elif "🎯" in line or "⛔" in line:
                formatted_lines.append(f"### {line}") # H3 for section
            
            # Status -> Bold with spacing
            elif "סטטוס נוכחי" in line:
                # formatted_lines.append("") # Spacing removed
                formatted_lines.append(f"**{line}**")
            
            # Instructions/Risk -> Bullet points or distinct lines
            elif "הוראה:" in line or "אזהרת סיכון" in line or "רמת סיכון" in line:
                 formatted_lines.append(f"- {line}")
            
            # Summary (usually last long line)
            elif i == len(lines) - 1:
                # formatted_lines.append("") # Spacing removed
                formatted_lines.append(f"📝 **סיכום:** {line}")
            
            # General text (Explanations)
            else:
                formatted_lines.append(line)
        
        # Add separator line at the end - REMOVED per user request
        # formatted_lines.append("")
        # formatted_lines.append("⎯" * 35)

        body = "\n".join(formatted_lines)
        
        return f"{header}\n{body}"

    def send_batch_analysis(self, analyses: List[Dict]) -> bool:
        """
        Sends a batch of analysis results to Discord.
        Note: This method is less flexible with the new per-sector webhook architecture
        unless we group by webhook, but kept for compatibility.
        """
        overall_success = True
        
        # 1. Send Main Header - DISABLED (User request: no point sending to general webhook if division exists)
        # header = f"🚀 **AthenaInvest Analysis Update** 🚀\n📅 {time.strftime('%Y-%m-%d %H:%M:%S')}"
        # if not self.send_raw_message(header):
        #    overall_success = False

        # 2. Send each stock as a SEPARATE Message
        for item in analyses:
            ticker = item.get('ticker', 'Unknown')
            output = item.get('output', '')
            analysis_data = item.get('analysis', {})
            sector = item.get('sector')
            industry = item.get('industry')
            summary = item.get('summary')
            market_cap = item.get('market_cap')
            webhook_url = item.get('webhook_url') # Allow overriding per item
            
            # Determine color/positive
            is_positive = analysis_data.get('is_positive', False)
            
            if not self.send_analysis_message(ticker=ticker, content=output, is_positive=is_positive,
                                              sector=sector, industry=industry, summary=summary, market_cap=market_cap, webhook_url=webhook_url):
                overall_success = False
        
        return overall_success

# For backward compatibility if needed, though we should update main.py
DiscordNotifier = ClassicAnalysisNotifier
