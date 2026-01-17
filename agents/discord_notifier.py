import requests
import time
import math
import io
import json
import pandas as pd
from typing import List, Dict, Optional
from config import WEBHOOK_URL
from datetime import datetime

# print("DEBUG: Loading agents/discord_notifier.py...")

# Lazy import matplotlib to avoid hard dependency at module level if not installed
try:
    import matplotlib
    matplotlib.use('Agg') # Use non-interactive backend
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    import numpy as np
    from matplotlib.patches import Wedge
    try:
        from bidi.algorithm import get_display
        import arabic_reshaper
        HAS_BIDI = True
    except ImportError:
        HAS_BIDI = False
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

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
    
    def _bidi_safe(self, text: str) -> str:
        """
        Wraps text in a Quote Block (> ) to prevent truncation and allow formatting.
        Adds > to the start of every line.
        """
        # We KEEP the formatting (bold, etc.) as Quote Blocks support it.
        # Just ensure every line starts with '> '
        lines = text.split('\n')
        quoted_lines = [f"> {line}" for line in lines]
        return "\n".join(quoted_lines)

    def _create_analysis_embed(self, ticker: str, content: str, is_positive: bool,
                             sector: str = None, industry: str = None, summary: str = None, 
                             market_cap: str = None, earnings_info: str = None) -> Dict:
        """
        Creates a structured Discord Embed object from the analysis content.
        Parses the text content into sections for better readability.
        """
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        if not lines:
            return {}

        # 1. Header & Title
        # Raw: "**TICKER** - 123.45$" -> Target Title: "🟢 TICKER - 123.45$"
        status_icon = "🟢" if is_positive else "🔴"
        color = 0x089981 if is_positive else 0xf23645
        
        header_line = lines[0].replace('**', '')
        title = f"{status_icon} {header_line}"
        
        # 2. Parse Content Sections
        sections = {
            "events": [],
            "signal": None,
            "status": [],
            "risk": None,
            "strategy": [],
            "summary_text": None
        }
        
        current_section = None
        
        # Skip header line
        for i in range(1, len(lines)):
            line = lines[i]
            
            # Events (Date/Earnings)
            if "📅" in line or "⏳" in line:
                sections["events"].append(line)
                continue
                
            # Signal (Entry/No Entry)
            if "🎯" in line or "⛔" in line:
                sections["signal"] = line.replace("**", "")
                current_section = None
                continue
                
            # Status
            if "סטטוס נוכחי" in line:
                current_section = "status"
                sections["status"].append(line.replace("**", ""))
                continue
                
            # Risk
            if "רמת סיכון" in line or "אזהרת סיכון" in line:
                sections["risk"] = line
                current_section = None
                continue
                
            # Strategy (Instructions)
            if "הוראה:" in line:
                current_section = "strategy"
                sections["strategy"].append(line)
                continue
            
            # Summary (Last line is treated as summary if not matched elsewhere)
            if i == len(lines) - 1:
                sections["summary_text"] = line
                current_section = None
                continue

            # Append description lines to current section
            if current_section == "status":
                sections["status"].append(line)
            elif current_section == "strategy":
                sections["strategy"].append(line)
        
        # 3. Build Fields
        fields = []
        
        # Market Data Fields (Inline - Label in Name, Value in Value as header trick or just Name)
        # User requested: "שווי שוק: $1.84T" in one line.
        # We use the Name for the content and a zero-width space for the value to ensure it renders as a "header" field.
        if market_cap:
            fields.append({"name": f"💰 שווי שוק: {market_cap}", "value": "\u200b", "inline": True})
        if sector:
            fields.append({"name": f"🏢 סקטור: {sector}", "value": "\u200b", "inline": True})
        if industry:
            fields.append({"name": f"🏭 תעשייה: {industry}", "value": "\u200b", "inline": True})
            
        # Events (Earnings only, date is in footer)
        # Prioritize explicit earnings_info if provided
        if earnings_info:
             fields.append({
                "name": "📅 אירועים",
                "value": self._bidi_safe(earnings_info) if not earnings_info.startswith("\u200f") else self._bidi_safe(earnings_info),
                "inline": False
            })
        else:
            # Fallback to parsing
            earnings_lines = [line for line in sections["events"] if "⏳" in line]
            if earnings_lines:
                fields.append({
                    "name": "📅 אירועים",
                    "value": "\n".join(earnings_lines),
                    "inline": False
                })
            
        # Technical Signal
        if sections["signal"]:
            fields.append({
                "name": "🎯 איתות טכני",
                "value": self._bidi_safe(sections["signal"]),
                "inline": False
            })
            
        # Status
        if sections["status"]:
            # First line is the header (e.g. "Status: Breakout"), rest is description
            status_val = "\n".join([self._bidi_safe(line) for line in sections["status"]])
            fields.append({
                "name": "🚀 סטטוס",
                "value": status_val,
                "inline": False
            })

        # Risk
        if sections["risk"]:
            fields.append({
                "name": "⚖️ סיכון",
                "value": self._bidi_safe(sections["risk"]),
                "inline": False
            })
            
        # Strategy
        if sections["strategy"]:
            strategy_val = "\n".join([self._bidi_safe(line) for line in sections["strategy"]])
            fields.append({
                "name": "💡 הוראה",
                "value": strategy_val,
                "inline": False
            })

        # Technical Summary (from text analysis)
        if sections["summary_text"]:
            clean_tech_summary = sections["summary_text"].replace("📝 **סיכום:**", "").strip()
            # If it starts with "סיכום:", remove it too
            if clean_tech_summary.startswith("סיכום:"):
                 clean_tech_summary = clean_tech_summary.replace("סיכום:", "", 1).strip()
            
            fields.append({
                "name": "📝 סיכום טכני",
                "value": self._bidi_safe(clean_tech_summary),
                "inline": False
            })

        # Company Profile (from API)
        if summary:
            if len(summary) > 1024:
                summary = summary[:1021] + "..."
            
            fields.append({
                "name": "ℹ️ פרופיל חברה",
                "value": self._bidi_safe(summary),
                "inline": False
            })

        # 4. Construct Embed
        embed = {
            "title": title,
            "color": color,
            "fields": fields,
            "timestamp": datetime.now().astimezone().isoformat(),
            "footer": {
                "text": "Athena Invest Analysis"
            }
        }
        
        return embed

    def _generate_chart_image(self, df: pd.DataFrame, ticker: str, is_positive: bool) -> Optional[io.BytesIO]:
        """
        Generates a professional price chart with SMA 150, BBands, Volume and RSI.
        """
        if not HAS_MATPLOTLIB or df is None or df.empty:
            return None
            
        try:
            # Setup colors
            discord_dark = '#2f3136'
            text_color = '#dcddde'
            grid_color = '#40444b'
            
            # Colors per user request
            col_green = '#089981'
            col_red = '#f23645'
            
            price_color = col_green if is_positive else col_red
            sma_color = '#faa61a' # Yellow
            bb_color = '#7289da' # Discord Blurple for bands
            
            # Create figure with 2 subplots (Price+Vol, RSI)
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), dpi=100, sharex=True, 
                                         gridspec_kw={'height_ratios': [3, 1], 'hspace': 0.15}) 
            fig.patch.set_facecolor(discord_dark)
            
            # --- Panel 1: Price, SMA, BBands, Volume ---
            ax1.set_facecolor(discord_dark)
            
            # Move Y-Axis to Right (Standard for Trading Charts)
            ax1.yaxis.tick_right()
            ax1.yaxis.set_label_position("right")
            ax1.tick_params(axis='y', which='both', labelleft=False, labelright=True, left=False, right=True)
            
            # Prepare dates and data
            # Calculate Previous Close before slicing to have it for the first visible candle
            df = df.copy()
            df['Prev_Close'] = df['Close'].shift(1)
            
            df = df.tail(126) # Last ~6 months
            # Create integer index for x-axis to avoid gaps
            x_indices = np.arange(len(df))
            dates = df.index
            
            # Handle index if not datetime
            if not isinstance(df.index, pd.DatetimeIndex):
                if 'Date' in df.columns:
                    dates = pd.to_datetime(df['Date'])
                else:
                    try:
                        dates = pd.to_datetime(df.index)
                    except:
                        pass 

            # 1. Bollinger Bands
            if 'BB_Upper' in df.columns and 'BB_Lower' in df.columns:
                # Upper Band (Red)
                ax1.plot(x_indices, df['BB_Upper'], color=col_red, linewidth=0.8, alpha=0.7, label='_nolegend_')
                # Lower Band (Green)
                ax1.plot(x_indices, df['BB_Lower'], color=col_green, linewidth=0.8, alpha=0.7, label='_nolegend_')
                
                # Middle Band (Moving Average) - usually SMA 20
                if 'BB_Middle' in df.columns:
                    ax1.plot(x_indices, df['BB_Middle'], color='#b9bbbe', linewidth=0.8, linestyle='-.', alpha=0.6, label='_nolegend_')

                ax1.fill_between(x_indices, df['BB_Upper'], df['BB_Lower'], color=bb_color, alpha=0.05)

            # 2. Candles
            # Create boolean mask for up/down days BASED ON PREVIOUS CLOSE
            # Use Prev_Close (fallback to Open for first item if NaN)
            prev_close_filled = df['Prev_Close'].fillna(df['Open'])
            
            up = df['Close'] >= prev_close_filled
            down = df['Close'] < prev_close_filled
            
            col_up = col_green
            col_down = col_red
            
            # Wicks
            width = 0.6
            width2 = 0.08
            ax1.vlines(x_indices[up], df['Low'][up], df['High'][up], color=col_up, linewidth=1, zorder=3)
            ax1.vlines(x_indices[down], df['Low'][down], df['High'][down], color=col_down, linewidth=1, zorder=3)
            
            # Bodies
            ax1.bar(x_indices[up], df['Close'][up] - df['Open'][up], width, bottom=df['Open'][up], color=col_up, edgecolor=col_up, linewidth=0.5, zorder=3)
            ax1.bar(x_indices[down], df['Open'][down] - df['Close'][down], width, bottom=df['Close'][down], color=col_down, edgecolor=col_down, linewidth=0.5, zorder=3)
            
            # 3. SMA 150
            if 'SMA_150' in df.columns:
                ax1.plot(x_indices, df['SMA_150'], color=sma_color, label='SMA 150', linewidth=1.5, linestyle='--', zorder=4)

            # 4. Volume (Twin Axis)
            ax1v = ax1.twinx()
            ax1v.bar(x_indices[up], df['Volume'][up], color=col_up, alpha=0.5, width=width)
            ax1v.bar(x_indices[down], df['Volume'][down], color=col_down, alpha=0.5, width=width)
            ax1v.set_ylim(0, df['Volume'].max() * 4) # Push volume to bottom 1/4
            ax1v.axis('off') # Hide volume axis info

            # Formatting Ax1
            ax1.grid(True, color=grid_color, linestyle=':', alpha=0.4) # More subtle grid
            ax1.tick_params(axis='y', colors=text_color, labelsize=9)
            ax1.set_ylabel('') # Remove label to save space, numbers are enough
            for spine in ax1.spines.values():
                spine.set_color(text_color)
                spine.set_alpha(0.3)
            ax1.spines['top'].set_visible(False)
            ax1.spines['left'].set_visible(False) # Hide left spine since ticks are on right
            
            # Legend Ax1
            import matplotlib.lines as mlines
            line_sma = mlines.Line2D([], [], color=sma_color, label='SMA 150', linewidth=1.5, linestyle='--')
            patch_bb = mlines.Line2D([], [], color=bb_color, label='Bollinger Bands (20, 2)', linewidth=1, alpha=0.5)
            line_ma20 = mlines.Line2D([], [], color='#b9bbbe', label='SMA 20 (Basis)', linewidth=0.8, linestyle='-.')
            
            ax1.legend(handles=[line_sma, patch_bb, line_ma20], facecolor=discord_dark, labelcolor=text_color, loc='upper left', frameon=False, fontsize=9)
            
            # Ensure Y-axis is on the right
            ax1.yaxis.tick_right()
            ax1.yaxis.set_label_position("right")
            ax1.tick_params(axis='y', which='both', labelleft=False, labelright=True)
            
            # Add OHLC Info Box - Moved to top title area to avoid legend overlap
            last_candle = df.iloc[-1]
            ohlc_text = (f"O: {last_candle['Open']:.2f}  H: {last_candle['High']:.2f}  "
                         f"L: {last_candle['Low']:.2f}  C: {last_candle['Close']:.2f}  "
                         f"Vol: {int(last_candle['Volume']):,}")
            
            # Add text annotation above the plot area
            ax1.text(0.0, 1.02, ohlc_text, transform=ax1.transAxes, color=text_color, fontsize=9, alpha=0.8)
            
            # Title
            ax1.set_title(f"{ticker} - Technical Analysis (6 Months)", color='white', fontsize=16, fontweight='bold', pad=25) # Increased pad for OHLC text

            # Current Price Annotation (Badge Style)
            last_price = df['Close'].iloc[-1]
            last_idx = x_indices[-1]
            
            # Use distinct color for current price
            current_price_color = '#00e5ff' # Cyan
            
            # Add line pointing to price
            ax1.axhline(y=last_price, color=current_price_color, linestyle='--', linewidth=0.8, alpha=0.5)
            
            # Add text with background box
            bbox_props = dict(boxstyle="larrow,pad=0.3", fc=current_price_color, ec="none", alpha=0.8)
            ax1.annotate(f'{last_price:.2f}', xy=(1, last_price), xycoords=('axes fraction', 'data'),
                        xytext=(5, 0), textcoords='offset points',
                        color='black', fontweight='bold', fontsize=10, va='center', ha='left',
                        bbox=bbox_props)

            # Bollinger Bands Annotations (Upper/Lower)
            if 'BB_Upper' in df.columns and 'BB_Lower' in df.columns:
                # Upper Band Annotation (Red)
                last_bb_upper = df['BB_Upper'].iloc[-1]
                bbox_props_upper = dict(boxstyle="larrow,pad=0.3", fc=col_red, ec="none", alpha=0.8)
                ax1.annotate(f'{last_bb_upper:.2f}', xy=(1, last_bb_upper), xycoords=('axes fraction', 'data'),
                            xytext=(5, 0), textcoords='offset points',
                            color='black', fontweight='bold', fontsize=8, va='center', ha='left',
                            bbox=bbox_props_upper)
                
                # Lower Band Annotation (Green)
                last_bb_lower = df['BB_Lower'].iloc[-1]
                bbox_props_lower = dict(boxstyle="larrow,pad=0.3", fc=col_green, ec="none", alpha=0.8)
                ax1.annotate(f'{last_bb_lower:.2f}', xy=(1, last_bb_lower), xycoords=('axes fraction', 'data'),
                            xytext=(5, 0), textcoords='offset points',
                            color='black', fontweight='bold', fontsize=8, va='center', ha='left',
                            bbox=bbox_props_lower)
            
            # SMA 150 Annotation (Orange)
            if 'SMA_150' in df.columns:
                last_sma_150 = df['SMA_150'].iloc[-1]
                if not pd.isna(last_sma_150):
                    bbox_props_sma150 = dict(boxstyle="larrow,pad=0.3", fc=sma_color, ec="none", alpha=0.8)
                    ax1.annotate(f'{last_sma_150:.2f}', xy=(1, last_sma_150), xycoords=('axes fraction', 'data'),
                                xytext=(5, 0), textcoords='offset points',
                                color='black', fontweight='bold', fontsize=8, va='center', ha='left',
                                bbox=bbox_props_sma150)

            # --- Panel 2: RSI ---
            ax2.set_facecolor(discord_dark)
            
            # Move Y-Axis to Right
            ax2.yaxis.tick_right()
            ax2.yaxis.set_label_position("right")
            
            if 'RSI' in df.columns:
                # Plot RSI Line
                ax2.plot(x_indices, df['RSI'], color='#b9bbbe', linewidth=1.5, label='RSI')
                
                # Plot RSI Moving Average (14 period)
                rsi_sma = df['RSI'].rolling(window=14).mean()
                ax2.plot(x_indices, rsi_sma, color='#f1c40f', linewidth=1.2, label='RSI SMA 14') # Yellow
                
                # Overbought/Oversold Lines
                ax2.axhline(70, color=col_red, linestyle='--', linewidth=1, alpha=0.5)
                ax2.axhline(30, color=col_green, linestyle='--', linewidth=1, alpha=0.5)
                
                # Fill zones
                ax2.fill_between(x_indices, df['RSI'], 70, where=(df['RSI'] >= 70), color=col_red, alpha=0.3)
                ax2.fill_between(x_indices, df['RSI'], 30, where=(df['RSI'] <= 30), color=col_green, alpha=0.3)
                ax2.set_ylim(0, 100)
                # ax2.set_ylabel('RSI', color=text_color) # Removed label
                
                # RSI Legend
                # Placed above the plot to avoid overlapping with the line
                ax2.legend(facecolor=discord_dark, labelcolor=text_color, loc='lower left', bbox_to_anchor=(0, 1.02, 1, 0.102), mode="expand", borderaxespad=0, frameon=False, fontsize=8, ncol=2)
                
                # Current RSI Value Badge
                last_rsi = df['RSI'].iloc[-1]
                
                # Current RSI SMA Value Badge
                last_rsi_sma = rsi_sma.iloc[-1] if not rsi_sma.isna().iloc[-1] else None
                
                # Calculate offsets to prevent overlap
                rsi_offset = 0
                sma_offset = 0
                
                if last_rsi_sma is not None:
                     diff = last_rsi - last_rsi_sma
                     # If values are close (less than 10 units), push them apart
                     if abs(diff) < 10:
                         if diff >= 0: # RSI >= SMA
                             rsi_offset = 8
                             sma_offset = -8
                         else: # RSI < SMA
                             rsi_offset = -8
                             sma_offset = 8
                
                bbox_props_rsi = dict(boxstyle="larrow,pad=0.3", fc='#b9bbbe', ec="none", alpha=0.8)
                ax2.annotate(f'{last_rsi:.1f}', xy=(1, last_rsi), xycoords=('axes fraction', 'data'),
                            xytext=(5, rsi_offset), textcoords='offset points',
                            color='black', fontweight='bold', fontsize=9, va='center', ha='left',
                            bbox=bbox_props_rsi)
                
                if last_rsi_sma is not None:
                    bbox_props_sma = dict(boxstyle="larrow,pad=0.3", fc='#f1c40f', ec="none", alpha=0.8)
                    ax2.annotate(f'{last_rsi_sma:.1f}', xy=(1, last_rsi_sma), xycoords=('axes fraction', 'data'),
                                xytext=(5, sma_offset), textcoords='offset points',
                                color='black', fontweight='bold', fontsize=9, va='center', ha='left',
                                bbox=bbox_props_sma)
            
            # Formatting Ax2
            ax2.grid(True, color=grid_color, linestyle=':', alpha=0.4)
            ax2.tick_params(axis='x', colors=text_color, labelsize=9)
            ax2.tick_params(axis='y', colors=text_color, labelsize=8)
            ax2.set_ylabel('') # Remove label
            for spine in ax2.spines.values():
                spine.set_color(text_color)
                spine.set_alpha(0.3)
            ax2.spines['top'].set_visible(False)
            ax2.spines['left'].set_visible(False) # Hide left spine
            
            # X-Axis Formatting
            tick_indices = np.linspace(0, len(x_indices) - 1, 8, dtype=int)
            ax2.set_xticks(tick_indices)
            
            tick_labels = []
            if isinstance(dates, pd.DatetimeIndex):
                 tick_labels = [dates[i].strftime('%d-%b') for i in tick_indices]
            else:
                 try:
                     # Use iloc for positional access if available (e.g. Series), otherwise index
                     def get_val(pos):
                         if hasattr(dates, 'iloc'):
                             return dates.iloc[pos]
                         return dates[pos]
                         
                     tick_labels = [pd.to_datetime(get_val(i)).strftime('%d-%b') for i in tick_indices]
                 except:
                     def get_val_fallback(pos):
                         if hasattr(dates, 'iloc'):
                             return dates.iloc[pos]
                         return dates[pos]
                     tick_labels = [str(get_val_fallback(i))[:5] for i in tick_indices]
            
            ax2.set_xticklabels(tick_labels, rotation=45, ha='right')
            
            # Watermark
            fig.text(0.5, 0.5, ticker, fontsize=100, color='white', 
                     ha='center', va='center', alpha=0.08, rotation=0, weight='bold')

            # Adjust layout
            # plt.tight_layout() # Usually good but with custom gridspec sometimes tricky
            plt.subplots_adjust(bottom=0.15, right=0.95, top=0.92, hspace=0.15)
            
            # Output
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight', facecolor=discord_dark)
            plt.close(fig)
            return buf
            
        except Exception as e:
            print(f"Error generating chart for {ticker}: {e}")
            import traceback
            traceback.print_exc()
            return None

    def send_analysis_message(self, ticker: str, content: str, is_positive: bool, 
                              sector: str = None, industry: str = None, summary: str = None, 
                              market_cap: str = None, webhook_url: Optional[str] = None,
                              earnings_info: str = None, image_buffer: Optional[io.BytesIO] = None) -> bool:
        """
        Sends the analysis as a structured Discord Embed, optionally with a chart image.
        """
        # Create the embed
        embed = self._create_analysis_embed(ticker, content, is_positive, sector, industry, summary, market_cap, earnings_info)
        
        target_url = webhook_url or self.webhook_url
        if not target_url:
             print(f"Error: No webhook URL configured for {ticker} (Sector: {sector})")
             return False

        try:
            if image_buffer:
                # Prepare image for sending
                image_buffer.seek(0)
                files = {
                    'file': ('chart.png', image_buffer, 'image/png')
                }
                # Update embed to use attachment
                embed["image"] = {"url": "attachment://chart.png"}
                
                payload = {
                    "embeds": [embed]
                }
                
                response = requests.post(
                    target_url,
                    data={'payload_json': json.dumps(payload)},
                    files=files
                )
            else:
                # Standard JSON send
                response = requests.post(
                    target_url,
                    json={
                        "embeds": [embed]
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
        DEPRECATED: Now using _create_analysis_embed.
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
        """
        overall_success = True
        
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
            df = item.get('df')  # Extract df
            
            # Extract Earnings Info specifically
            earnings_days = analysis_data.get('days_until_earnings')
            earnings_date = analysis_data.get('next_earnings_date')
            earnings_info_str = None
            
            if earnings_days is not None:
                 date_part = f" ({earnings_date.strftime('%d.%m.%Y')})" if earnings_date else ""
                 earnings_info_str = f"⏳ ימים לדווח תוצאות: {earnings_days}{date_part}"
            
            # Determine color/positive
            is_positive = analysis_data.get('is_positive', False)
            
            # Generate Chart
            image_buffer = None
            if df is not None:
                image_buffer = self._generate_chart_image(df, ticker, is_positive)
            
            if not self.send_analysis_message(ticker=ticker, content=output, is_positive=is_positive,
                                              sector=sector, industry=industry, summary=summary, market_cap=market_cap, webhook_url=webhook_url,
                                              earnings_info=earnings_info_str, image_buffer=image_buffer):
                overall_success = False
        
        return overall_success

class FearAndGreedNotifier(BaseDiscordNotifier):
    """
    Specialized notifier for Fear & Greed Index.
    """
    
    def send_fear_and_greed(self, score: float, rating: str, timestamp: str, webhook_url: Optional[str] = None) -> bool:
        """
        Sends a visual Fear & Greed Index update.
        """
        target_url = webhook_url or self.webhook_url
        if not target_url:
            print("Error: No webhook URL provided for Fear & Greed.")
            return False

        # Build message
        # Use Embed title style for Status and Score
        status_line = f"Status: {rating.upper()}"
        score_line = f"Fear & Greed score {int(score)} ({rating.lower()})"
        
        # This was basic content
        # message_content = f"**{status_line}**\n{score_line}"

        if HAS_MATPLOTLIB:
            try:
                # print("🎨 Generating Fear & Greed Image...")
                # Generate Image
                image_buffer = self._generate_gauge_image(score)
                image_buffer.seek(0)
                
                # DEBUG: Save to disk to verify generation
                # with open("latest_gauge_debug.png", "wb") as f:
                #    f.write(image_buffer.getvalue())
                # print("✅ Image generated and saved to latest_gauge_debug.png")
                
                # Reset buffer for reading
                image_buffer.seek(0)
                
                # Create Embed
                embed = {
                    "title": "😨 Fear & Greed Index 🤑",
                    "description": f"**{status_line}**\n{score_line}",
                    "color": self._get_color_for_score(score),
                    "image": {
                        "url": "attachment://gauge.png"
                    },
                    "timestamp": datetime.now().astimezone().isoformat()
                }

                # Send with file attachment and Embed
                files = {
                    'file': ('gauge.png', image_buffer, 'image/png')
                }
                
                payload = {
                    # "content": message_content, # Optional if we have embed
                    "embeds": [embed]
                }
                
                response = requests.post(
                    target_url,
                    data={'payload_json': json.dumps(payload)},
                    files=files
                )
                response.raise_for_status()
                return True
            except Exception as e:
                print(f"❌ Error generating or sending Fear & Greed image: {e}")
                import traceback
                traceback.print_exc()
                # Fallback to text if image fails?
                # For now let's just return False so we see the error
                return False
        else:
            # Fallback to text visualization
            print("❌ Matplotlib not available! Falling back to text visualization. Check logs for import errors.")
            visualization = self._create_text_visualization(score, rating)
            message = f"# 😨 Fear & Greed Index 🤑\n"
            message += f"> **Score:** {int(score)}/100\n"
            message += f"> **Rating:** {rating.title()}\n"
            message += f"\n{visualization}"

            try:
                response = requests.post(
                    target_url,
                    json={"content": message},
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                return True
            except Exception as e:
                print(f"Error sending Fear & Greed update: {e}")
                return False

    def _get_color_for_score(self, score: float) -> int:
        """
        Returns a Discord integer color based on score.
        """
        # 0-25: Extreme Fear (Red)
        if score < 25: return 0xFF3333
        # 25-45: Fear (Orange)
        if score < 45: return 0xFF9933
        # 45-55: Neutral (Grey/Yellow)
        if score < 55: return 0xD3D3D3
        # 55-75: Greed (Light Green)
        if score < 75: return 0x99CC33
        # 75-100: Extreme Greed (Dark Green)
        return 0x339933

    def _generate_gauge_image(self, score: float) -> io.BytesIO:
        """
        Generates a gauge chart image using matplotlib.
        Returns a BytesIO object containing the PNG image.
        """
        # Setup
        # Use Discord Dark theme background color
        discord_dark = '#2f3136'
        text_color = 'white'
        
        fig, ax = plt.subplots(figsize=(8, 5), subplot_kw={'aspect': 'equal'})
        
        # Set background colors
        fig.patch.set_facecolor(discord_dark)
        ax.set_facecolor(discord_dark)
        ax.axis('off')
        
        # Define ranges and colors (CNN Fear & Greed style)
        ranges = [(0, 25), (25, 45), (45, 55), (55, 75), (75, 100)]
        colors = ['#FF3333', '#FF9933', '#D3D3D3', '#99CC33', '#339933']
        labels = ['EXTREME\nFEAR', 'FEAR', 'NEUTRAL', 'GREED', 'EXTREME\nGREED']
        
        # Draw wedges
        for idx, (start, end) in enumerate(ranges):
            theta1 = 180 - (end * 1.8)
            theta2 = 180 - (start * 1.8)
            
            wedge = Wedge((0, 0), 1, theta1, theta2, width=0.4, facecolor=colors[idx], edgecolor=discord_dark, linewidth=2)
            ax.add_patch(wedge)
            
            # Add labels
            mid_angle = (theta1 + theta2) / 2
            r = 0.75
            x = r * np.cos(np.radians(mid_angle))
            y = r * np.sin(np.radians(mid_angle))
            
            rotation = mid_angle - 90
            
            # Black text on colored wedges usually reads better, but let's see.
            ax.text(x, y, labels[idx], ha='center', va='center', fontsize=9, fontweight='bold', rotation=rotation, color='black')

        # Draw Needle
        angle = 180 - (score * 1.8)
        angle_rad = np.radians(angle)
        
        r_needle = 0.9
        needle_color = 'white'
        
        ax.arrow(0, 0, r_needle * np.cos(angle_rad), r_needle * np.sin(angle_rad), 
                 head_width=0.05, head_length=0.1, fc=needle_color, ec=needle_color, width=0.02)
        
        # Center circle
        circle = plt.Circle((0, 0), 0.1, color=needle_color)
        ax.add_patch(circle)
        
        # Score Text
        ax.text(0, -0.2, f"{int(score)}", ha='center', va='center', fontsize=24, fontweight='bold', color=text_color)
        
        # Date Text (Hebrew)
        days = {0: 'שני', 1: 'שלישי', 2: 'רביעי', 3: 'חמישי', 4: 'שישי', 5: 'שבת', 6: 'ראשון'}
        months = {1: 'ינואר', 2: 'פברואר', 3: 'מרץ', 4: 'אפריל', 5: 'מאי', 6: 'יוני', 
                  7: 'יולי', 8: 'אוגוסט', 9: 'ספטמבר', 10: 'אוקטובר', 11: 'נובמבר', 12: 'דצמבר'}
        
        now = datetime.now()
        day_name = days[now.weekday()]
        month_name = months[now.month]
        
        date_str = f"תאריך: יום {day_name}, {now.day} ב{month_name} {now.year}"
        
        # Handle Hebrew RTL
        if HAS_BIDI:
            try:
                reshaped_text = arabic_reshaper.reshape(date_str)
                date_str = get_display(reshaped_text)
            except Exception as e:
                 print(f"Warning: Failed to reshape Hebrew text: {e}")

        plt.title(date_str, fontsize=14, pad=20, color=text_color)
        
        plt.xlim(-1.1, 1.1)
        plt.ylim(-0.2, 1.2)
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight', facecolor=discord_dark)
        plt.close(fig) # Close the figure to free memory
        return buf

    def _create_text_visualization(self, score: float, rating: str) -> str:
        """
        Creates a text-based visual scale for the score (Fallback).
        """
        total_segments = 20
        pointer_idx = min(max(int(score / 5), 0), 19)
        
        final_bar = []
        for i in range(20):
            val = i * 5
            if val < 25:
                base = "🟥"
            elif val < 45:
                base = "🟧"
            elif val < 55:
                base = "⬜"
            elif val < 75:
                base = "🟩"
            else:
                base = "🟦"
            
            if 45 <= val < 55:
                 base = "🟨"

            if i == pointer_idx:
                final_bar.append("🔘")
            else:
                final_bar.append(base)
        
        return "".join(final_bar)

# For backward compatibility if needed, though we should update main.py
DiscordNotifier = ClassicAnalysisNotifier
