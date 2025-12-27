# API Gateway Upload Endpoint Fix Guide

## The Problem

The API Gateway (`src/microservices/api-gateway/main.py`) has a **mock upload endpoint** at line 1306 that:

1. **Generates fake data** instead of doing real AI processing
2. **Directly inserts into PostgreSQL** with status "processed" 
3. **Never calls the AI processing service**
4. **Never uses Tesseract OCR** for images
5. **Never extracts real entities with OpenAI**

Result: ALL uploaded documents show **"0 entities extracted"**

## The Risk

- The file is **2,417 lines long** with complex routing logic
- Mock code is **150+ lines** deeply integrated into the upload function
- Previous edit attempts caused **syntax errors** that crashed the entire API Gateway
- Affects **all microservices** that depend on the Gateway

## Current Code (Lines 1306-1456)

```python
@app.post("/documents/upload")
async def upload_document(request: Request):
    """Upload a document with industry-standard invoice extraction"""  # ← WRONG: This is mock
    try:
        # Parse multipart form data
        form = await request.form()
        file = form.get("file")
        
        if not file:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # ❌ PROBLEM STARTS HERE: Generates mock data
        doc_id = f"doc_{hashlib.md5(str(datetime.utcnow()).encode()).hexdigest()[:8]}"
        filename = file.filename if hasattr(file, 'filename') else "unknown"
        
        # ... 120+ lines of fake vendor generation, invoice data, etc.
        
        if DATABASE_AVAILABLE:
            db.insert_document(document_data)  # ❌ Inserts fake data directly
            db.insert_invoice_extraction(extraction_data)  # ❌ Fake invoice data
        
        return {
            "document_id": doc_id,
            "status": "uploaded",
            "message": "Document uploaded and processed successfully",
            "processing_status": "completed",  # ❌ LIE: Nothing was processed!
            "filename": filename
        }
```

## What It SHOULD Be

```python
@app.post("/documents/upload")
async def upload_document(request: Request):
    """Upload a document for REAL AI processing with OCR"""
    try:
        # Parse form
        form = await request.form()
        file = form.get("file")
        
        if not file:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # Read file content
        file_content = await file.read()
        filename = file.filename if hasattr(file, 'filename') else "unknown"
        content_type = file.content_type if hasattr(file, 'content_type') else "application/octet-stream"
        
        logger.info(f"API Gateway: Forwarding {filename} to document-ingestion")
        
        # ✅ FORWARD TO REAL AI PROCESSING
        files = {"file": (filename, file_content, content_type)}
        data = {
            "user_id": "demo1234",
            "document_type": "invoice" if "invoice" in filename.lower() else "document",
            "metadata": "{}"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://docintel-document-ingestion:8000/documents/upload",
                files=files,
                data=data,
                timeout=60.0
            )
            response.raise_for_status()
            result = response.json()
            
            logger.info(f"Document {result.get('document_id')} queued for AI processing")
            return result
            
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
```

## Step-by-Step Fix Guide

### BEFORE YOU START:

1. **Backup the file**:
   ```bash
   cd "/home/saidul/Desktop/compello As/Document-Intelligence-Platform"
   cp src/microservices/api-gateway/main.py src/microservices/api-gateway/main.py.backup
   ```

2. **Identify the exact lines to replace**:
   ```bash
   grep -n "@app.post(\"/documents/upload\")" src/microservices/api-gateway/main.py
   # Should show: 1306
   ```

3. **Find where the mock endpoint ENDS**:
   ```bash
   sed -n '1306,1500p' src/microservices/api-gateway/main.py | grep -n "@app.delete" | head -1
   # This shows where the next endpoint starts
   ```

### THE FIX:

**Replace lines 1306-1456** (entire mock upload function) with the clean version above.

**Critical**: Make sure you:
- Delete ALL 150 lines of mock code
- Keep proper indentation (4 spaces for function body)
- Don't break the `@app.delete` endpoint that comes after
- Preserve the `@app.api_route` that follows

### TESTING:

```bash
# 1. Syntax check
python3 -m py_compile src/microservices/api-gateway/main.py

# 2. Rebuild
docker compose build api-gateway

# 3. Restart
docker compose up -d api-gateway

# 4. Wait and check health
sleep 20
curl http://localhost:8003/health

# 5. Check logs
docker compose logs api-gateway --tail 20
```

### IF IT BREAKS:

```bash
# Restore backup
cp src/microservices/api-gateway/main.py.backup src/microservices/api-gateway/main.py

# Restart
docker compose up -d api-gateway
```

## Prompt to Give AI Assistant

```
I need to fix the API Gateway upload endpoint in:
src/microservices/api-gateway/main.py

Current situation:
- Lines 1306-1456 contain a mock upload endpoint
- It generates fake vendor/invoice data instead of real AI processing
- Documents show "0 entities extracted" because no AI processing happens

Required fix:
- Replace the entire @app.post("/documents/upload") function (lines 1306-1456)
- New version should forward to: http://docintel-document-ingestion:8000/documents/upload
- Must preserve correct indentation and not break subsequent endpoints
- Backup exists at: main.py.backup_20251227_234818

The file is 2,417 lines long, so be very careful with the replacement.
Do NOT modify any other endpoints or functions.
```

## Why Previous Attempts Failed

1. **Incomplete replacement**: Left fragments of old code
2. **Indentation errors**: Mixed tabs/spaces or wrong indent levels  
3. **Missing closing braces**: Didn't properly close the try/except
4. **Broke subsequent endpoint**: Damaged the `@app.delete` that follows

## Success Criteria

After the fix:
1. ✅ API Gateway starts without errors
2. ✅ Health endpoint returns 200 OK
3. ✅ Upload a PNG invoice
4. ✅ Wait 15 seconds
5. ✅ Refresh documents page
6. ✅ See **REAL entities extracted** (not 0)

## Current Workaround

Until fixed:
- System is **stable** and **functional**
- Delete works perfectly
- Uploads work but generate **mock data**
- Documents show "0 entities extracted"

The backup is preserved at:
`src/microservices/api-gateway/main.py.backup_20251227_234818`
