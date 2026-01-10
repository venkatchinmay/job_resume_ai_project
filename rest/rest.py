import requests
from functools import lru_cache
import time

OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"

class Rest:
    
    @lru_cache(maxsize=128)
    def get_open_router_models(self):
        max_retries = 3
        base_delay = 2  # Start with 2 seconds
        
        for attempt in range(max_retries):
            try:
                response = requests.get(OPENROUTER_MODELS_URL, timeout=30)
                if response.status_code == 200:
                    data = response.json()
                    models = data.get("data", [])
                    print(f"✅ Fetched {len(models)} models from OpenRouter")
                    return models
                else:
                    print(f"⚠️  Error fetching models (attempt {attempt+1}/{max_retries}): HTTP {response.status_code}")
                    
            except requests.exceptions.Timeout:
                print(f"⚠️  Timeout fetching models (attempt {attempt+1}/{max_retries})")
            except requests.exceptions.ConnectionError as e:
                print(f"⚠️  Connection error (attempt {attempt+1}/{max_retries}): {e}")
            except Exception as e:
                print(f"⚠️  Exception fetching models (attempt {attempt+1}/{max_retries}): {e}")
            
            # Retry with exponential backoff
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                print(f"⏳ Retrying in {delay}s...")
                time.sleep(delay)
        
        print("❌ Failed to fetch models after all retries. Returning empty list.")
        return []         