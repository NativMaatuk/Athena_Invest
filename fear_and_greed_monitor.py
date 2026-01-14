"""
AthenaInvest - Fear & Greed Monitor
Dedicated script to monitor Fear & Greed Index hourly.
"""
import sys
import io
from unittest.mock import MagicMock

# Mock talib to avoid C-library dependency for this lightweight script
sys.modules['talib'] = MagicMock()

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import os
# We can now safely import from agents, as talib is mocked
from agents.fear_and_greed_agent import FearAndGreedAgent
from agents.discord_notifier import FearAndGreedNotifier
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
WEBHOOK_URL = os.getenv('WEBHOOK_URL')
WEBHOOK_FEAR_AND_GREED = os.getenv('WEBHOOK_FEAR_AND_GREED')


def main():
    print("=" * 80)
    print("AthenaInvest - Fear & Greed Monitor".center(80))
    print("=" * 80)
    print()

    try:
        print("🔍 Checking Fear & Greed Index...")
        fng_agent = FearAndGreedAgent()
        fng_data = fng_agent.get_data()
        
        if fng_data:
            print(f"   Score: {int(fng_data.get('score'))}")
            print(f"   Rating: {fng_data.get('rating')}")
            
            # Send to Discord
            fng_webhook = WEBHOOK_FEAR_AND_GREED or WEBHOOK_URL
            
            if fng_webhook:
                fng_notifier = FearAndGreedNotifier()
                # Check for matplotlib availability indirectly or just let it try (it handles its own fallback/imports)
                
                success = fng_notifier.send_fear_and_greed(
                    fng_data['score'], 
                    fng_data['rating'], 
                    fng_data['timestamp'], 
                    webhook_url=fng_webhook
                )
                
                if success:
                    print("✅ Sent Fear & Greed to Discord")
                else:
                    print("❌ Failed to send Fear & Greed to Discord")
            else:
                print("ℹ️ No webhook configured for Fear & Greed")
        else:
            print("⚠️ Failed to fetch Fear & Greed data")
            
    except Exception as e:
        print(f"⚠️ Error processing Fear & Greed: {e}")
        import traceback
        traceback.print_exc()

    print()
    print("=" * 80)

if __name__ == "__main__":
    main()
