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
from config import TICKERS, WEBHOOK_URL


def main():
    """Run classic technical analysis on configured tickers."""
    analyzer = ClassicAnalyzer()
    
    # Initialize Discord notifier if webhook URL is configured
    discord_notifier = None
    if WEBHOOK_URL:
        try:
            discord_notifier = DiscordNotifier()
            print("✅ Discord notifications enabled")
        except Exception as e:
            print(f"⚠️ Discord notifications disabled: {str(e)}")
    else:
        print("ℹ️ Discord webhook URL not configured (set WEBHOOK_URL in .env)")
    
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
            
            # Format and display output
            output = analyzer.format_output(ticker, analysis)
            print(output)
            
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
            
            # Store for Discord (with full analysis data for better formatting)
            if discord_notifier:
                discord_analyses.append({
                    'ticker': ticker,
                    'output': output,
                    'analysis': analysis  # Store full analysis for better Discord formatting
                })
            
        except Exception as e:
            print(f"${ticker}")
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

