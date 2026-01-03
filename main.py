"""
AthenaInvest - Main Entry Point
"""
import pandas as pd
from agents import TechnicalAnalyzer
from config import TICKERS


def main():
    """Run technical analysis on configured tickers."""
    analyzer = TechnicalAnalyzer()
    
    print("=" * 70)
    print("AthenaInvest - Technical Analysis")
    print("=" * 70)
    print()
    
    results = []
    
    for ticker in TICKERS:
        print(f"\n{'=' * 70}")
        print(f"Analyzing: {ticker}")
        print(f"{'=' * 70}")
        
        try:
            # Analyze the ticker
            print(f"Fetching data and calculating indicators...")
            df = analyzer.analyze(ticker)
            
            # Calculate score
            print(f"Calculating technical score...")
            score, summary = analyzer.calculate_score(df)
            
            # Display results
            print(f"\n{summary}")
            
            # Show last row data
            print(f"\nLast Data Point:")
            last_row = df.iloc[-1]
            
            # Handle date column (could be 'Date' or index)
            if 'Date' in df.columns:
                date_val = last_row['Date']
            elif isinstance(df.index, pd.DatetimeIndex):
                date_val = df.index[-1]
            else:
                date_val = 'N/A'
            
            print(f"  Date: {date_val}")
            print(f"  Close Price: ${last_row['Close']:.2f}")
            
            if pd.notna(last_row.get('SMA_150')):
                print(f"  SMA_150: ${last_row['SMA_150']:.2f}")
            if pd.notna(last_row.get('EMA_50')):
                print(f"  EMA_50: ${last_row['EMA_50']:.2f}")
            if pd.notna(last_row.get('RSI')):
                print(f"  RSI: {last_row['RSI']:.2f}")
            if pd.notna(last_row.get('Volume')):
                print(f"  Volume: {last_row['Volume']:,.0f}")
            
            # Additional Indicators
            print(f"\nAdditional Indicators:")
            if pd.notna(last_row.get('CCI')):
                print(f"  CCI: {last_row['CCI']:.2f}")
            if pd.notna(last_row.get('BBands_Upper')) and pd.notna(last_row.get('BBands_Lower')):
                print(f"  Bollinger Bands:")
                print(f"    Upper: ${last_row['BBands_Upper']:.2f}")
                print(f"    Middle: ${last_row['BBands_Middle']:.2f}")
                print(f"    Lower: ${last_row['BBands_Lower']:.2f}")
                # Show position relative to bands
                if last_row['Close'] > last_row['BBands_Upper']:
                    print(f"    Status: Price above upper band (overbought)")
                elif last_row['Close'] < last_row['BBands_Lower']:
                    print(f"    Status: Price below lower band (oversold)")
                else:
                    print(f"    Status: Price within bands (normal)")
            
            # Store results
            results.append({
                'ticker': ticker,
                'score': score,
                'close_price': last_row['Close']
            })
            
        except Exception as e:
            print(f"❌ Error analyzing {ticker}: {str(e)}")
            import traceback
            traceback.print_exc()
            results.append({
                'ticker': ticker,
                'score': None,
                'error': str(e)
            })
    
    # Summary
    print(f"\n{'=' * 70}")
    print("Analysis Summary")
    print(f"{'=' * 70}")
    
    successful_results = [r for r in results if r.get('score') is not None]
    if successful_results:
        print(f"\nSuccessfully analyzed {len(successful_results)} ticker(s):")
        for result in successful_results:
            print(f"  {result['ticker']}: Score = {result['score']:.2f}/10.0, Price = ${result['close_price']:.2f}")
    
    failed_results = [r for r in results if r.get('score') is None]
    if failed_results:
        print(f"\nFailed to analyze {len(failed_results)} ticker(s):")
        for result in failed_results:
            print(f"  {result['ticker']}: {result.get('error', 'Unknown error')}")
    
    print(f"\n{'=' * 70}")
    print("Analysis Complete")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
