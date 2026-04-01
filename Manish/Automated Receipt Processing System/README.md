# 🧾 Automated Receipt Processing System — AWS Serverless


https://github.com/user-attachments/assets/cc46185e-0c2a-4efd-845c-de154c748b7b

[documentation.pdf](https://github.com/user-attachments/files/26321842/documentation.pdf)


> **Zero manual work.** Upload a receipt PDF → get structured data in your inbox, automatically.

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python)](https://www.python.org/)
[![AWS Lambda](https://img.shields.io/badge/AWS-Lambda-orange?logo=awslambda)](https://aws.amazon.com/lambda/)
[![AWS Textract](https://img.shields.io/badge/AWS-Textract-yellow)](https://aws.amazon.com/textract/)
[![AWS DynamoDB](https://img.shields.io/badge/AWS-DynamoDB-blue)](https://aws.amazon.com/dynamodb/)
[![AWS SES](https://img.shields.io/badge/AWS-SES-green)](https://aws.amazon.com/ses/)
[![License: MIT](https://img.shields.io/badge/License-MIT-lightgrey)](LICENSE)

---

## 📌 Overview

This project is a **fully serverless, event-driven pipeline** for processing receipt PDFs. Drop a receipt into an S3 bucket and the system automatically:

1. Detects the upload via an S3 event trigger
2. Extracts structured data (vendor, date, total, line items) using **Amazon Textract**
3. Persists the results to **Amazon DynamoDB**
4. Sends a formatted **HTML email notification** via **Amazon SES**

Built to solve real-world pain points in **expense tracking** and **financial workflow automation** — with no servers to manage and near-zero cost at low volumes.

---

## 🏗️ Architecture

```
                        ┌─────────────────────────────────────────────┐
                        │              AWS Cloud                       │
                        │                                             │
  📄 Receipt PDF        │  ┌──────────┐    ┌────────────────────┐    │
 ──────────────────────▶│  │  S3      │───▶│  Lambda Function   │    │
  (manual upload /      │  │  Bucket  │    │  (processor.py)    │    │
   automated feed)      │  └──────────┘    └────────┬───────────┘    │
                        │   (Event          ┌────────┘               │
                        │    Trigger)       ▼                        │
                        │             ┌──────────────┐               │
                        │             │   Textract   │               │
                        │             │AnalyzeExpense│               │
                        │             └──────┬───────┘               │
                        │                    │ Extracted Data        │
                        │          ┌─────────┴──────────┐            │
                        │          ▼                    ▼            │
                        │   ┌────────────┐      ┌──────────────┐    │
                        │   │  DynamoDB  │      │  SES Email   │    │
                        │   │  (Storage) │      │(Notification)│    │
                        │   └────────────┘      └──────────────┘    │
                        └─────────────────────────────────────────────┘
```

---

## ⚙️ Tech Stack

| Service / Tool | Role |
|---|---|
| **AWS S3** | Receipt PDF storage & event source |
| **AWS Lambda** | Serverless compute — orchestrates the pipeline |
| **Amazon Textract** | AI-powered document data extraction (`AnalyzeExpense`) |
| **Amazon DynamoDB** | NoSQL storage for structured receipt records |
| **Amazon SES** | Transactional email delivery |
| **Python 3.9+** | Lambda runtime & extraction logic |
| **Boto3** | AWS SDK for Python |

---

## ✨ Features

- **Fully automated** — zero manual steps after initial setup
- **Event-driven** — Lambda triggers instantly on S3 upload
- **Intelligent extraction** — uses Textract's dedicated `AnalyzeExpense` API for receipts
- **Structured output** — vendor name, date, total amount, and individual line items
- **Persistent storage** — every receipt is recorded in DynamoDB with a unique ID
- **Email notifications** — HTML-formatted email sent on every successful processing
- **Resilient design** — email failures are caught and logged without crashing the pipeline
- **Scalable & cost-efficient** — pay only for what you use; scales to zero when idle

---

## 📥 Data Flow

```
1. User uploads receipt PDF  →  S3 Bucket
2. S3 PUT event              →  Triggers Lambda
3. Lambda calls              →  Textract AnalyzeExpense
4. Textract returns          →  Vendor, Date, Total, Line Items
5. Lambda writes             →  DynamoDB (receipt_id, all fields, timestamp)
6. Lambda sends              →  SES HTML email to recipient
```

### Extracted Fields

| Field | Source |
|---|---|
| `receipt_id` | UUID generated per receipt |
| `vendor` | `VENDOR_NAME` from Textract SummaryFields |
| `date` | `INVOICE_RECEIPT_DATE` from Textract SummaryFields |
| `total` | `TOTAL` from Textract SummaryFields |
| `items[]` | Line items: name, price, quantity |
| `s3_path` | Full S3 URI of the source file |
| `processed_timestamp` | ISO 8601 timestamp of Lambda execution |

---

## 🚀 Deployment Guide

### Prerequisites

- AWS account with appropriate IAM permissions
- Python 3.9+ (for local development/testing)
- AWS CLI configured (`aws configure`)

### Step 1 — Create S3 Bucket

```bash
aws s3 mb s3://your-receipts-bucket --region us-east-1
```

### Step 2 — Create DynamoDB Table

```bash
aws dynamodb create-table \
  --table-name Receipts \
  --attribute-definitions AttributeName=receipt_id,AttributeType=S \
  --key-schema AttributeName=receipt_id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST
```

### Step 3 — Verify SES Email Addresses

Both the sender and recipient email addresses must be verified in SES before use.

```bash
aws ses verify-email-identity --email-address your-sender@example.com
aws ses verify-email-identity --email-address your-recipient@example.com
```

> **Note:** If your SES account is in sandbox mode, both sender and recipient must be verified. Request production access to send to unverified addresses.

### Step 4 — Create Lambda IAM Role

Create a role with the following AWS managed policies:
- `AmazonS3ReadOnlyAccess`
- `AmazonTextractFullAccess`
- `AmazonDynamoDBFullAccess`
- `AmazonSESFullAccess`
- `AWSLambdaBasicExecutionRole`

### Step 5 — Deploy Lambda Function

1. Zip the source code:
   ```bash
   zip function.zip processor.py
   ```

2. Create the Lambda function:
   ```bash
   aws lambda create-function \
     --function-name ReceiptProcessor \
     --runtime python3.11 \
     --role arn:aws:iam::YOUR_ACCOUNT_ID:role/LambdaReceiptRole \
     --handler processor.lambda_handler \
     --zip-file fileb://function.zip \
     --timeout 60 \
     --memory-size 256
   ```

3. Set environment variables:
   ```bash
   aws lambda update-function-configuration \
     --function-name ReceiptProcessor \
     --environment "Variables={DYNAMODB_TABLE=Receipts,SES_SENDER_EMAIL=sender@example.com,SES_RECIPIENT_EMAIL=recipient@example.com}"
   ```

### Step 6 — Configure S3 Trigger

```bash
aws lambda add-permission \
  --function-name ReceiptProcessor \
  --statement-id S3InvokePermission \
  --action lambda:InvokeFunction \
  --principal s3.amazonaws.com \
  --source-arn arn:aws:s3:::your-receipts-bucket

aws s3api put-bucket-notification-configuration \
  --bucket your-receipts-bucket \
  --notification-configuration '{
    "LambdaFunctionConfigurations": [{
      "LambdaFunctionArn": "arn:aws:lambda:us-east-1:YOUR_ACCOUNT_ID:function:ReceiptProcessor",
      "Events": ["s3:ObjectCreated:*"],
      "Filter": {
        "Key": { "FilterRules": [{"Name": "suffix", "Value": ".pdf"}] }
      }
    }]
  }'
```

---

## 🔧 Configuration

| Environment Variable | Default | Description |
|---|---|---|
| `DYNAMODB_TABLE` | `Receipts` | DynamoDB table name |
| `SES_SENDER_EMAIL` | `your-email@example.com` | Verified SES sender address |
| `SES_RECIPIENT_EMAIL` | `recipient@example.com` | Email address to receive notifications |

---

## 📦 Project Structure

```
Automated-Receipt-Processing-System-AWS-Serverless/
│
├── processor.py          # Lambda handler — full pipeline logic
│   ├── lambda_handler()              # Entry point, reads S3 event
│   ├── process_receipt_with_textract()  # Textract AnalyzeExpense call
│   ├── store_receipt_in_dynamodb()   # DynamoDB put_item
│   └── send_email_notification()    # SES HTML email
│
└── README.md             # This file
```

---

## 🧪 Testing

### Manual Test via AWS Console

1. Navigate to your Lambda function in the AWS Console
2. Create a test event using the **S3 Put** template
3. Replace `bucket.name` and `object.key` with your actual bucket and a test PDF key
4. Click **Test** and check CloudWatch Logs for output

### Test via CLI

```bash
# Upload a test receipt
aws s3 cp sample_receipt.pdf s3://your-receipts-bucket/

# Check CloudWatch Logs
aws logs tail /aws/lambda/ReceiptProcessor --follow
```

### Expected DynamoDB Record

```json
{
  "receipt_id": "a1b2c3d4-...",
  "vendor": "Whole Foods Market",
  "date": "2026-03-27",
  "total": "47.83",
  "items": [
    { "name": "Organic Milk", "price": "5.99", "quantity": "2" },
    { "name": "Sourdough Bread", "price": "6.49", "quantity": "1" }
  ],
  "s3_path": "s3://your-receipts-bucket/receipt.pdf",
  "processed_timestamp": "2026-03-27T14:30:00.123456"
}
```

---

## 📊 Impact

- **~80% reduction** in manual data entry for expense tracking
- **Real-time processing** — receipt data available within seconds of upload
- **Auditability** — every receipt stored with a unique ID and timestamp
- **Cost efficiency** — runs entirely on AWS Free Tier for low volumes

---

## 🔮 Future Improvements

- [ ] **OCR for scanned receipts** — integrate Textract's `DetectDocumentText` as fallback
- [ ] **Analytics dashboard** — query DynamoDB and visualize spending trends
- [ ] **Multi-format support** — handle JPEG/PNG receipts in addition to PDF
- [ ] **AI-enhanced extraction** — use LLMs for smarter categorization and anomaly detection
- [ ] **CI/CD pipeline** — automate deployments with GitHub Actions + SAM/CDK
- [ ] **Cost alerts** — trigger SNS notification when total exceeds a threshold

---

## 🧠 Key Learnings

- Hands-on experience designing **event-driven serverless architectures** on AWS
- Practical use of **Amazon Textract's AnalyzeExpense API** for structured document parsing
- Building **resilient Lambda functions** that handle partial failures gracefully
- Real-world automation of a common business workflow end-to-end

---

## 🤝 Connect

**Manish Kudtarkar**

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-blue?logo=linkedin)](https://www.linkedin.com/in/manish-kudtarkar)
[![GitHub](https://img.shields.io/badge/GitHub-Follow-black?logo=github)](https://github.com/ManishKudtarkar)

---

## ⭐ Support

If this project was useful or interesting, consider giving it a ⭐ on GitHub — it helps others discover it!
