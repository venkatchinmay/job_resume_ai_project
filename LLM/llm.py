from config.settings import Settings
from models.openrouter_models import OpenRouterModels
from prompt_loader.jinja_template import JinjaTemplate
from models.transformer_models import LocalTransformerModels
from models.groq_models import GroqModels

class LLM:

    @staticmethod
    def _get_chat_model_llms(platform, model_name, temperature):
        platform_instance = LLM._get_platform(platform, model_name)
        return platform_instance.get_chat_model(model_name, temperature)
    
    @staticmethod
    def _get_platform(platform, model_name): 
        if platform == "openrouter":
            openai_api_key = Settings().get_conf("OPENROUTER_API_KEY")
            openrouter_models = OpenRouterModels(openai_api_key)
            if model_name in openrouter_models.models:
                return openrouter_models
            else:
                raise ValueError(f"Unknown model: {model_name}")
        elif platform == "groq":
            groq_api_key = Settings().get_conf("GROQ_API_KEY")
            groq_models = GroqModels(groq_api_key)
            if model_name in groq_models.models:
                return groq_models
            else:
                raise ValueError(f"Unknown model: {model_name}")

        elif platform == "transformer":
            transformer_models = LocalTransformerModels()
            return transformer_models
        else:
            raise ValueError(f"Unknown platform: {platform}")

    @staticmethod
    def get_llm_model_without_tools(platform, model_name, temperature, prompt_file_name: str = None, arguments: dict = None):
        platform_instance = LLM._get_platform(platform, model_name)
        chat_model = platform_instance.get_chat_model(model_name, temperature)
        if prompt_file_name is not None:
            prompt = JinjaTemplate().load_prompt(prompt_file_name, arguments)
        else:
            prompt = arguments.get("prompt")

        return chat_model, prompt

    @staticmethod
    def get_llm_model_with_tools(platform, model_name, temperature, prompt_file_name: str = None, arguments: dict = None, tools: list = None):
        chat_model, prompt = LLM.get_llm_model_without_tools(platform, model_name, temperature, prompt_file_name, arguments)
        if tools:
            chat_model = chat_model.bind_tools(tools)
        return chat_model, prompt

   

         
