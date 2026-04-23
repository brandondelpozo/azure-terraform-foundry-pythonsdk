# SAS URL Upload Test

This directory contains test scripts for generating SAS URLs and uploading doc files to the Azure Foundry endpoint.

## Files Created

- `test_sas_upload.sh` - Comprehensive test script with logging and JSON results
- `test_sas_upload_simple.sh` - Minimal test script for quick testing
- `SAS_UPLOAD_README.md` - This documentation file

## Test Results

When you run the comprehensive test, it generates timestamped result files:
- `sas_upload_test_YYYYMMDD_HHMMSS.log` - Detailed test log
- `sas_upload_test_YYYYMMDD_HHMMSS_result.json` - Test summary in JSON format

## Usage

### Comprehensive Test

```bash
cd test-files
./test_sas_upload.sh
```

This script:
1. Generates a SAS URL from the endpoint
2. Uploads `sample_test.docx` using the SAS URL
3. Verifies the upload was successful
4. Creates detailed logs and JSON results
5. Uses timestamped filenames to avoid conflicts

### Simple Test

```bash
cd test-files
./test_sas_upload_simple.sh
```

This script:
1. Generates a SAS URL from the endpoint
2. Uploads `sample_test.docx` using the SAS URL
3. Provides minimal output for quick verification

## Endpoint Details

- **URL**: `https://func-testfoundry3-endpoint.azurewebsites.net/api/generate-upload-url`
- **Method**: POST
- **Request Body**: `{"filename": "your_filename.docx"}`
- **Response**: 
  ```json
  {
    "sas_url": "https://stfoundry3endpoint.blob.core.windows.net/uploads/filename.docx?...",
    "blob_name": "filename.docx",
    "container": "uploads",
    "expires_in_minutes": 15
  }
  ```

## Upload Details

- **Method**: PUT to the SAS URL
- **Headers**:
  - `x-ms-blob-type: BlockBlob`
  - `Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document`
- **Body**: Binary data of the docx file

## Requirements

- `curl` command line tool
- `jq` for JSON parsing (required for comprehensive test)
- An existing docx file (defaults to `sample_test.docx`)

## Test Results Example

The comprehensive test generates a JSON result like this:

```json
{
  "test_timestamp": "20260423_083128",
  "test_file": "sample_test.docx",
  "upload_filename": "sas_upload_test_20260423_083128.docx",
  "original_size_bytes": 36923,
  "sas_response": {...},
  "upload_success": true,
  "blob_name": "sas_upload_test_20260423_083128.docx",
  "container": "uploads",
  "expires_in_minutes": 15,
  "sas_url": "https://stfoundry3endpoint.blob.core.windows.net/uploads/...",
  "test_completed": "2026-04-23T13:31:33.3NZ"
}
```

## Troubleshooting

1. **Missing filename error**: Ensure the request body includes the filename parameter
2. **Upload fails**: Check that the SAS URL hasn't expired (15-minute timeout)
3. **File not found**: Ensure `sample_test.docx` exists in the test-files directory
4. **Permission denied**: Make sure the shell scripts are executable (`chmod +x *.sh`)
