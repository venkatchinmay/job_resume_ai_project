import pypdf
import os
from dotenv import load_dotenv
from models.openrouter_models import OpenRouterModels
from groq import Groq
load_dotenv()


def extract_pdf_content(pdf_path):
    with open(pdf_path, 'rb') as file:
        reader = pypdf.PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
    return text

def get_free_models():
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("Warning: OPENROUTER_API_KEY not set")
        return []
    # Initialize with API key and access public .models attribute
    return OpenRouterModels(api_key).models 

def get_models():
    models = []
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("Warning: GROQ_API_KEY not set")
        return []
    client = Groq(api_key=api_key)

    try:
        response = client.models.list()
        for model in response.data:
            models.append(model.id)
        
    except Exception as e:
        raise ValueError(f"Error fetching models: {e}")
    return models      

if __name__ == "__main__":
    print(get_free_models())
    print(get_models())
