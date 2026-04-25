import re

# ── Patch backend/documents/routes.py ──────────────────────────────────────
with open('backend/documents/routes.py', encoding='utf-8') as f:
    content = f.read()

OLD = (
    '@router.post("/upload")\n'
    'async def upload_document(\n'
    '    background_tasks: BackgroundTasks,\n'
    '    file: UploadFile = File(...),\n'
    '    current_user: User = Depends(get_current_user),\n'
    '    db: Session = Depends(get_db)\n'
    '):\n'
    '    if not file.filename.endswith(".pdf"):\n'
    '        raise HTTPException(status_code=400, detail="Only PDF files are supported")\n'
    '    unique_name = f"{uuid.uuid4().hex}_{file.filename}"\n'
    '    file_path = save_uploaded_file(current_user.id, unique_name, await file.read())\n'
    '    doc = Document(user_id=current_user.id, filename=unique_name, original_name=file.filename, is_indexed=0)\n'
    '    db.add(doc); db.commit(); db.refresh(doc)\n'
    '    from backend.config import DATABASE_URL\n'
    '    background_tasks.add_task(_process_and_index, current_user.id, file_path, doc.id, DATABASE_URL)\n'
    '    return {"message": "Upload successful", "doc_id": doc.id, "filename": file.filename}'
)

NEW = (
    '@router.post("/upload")\n'
    'async def upload_document(\n'
    '    background_tasks: BackgroundTasks,\n'
    '    file: UploadFile = File(...),\n'
    '    current_user: User = Depends(get_current_user),\n'
    '    db: Session = Depends(get_db)\n'
    '):\n'
    '    import hashlib\n'
    '    if not file.filename.endswith(".pdf"):\n'
    '        raise HTTPException(status_code=400, detail="Only PDF files are supported")\n'
    '    file_content = await file.read()\n'
    '    content_hash = hashlib.sha256(file_content).hexdigest()\n'
    '    # Deduplication: same content already indexed by this user?\n'
    '    existing = db.query(Document).filter(\n'
    '        Document.user_id == current_user.id,\n'
    '        Document.content_hash == content_hash,\n'
    '        Document.canonical_doc_id == None\n'
    '    ).first()\n'
    '    if existing and existing.is_indexed == 1:\n'
    '        alias = Document(user_id=current_user.id, filename=existing.filename,\n'
    '                         original_name=file.filename, is_indexed=1,\n'
    '                         content_hash=content_hash, canonical_doc_id=existing.id)\n'
    '        db.add(alias); db.commit(); db.refresh(alias)\n'
    '        return {"message": "Content already processed - reused instantly",\n'
    '                "doc_id": alias.id, "filename": file.filename, "reused": True, "status": "Ready"}\n'
    '    unique_name = str(uuid.uuid4().hex) + "_" + file.filename\n'
    '    file_path = save_uploaded_file(current_user.id, unique_name, file_content)\n'
    '    doc = Document(user_id=current_user.id, filename=unique_name, original_name=file.filename,\n'
    '                   is_indexed=0, content_hash=content_hash, canonical_doc_id=None)\n'
    '    db.add(doc); db.commit(); db.refresh(doc)\n'
    '    from backend.config import DATABASE_URL\n'
    '    background_tasks.add_task(_process_and_index, current_user.id, file_path, doc.id, DATABASE_URL)\n'
    '    return {"message": "Upload successful", "doc_id": doc.id, "filename": file.filename,\n'
    '            "reused": False, "status": "Processing"}'
)

if OLD in content:
    content = content.replace(OLD, NEW, 1)
    with open('backend/documents/routes.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("routes.py: OK")
else:
    print("routes.py: PATTERN NOT FOUND")
    print(repr(content[1900:2100]))

# ── Patch frontend/src/App.jsx ─────────────────────────────────────────────
with open('frontend/src/App.jsx', encoding='utf-8') as f:
    app = f.read()

if 'DocProvider' not in app:
    app = app.replace(
        'import { ThemeProvider } from "./context/ThemeContext";',
        'import { ThemeProvider } from "./context/ThemeContext";\nimport { DocProvider } from "./context/DocContext";'
    )
    app = app.replace('<ThemeProvider>', '<ThemeProvider>\n      <DocProvider>')
    app = app.replace('</ThemeProvider>', '</DocProvider>\n    </ThemeProvider>')
    with open('frontend/src/App.jsx', 'w', encoding='utf-8') as f:
        f.write(app)
    print("App.jsx: OK")
else:
    print("App.jsx: already patched")
