import os
import json
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get API Key
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# OpenRouter API Base URL
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"

def get_free_models():
    """
    Fetches the list of available models from OpenRouter and filters for free ones.
    """
    try:
        print("Fetching model list from OpenRouter...")
        response = requests.get(OPENROUTER_MODELS_URL)
        
        if response.status_code != 200:
            print(f"Error fetching models: {response.status_code} - {response.text}")
            return []
            
        data = response.json()
        all_models = data.get("data", [])
        
        free_models = []
        for model in all_models:
            pricing = model.get("pricing", {})
            prompt_price = float(pricing.get("prompt", 0))
            completion_price = float(pricing.get("completion", 0))
            
            # Check if both prices are effectively zero
            if prompt_price == 0.0 and completion_price == 0.0:
                free_models.append(model["id"])
                
        return free_models

    except Exception as e:
        print(f"Exception fetching models: {e}")
        return []

def chat_with_openrouter(prompt, model):
    """
    Sends a chat completion request to OpenRouter using the requests library.
    """
    if not OPENROUTER_API_KEY:
        print("Error: OPENROUTER_API_KEY not found in environment variables.")
        return None

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": model,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }

    try:
        print(f"Sending request to {model}...")
        response = requests.post(OPENROUTER_URL, headers=headers, data=json.dumps(data))
        
        if response.status_code != 200:
            print(f"Error {response.status_code}: {response.text}")
            return None

        result = response.json()
        
        if 'choices' in result and len(result['choices']) > 0:
            content = result['choices'][0]['message']['content']
            return content
        else:
            print("No choices in response:", result)
            return None

    except Exception as e:
        print(f"Exception occurred: {e}")
        return None

# ==========================================
# TOOL USE EXAMPLE
# ==========================================

def get_current_weather(location, unit="celsius"):
    """Get the current weather in a given location"""
    # Mock response
    return json.dumps({
        "location": location,
        "temperature": "22",
        "unit": unit,
        "forecast": ["sunny", "windy"]
    })

def chat_with_tools_openrouter(prompt, model="google/gemini-2.0-flash-exp:free"):
    """
    Demonstrates tool calling with OpenRouter (OpenAI-compatible).
    """
    print(f"\n--- Testing Tool Use with model: {model} ---")
    
    if not OPENROUTER_API_KEY:
        print("Error: OPENROUTER_API_KEY not set.")
        return

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    tool_definition = {
        "type": "function",
        "function": {
            "name": "get_current_weather",
            "description": "Get the current weather in a given location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and state, e.g. San Francisco, CA",
                    },
                    "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
                },
                "required": ["location"],
            },
        }
    }

    messages = [{"role": "user", "content": prompt}]

    data = {
        "model": model,
        "messages": messages,
        "tools": [tool_definition],
        "tool_choice": "auto" 
    }

    try:
        # Step 1: Send initial request with tools
        print("1. Sending initial prompt with tools...")
        response = requests.post(OPENROUTER_URL, headers=headers, data=json.dumps(data))
        
        if response.status_code != 200:
            print(f"Error {response.status_code}: {response.text}")
            return

        result = response.json()
        message = result['choices'][0]['message']
        
        # Step 2: Check for tool calls
        if message.get("tool_calls"):
            tool_calls = message['tool_calls']
            print(f"2. Model decided to call tools: {len(tool_calls)} call(s)")
            
            # Append the model's response (with tool calls) to conversation
            messages.append(message)

            for tool_call in tool_calls:
                function_name = tool_call['function']['name']
                function_args = json.loads(tool_call['function']['arguments'])
                
                print(f"   - Function: {function_name}")
                print(f"   - Arguments: {function_args}")
                
                if function_name == "get_current_weather":
                    function_response = get_current_weather(
                        location=function_args.get("location"),
                        unit=function_args.get("unit", "celsius")
                    )
                    
                    # Append tool response
                    messages.append({
                        "tool_call_id": tool_call['id'],
                        "role": "tool",
                        "name": function_name,
                        "content": function_response,
                    })

            # Step 3: Send the tool outputs back to the model
            print("3. Sending tool outputs back to model...")
            final_data = {
                "model": model,
                "messages": messages
            }
            
            final_response = requests.post(OPENROUTER_URL, headers=headers, data=json.dumps(final_data))
            
            if final_response.status_code != 200:
                 print(f"Error in final step {final_response.status_code}: {final_response.text}")
                 return

            final_result = final_response.json()
            final_content = final_result['choices'][0]['message']['content']
            print(f"\n[Final Response]: {final_content}")
            
        else:
            print("Model did not call any tools. Response:", message.get("content"))

    except Exception as e:
        print(f"Exception during tool use test: {e}")


if __name__ == "__main__":
    if not OPENROUTER_API_KEY:
        print("----------------------------------------------------------------")
        print("WARNING: OPENROUTER_API_KEY is not set.")
        print("Create a .env file and add: OPENROUTER_API_KEY=sk-or-...")
        print("----------------------------------------------------------------")
    
    # 1. Get Free Models dynamically
    free_models_list = get_free_models()
    
    if free_models_list:
        print(f"\nFound {len(free_models_list)} free models.")
        
        # 2. Pick a model for basic chat
        preferred = [m for m in free_models_list if "gemini" in m.lower() or "llama" in m.lower() or "mistral" in m.lower()]
        others = [m for m in free_models_list if m not in preferred]
        candidates = preferred + others
        
        print("\n=== BASIC CHAT TEST ===")
        user_prompt = "Explain why the sky is blue in one sentence."
        
        for model_to_use in candidates[:3]:
            print(f"\nTesting model: {model_to_use}")
            response = chat_with_openrouter(user_prompt, model=model_to_use)
            if response:
                print(f"Response: {response}")
                break
        
        # 3. Test Tool Use
        # We need a smart model for tools. Gemini 2.0 Flash or Llama 3 is good.
        print("\n=== TOOL USE TEST ===")
        tool_model = "google/gemini-2.0-flash-exp:free"
        
        # Check if the specific model is in our free list (it should be)
        if tool_model not in free_models_list:
             print(f"Note: {tool_model} might not be in the free list at this moment, trying anyway...")
             
        chat_with_tools_openrouter("What is the weather in Tokyo?", model=tool_model)

    else:
        print("No free models found or failed to fetch list.")
