// State management
let currentJobId = null;
let eventSource = null;
let currentResults = null; // Store results for download

// DOM Elements
const uploadForm = document.getElementById('upload-form');
const resumeInput = document.getElementById('resume-input');
const dropZone = document.getElementById('drop-zone');
const fileInfo = document.getElementById('file-info');
const fileName = document.getElementById('file-name');
const removeFileBtn = document.getElementById('remove-file');
const submitBtn = document.getElementById('submit-btn');
const toggleAdvancedBtn = document.getElementById('toggle-advanced');
const advancedSettings = document.getElementById('advanced-settings');

const uploadSection = document.getElementById('upload-section');
const progressSection = document.getElementById('progress-section');
const resultsSection = document.getElementById('results-section');

const progressFill = document.getElementById('progress-fill');
const progressText = document.getElementById('progress-text');
const resultsBody = document.getElementById('results-body');
const resultsCount = document.getElementById('results-count');

// Download elements
const downloadBtn = document.getElementById('download-btn');
const formatDropdown = document.getElementById('format-dropdown');

// Platform selector elements
const platformSelect = document.getElementById('platform');
const transformerWarning = document.getElementById('transformer-warning');

// Platform selector warning logic
platformSelect.addEventListener('change', function () {
    if (this.value === 'transformers') {
        transformerWarning.classList.remove('hidden');
    } else {
        transformerWarning.classList.add('hidden');
    }
});


// File upload handling
dropZone.addEventListener('click', () => {
    resumeInput.click();
});

dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('drag-over');
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('drag-over');
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('drag-over');

    const files = e.dataTransfer.files;
    if (files.length > 0 && files[0].type === 'application/pdf') {
        resumeInput.files = files;
        handleFileSelect(files[0]);
    } else {
        alert('Please upload a PDF file');
    }
});

resumeInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        handleFileSelect(e.target.files[0]);
    }
});

removeFileBtn.addEventListener('click', () => {
    resumeInput.value = '';
    dropZone.classList.remove('hidden');
    fileInfo.classList.add('hidden');
    submitBtn.disabled = true;
});

function handleFileSelect(file) {
    if (file.type !== 'application/pdf') {
        alert('Please select a PDF file');
        return;
    }

    fileName.textContent = file.name;
    dropZone.classList.add('hidden');
    fileInfo.classList.remove('hidden');
    submitBtn.disabled = false;
}

// Advanced settings toggle
toggleAdvancedBtn.addEventListener('click', () => {
    advancedSettings.classList.toggle('hidden');
    toggleAdvancedBtn.classList.toggle('active');
});

// Form submission
uploadForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const formData = new FormData(uploadForm);

    // Disable form
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="btn-text">Processing...</span>';

    try {
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.error) {
            alert('Error: ' + data.error);
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<span class="btn-text">🚀 Find My Perfect Jobs</span>';
            return;
        }

        currentJobId = data.job_id;

        // Show progress section
        uploadSection.classList.add('hidden');
        progressSection.classList.remove('hidden');

        // Start listening to progress updates
        startProgressStream(currentJobId);

    } catch (error) {
        console.error('Upload error:', error);
        alert('Failed to upload file. Please try again.');
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<span class="btn-text">🚀 Find My Perfect Jobs</span>';
    }
});

// Progress streaming
function startProgressStream(jobId) {
    eventSource = new EventSource(`/status/${jobId}`);

    eventSource.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);

            if (data.keepalive) {
                return; // Ignore keepalive messages
            }

            if (data.error) {
                console.error('Stream error:', data.error);
                eventSource.close();
                alert('Error: ' + data.error);
                return;
            }

            updateProgress(data);

            if (data.step === 'complete') {
                eventSource.close();
                loadResults(jobId);
            }

            if (data.step === 'error') {
                eventSource.close();
                alert('Processing failed: ' + data.message);
            }

        } catch (error) {
            console.error('Error parsing progress data:', error);
        }
    };

    eventSource.onerror = (error) => {
        console.error('EventSource error:', error);
        eventSource.close();
    };
}

function updateProgress(data) {
    const { step, message, progress } = data;

    // Update overall progress bar
    progressFill.style.width = `${progress}%`;
    progressText.textContent = `${progress}%`;

    // Update step status
    const stepElement = document.querySelector(`[data-step="${step}"]`);
    if (stepElement) {
        const messageElement = stepElement.querySelector('.step-message');
        messageElement.textContent = message;

        // Mark as active
        document.querySelectorAll('.progress-step').forEach(el => {
            el.classList.remove('active');
        });
        stepElement.classList.add('active');

        // Mark previous steps as completed
        let currentStepFound = false;
        document.querySelectorAll('.progress-step').forEach(el => {
            if (el === stepElement) {
                currentStepFound = true;
            } else if (!currentStepFound) {
                el.classList.add('completed');
            }
        });
    }

    // Mark complete step
    if (step === 'complete') {
        document.querySelectorAll('.progress-step').forEach(el => {
            el.classList.add('completed');
            el.classList.remove('active');
        });
    }
}

async function loadResults(jobId) {
    try {
        const response = await fetch(`/results/${jobId}`);
        const data = await response.json();

        if (data.error) {
            alert('Error loading results: ' + data.error);
            return;
        }

        displayResults(data.results);

        // Show results section
        progressSection.classList.add('hidden');
        resultsSection.classList.remove('hidden');

        // Scroll to results
        resultsSection.scrollIntoView({ behavior: 'smooth' });

    } catch (error) {
        console.error('Error loading results:', error);
        alert('Failed to load results');
    }
}

function displayResults(results) {
    resultsBody.innerHTML = '';

    // Filter out jobs with 0 scores
    const validResults = results.filter(job => job.score > 0);

    // Store results globally for download
    currentResults = validResults;

    resultsCount.textContent = `Found ${validResults.length} matching jobs`;

    validResults.forEach((job, index) => {
        const rank = index + 1;
        const row = document.createElement('tr');

        // Determine rank badge class
        let rankClass = 'rank-default';
        if (rank === 1) rankClass = 'rank-1';
        else if (rank === 2) rankClass = 'rank-2';
        else if (rank === 3) rankClass = 'rank-3';

        // Determine score class
        let scoreClass = 'score-low';
        if (job.score >= 70) scoreClass = 'score-high';
        else if (job.score >= 40) scoreClass = 'score-medium';

        // Extract domain from URL
        let displayUrl = job.url;
        try {
            const urlObj = new URL(job.url);
            displayUrl = urlObj.hostname.replace('www.', '') + urlObj.pathname.substring(0, 30) + '...';
        } catch (e) {
            // Keep original URL if parsing fails
        }

        row.innerHTML = `
            <td>
                <div class="rank-badge ${rankClass}">${rank}</div>
            </td>
            <td>
                <div class="score-bar">
                    <div class="score-progress">
                        <div class="score-progress-fill ${scoreClass}" style="width: ${job.score}%"></div>
                    </div>
                    <span class="score-value">${job.score}</span>
                </div>
            </td>
            <td><span class="skill-score">${job.skills_score || 0}</span></td>
            <td><span class="location-score">${job.location_score || 0}</span></td>
            <td>
                <a href="${job.url}" target="_blank" rel="noopener noreferrer" class="job-link" title="${job.url}">
                    ${displayUrl}
                </a>
            </td>
        `;

        resultsBody.appendChild(row);
    });
}

// Download functionality
function downloadAsCSV() {
    if (!currentResults || currentResults.length === 0) return;

    // Create CSV header
    let csv = 'Rank,Overall Score,Skills Score,Location Score,Job URL\n';

    // Add data rows
    currentResults.forEach((job, index) => {
        const rank = index + 1;
        const row = [
            rank,
            job.score,
            job.skills_score || 0,
            job.location_score || 0,
            `"${job.url}"` // Quote URL to handle commas
        ].join(',');
        csv += row + '\n';
    });

    downloadFile(csv, 'job-matches.csv', 'text/csv');
}

function downloadAsTXT() {
    if (!currentResults || currentResults.length === 0) return;

    const timestamp = new Date().toLocaleString();
    let txt = '═══════════════════════════════════════════════════════\n';
    txt += '           AI JOB MATCHER - RESULTS REPORT\n';
    txt += '═══════════════════════════════════════════════════════\n';
    txt += `Generated: ${timestamp}\n`;
    txt += `Total Matches: ${currentResults.length}\n`;
    txt += '═══════════════════════════════════════════════════════\n\n';

    currentResults.forEach((job, index) => {
        const rank = index + 1;
        txt += `─────────────────────────────────────────────────────\n`;
        txt += `RANK #${rank}\n`;
        txt += `─────────────────────────────────────────────────────\n`;
        txt += `Overall Score:    ${job.score}/100\n`;
        txt += `Skills Match:     ${job.skills_score || 0}/10\n`;
        txt += `Location Match:   ${job.location_score || 0}/10\n`;
        txt += `Job URL:          ${job.url}\n\n`;
    });

    txt += '═══════════════════════════════════════════════════════\n';
    txt += '              END OF REPORT\n';
    txt += '═══════════════════════════════════════════════════════\n';

    downloadFile(txt, 'job-matches.txt', 'text/plain');
}

function downloadAsJSON() {
    if (!currentResults || currentResults.length === 0) return;

    const data = {
        generated_at: new Date().toISOString(),
        total_results: currentResults.length,
        jobs: currentResults.map((job, index) => ({
            rank: index + 1,
            overall_score: job.score,
            skills_score: job.skills_score || 0,
            location_score: job.location_score || 0,
            url: job.url
        }))
    };

    const json = JSON.stringify(data, null, 2);
    downloadFile(json, 'job-matches.json', 'application/json');
}

function downloadFile(content, filename, mimeType) {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
}

// Download button event listeners
if (downloadBtn) {
    downloadBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        formatDropdown.classList.toggle('hidden');
    });
}

// Format selection event listeners
if (formatDropdown) {
    formatDropdown.querySelectorAll('.format-option').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const format = btn.getAttribute('data-format');

            if (format === 'csv') downloadAsCSV();
            else if (format === 'txt') downloadAsTXT();
            else if (format === 'json') downloadAsJSON();

            formatDropdown.classList.add('hidden');
        });
    });
}

// Close dropdown when clicking outside
document.addEventListener('click', (e) => {
    if (formatDropdown && !formatDropdown.classList.contains('hidden')) {
        if (!e.target.closest('.download-container')) {
            formatDropdown.classList.add('hidden');
        }
    }
});

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    console.log('AI Job Matcher initialized');
});
