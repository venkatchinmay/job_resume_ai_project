from jobspy import scrape_jobs
import logging
import pandas as pd

# Configure logging to see the output from JobSpy
logging.basicConfig(level=logging.INFO)

print("Starting verification...")
try:
    # Use a search term that likely has few results to trigger the edge case
    # "API Developer Kafka" in Hyderabad might trigger it as per user logs
    jobs = scrape_jobs(
        site_name=["naukri"],
        search_term="API Developer Kafka",
        location="Hyderabad",
        results_wanted=30, # Request more than 20 to ensure it tries to page if we didn't fix it
        country_indeed="india",
        hours_old=168
    )
    print(f"Found {len(jobs)} jobs")
    if not jobs.empty:
        print(jobs[['title', 'company', 'job_url']].head())
except Exception as e:
    print(f"Verification failed with error: {e}")
