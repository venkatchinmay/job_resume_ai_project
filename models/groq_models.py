from langchain_groq import ChatGroq
from rest import Rest
from .models import Models
from functools import lru_cache
from groq import Groq

class GroqModels(Models):
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(GroqModels, cls).__new__(cls)
        return cls._instance

    def __init__(self, GROQ_API_KEY):
        # Ensure initialization only happens once
        if hasattr(self, '_initialized') and self._initialized:
            return
            
        self._GROQ_API_KEY = GROQ_API_KEY   
        self.models = self._get_models()
        self._initialized = True

    def _get_models(self):
        grok_models = []
        client = Groq(api_key=self._GROQ_API_KEY)

        try:
            models = client.models.list()
            for model in models.data:
               grok_models.append(model.id)
        
        except Exception as e:
            raise ValueError(f"Error fetching models: {e}")
        return grok_models

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
        return ChatGroq(
                api_key=self._GROQ_API_KEY, 
                model=model_name,
                temperature=temperature
            )