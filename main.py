import os
from dotenv import load_dotenv
from LLM.llm import LLM
from langchain_core.tools import tool
import json
import re
from typing import Optional, Dict, Any
from langchain_core.messages import SystemMessage
from jobspy import scrape_jobs
from firecrawl import FirecrawlApp
import time
import pypdf
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
import math

## Input variables

file_path = "/home/chinmay/2025-incometaxproofs/Bindu.Ch_Resume_word_format_with_bullets.pdf" 
location = "Hyderabad"
country = "India"
max_search_queries = 10
hours_old = 168
platform = "groq"

##  STEP: 0 Loading Environment variables 

load_dotenv()

def _extract_and_parse_json(
    text: str, 
    strict: bool = False
) -> Optional[Dict[Any, Any]]:
    """
    Extract and parse JSON from various text formats
    
    Args:
        text: Input text containing JSON
        strict: If True, raise exceptions; if False, return None on error
    
    Returns:
        Parsed JSON dictionary/list or None
    """
    try:
        # Method 1: Try markdown code block (objects)
        pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
        match = re.search(pattern, text, re.DOTALL)
        
        if match:
            return json.loads(match.group(1))
        
        # Method 1b: Try markdown code block (arrays)
        pattern = r'```(?:json)?\s*(\[.*?\])\s*```'
        match = re.search(pattern, text, re.DOTALL)
        
        if match:
            return json.loads(match.group(1))
        
        # Method 2: Try to find raw JSON object
        start = text.find('{')
        end = text.rfind('}') + 1
        
        if start != -1 and end != 0:
            json_str = text[start:end]
            return json.loads(json_str)
        
        # Method 3: Try to find raw JSON array
        start = text.find('[')
        end = text.rfind(']') + 1
        
        if start != -1 and end != 0:
            json_str = text[start:end]
            return json.loads(json_str)
        
        if strict:
            raise ValueError("No JSON found in text")
        return None
        
    except json.JSONDecodeError as e:
        if strict:
            raise ValueError(f"Invalid JSON: {e}")
        return None
    except Exception as e:
        if strict:
            raise ValueError(f"Error extracting JSON: {e}")
        return None

def _extract_pdf_content(pdf_path):
    with open(pdf_path, 'rb') as file:
        reader = pypdf.PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
    return text

## STEP:1 Extract and Summerize the PDF File
def resume_summerize(platform,file_path):
    pdf_content = _extract_pdf_content(file_path)
    model_name = _get_model(platform)
    temperature = 0
    prompt_file_name = "resume_summerize.jinja2"
    arguments = {
        "resume_content": pdf_content
    }

    chat_model, prompt = LLM.get_llm_model_without_tools(platform, model_name, temperature, prompt_file_name, arguments)
    messages = [
        SystemMessage(content=prompt),
    ]
    response = chat_model.invoke(messages)
    data = _extract_and_parse_json(response.content)
    return data

## STEP:2 Adding Extra Information
def adding_extra_info(data):
    data["location"] = location
    data["JobType"] = "fulltime"
    data["Country"] = country
    return data 

## STEP:3 Detecting Search Queries
def detecting_search_queries(platform,data,max_search_queries=10):
    prompt_file_name = "generate_queries.jinja2"
    arguments = {
        "resume_data": data,
        "MAX_SEARCH_QUERIES": max_search_queries
    }
    model_name = _get_model(platform)
    temperature = 0.4
    chat_model, prompt = LLM.get_llm_model_without_tools(platform, model_name, temperature, prompt_file_name, arguments)
    messages = [
            SystemMessage(content=prompt),
        ]
    response = chat_model.invoke(messages)
    content = response.content

    # 1. Clean Markdown backticks if the model included them
    if content.startswith("```"):
        content = re.sub(r'^```json\s*|```$', '', content, flags=re.MULTILINE).strip()

    try:
        queries = json.loads(content)
        if queries:
            return queries
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        return None
    return None


## STEP:4 Job Searching
def jobs_searching(queries, results_wanted=15):
    all_results = []
    for q in queries:
        try:
            jobs = scrape_jobs(
                site_name=["indeed", "linkedin", "glassdoor", "naukri", "google","zip_recruiter"],
                search_term=q["search_term"],
                location= location,
                results_wanted=results_wanted,
                country_indeed=country,  # Crucial for India-specific Indeed/Glassdoor
                hours_old=hours_old,          
            )
            
            if not jobs.empty:
                # Convert DataFrame to list of dicts
                all_results.extend(jobs.to_dict('records'))
        except Exception as e:
            print(f"Error fetching from portals for query '{q}': {e}")

    urls = []
    for result in all_results:
        urls.append(result["job_url"])
    return urls 

## STEP:5 Remote Job Searching
def remote_jobs_searching(queries, results_wanted=15):
    all_results = []
    for q in queries:
        try:
            jobs = scrape_jobs(
                site_name=["indeed", "linkedin", "glassdoor", "naukri", "google","zip_recruiter"],
                search_term=q["search_term"],
                location= location,
                results_wanted=results_wanted,
                country_indeed=country,  # Crucial for India-specific Indeed/Glassdoor
                hours_old=hours_old,
                is_remote=True          
            )
            
            if not jobs.empty:
                # Convert DataFrame to list of dicts
                all_results.extend(jobs.to_dict('records'))
        except Exception as e:
            print(f"Error fetching from portals for query '{q}': {e}")

    urls = []
    for result in all_results:
        urls.append(result["job_url"])
    return urls

## STEP:6 Evaluating Job Matching URLs
def process_job_matching(resume_data, urls, platform, progress_callback=None):
    if platform == "openrouter":
        return _process_job_matching_open_router(platform,resume_data, urls, progress_callback)
    
    elif platform == "groq":
        return _process_groq_job_matching(platform,resume_data, urls, progress_callback)
    
    else:
        return _process_job_matching_transformers(resume_data, urls, progress_callback)
    

def _get_model(platform):
    if platform == "openrouter":
        return "meta-llama/llama-3.3-70b-instruct:free"
    elif platform == "groq":
        return "llama-3.3-70b-versatile"
    else:
        return "transformers"

def _process_job_matching_open_router(platform,resume_data, urls, progress_callback=None):
    # 1. Parallel Scraping
    number_of_workers = len(urls)
    
    if progress_callback:
        progress_callback('ranking', f'Scraping {len(urls)} job descriptions...', 75)
    
    print(f"Starting parallel scraping with {number_of_workers} workers...")
    with ThreadPoolExecutor(max_workers=number_of_workers) as executor:
        descriptions = list(executor.map(_scrape_url_linkedin, urls))
    
    # Create List of valid jobs: [{"url": u, "description": d}, ...]
    valid_jobs = [{"url": u, "description": d} for u, d in zip(urls, descriptions) if d]
    total_jobs = len(valid_jobs)
    
    if progress_callback:
        progress_callback('ranking', f'Scraped {total_jobs} jobs successfully', 80)
    
    print(f"Scraped {total_jobs} valid jobs.")
    if total_jobs == 0:
        return pd.DataFrame()
    # 2. Split into 5 Equal Chunks
    # We aim for exactly 5 chunks.
    num_chunks = 5
    if total_jobs < num_chunks:
        chunk_size = 1
    else:
        chunk_size = math.ceil(total_jobs / num_chunks)
    
    chunks = []
    for i in range(0, total_jobs, chunk_size):
        chunks.append(valid_jobs[i:i + chunk_size])
        
    print(f"Split jobs into {len(chunks)} batches for LLM processing.")
    
    all_results = []
    
    # 3. Process each batch
    for i, batch in enumerate(chunks, 1):
        # Calculate progress for this batch (80% to 95% range = 15% total)
        progress_per_batch = 15 / len(chunks)
        current_progress = 80 + int((i - 1) * progress_per_batch)
        
        if progress_callback:
            progress_callback('ranking', f'Processing batch {i}/{len(chunks)} ({len(batch)} jobs)...', current_progress)
        
        print(f"\n--- Processing Batch {i}/{len(chunks)} ({len(batch)} jobs) ---")
        
        batch_scores = _process_batch_suitability(platform,resume_data, batch)
        
        
        # Print URL and Score for the user (and map score back to proper list)
        for job_item in batch:
            # Find score in results, default to 0
            u = job_item['url']
            score = 0
            skills_score = 0
            location_score = 0
            # Look for the score in the batch_scores list returned by LLM
            found = next((res for res in batch_scores if res.get('url') == u), None)
            if found:
                score = found.get('score', 0)
                skills_score = found.get('skills_score', 0)
                location_score = found.get('location_score', 0)
            
            #print(f"URL: {u} | Score: {score}")
            all_results.append({
                "url": u, 
                "score": score, 
                "skills_score": skills_score,
                "location_score": location_score
            })
    # 4. Ranking
    if not all_results:
        print("No results generated.")
        return pd.DataFrame()
    df = pd.DataFrame(all_results)
    # Ensure score execution
    df["score"] = pd.to_numeric(df["score"], errors='coerce').fillna(0)
    
    df = df.sort_values(by="score", ascending=False).reset_index(drop=True)
    df.index += 1
    df.index.name = "Rank"
    
    return df

def _process_groq_job_matching(platform,resume_data, urls, progress_callback=None):
    # 1. Parallel Scraping
    number_of_workers = len(urls)
    
    if progress_callback:
        progress_callback('ranking', f'Scraping {len(urls)} job descriptions...', 75)
    
    print(f"Starting parallel scraping with {number_of_workers} workers...")
    with ThreadPoolExecutor(max_workers=number_of_workers) as executor:
        descriptions = list(executor.map(_scrape_url_linkedin, urls))
    
    # Create List of valid jobs: [{"url": u, "description": d}, ...]
    valid_jobs = [{"url": u, "description": d} for u, d in zip(urls, descriptions) if d]
    total_jobs = len(valid_jobs)
    
    if progress_callback:
        progress_callback('ranking', f'Scraped {total_jobs} jobs successfully', 80)
    
    print(f"Scraped {total_jobs} valid jobs.")
    if total_jobs == 0:
        return pd.DataFrame()
    
    # 2. Split into chunks of 5 jobs each
    chunk_size = 5
    chunks = []
    for i in range(0, total_jobs, chunk_size):
        chunks.append(valid_jobs[i:i + chunk_size])
        
    print(f"Split jobs into {len(chunks)} batches for LLM processing (5 jobs per batch).")
    
    all_results = []
    
    # 3. Process each batch
    for i, batch in enumerate(chunks, 1):
        # Calculate progress for this batch (80% to 95% range = 15% total)
        progress_per_batch = 15 / len(chunks)
        current_progress = 80 + int((i - 1) * progress_per_batch)
        
        if progress_callback:
            progress_callback('ranking', f'Processing batch {i}/{len(chunks)} ({len(batch)} jobs)...', current_progress)
        
        print(f"\n--- Processing Batch {i}/{len(chunks)} ({len(batch)} jobs) ---")
        
        batch_scores = _process_batch_suitability(platform,resume_data, batch)
        
        # Print URL and Score for the user (and map score back to proper list)
        for job_item in batch:
            # Find score in results, default to 0
            u = job_item['url']
            score = 0
            # Look for the score in the batch_scores list returned by LLM
            found = next((res for res in batch_scores if res.get('url') == u), None)
            if found:
                score = found.get('score', 0)
            
            #print(f"URL: {u} | Score: {score}")
            all_results.append({"url": u, "score": score})
    
    # 4. Ranking
    if not all_results:
        print("No results generated.")
        return pd.DataFrame()
    
    df = pd.DataFrame(all_results)
    # Ensure score execution
    df["score"] = pd.to_numeric(df["score"], errors='coerce').fillna(0)
    
    df = df.sort_values(by="score", ascending=False).reset_index(drop=True)
    df.index += 1
    df.index.name = "Rank"
    
    return df

def _process_job_matching_transformers(resume_data, urls, progress_callback=None):
    # 1. Parallel Scraping
    number_of_workers = len(urls)
    
    if progress_callback:
        progress_callback('ranking', f'Scraping {len(urls)} job descriptions...', 75)
    
    print(f"Starting parallel scraping with {number_of_workers} workers...")
    with ThreadPoolExecutor(max_workers=number_of_workers) as executor:
        descriptions = list(executor.map(_scrape_url_linkedin, urls))
    
    # Create List of valid jobs: [{"url": u, "description": d}, ...]
    valid_jobs = [{"url": u, "description": d} for u, d in zip(urls, descriptions) if d]
    total_jobs = len(valid_jobs)
    
    if progress_callback:
        progress_callback('ranking', f'Scraped {total_jobs} jobs successfully', 80)
    
    print(f"Scraped {total_jobs} valid jobs.")
    if total_jobs == 0:
        return pd.DataFrame()
    
    # 2. Split into chunks of 5 jobs each
    chunk_size = 5
    chunks = []
    for i in range(0, total_jobs, chunk_size):
        chunks.append(valid_jobs[i:i + chunk_size])
        
    print(f"Split jobs into {len(chunks)} batches for LLM processing (5 jobs per batch).")
    
    all_results = []
    
    # 3. Process each batch
    for i, batch in enumerate(chunks, 1):
        # Calculate progress for this batch (80% to 95% range = 15% total)
        progress_per_batch = 15 / len(chunks)
        current_progress = 80 + int((i - 1) * progress_per_batch)
        
        if progress_callback:
            progress_callback('ranking', f'Processing batch {i}/{len(chunks)} ({len(batch)} jobs)...', current_progress)
        
        print(f"\n--- Processing Batch {i}/{len(chunks)} ({len(batch)} jobs) ---")
        
        batch_scores = _process_transformer_batch_suitability(resume_data, batch)
        
        # Print URL and Score for the user (and map score back to proper list)
        for job_item in batch:
            # Find score in results, default to 0
            u = job_item['url']
            score = 0
            # Look for the score in the batch_scores list returned by LLM
            found = next((res for res in batch_scores if res.get('url') == u), None)
            if found:
                score = found.get('score', 0)
            
            #print(f"URL: {u} | Score: {score}")
            all_results.append({"url": u, "score": score})
    
    # 4. Ranking
    if not all_results:
        print("No results generated.")
        return pd.DataFrame()
    
    df = pd.DataFrame(all_results)
    # Ensure score execution
    df["score"] = pd.to_numeric(df["score"], errors='coerce').fillna(0)
    
    df = df.sort_values(by="score", ascending=False).reset_index(drop=True)
    df.index += 1
    df.index.name = "Rank"
    
    return df

def _process_transformer_batch_suitability(resume, job_chunk):
    """
    Sends a batch of jobs to a local transformer model and returns a list of {url, score, skills_score, location_score}.
    """
    # Convert job chunk to JSON string for the prompt
    jobs_json = json.dumps(job_chunk, indent=2)
    
    # Use simplified prompt for small transformer models
    prompt_file_name = "ranking_urls_simple.jinja2"
    arguments = {
        "resume": resume,
        "jobs_json": jobs_json
    }
    
    # Initialize transformer model with very low temperature for deterministic JSON
    chat_model, prompt_content = LLM.get_llm_model_without_tools(
        "transformer", 
        "Qwen/Qwen2.5-1.5B-Instruct", 
        0.01,  # Very low temperature for structured output
        prompt_file_name, 
        arguments
    )
    
    messages = [
        SystemMessage(content=prompt_content),
    ]
    
    # Debug: Print prompt length
    print(f"\n=== TRANSFORMER MODEL DEBUG ===")
    print(f"Prompt length: {len(prompt_content)} characters")
    print(f"Number of jobs in batch: {len(job_chunk)}")
    print(f"First 500 chars of prompt:\n{prompt_content[:500]}...")
    
    try:
        # Generate response with transformer model
        response = chat_model.generate_response(messages, temperature=0.01, max_new_tokens=4096)
        
        print(f"\n=== RAW RESPONSE ===")
        print(response)
        print(f"=== END RAW RESPONSE ===\n")
        
        # Try to extract JSON from response
        content = response.strip()
        
        # Clean potential markdown formatting
        if content.startswith("```"):
            content = content.replace("```json", "").replace("```", "").strip()
        
        # Try to parse JSON
        try:
            results = json.loads(content)
            print(f"✅ Successfully parsed {len(results)} job scores from transformer model")
            return results
        except json.JSONDecodeError as json_err:
            print(f"⚠️ JSON parsing failed: {json_err}")
            print(f"Attempting to extract JSON from response...")
            
            # Try to find JSON array in the response
            extracted = _extract_and_parse_json(content)
            if extracted and isinstance(extracted, list):
                print(f"✅ Extracted {len(extracted)} results using fallback parser")
                return extracted
            else:
                print(f"❌ Could not extract valid JSON array from response")
                return []
            
    except Exception as e:
        print(f"❌ Error processing transformer batch: {e}")
        import traceback
        traceback.print_exc()
        return []           

def _scrape_url_linkedin(url):
    app = FirecrawlApp(api_url='http://localhost:3002', api_key='test-key')
    
    max_retries = 3
    MIN_CONTENT = 50  # ← ADD THIS
    
    for attempt in range(max_retries):
        try:
            start_time = time.time()
            result = app.scrape(url, formats=['markdown'], 
                              timeout=120000,  # ← CHANGE from 60000
                              wait_for=5000)
            
            if hasattr(result, 'markdown') and result.markdown:
                # ← ADD CONTENT VALIDATION
                if len(result.markdown) >= MIN_CONTENT:
                    elapsed = time.time() - start_time
                    print(f"✅ Scrape successful! (took {elapsed:.2f}s)")
                    return result.markdown
                else:
                    # Content too short - retry
                    print(f"⚠️  Attempt {attempt+1}: Content too short ({len(result.markdown)} chars)")
                    if attempt < max_retries - 1:
                        time.sleep(5 * (attempt + 1))  # ← CHANGE to exponential
                        continue  # ← ADD explicit continue
                        
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(5 * (attempt + 1))  # ← CHANGE to exponential
                continue
            print(f"❌ Error: {str(e)} | URL: {url}")
            return None
    
    print(f"❌ Failed after {max_retries} attempts | URL: {url}")
    return None     
    

def _process_batch_suitability(platform,resume, job_chunk):
    """
    Sends a batch of jobs to the LLM and returns a list of {url, score, skills_score, location_score}.
    """
    # Convert job chunk to JSON string for the prompt
    jobs_json = json.dumps(job_chunk, indent=2)
    
    prompt_file_name = "ranking_urls.jinja2"
    arguments = {
        "resume": resume,
        "jobs_json": jobs_json
    }
    model = _get_model(platform)
    # Initialize LLM
    # Using temperature 0.1 for more consistent, deterministic JSON output
    chat_model, prompt_content = LLM.get_llm_model_without_tools(
        platform, 
        model, 
        0.1,  
        prompt_file_name, 
        arguments
    )
    
    messages = [
        SystemMessage(content=prompt_content),
    ]
    
    # LLM Call (1 call per batch)
    try:
        response = chat_model.invoke(messages)
        content = response.content.strip()
        
        # Clean potential markdown formatting
        if content.startswith("```"):
            content = content.replace("```json", "").replace("```", "")
        
        results = json.loads(content.strip())
        return results
    except Exception as e:
        print(f"Error processing batch: {e}")
        return []



def produce_ranked_jobs():
    print("Resume Summerizing")
    data = resume_summerize(platform,file_path)
    print("Adding Extra Info")
    data = adding_extra_info(data)
    print("Detecting Search Queries")
    queries = detecting_search_queries(platform,data)
    print("Job Searching")
    job_urls = []
    urls = jobs_searching(queries)
    job_urls.extend(urls)
    print("Remote Job Searching")
    urls = remote_jobs_searching(queries)
    job_urls.extend(urls)
    print("Job Matching")
    ranked_jobs = process_job_matching(data, job_urls,platform)
    return ranked_jobs

if __name__ == "__main__":
  ranked_jobs = produce_ranked_jobs()
  # Print each ranked job's URL and score
  print("\n" + "="*80)
  print("RANKED JOBS - URL and Score:")
  print("="*80)
  for idx, row in ranked_jobs.iterrows():
    print(f"Rank: {idx} | Score: {row['score']:>6.2f} | Skills Score: {row['skills_score']:>6.2f} | Location Score: {row['location_score']:>6.2f} | URL: {row['url']}")
  print("="*80)
  print(f"Total ranked jobs: {len(ranked_jobs)}")    

