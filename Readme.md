# AI-Powered Job Matcher

An intelligent job search and ranking system that analyzes resumes and automatically finds, scrapes, and ranks job postings based on skills and location match.

## Features

- 🤖 **AI-Powered Resume Analysis** - Extracts skills, experience, and qualifications
- 🔍 **Multi-Portal Job Search** - Searches Indeed, LinkedIn, Glassdoor, Naukri, Google, ZipRecruiter
- 📊 **Intelligent Ranking** - Scores jobs based on skills (70%) and location (30%)
- 🌐 **Modern Web UI** - Beautiful dark mode interface with real-time progress tracking
- ⚡ **Parallel Processing** - Fast job scraping using ThreadPoolExecutor

## Prerequisites

- Python 3.8+
- Firecrawl instance running (for job description scraping)
- OpenRouter API key (for LLM)

## Setup

### 1. Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt
```

### 2. Environment Variables

Create a `.env` file in the project root:

```
OPENROUTER_API_KEY=your_api_key_here
```

### 3. Start Firecrawl (if self-hosted)

```bash
kubectl port-forward -n firecrawl svc/firecrawl-firecrawl-api 3002:3002
```

## Running the Application

### Web UI (Recommended)

1. Start the Flask server:
```bash
python3 app.py
```

2. Open your browser and navigate to:
```
http://localhost:5000
```

3. Upload your resume (PDF), select location, and click "Find My Perfect Jobs"!

### Command Line

```bash
python3 main.py
```

## How It Works

1. **Resume Analysis** - Extracts and summarizes resume content using LLM
2. **Query Generation** - Creates optimized search queries based on skills
3. **Job Discovery** - Searches 6+ job portals for relevant positions
4. **Web Scraping** - Fetches full job descriptions using Firecrawl
5. **AI Ranking** - Scores each job on skills match (0-70) and location match (0-30)
6. **Results Display** - Shows ranked jobs with clickable links

## Architecture

```
Frontend (HTML/CSS/JS) → Flask API → Background Processing
                                    ↓
                              LLM Analysis → Job Search → Ranking
```

## Technologies

- **Backend**: Flask, Python
- **Frontend**: Vanilla JS, CSS (Glassmorphism Design)
- **LLM**: Llama 3.3 70B via OpenRouter
- **Job Search**: JobSpy library
- **Web Scraping**: Firecrawl
- **Real-time Updates**: Server-Sent Events (SSE)

## Configuration

Edit `main.py` to customize:
- `max_search_queries`: Number of search queries (default: 10)
- `hours_old`: Job recency in hours (default: 168 = 7 days)
- Job portals to search
- LLM model and temperature

## License

MIT
