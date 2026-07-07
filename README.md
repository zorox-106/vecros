# Vecros Drone Inspection Service

A serverless backend built on **AWS Lambda + API Gateway + DynamoDB + S3** that manages drone-based warehouse inspections.

> [!NOTE]
> **Live Deployed API Base URL (Region: eu-north-1):**
> - **API Gateway Endpoints:** `https://4nonq48d5c.execute-api.eu-north-1.amazonaws.com/dev`
> - **DynamoDB Table:** `DroneInspectionTable-dev`
> - **S3 Image Storage Bucket:** `vecros-inspection-images-dev-351947424692`

---

## Architecture

```
Client (Mobile / Web / cURL)
        │
        ▼
API Gateway (REST API)
        │
        ├── POST   /inspections                          → CreateInspectionFunction
        ├── GET    /warehouses/{warehouse_id}/inspections → ListByWarehouseFunction
        ├── GET    /drones/{drone_id}/inspections         → ListByDroneFunction
        ├── POST   /inspections/{inspection_id}/images/upload → GeneratePresignedUrlFunction
        └── GET    /inspections/{inspection_id}/images    → ListImagesFunction
        │
        ▼
AWS Lambda (Python 3.9)  ←── IAM Execution Role (no credentials in code)
        │
        ├── DynamoDB  (entity storage & associations via single-table design)
        └── S3        (image storage — client uploads directly via pre-signed URL)
```

**Key design principles:**
- Lambda **never handles image bytes** — only generates S3 pre-signed PUT URLs
- **IAM role only** — boto3 picks up credentials from the Lambda execution role automatically
- **No table scans** — all queries use the primary key or a GSI
- **Single-table DynamoDB design** — all 4 entity types + their associations in one table

---

## DynamoDB Design

### Why Single-Table?

All access patterns are known upfront. A single-table design means:
- No cross-table joins (DynamoDB doesn't support them)
- Fewer read/write operations
- One table to manage, monitor, and back up
- Demonstrates advanced DynamoDB knowledge (evaluated criterion)

### Table: `DroneInspectionTable`

| Attribute  | Type   | Role                            |
|------------|--------|---------------------------------|
| `PK`       | String | Partition Key                   |
| `SK`       | String | Sort Key                        |
| `GSI1PK`   | String | GSI-1 Partition Key             |
| `GSI1SK`   | String | GSI-1 Sort Key                  |
| `GSI2PK`   | String | GSI-2 Partition Key             |
| `GSI2SK`   | String | GSI-2 Sort Key                  |
| `entity_type` | String | WAREHOUSE / DRONE / INSPECTION / IMAGE |
| `created_at` | String | ISO 8601 timestamp             |

### Key Patterns

| Entity     | PK                        | SK               |
|------------|---------------------------|------------------|
| Warehouse  | `WAREHOUSE#<id>`          | `METADATA`       |
| Drone      | `DRONE#<id>`              | `METADATA`       |
| Inspection | `INSPECTION#<id>`         | `METADATA`       |
| Image      | `INSPECTION#<insp_id>`    | `IMAGE#<img_id>` |

### GSI Definitions

| GSI   | Partition Key | Sort Key  | Access Pattern                          |
|-------|---------------|-----------|------------------------------------------|
| GSI1  | `GSI1PK`      | `GSI1SK`  | List inspections by warehouse            |
| GSI2  | `GSI2PK`      | `GSI2SK`  | List inspections by drone                |

### Access Patterns → DynamoDB Queries

| Access Pattern                    | Query Strategy                                                    |
|-----------------------------------|--------------------------------------------------------------------|
| List inspections by warehouse     | GSI1: `GSI1PK = WAREHOUSE#<id>` AND `GSI1SK begins_with INSPECTION#` |
| List inspections by drone         | GSI2: `GSI2PK = DRONE#<id>` AND `GSI2SK begins_with INSPECTION#`     |
| Get single inspection             | Primary: `PK = INSPECTION#<id>`, `SK = METADATA`                  |
| List images for inspection        | Primary: `PK = INSPECTION#<id>`, `SK begins_with IMAGE#`           |

The sort key includes a **timestamp prefix** (`INSPECTION#<ISO-timestamp>`) so results are naturally time-ordered.

---

## API Reference

### 1. Create Inspection

```
POST /inspections
Content-Type: application/json

{
  "warehouse_id": "wh-001",
  "drone_id":     "drone-001",
  "notes":        "Routine shelf inspection"  // optional
}
```

**Response 201:**
```json
{
  "inspection_id": "550e8400-e29b-41d4-a716-446655440000",
  "warehouse_id":  "wh-001",
  "drone_id":      "drone-001",
  "notes":         "Routine shelf inspection",
  "status":        "CREATED",
  "created_at":    "2026-07-07T08:00:00+00:00"
}
```

---

### 2. List Inspections by Warehouse

```
GET /warehouses/{warehouse_id}/inspections
```

**Response 200:**
```json
{
  "warehouse_id": "wh-001",
  "count": 2,
  "inspections": [ { ... }, { ... } ]
}
```

---

### 3. List Inspections by Drone

```
GET /drones/{drone_id}/inspections
```

**Response 200:**
```json
{
  "drone_id": "drone-001",
  "count": 1,
  "inspections": [ { ... } ]
}
```

---

### 4. Generate Pre-signed Upload URL

```
POST /inspections/{inspection_id}/images/upload
Content-Type: application/json

{
  "file_name":    "shelf_row_3.jpg",
  "content_type": "image/jpeg"
}
```

**Response 200:**
```json
{
  "image_id":   "img-uuid",
  "upload_url": "https://s3.amazonaws.com/...?X-Amz-Signature=...",
  "s3_key":     "inspections/insp-001/img-uuid/shelf_row_3.jpg",
  "expires_in": 3600
}
```

The client then uploads directly:
```bash
curl -X PUT "<upload_url>" \
  -H "Content-Type: image/jpeg" \
  --data-binary @shelf_row_3.jpg
```

---

### 5. List Images for Inspection

```
GET /inspections/{inspection_id}/images
```

**Response 200:**
```json
{
  "inspection_id": "insp-001",
  "count": 1,
  "images": [
    {
      "image_id":     "img-uuid",
      "file_name":    "shelf_row_3.jpg",
      "s3_key":       "inspections/insp-001/img-uuid/shelf_row_3.jpg",
      "view_url":     "https://s3.amazonaws.com/...?X-Amz-Signature=...",
      "created_at":   "2026-07-07T09:00:00+00:00"
    }
  ]
}
```

---

## Project Structure

```
vecros-drone-inspection/
├── lambdas/
│   ├── create_inspection/        handler.py
│   ├── list_by_warehouse/        handler.py
│   ├── list_by_drone/            handler.py
│   ├── generate_presigned_url/   handler.py
│   └── list_images/              handler.py
├── shared/
│   ├── db.py          # DynamoDB client + key builders + query helpers
│   ├── s3.py          # S3 client + pre-signed URL helpers
│   ├── response.py    # Standard HTTP response builder
│   └── validators.py  # Input validation
├── infra/
│   └── template.yaml  # AWS SAM template
├── tests/
│   ├── test_create_inspection.py
│   ├── test_list_by_warehouse.py
│   ├── test_list_by_drone.py
│   ├── test_presigned_url.py
│   └── test_list_images.py
├── requirements.txt
└── README.md
```

---

## Deployment

### Prerequisites

- [AWS CLI](https://aws.amazon.com/cli/) configured with an IAM user/role
- [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)
- Python 3.9+

### Steps

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd vecros-drone-inspection

# 2. Install dependencies locally (for tests)
pip install -r requirements.txt

# 3. Run unit tests
python -m pytest tests/ -v

# 4. Build the SAM application
cd infra
sam build

# 5. Deploy (first time — guided wizard)
sam deploy --guided \
  --parameter-overrides Stage=dev

# 6. On subsequent deployments
sam deploy --parameter-overrides Stage=dev
```

After deployment, SAM outputs the **API Base URL**. Use it to call the endpoints.

---

## IAM & Security

- All Lambda functions share a **single IAM execution role** with least-privilege inline policies
- **DynamoDB**: `PutItem`, `GetItem`, `Query` on the table and its indexes
- **S3**: `PutObject`, `GetObject`, `ListBucket` scoped to the images bucket
- **CloudWatch**: Basic logging via the AWS managed `AWSLambdaBasicExecutionRole` policy
- **No credentials anywhere in code** — boto3 automatically uses the attached execution role

---

## Design Decisions & Trade-offs

| Decision | Rationale |
|---|---|
| **Single-table DynamoDB** | All access patterns are known; avoids cross-table joins; cleaner ops |
| **GSIs over Scans** | GSI queries are O(result set size); scans are O(table size) — never acceptable in production |
| **Sort key = timestamp** | Enables time-ordered listing without a secondary sort step |
| **S3 pre-signed PUT URLs** | Lambda never touches bytes → no 6 MB payload limit, no Lambda timeout risk, no egress cost |
| **Image metadata in DynamoDB** | Keeps image records discoverable without listing S3 (which is eventually consistent and slower) |
| **PAY_PER_REQUEST billing** | No capacity planning; auto-scales with load; perfect for an assignment / early-stage product |
| **SAM over raw CloudFormation** | Concise, purpose-built for serverless; `sam local invoke` enables local testing |
