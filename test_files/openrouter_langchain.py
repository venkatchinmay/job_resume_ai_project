import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_core.prompts import PromptTemplate
from openrouter_test import get_free_models

# Load environment variables
load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

if not OPENROUTER_API_KEY:
    print("WARNING: OPENROUTER_API_KEY not found. Please set it in .env")

# ==========================================
# 1. SETUP LANGCHAIN MODEL
# ==========================================
def get_chat_model(model_name):
    """
    Returns a configured ChatOpenAI instance pointing to OpenRouter.
    """
    return ChatOpenAI(
        model=model_name,
        openai_api_key=OPENROUTER_API_KEY,
        openai_api_base=OPENROUTER_BASE_URL,
        temperature=0.7,
    )

# ==========================================
# 2. DEFINE TOOLS
# ==========================================
@tool
def get_current_weather(location: str, unit: str = "celsius") -> str:
    """Get the current weather in a given location"""
    return f"The weather in {location} is usually sunny and 22 {unit}."

# ==========================================
# 3. RUN EXAMPLES
# ==========================================
def run_langchain_examples():
    # 1. Fetch available free models
    print("Fetching free models from OpenRouter...")
    free_models = get_free_models()
    
    if not free_models:
        print("No free models found! (or network error)")
        return

    # Prepare a list of candidates
    # Prioritize reliable models for tool calling
    preferred = [m for m in free_models if "gemini" in m.lower() or "llama" in m.lower() or "mistral" in m.lower()]
    others = [m for m in free_models if m not in preferred]
    candidates = preferred + others
    
    # Try up to 5 Models
    for model_name in candidates[:5]:
        print(f"\n==========================================")
        print(f"Attempting with Model: {model_name}")
        print(f"==========================================")
        
        try:
            llm = get_chat_model(model_name)

            # --- EXAMPLE A: BASIC CHAT ---
            print("\n--- [A] Basic Chat ---")
            messages = [
                SystemMessage(content="You are a helpful assistant."),
                HumanMessage(content="Explain quantum entanglement in simple terms.")
            ]
            response = llm.invoke(messages)
            print("Response:", response.content)
            
            # --- EXAMPLE B: TOOL USE ---
            print("\n--- [B] Tool Use (Function Calling) ---")
            
            # Bind tools to the LLM
            llm_with_tools = llm.bind_tools([get_current_weather])
            
            query = "What is the weather in Paris?"
            print(f"User Query: {query}")
        
            # Invoking the model with tools
            response = llm_with_tools.invoke(query)
            
            print(f"Model Response Type: {type(response)}")
            print(f"Tool Calls: {response.tool_calls}")
            
            if response.tool_calls:
                for tool_call in response.tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]
                    
                    print(f"Executing Tool: {tool_name} with args {tool_args}")
                    
                    if tool_name == "get_current_weather":
                        # Execute the tool using .invoke() which handles the arguments dict
                        # The @tool decorator makes it a StructuredTool, so we call .invoke()
                        result = get_current_weather.invoke(tool_args)
                        print(f"Tool Result: {result}")
            else:
                 print("Model did not decide to call a tool. Content:", response.content)
            
            # --- EXAMPLE C: JINJA2 PROMPT TEMPLATE ---
            print("\n--- [C] Prompt Template with Jinja2 ---")
            
            # Define a Jinja2 template with loops
            jinja_template = """
            You are a {{ role }}.
            
            Your current tasks are:
            {% for task in tasks %}
            - {{ task }}
            {% endfor %}
            
            User's Request: {{ query }}
            
            Answer:
            """
            
            prompt = PromptTemplate(
                template=jinja_template,
                input_variables=["role", "tasks", "query"],
                template_format="jinja2"
            )
            
            # Create a chain
            chain = prompt | llm
            
            # Invoke header
            print("Invoking Jinja2 Chain...")
            
            response = chain.invoke({
                "role": "Python Technical Interviewer",
                "tasks": ["Assess knowledge of decorators", "Check simplicity", "Be concise"],
                "query": "Ask me a beginner-level interview question."
            })
            
            print(f"Response: {response.content}")

            print(f"\n[SUCCESS] Examples ran successfully with {model_name}")
            break # Exit loop on success
            
        except Exception as e:
            print(f"Error with {model_name}: {e}")
            print("Trying next model...")
    else:
        print("\n[FAILED] Could not successfully run examples with any of the attempted models.")

if __name__ == "__main__":
    run_langchain_examples()
