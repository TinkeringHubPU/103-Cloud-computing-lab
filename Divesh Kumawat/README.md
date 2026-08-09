# Cloud Fun Facts Generator

This project is a simple web application that generates fun, witty facts about Cloud Computing. It uses an AWS serverless architecture comprising Amazon S3 (or local hosting) for the frontend, API Gateway, AWS Lambda, Amazon DynamoDB, and Amazon Bedrock.

This guide will walk you through deploying this project manually using the AWS Management Console and AWS CLI.

## Architecture Overview

1. **Frontend**: A simple HTML/JS page (`index.html`) that fetches and displays facts.
2. **API Gateway**: Provides a public endpoint for the frontend to communicate with the backend.
3. **AWS Lambda**: The backend compute service (`Lambda.py`) that handles requests, fetches a random fact from DynamoDB, and uses Amazon Bedrock to rewrite it in a witty way.
4. **Amazon DynamoDB**: A NoSQL database storing the raw cloud facts.
5. **Amazon Bedrock**: A fully managed AI service used to generate witty variations of the facts using the Amazon Nova 2 Lite model.

---

## Prerequisites

1. An **AWS Account**.
2. **AWS CLI** installed and configured with appropriate permissions.
3. Access to **Amazon Bedrock** (Make sure model access for `Amazon Nova 2 Lite` is enabled in your AWS region, e.g., `us-east-1`).

---

## Step 1: Create the DynamoDB Table

1. Go to the **DynamoDB console** in AWS.
2. Click **Create table**.
3. **Table details**:
   - **Table name**: Enter `generator`. *(Note: The batch_statements.json uses `generator` as the table name. You will need to update `Lambda.py` on line 19 from `CloudFacts` to `generator` so they match, OR name the table `CloudFacts` and update the table name inside `batch_statements.json`.)*
   - **Partition key**: Enter `FactId` and select **String**.
4. Leave other settings as default and click **Create table**.

### Load Data into DynamoDB
Once the table is created, you can populate it using the provided `batch_statements.json` file.
Open your terminal in the project directory and run the following AWS CLI command:

```bash
aws dynamodb batch-execute-statement --statements file://batch_statements.json
```
*Note: Make sure your AWS CLI is configured for the correct region where you created the table.*

---

## Step 2: Create the IAM Role for Lambda

Your Lambda function needs permissions to access DynamoDB, Bedrock, and CloudWatch Logs.

1. Go to the **IAM console** -> **Roles** -> **Create role**.
2. Select **AWS service** as the trusted entity and **Lambda** as the use case.
3. Skip attaching managed policies for now and click **Next**.
4. Give the role a name (e.g., `CloudFunFactsLambdaRole`) and click **Create role**.
5. Find the newly created role and click **Add permissions** -> **Create inline policy**.
6. Switch to the **JSON** editor and paste the contents of `lambda_role.json`.
   - ⚠️ **Important**: Before saving, you must replace the placeholders in the JSON (`<<AWS_ACCOUNT_ID>>`, `<<AWS_REGION>>`, `<<DYNAMODB_TABLE_NAME>>`, `<<LAMBDA_FUNCTION_NAME>>`) with your actual AWS details.
7. Name the policy (e.g., `CloudFunFactsPolicy`) and save it.

---

## Step 3: Create the AWS Lambda Function

1. Go to the **Lambda console** -> **Create function**.
2. Choose **Author from scratch**.
3. **Function name**: e.g., `CloudFunFactsFunction`.
4. **Runtime**: Select **Python 3.12** (or your preferred Python 3.x version).
5. **Execution role**: Choose **Use an existing role** and select the role you created in Step 2 (`CloudFunFactsLambdaRole`).
6. Click **Create function**.

### Configure the Function:
1. In the **Code source** section, replace the default code with the contents of `Lambda.py`.
2. *(If you named your DynamoDB table `generator`, remember to change `table = dynamodb.Table("CloudFacts")` to `table = dynamodb.Table("generator")` on line 19).*
3. Click **Deploy** to save the changes.
4. Go to the **Configuration** tab -> **General configuration** -> **Edit**.
   - Increase the **Timeout** to `15 seconds` (or more), as calling Amazon Bedrock might take a few seconds.
   - Click **Save**.

---

## Step 4: Create the API Gateway

1. Go to the **API Gateway console**.
2. Click **Create API** and choose **HTTP API** (Build).
3. **Integrations**: Click **Add integration**, select **Lambda**, and choose your function (`CloudFunFactsFunction`).
4. **API name**: e.g., `CloudFunFactsAPI`. Click **Next**.
5. **Configure routes**:
   - **Method**: `GET`
   - **Resource path**: `/fact`
   - **Integration target**: Your Lambda function.
   - Click **Next**, leave the stage as default, and click **Create**.

### Configure CORS:
Since your frontend (running locally or on S3) will call this API, you need to enable CORS.
1. In your HTTP API settings on the left sidebar, click **CORS**.
2. Click **Configure**.
3. **Access-Control-Allow-Origin**: Add `*` (or your specific domain for better security).
4. **Access-Control-Allow-Methods**: Add `GET` and `OPTIONS`.
5. **Access-Control-Allow-Headers**: Add `Content-Type`.
6. Click **Save**.

Note your **Invoke URL** (e.g., `https://<api-id>.execute-api.<region>.amazonaws.com/fact`).

---

## Step 5: Configure and Run the Frontend

1. Open `index.html` in your text editor.
2. Locate the JavaScript section near the bottom.
3. Replace the placeholder endpoint with your actual API Gateway Invoke URL:
   ```javascript
   const API_URL = 'https://<your-api-id>.execute-api.<region>.amazonaws.com/fact';
   ```
4. Save the file.
5. Open `index.html` in any web browser to test locally.

---

## Step 6: Deploy Frontend via AWS Amplify (GitHub Integration)

To host your frontend on the internet, you can easily deploy it using AWS Amplify:

1. Push your updated code (including the configured `index.html` with your API endpoint) to a **GitHub repository**.
2. Go to the **AWS Amplify console**.
3. Click **Create new app**.
4. Select **GitHub** as the source provider and click **Next**.
5. Authorize AWS Amplify to access your GitHub account if prompted.
6. Select the repository and the branch where your `index.html` is located, then click **Next**.
7. In the **Build settings** page, Amplify should automatically detect your simple HTML setup. Leave the default settings as they are. (Since it's a plain HTML file, no build command is needed).
8. Click **Next**, review the details, and click **Save and deploy**.
9. Wait for the deployment to finish. Amplify will provide you with a live domain URL (e.g., `https://main.xxxxxx.amplifyapp.com`).
10. Open that URL in your browser to view your live, globally accessible application!

---

## Troubleshooting

- **Error: "Could not fetch fact. Check your API endpoint!"**: Ensure your API Gateway URL is correct, your Lambda function is deployed successfully, and CORS is properly configured in API Gateway.
- **Lambda Timeout / "Nahi Hua" fallback**: If Bedrock takes too long to respond, the Lambda function might time out. Ensure you increased the Lambda timeout to at least 15 seconds. Also, verify that your IAM role has the correct `bedrock:InvokeModel` permissions and that your AWS account has requested access to the `Amazon Nova 2 Lite` model in Bedrock.
- **DynamoDB Empty Fact List**: Ensure the DynamoDB table name in `Lambda.py` perfectly matches the one you created and populated.
