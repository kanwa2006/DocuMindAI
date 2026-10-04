import urllib.request
import urllib.parse
import json
import uuid
import ssl
from fpdf import FPDF

ctx = ssl.create_default_context()

csrf_req = urllib.request.Request(
    'https://documindai-api.onrender.com/api/v1/csrf-token',
    headers={'User-Agent': 'Mozilla/5.0', 'Origin': 'https://documindai-app.vercel.app'}
)
with urllib.request.urlopen(csrf_req, timeout=15, context=ctx) as r:
    csrf_cookie = r.headers.get('Set-Cookie').split(';')[0]
    csrf_token = json.loads(r.read().decode())['csrf_token']

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

headers = {
    'User-Agent': 'Mozilla/5.0',
    'Origin': 'https://documindai-app.vercel.app',
    'X-CSRF-Token': csrf_token,
    'Cookie': f'{csrf_cookie}; {auth_cookie}',
    'Authorization': f'Bearer {token}'
}

doc_id = str(uuid.uuid4())
pre_req = urllib.request.Request(
    f'https://documindai-api.onrender.com/api/v1/documents/upload/presigned?filename=test.pdf&content_type=application/pdf&file_size=500&workspace_id=general',
    headers=headers
)
with urllib.request.urlopen(pre_req, timeout=15, context=ctx) as r:
    pre_info = json.loads(r.read().decode())

pdf = FPDF()
pdf.add_page()
pdf.set_font('Helvetica', size=12)
pdf.cell(text='Hello DocuMindAI Verification')
pdf_bytes = bytes(pdf.output())

boundary = '----B' + uuid.uuid4().hex
p1 = f'--{boundary}\r\nContent-Disposition: form-data; name="workspace_id"\r\n\r\ngeneral\r\n'.encode()
p2 = f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="test.pdf"\r\nContent-Type: application/pdf\r\n\r\n'.encode()
p3 = pdf_bytes
p4 = f'\r\n--{boundary}--\r\n'.encode()
body = p1 + p2 + p3 + p4

upload_req = urllib.request.Request(
    'https://documindai-api.onrender.com/api/v1/documents/upload/local',
    data=body,
    headers={**headers, 'Content-Type': f'multipart/form-data; boundary={boundary}'}
)
with urllib.request.urlopen(upload_req, timeout=15, context=ctx) as r:
    upload_res = json.loads(r.read().decode())
print("Upload local response:", upload_res)

verify_payload = json.dumps({
    'document_id': pre_info['document_id'],
    'filename': 'test.pdf',
    'object_key': upload_res['storage_path'],
    'mime_type': 'application/pdf',
    'size_bytes': len(pdf_bytes)
}).encode('utf-8')

verify_req = urllib.request.Request(
    'https://documindai-api.onrender.com/api/v1/documents/upload/verify',
    data=verify_payload,
    headers={**headers, 'Content-Type': 'application/json'}
)
try:
    with urllib.request.urlopen(verify_req, timeout=30, context=ctx) as r:
        print('Verify status:', r.status, r.read().decode())
except urllib.error.HTTPError as he:
    print('Verify HTTPError:', he.code, he.read().decode())
