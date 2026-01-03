import requests
import textwrap
import time
from typing import List, Dict, Optional
from config import WEBHOOK_URL

class DiscordNotifier:
    """
    Handles sending notifications to Discord via webhook using Embeds.
    Strictly follows the Classic Analysis Output Specification.
    """
    def __init__(self):
        self.webhook_url = WEBHOOK_URL
        if not self.webhook_url:
            raise ValueError("WEBHOOK_URL is not configured")

    def send_analysis_message(self, ticker: str, content: str, is_positive: bool) -> bool:
        """
        Sends the analysis as a formatted text message.
        """
        formatted_message = self._beautify_content(content, is_positive)

        try:
            response = requests.post(
                self.webhook_url,
                json={
                    "content": formatted_message
                },
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            time.sleep(2.0) # Slight delay
            return True
        except Exception as e:
            print(f"Error sending Discord analysis: {e}")
            return False

    def _beautify_content(self, content: str, is_positive: bool) -> str:
        """
        Parses raw analysis output and reformats it into high-end Discord Markdown.
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
        
        # Add Date/Context immediately after header in italic/quote
        # We can find the date line (usually line 1)
        
        # We skip line 0 (header)
        for i in range(1, len(lines)):
            line = lines[i]
            
            # Date/Earnings -> Italic quote
            if "📅" in line or "⏳" in line:
                formatted_lines.append(f"> *{line}*")
            
            # Entry/No Entry (Major Signal) -> Subheader style
            elif "🎯" in line or "⛔" in line:
                # formatted_lines.append("") # Removed empty line as per request
                formatted_lines.append(f"### {line}") # H3 for section
            
            # Status -> Bold with spacing
            elif "סטטוס נוכחי" in line:
                formatted_lines.append("")
                formatted_lines.append(f"**{line}**")
            
            # Instructions/Risk -> Bullet points or distinct lines
            elif "הוראה:" in line or "אזהרת סיכון" in line or "רמת סיכון" in line:
                 formatted_lines.append(f"- {line}")
            
            # Summary (usually last long line)
            elif i == len(lines) - 1:
                formatted_lines.append("")
                formatted_lines.append(f"📝 **סיכום:** {line}")
            
            # General text (Explanations)
            else:
                formatted_lines.append(line)
        
        body = "\n".join(formatted_lines)
        
        return f"{header}\n{body}"

    def send_message(self, content: str) -> bool:
        """
        Sends a plain text message to Discord (used for headers).
        """
        try:
            response = requests.post(
                self.webhook_url,
                json={"content": content},
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"Error sending Discord message: {e}")
            return False

    def send_batch_analysis(self, analyses: List[Dict]) -> bool:
        """
        Sends a batch of analysis results to Discord.
        """
        overall_success = True
        
        # 1. Send Main Header
        header = f"🚀 **AthenaInvest Analysis Update** 🚀\n📅 {time.strftime('%Y-%m-%d %H:%M:%S')}"
        if not self.send_message(header):
            overall_success = False

        # 2. Send each stock as a SEPARATE Message
        for item in analyses:
            ticker = item.get('ticker', 'Unknown')
            output = item.get('output', '')
            analysis_data = item.get('analysis', {})
            
            # Determine color
            is_positive = analysis_data.get('is_positive', False)
            # color = 0x00FF00 if is_positive else 0xFF0000 # Unused now
            
            if not self.send_analysis_message(ticker=ticker, content=output, is_positive=is_positive):
                overall_success = False
        
        return overall_success
