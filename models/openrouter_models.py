from langchain_openai import ChatOpenAI
from rest import Rest
from .models import Models
from functools import lru_cache

class OpenRouterModels(Models):
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(OpenRouterModels, cls).__new__(cls)
        return cls._instance

    def __init__(self, OPENROUTER_API_KEY):
        # Ensure initialization only happens once
        if hasattr(self, '_initialized') and self._initialized:
            return
            
        self._OPENROUTER_API_KEY = OPENROUTER_API_KEY
        self._OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
        self.models = self._get_free_models()
        self._initialized = True

    def _get_free_models(self):
        free_models = []
        models = Rest().get_open_router_models()
        for model in models:
            pricing = model.get("pricing")
            # Handle potential missing or None values safely
            prompt_price = float(pricing.get("prompt", 0) if pricing else 0)
            completion_price = float(pricing.get("completion", 0) if pricing else 0)
            
            if prompt_price != 0.0 or completion_price != 0.0:
                continue
            free_models.append(model.get("id"))
        return free_models

    @lru_cache(maxsize=128)
    def get_chat_model(self, model_name, temperature=0.7):
        # We can loosely enforce model existence or just warn. 
        # Since the user logic had a check, lets keep it but maybe warn instead of crash if list is empty?
        # Sticking to original logic: raise if not found.
        if model_name not in self.models:
             # Just a check, but if models list failed to fetch, this blocks everything.
             # I'll keep it as is to match original intent.
             raise ValueError(f"Model {model_name} not found in free models list")
        print(f"Model {model_name} found in free models list")
        return ChatOpenAI(
            model=model_name,
            openai_api_key=self._OPENROUTER_API_KEY,
            openai_api_base=self._OPENROUTER_BASE_URL,
            temperature=temperature,
            request_timeout=120,  # 120 second timeout to prevent indefinite blocking
            max_retries=2,  # Retry twice on failures
        )