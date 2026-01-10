from flask import Flask, render_template, request, jsonify, Response
from flask_cors import CORS
import os
import uuid
import json
import threading
from werkzeug.utils import secure_filename
import time
from queue import Queue
from typing import Optional, Dict, Any

# Import existing logic
from main import (
    _extract_pdf_content,
    resume_summerize as original_resume_summerize,
    adding_extra_info,
    detecting_search_queries,
    jobs_searching,
    remote_jobs_searching,
    process_job_matching
)

app = Flask(__name__)
CORS(app)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Preload TransformerModels to avoid first-request latency
#print("Loading TransformerModels...")
#from models.transformer_models import TransformerModels
#transformer_model = TransformerModels("Qwen/Qwen2.5-1.5B-Instruct")
#print("TransformerModels loaded successfully!")

# Store job processing status
job_status = {}
job_results = {}
progress_queues = {}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'pdf'


def emit_progress(job_id: str, step: str, message: str, progress: int):
    """Emit progress update to the queue"""
    if job_id in progress_queues:
        progress_queues[job_id].put({
            'step': step,
            'message': message,
            'progress': progress
        })


def process_job_async(job_id: str, file_path: str, location: str, country: str, 
                     max_queries: int, hours_old: int, platform: str):
    """Background job processing with progress tracking"""
    try:
        emit_progress(job_id, 'resume_analysis', 'Extracting and summarizing resume...', 10)
        
        # Step 1: Resume Summarization
        from main import resume_summerize
        
        data = resume_summerize(platform, file_path)
        emit_progress(job_id, 'resume_analysis', 'Resume analyzed successfully!', 20)
        
        # Step 2: Add extra info
        emit_progress(job_id, 'enrichment', 'Enriching resume data...', 25)
        data["location"] = location
        data["JobType"] = "fulltime"
        data["Country"] = country
        emit_progress(job_id, 'enrichment', 'Data enriched successfully!', 30)
        
        # Step 3: Generate search queries
        emit_progress(job_id, 'queries', 'Generating optimized search queries...', 35)
        queries = detecting_search_queries(platform, data, max_queries)
        emit_progress(job_id, 'queries', f'Generated {len(queries)} search queries', 40)
        
        # Step 4: Job searching
        emit_progress(job_id, 'job_search', 'Searching job portals...', 45)
        job_urls = []
        urls = jobs_searching(queries)
        job_urls.extend(urls)
        emit_progress(job_id, 'job_search', f'Found {len(urls)} regular jobs', 55)
        
        # Step 5: Remote job searching
        emit_progress(job_id, 'remote_search', 'Searching remote opportunities...', 60)
        urls = remote_jobs_searching(queries)
        job_urls.extend(urls)
        emit_progress(job_id, 'remote_search', f'Found {len(urls)} remote jobs. Total: {len(job_urls)}', 70)
        
        # Step 6: Scraping and ranking
        emit_progress(job_id, 'ranking', f'Scraping and ranking {len(job_urls)} job descriptions...', 75)
        
        # Create a progress callback wrapper that includes job_id
        def ranking_progress(step, message, progress):
            emit_progress(job_id, step, message, progress)
        
        ranked_jobs = process_job_matching(data, job_urls, platform, progress_callback=ranking_progress)
        
        emit_progress(job_id, 'ranking', 'Ranking complete!', 95)
        
        # Convert DataFrame to list of dicts
        results = ranked_jobs.to_dict('records')
        
        # Store results
        job_results[job_id] = results
        job_status[job_id] = 'completed'
        
        emit_progress(job_id, 'complete', f'Successfully ranked {len(results)} jobs!', 100)
        
        # Cleanup uploaded file
        if os.path.exists(file_path):
            os.remove(file_path)
            
    except Exception as e:
        job_status[job_id] = 'failed'
        emit_progress(job_id, 'error', f'Error: {str(e)}', 0)
        print(f"Error processing job {job_id}: {e}")


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and start processing"""
    
    if 'resume' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['resume']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Only PDF files are allowed'}), 400
    
    # Get form parameters
    location = request.form.get('location', 'Hyderabad')
    country = request.form.get('country', 'India')
    max_queries = int(request.form.get('max_queries', 10))
    hours_old = int(request.form.get('hours_old', 168))
    platform = request.form.get('platform', 'groq')  # Get platform from form
    
    # Save file
    filename = secure_filename(file.filename)
    job_id = str(uuid.uuid4())
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{job_id}_{filename}")
    file.save(file_path)
    
    # Initialize job tracking
    job_status[job_id] = 'processing'
    progress_queues[job_id] = Queue()
    
    # Start background processing
    thread = threading.Thread(
        target=process_job_async,
        args=(job_id, file_path, location, country, max_queries, hours_old, platform)
    )
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'job_id': job_id,
        'status': 'processing',
        'message': 'Job processing started'
    })


@app.route('/status/<job_id>')
def stream_status(job_id):
    """Stream progress updates via Server-Sent Events"""
    
    def generate():
        while True:
            if job_id not in progress_queues:
                yield f"data: {json.dumps({'error': 'Job not found'})}\n\n"
                break
            
            try:
                # Wait for progress update with timeout
                update = progress_queues[job_id].get(timeout=1)
                yield f"data: {json.dumps(update)}\n\n"
                
                # If job is complete or failed, close stream
                if update['step'] in ['complete', 'error']:
                    break
                    
            except:
                # Send keepalive
                yield f"data: {json.dumps({'keepalive': True})}\n\n"
                
                # Check if job finished
                if job_id in job_status and job_status[job_id] in ['completed', 'failed']:
                    break
    
    return Response(generate(), mimetype='text/event-stream')


@app.route('/results/<job_id>')
def get_results(job_id):
    """Get final results for a job"""
    
    if job_id not in job_status:
        return jsonify({'error': 'Job not found'}), 404
    
    if job_status[job_id] == 'processing':
        return jsonify({'status': 'processing'}), 202
    
    if job_status[job_id] == 'failed':
        return jsonify({'error': 'Job processing failed'}), 500
    
    if job_id not in job_results:
        return jsonify({'error': 'Results not available'}), 404
    
    return jsonify({
        'status': 'completed',
        'results': job_results[job_id]
    })


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)
