import os
import json
from dotenv import load_dotenv

class Settings:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Settings, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """
        Load environment variables from .env file and config from config.json
        """
        load_dotenv()
        
        # Load JSON config
        config_path = os.path.join(os.path.dirname(__file__), 'config.json')
        self.json_config = {}
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    self.json_config = json.load(f)
            except Exception as e:
                print(f"Warning: Failed to load config.json: {e}")

        
       
       
    def get_conf(self, key, default=None):
        return os.getenv(key) or self.json_config.get(key) or default


# Create a singleton instance
settings = Settings()
