"""
AthenaInvest - Classic Technical Analysis
Main entry point for classic technical analysis based on SMA_150 and ATR.
"""
import sys
import io

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from agents import ClassicAnalyzer, DiscordNotifier
from agents.ticker_info_agent import TickerInfoAgent
from config import TICKERS, WEBHOOK_URL, SECTOR_CHANNEL_MAP, SECTOR_HEBREW_MAP


def main():
    """Run classic technical analysis on configured tickers."""
    analyzer = ClassicAnalyzer()
    ticker_info_agent = TickerInfoAgent()
    
    # Initialize Discord notifier if webhook URL is configured
    discord_notifier = None
    # We check if ANY webhook is configured, but strictly speaking we check the main one or just proceed
    # Since we support multiple webhooks, we can initialize it even if WEBHOOK_URL is None, 
    # as long as specific ones might be set. But existing logic checks WEBHOOK_URL.
    # We'll allow it if WEBHOOK_URL is set, or just always init and let it fail gracefully per message.
    # For now, sticking to existing check or slightly relaxing it.
    
    try:
        discord_notifier = DiscordNotifier()
        if WEBHOOK_URL:
             print("✅ Discord notifications enabled")
        else:
             print("ℹ️ Main Discord webhook not set, but individual sector webhooks might be used.")
    except Exception as e:
        print(f"⚠️ Discord notifications disabled: {str(e)}")
    
    print("=" * 80)
    print("AthenaInvest - Classic Technical Analysis".center(80))
    print("=" * 80)
    print()
    
    results = []
    discord_analyses = []  # Store analyses for Discord
    
    for i, ticker in enumerate(TICKERS, 1):
        try:
            # Fetch data and calculate indicators
            df, days_until_earnings = analyzer.analyze(ticker)
            
            # Perform classic analysis
            analysis = analyzer.analyze_classic(df, days_until_earnings)
            analysis['ticker'] = ticker
            
            # Fetch Ticker Info (Sector, Industry & Summary)
            info = ticker_info_agent.get_ticker_info(ticker)
            english_sector = info.get('sector_en', 'Unknown')
            hebrew_sector = info.get('sector', english_sector)
            hebrew_industry = info.get('industry', 'Unknown')
            summary = info.get('summary', '')
            market_cap = info.get('market_cap', 'N/A')
            
            # Format and display output
            output = analyzer.format_output(ticker, analysis)
            print(output)
            print(f"   Sector (EN): {english_sector}")
            print(f"   Sector (HE): {hebrew_sector}")
            print(f"   Industry (HE): {hebrew_industry}")
            print(f"   Market Cap: {market_cap}")
            print(f"   Summary: {summary}")
            
            # Add spacing between stocks (except for the last one)
            if i < len(TICKERS):
                print()
            
            # Store results
            results.append({
                'ticker': ticker,
                'is_positive': analysis['is_positive'],
                'status': analysis['status'],
                'success': True
            })
            
            # Determine Webhook URL based on English Sector (internal logic)
            webhook_url = SECTOR_CHANNEL_MAP.get(english_sector)
            if not webhook_url:
                # Try partial match or fallback
                # For now, simple fallback
                webhook_url = WEBHOOK_URL
            
            # Store for Discord (with full analysis data for better formatting)
            # Pass the HEBREW sector to the notifier
            if discord_notifier:
                discord_analyses.append({
                    'ticker': ticker,
                    'output': output,
                    'analysis': analysis,
                    'sector': hebrew_sector, # Send Hebrew sector to Discord
                    'industry': hebrew_industry, # Send Hebrew industry to Discord
                    'summary': summary,
                    'market_cap': market_cap,
                    'webhook_url': webhook_url
                })
            
        except Exception as e:
            print(f"{ticker}")
            print(f"❌ Error analyzing: {str(e)}")
            if i < len(TICKERS):
                print()
            
            results.append({
                'ticker': ticker,
                'success': False,
                'error': str(e)
            })
    
    # Summary
    print()
    print("=" * 80)
    print("Analysis Summary".center(80))
    print("=" * 80)
    
    successful_results = [r for r in results if r.get('success')]
    if successful_results:
        positive_results = [r for r in successful_results if r.get('is_positive')]
        negative_results = [r for r in successful_results if not r.get('is_positive')]
        
        # Count by status
        status_counts = {}
        for r in successful_results:
            status = r.get('status', 'unknown')
            status_counts[status] = status_counts.get(status, 0) + 1
        
        print(f"\n✅ Successfully analyzed {len(successful_results)} stocks:")
        print(f"   📈 Positive: {len(positive_results)}")
        print(f"   📉 Negative: {len(negative_results)}")
        
        if status_counts:
            print(f"\n📊 Breakdown by Status:")
            status_names = {
                'breakout': '🚀 Breakout',
                'stretched': '🚀 Stretched',
                'breakdown': '💥 Breakdown',
                'stagnation': '⚠️ Stagnation',
                'accumulation': '📊 Accumulation'
            }
            for status, count in sorted(status_counts.items(), key=lambda x: x[1], reverse=True):
                status_display = status_names.get(status, status)
                print(f"   {status_display}: {count}")
    
    failed_results = [r for r in results if not r.get('success')]
    if failed_results:
        print(f"\n❌ Failed {len(failed_results)} stocks:")
        for result in failed_results:
            print(f"   {result['ticker']}: {result.get('error', 'Unknown error')}")
    
    print()
    print("=" * 80)
    print("Analysis Complete".center(80))
    print("=" * 80)
    
    # Send to Discord if configured
    if discord_notifier and discord_analyses:
        print("\n📤 Sending results to Discord...")
        if discord_notifier.send_batch_analysis(discord_analyses):
            print("✅ Successfully sent to Discord")
        else:
            print("❌ Failed to send some messages to Discord")


if __name__ == "__main__":
    main()
