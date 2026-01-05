import requests
from typing import Dict, Any, Optional

class FearAndGreedAgent:
    """
    Agent to fetch Fear and Greed Index data from CNN.
    """
    BASE_URL = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    def get_data(self) -> Dict[str, Any]:
        """
        Fetches the current Fear and Greed Index data.
        Returns a dictionary with 'score', 'rating', and 'timestamp'.
        """
        try:
            response = requests.get(self.BASE_URL, headers=self.HEADERS, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            fng_data = data.get('fear_and_greed', {})
            
            return {
                'score': fng_data.get('score', 0),
                'rating': fng_data.get('rating', 'Unknown'),
                'timestamp': fng_data.get('timestamp')
            }
        except Exception as e:
            print(f"Error fetching Fear and Greed data: {e}")
            return None

