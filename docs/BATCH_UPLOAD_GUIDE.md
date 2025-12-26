# Batch Upload Feature - User Guide

## Overview

The Document Intelligence Platform now supports batch uploading of multiple documents in a single request. You can upload 10 to 15 documents simultaneously for efficient processing.

## Features

- Upload 10-15 documents per batch request
- Automatic validation of file types and sizes
- Individual error handling per file
- Batch tracking with unique batch ID
- Background processing for all uploaded documents
- Detailed success/failure reporting

## Supported File Types

- PDF: `.pdf`
- Word Documents: `.docx`, `.doc`
- Text Files: `.txt`
- Images: `.jpg`, `.jpeg`, `.png`, `.tiff`

## File Size Limits

- Maximum file size: 50MB per file
- Maximum files per batch: 15 files
- Minimum files per batch: 1 file

## API Endpoint

### POST /documents/batch-upload

Upload multiple documents in a single batch request.

**URL**: `http://localhost:8000/documents/batch-upload`

**Method**: `POST`

**Content-Type**: `multipart/form-data`

**Parameters**:
- `document_type` (query, optional): Type of documents (e.g., "invoice", "contract", "receipt")
- `files` (form-data, required): Multiple files to upload

## Usage Examples

### Using Swagger UI (Browser)

1. Open http://localhost:8000/docs
2. Navigate to **POST /documents/batch-upload**
3. Click **"Try it out"**
4. Set `document_type` (optional): e.g., "invoice"
5. Click **"Add string item"** multiple times to add files
6. Select your files (up to 15)
7. Click **"Execute"**

### Using cURL (Command Line)

```bash
curl -X POST "http://localhost:8000/documents/batch-upload?document_type=invoice" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "files=@invoice1.pdf" \
  -F "files=@invoice2.pdf" \
  -F "files=@invoice3.pdf" \
  -F "files=@invoice4.pdf" \
  -F "files=@invoice5.pdf"
```

### Using Python

```python
import requests

url = "http://localhost:8000/documents/batch-upload"
params = {"document_type": "invoice"}

files = [
    ("files", ("invoice1.pdf", open("invoice1.pdf", "rb"), "application/pdf")),
    ("files", ("invoice2.pdf", open("invoice2.pdf", "rb"), "application/pdf")),
    ("files", ("invoice3.pdf", open("invoice3.pdf", "rb"), "application/pdf")),
]

response = requests.post(url, params=params, files=files)
print(response.json())
```

### Using JavaScript/Node.js

```javascript
const FormData = require('form-data');
const fs = require('fs');
const axios = require('axios');

const form = new FormData();
form.append('files', fs.createReadStream('invoice1.pdf'));
form.append('files', fs.createReadStream('invoice2.pdf'));
form.append('files', fs.createReadStream('invoice3.pdf'));

axios.post('http://localhost:8000/documents/batch-upload?document_type=invoice', form, {
  headers: form.getHeaders()
})
.then(response => console.log(response.data))
.catch(error => console.error(error));
```

## Response Format

### Success Response (200 OK)

```json
{
  "batch_id": "51b7b6d4-c968-4a45-b3d7-df2d37a85b4d",
  "total_documents": 12,
  "successful_uploads": 12,
  "failed_uploads": 0,
  "document_ids": [
    "74455bda-1e39-43ce-9a3b-975070ca882e",
    "b6279137-d48b-4480-b520-d5b110cb4b02",
    "4b7d4c6b-46ac-47bd-9d29-e00fd6bd1358",
    "78982163-0580-45f8-b300-eecbcf2e19ae",
    "a15c4368-6252-43ea-a6cf-bdd5b5282a91",
    "c4807aaf-ea01-4939-8f7d-7a51bb9d33cf",
    "3706b160-0f81-482e-8407-55aa53dba03d",
    "35be1197-11ff-4f1e-8588-4286431fea0b",
    "cbec90a4-08b6-4084-94f5-1866b47f0b21",
    "8fb0c78a-4bf5-4076-a6d9-b503c5d43f54",
    "53f8d2f4-af85-4f19-b2ef-068219ba9c79",
    "a0cc4702-0fcb-4fd7-ae47-242005142e24"
  ]
}
```

**Response Fields**:
- `batch_id`: Unique identifier for this batch upload
- `total_documents`: Total number of files submitted
- `successful_uploads`: Number of files successfully uploaded
- `failed_uploads`: Number of files that failed to upload
- `document_ids`: Array of document IDs for successfully uploaded files

### Partial Success Response

If some files fail validation or upload, you'll still get a 200 response with details:

```json
{
  "batch_id": "abc-123-def-456",
  "total_documents": 5,
  "successful_uploads": 3,
  "failed_uploads": 2,
  "document_ids": [
    "doc-id-1",
    "doc-id-2",
    "doc-id-3"
  ]
}
```

Check the logs for details about which files failed and why.

### Error Responses

**400 Bad Request - Too Many Files**:
```json
{
  "detail": "Too many files. Maximum 15 files allowed per batch. You provided 20 files."
}
```

**400 Bad Request - No Files**:
```json
{
  "detail": "No files provided"
}
```

**400 Bad Request - Invalid File Type**:
Individual files with invalid types will be skipped and counted in `failed_uploads`.

**413 Payload Too Large**:
Individual files exceeding 50MB will be skipped and counted in `failed_uploads`.

## Validation Rules

### File Type Validation
- Only allowed extensions are accepted
- Invalid file types are skipped with error logged

### File Size Validation
- Each file must be under 50MB
- Oversized files are skipped with error logged

### Batch Size Validation
- Minimum: 1 file
- Maximum: 15 files
- Requests exceeding 15 files are rejected

## Processing Flow

1. **Upload**: Files are uploaded via multipart/form-data
2. **Validation**: Each file is validated for type, size, and name
3. **Storage**: Valid files are stored in blob storage
4. **Metadata**: Document records created in SQL database
5. **Analytics**: Raw data stored in data lake
6. **Events**: DocumentUploadedEvent published for each file
7. **Background Processing**: Each document scheduled for AI processing

## Tracking Your Batch

After uploading, you can track individual documents using their document IDs:

```bash
# Check status of a specific document
curl http://localhost:8000/documents/{document_id}/status
```

## Best Practices

1. **Group Similar Documents**: Upload documents of the same type together
2. **Check File Sizes**: Ensure files are under 50MB before uploading
3. **Validate File Types**: Only upload supported file formats
4. **Handle Partial Failures**: Check the response for failed uploads
5. **Monitor Progress**: Use document IDs to track processing status
6. **Batch Size**: For optimal performance, upload 10-12 files per batch

## Development Mode

In development mode:
- No authentication required
- Azure services are optional
- Files stored locally if blob storage not configured
- All operations logged for debugging

## Production Considerations

For production deployments:
- Enable authentication (Bearer token required)
- Configure Azure Blob Storage for file storage
- Configure Azure SQL Database for metadata
- Configure Azure Data Lake for analytics
- Enable Event Hub for event publishing
- Set up monitoring and alerting

## Troubleshooting

### Issue: "No files provided"
**Solution**: Ensure you're using `files` (plural) as the form field name

### Issue: Files not uploading
**Solution**: Check file types and sizes meet requirements

### Issue: All uploads failing
**Solution**: Check service logs with `docker logs docintel-document-ingestion`

### Issue: Partial failures
**Solution**: Review logs to see which files failed and why

## Testing

Test the batch upload feature:

```bash
# Create test files
for i in {1..12}; do echo "Test Document $i" > test_$i.txt; done

# Upload batch
curl -X POST "http://localhost:8000/documents/batch-upload?document_type=test" \
  -F "files=@test_1.txt" \
  -F "files=@test_2.txt" \
  -F "files=@test_3.txt" \
  -F "files=@test_4.txt" \
  -F "files=@test_5.txt" \
  -F "files=@test_6.txt" \
  -F "files=@test_7.txt" \
  -F "files=@test_8.txt" \
  -F "files=@test_9.txt" \
  -F "files=@test_10.txt" \
  -F "files=@test_11.txt" \
  -F "files=@test_12.txt"
```

## Support

For issues or questions:
- Check the API documentation: http://localhost:8000/docs
- Review service logs: `docker logs docintel-document-ingestion`
- Check health status: http://localhost:8000/health

