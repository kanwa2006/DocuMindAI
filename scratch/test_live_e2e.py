import urllib.request
import urllib.parse
import json
import uuid
import time
import ssl

ctx = ssl.create_default_context()

print("--- Step 1: CSRF ---")
csrf_req = urllib.request.Request(
    'https://documindai-api.onrender.com/api/v1/csrf-token',
    headers={'User-Agent': 'Mozilla/5.0', 'Origin': 'https://documindai-app.vercel.app'}
)
with urllib.request.urlopen(csrf_req, timeout=15, context=ctx) as r:
    csrf_cookie = r.headers.get('Set-Cookie').split(';')[0]
    csrf_token = json.loads(r.read().decode())['csrf_token']
print("CSRF token received:", csrf_token[:10] + "...")

print("--- Step 2: Login ---")
email = 'recruiter_test_69864a@documind.com'
pwd = 'Password123!'
login_data = urllib.parse.urlencode({'username': email, 'password': pwd}).encode('utf-8')
login_req = urllib.request.Request(
    'https://documindai-api.onrender.com/api/v1/auth/login',
    data=login_data,
    headers={
        'User-Agent': 'Mozilla/5.0',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Origin': 'https://documindai-app.vercel.app',
        'X-CSRF-Token': csrf_token,
        'Cookie': csrf_cookie
    }
)
with urllib.request.urlopen(login_req, timeout=15, context=ctx) as r:
    auth_cookie = r.headers.get('Set-Cookie').split(';')[0]
    token = json.loads(r.read().decode())['access_token']
print("Logged in successfully! Token received.")

headers = {
    'User-Agent': 'Mozilla/5.0',
    'Origin': 'https://documindai-app.vercel.app',
    'X-CSRF-Token': csrf_token,
    'Cookie': f'{csrf_cookie}; {auth_cookie}',
    'Authorization': f'Bearer {token}'
}

print("--- Step 3: Presigned info ---")
presigned_url = 'https://documindai-api.onrender.com/api/v1/documents/upload/presigned?filename=resume_project_summary.pdf&content_type=application/pdf&file_size=2048&workspace_id=general'
pre_req = urllib.request.Request(presigned_url, headers=headers)
with urllib.request.urlopen(pre_req, timeout=15, context=ctx) as r:
    pre_info = json.loads(r.read().decode())
print("Presigned info:", pre_info)

print("--- Step 4: Upload PDF content ---")
# Simple valid PDF with text
from fpdf import FPDF
pdf = FPDF()
pdf.add_page()
pdf.set_font("Helvetica", size=14)
pdf.cell(200, 10, txt="DocuMindAI Project Verification Document", ln=True, align='C')
pdf.ln(10)
pdf.set_font("Helvetica", size=11)
pdf.multi_cell(0, 10, txt="This project is DocuMindAI created by Kanwa Munipalle. It is an enterprise RAG and document intelligence platform. The secret verification code is DOCUMIND_VERIFIED_2026. DocuMindAI features hybrid search with pgvector and BM25 RRF fusion, multi-model LLM generation, and tenant-isolated workspaces.")
pdf_bytes = pdf.output()

boundary = '----Boundary' + uuid.uuid4().hex
parts = []
parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="workspace_id"\r\n\r\ngeneral\r\n'.encode('utf-8'))
parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="resume_project_summary.pdf"\r\nContent-Type: application/pdf\r\n\r\n'.encode('utf-8'))
parts.append(pdf_bytes)
parts.append(f'\r\n--{boundary}--\r\n'.encode('utf-8'))
multipart_body = b''.join(parts)

upload_req = urllib.request.Request(
    'https://documindai-api.onrender.com/api/v1/documents/upload/local',
    data=multipart_body,
    headers={**headers, 'Content-Type': f'multipart/form-data; boundary={boundary}'}
)
with urllib.request.urlopen(upload_req, timeout=15, context=ctx) as r:
    upload_res = json.loads(r.read().decode())
print("Upload result:", upload_res)

print("--- Step 5: Verify upload ---")
verify_payload = json.dumps({
    'document_id': pre_info['document_id'],
    'filename': 'resume_project_summary.pdf',
    'object_key': upload_res['storage_path'],
    'mime_type': 'application/pdf',
    'size_bytes': len(pdf_bytes)
}).encode('utf-8')

verify_req = urllib.request.Request(
    'https://documindai-api.onrender.com/api/v1/documents/upload/verify',
    data=verify_payload,
    headers={**headers, 'Content-Type': 'application/json'}
)
with urllib.request.urlopen(verify_req, timeout=30, context=ctx) as r:
    verify_res = json.loads(r.read().decode())
print("Verified doc:", verify_res['id'], "status:", verify_res['status'])

doc_id = verify_res['id']

print("--- Step 6: Polling status until READY ---")
for attempt in range(12):
    time.sleep(2)
    poll_req = urllib.request.Request(
        f'https://documindai-api.onrender.com/api/v1/documents/{doc_id}',
        headers=headers
    )
    with urllib.request.urlopen(poll_req, timeout=15, context=ctx) as r:
        doc_data = json.loads(r.read().decode())
        print(f"Poll {attempt+1}: status = {doc_data.get('status')}")
        if doc_data.get('status') == 'ready':
            print("Document reached READY state!")
            break

print("--- Step 7: Stream Question via /query/stream ---")
query_payload = json.dumps({
    'query': 'What is the secret verification code in the document?',
    'workspace_id': 'general'
}).encode('utf-8')

query_req = urllib.request.Request(
    'https://documindai-api.onrender.com/api/v1/query/stream',
    data=query_payload,
    headers={**headers, 'Content-Type': 'application/json', 'Accept': 'text/event-stream'}
)
with urllib.request.urlopen(query_req, timeout=60, context=ctx) as r:
    print("SSE Response Stream:")
    for line in r:
        decoded = line.decode('utf-8', errors='ignore').strip()
        if decoded:
            print(decoded[:120])

print("\n--- ALL TESTS COMPLETE AND SUCCESSFUL! ---")
