
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from .models import Models

class TransformerModels():
    _instances = {}  # Dictionary to store instances by model name

    def __new__(cls, model_name):
        # Return existing instance if model_name already cached
        if model_name not in cls._instances:
            instance = super(TransformerModels, cls).__new__(cls)
            cls._instances[model_name] = instance
            instance._initialized = False  # Mark as not initialized
        return cls._instances[model_name]

    def __init__(self, model_name):
        # Only initialize once per instance
        if self._initialized:
            return
            
        self.model_name = model_name
        self.model = self._get_model()
        self.tokenizer = self._get_tokenizer()
        self.device = self._get_device()
        self._initialized = True

    def _get_model(self):
        model = AutoModelForCausalLM.from_pretrained(
            self.model_name, 
            torch_dtype="auto", 
            trust_remote_code=True,  # Required for Qwen models
            device_map="auto" # Automatically handles device placement
        )
        return model

    def _get_tokenizer(self):
        tokenizer = AutoTokenizer.from_pretrained(
            self.model_name, 
            trust_remote_code=True  # Required for Qwen models
        )
        return tokenizer

    def _get_device(self):
        device = "cuda" if torch.cuda.is_available() else "cpu"
        return device

    def _prepare_inputs(self, messages):
        # Convert LangChain messages to proper format
        formatted_messages = []
        for msg in messages:
            # Handle LangChain SystemMessage/HumanMessage/AIMessage objects
            if hasattr(msg, 'content'):
                # SystemMessage -> system role, HumanMessage -> user role
                role = "system" if msg.__class__.__name__ == "SystemMessage" else "user"
                formatted_messages.append({"role": role, "content": msg.content})
            elif isinstance(msg, dict):
                # Already in correct format
                formatted_messages.append(msg)
        
        return self.tokenizer.apply_chat_template(
            formatted_messages,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
        ).to(self.model.device)

    def generate_response(self, messages, temperature=0.7, max_new_tokens=4096):
        inputs = self._prepare_inputs(messages)
        
        # Use more deterministic settings for JSON output
        generation_kwargs = {
            "max_new_tokens": max_new_tokens,
            "pad_token_id": self.tokenizer.eos_token_id,
            "eos_token_id": self.tokenizer.eos_token_id,
            "repetition_penalty": 1.1,  # Prevent repetition loops
        }
        
        # For very low temperatures, use greedy decoding (more deterministic)
        if temperature < 0.01:
            generation_kwargs["do_sample"] = False
        else:
            generation_kwargs["temperature"] = temperature
            generation_kwargs["do_sample"] = True
            generation_kwargs["top_p"] = 0.9
            generation_kwargs["top_k"] = 50
        
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                **generation_kwargs
            )
        
        generated_text = self.tokenizer.decode(
            outputs[0][inputs["input_ids"].shape[-1]:], 
            skip_special_tokens=True
        )
        return generated_text

        
class LocalTransformerModels(Models):
    def __init__(self):
        pass

    def get_chat_model(self, model_name, temperature=0.7):
        transformer_models = TransformerModels(model_name)
        return transformer_models