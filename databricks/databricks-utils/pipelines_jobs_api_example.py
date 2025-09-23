import os
import requests

# Databricks credentials
host = "https://your-workspace.cloud.databricks.com"
token = "your-databricks-token"

headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json'
}

# Example 1: Start pipeline update
pipeline_id = "your-pipeline-id"
pipeline_url = f"{host}/api/2.0/pipelines/{pipeline_id}/updates"
pipeline_response = requests.post(pipeline_url, headers=headers)
print(f"Pipeline update response: {pipeline_response.json()}")

# Example 2: Run job now
job_id = "your-job-id"
job_url = f"{host}/api/2.1/jobs/run-now"
job_data = {"job_id": job_id}
job_response = requests.post(job_url, headers=headers, json=job_data)
print(f"Job run response: {job_response.json()}")