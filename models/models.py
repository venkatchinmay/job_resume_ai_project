from abc import ABC, abstractmethod

class Models(ABC):
    
    @abstractmethod
    def get_chat_model(self, model_name, temperature):
        pass