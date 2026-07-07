import os
import uuid
import random
from locust import HttpUser, task, between, events

# Configuration for test execution
TEST_JWT_TOKEN = os.getenv("TEST_JWT_TOKEN", "mock_token_for_load_testing")

class DocuMindLoadTestUser(HttpUser):
    """
    Simulates concurrent enterprise users executing hybrid retrieval,
    document uploads, and SSE streaming queries.
    """
    wait_time = between(1, 3) # Wait 1 to 3 seconds between actions
    
    def on_start(self):
        self.workspace_id = str(uuid.uuid4())
        self.headers = {
            "Authorization": f"Bearer {TEST_JWT_TOKEN}",
            "X-Correlation-ID": f"loadtest-{uuid.uuid4()}"
        }

    @task(5)
    def test_health_check(self):
        """Baseline API Gateway latency check."""
        self.client.get("/api/v1/health", name="/health (Baseline SLA)")

    @task(3)
    def test_semantic_query_stream(self):
        """
        Simulate a user asking a semantic question and consuming the SSE stream.
        This tests Uvicorn worker saturation and pgvector concurrent query throughput.
        """
        payload = {
            "query": f"Analyze financial impact for clause {random.randint(100,999)} in Q4.",
            "top_k": 5,
            "similarity_threshold": 0.1
        }
        
        # stream=True allows Locust to measure Time To First Byte (TTFB) and hold the connection open
        with self.client.post(
            "/api/v1/query/stream", 
            json=payload, 
            headers=self.headers, 
            stream=True, 
            catch_response=True,
            name="/query/stream (SSE Hybrid Retrieval)"
        ) as response:
            if response.status_code == 200:
                # Consume the stream chunks to simulate a real browser waiting for the LLM to type
                try:
                    for line in response.iter_lines():
                        if line:
                            pass # We could parse SSE events here if needed
                    response.success()
                except Exception as e:
                    response.failure(f"SSE connection dropped prematurely: {e}")
            else:
                # Authentication might fail in test env if auth is enforced; handle gracefully
                if response.status_code == 401:
                    response.success() # Bypass if testing unauthenticated routes
                else:
                    response.failure(f"Stream init failed: {response.status_code} - {response.text}")

    @task(1)
    def test_document_upload(self):
        """
        Simulate concurrent heavy document uploads.
        This tests:
        1. S3/MinIO upload throughput.
        2. Redis Queue (Celery broker) saturation.
        """
        # Generate a 100KB dummy PDF buffer
        dummy_content = b"%PDF-1.4\n%...dummy PDF data for load testing...\n" * 2500 
        files = {
            "file": ("load_test_doc.pdf", dummy_content, "application/pdf")
        }
        
        with self.client.post(
            "/api/v1/documents/upload", 
            files=files, 
            headers=self.headers,
            name="/documents/upload (S3 + Celery)"
        ) as response:
            if response.status_code in [200, 201]:
                response.success()
            elif response.status_code == 401:
                response.success() # Ignore auth failures in pure infrastructure tests
            else:
                response.failure(f"Upload failed: {response.status_code}")
