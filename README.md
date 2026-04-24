# Gmail AI Dashboard

A serverless AI assistant built on AWS that connects to your Google account and answers questions about your Gmail and Google Calendar using Amazon Bedrock (Claude 3.5 Haiku).

## Architecture

- **AWS Lambda** — Auth and Ask functions (Python 3.12)
- **API Gateway** — REST API routing
- **DynamoDB** — Session storage with TTL cleanup
- **S3** — Static frontend hosting
- **Amazon Bedrock** — Claude 3.5 Haiku for AI responses
- **Google OAuth2** — Gmail and Calendar access

---

## Prerequisites

- [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html) configured with an IAM user
- [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)
- A [Google Cloud Console](https://console.cloud.google.com) project with OAuth2 credentials
- Amazon Bedrock model access enabled for `anthropic.claude-3-5-haiku-20241022-v1:0` in `us-east-1`

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/BrandynLo/Gmail-AI-Dashboard.git
cd Gmail-AI-Dashboard
```


### 2.5 Configure Google OAuth

In [Google Cloud Console](https://console.cloud.google.com) → APIs & Services → Credentials → Create OAuth client:
Create a project
<img width="1912" height="975" alt="image" src="https://github.com/user-attachments/assets/4de11fda-ba60-4309-b844-89346f5e0e16" />
<img width="1912" height="707" alt="image" src="https://github.com/user-attachments/assets/2bea7df4-c48d-4a01-a37a-725d68e819e1" />

Authenticate API Services (Google Gmail + Calender) 
<img width="1900" height="1033" alt="image" src="https://github.com/user-attachments/assets/9e2ef3be-9246-4df8-82e2-2f1e1f297968" />
<img width="1902" height="1033" alt="image" src="https://github.com/user-attachments/assets/e171fb93-0ac9-4738-98d1-b9caf313204a" />
<img width="1861" height="977" alt="Screenshot 2026-04-22 154446" src="https://github.com/user-attachments/assets/9ee0b71d-ccb8-4a6e-ad70-11eec8eee2bc" />
Enable Services:
<img width="875" height="755" alt="Screenshot 2026-04-22 154741" src="https://github.com/user-attachments/assets/324f1b8a-c940-4458-b5ef-b1e6957a51e8" />
Enable Scopes:
<img width="690" height="704" alt="Screenshot 2026-04-22 154923" src="https://github.com/user-attachments/assets/f05ce7e1-991d-47d9-b5b4-53889ba4fd38" />
<img width="961" height="493" alt="Screenshot 2026-04-22 155041" src="https://github.com/user-attachments/assets/0bfc8c3a-d3fd-47cf-b239-e805de0e071e" />

After creation of your first OAuth, you will get a API key used to authenticate with AWS
<img width="1253" height="826" alt="image" src="https://github.com/user-attachments/assets/29545447-045a-4097-91d8-13c8cb491f44" />

### Enable Google APIs

In Google Cloud Console → APIs & Services → Library, enable:
- Gmail API
- Google Calendar API

---
Sign up for AWS + Enable Claude 3 Haiku (May have to submit Use Case Details)
<img width="844" height="716" alt="Screenshot 2026-04-22 172011" src="https://github.com/user-attachments/assets/c2ccd86e-366b-438e-96ef-e4a08134714a" />
<img width="1902" height="1033" alt="image" src="https://github.com/user-attachments/assets/b6cd7bf3-50ef-4557-a1f5-d82b003e7227" />
Retain Access Key for later:
<img width="1902" height="1033" alt="image" src="https://github.com/user-attachments/assets/9365f3aa-f26e-4e78-9e93-97dc04d1474a" />


### 2. Configure AWS credentials

```bash
aws configure
# Enter your Access Key ID, Secret Access Key, region (us-east-1), output format (json)
```

### 3. Build and deploy (first time)

```bash
sam build
sam deploy --guided
```

When prompted:
```
Stack Name: AI-Dashboard-Email
AWS Region: us-east-1
Parameter GoogleClientId: <your Google OAuth Client ID>
Parameter GoogleClientSecret: <your Google OAuth Client Secret>
Parameter RedirectUri: https://placeholder.execute-api.us-east-1.amazonaws.com/Prod/callback
Confirm changes before deploy: N
Allow SAM CLI IAM role creation: Y
Disable rollback: N
AuthFunction has no authentication. Is this okay? [y/N]: y
AuthFunction has no authentication. Is this okay? [y/N]: y
AskFunction has no authentication. Is this okay? [y/N]: y
AskFunction has no authentication. Is this okay? [y/N]: y
Save arguments to configuration file: Y
```
<img width="1253" height="707" alt="image" src="https://github.com/user-attachments/assets/5debc122-ac37-455b-ba70-5fb15011fcd9" />

After deploy finishes, note the **ApiUrl** and **FrontendUrl** from the Outputs section:
```
Outputs
ApiUrl      = https://XXXXXXXXXX.execute-api.us-east-1.amazonaws.com/Prod
FrontendUrl = http://ai-dashboard-frontend-XXXXXXXXXXXX.s3-website-us-east-1.amazonaws.com
```
<img width="1253" height="707" alt="image" src="https://github.com/user-attachments/assets/54ff4017-594f-4444-a126-3663b7cc365a" />

`XXXXXXXXXX` is your unique API ID — you will need it in the next steps.

---

### 4. Patch index.html with your real API URL

The frontend ships with a placeholder URL. Replace it with your actual API ID:

```bash
sed -i 's|REPLACE_WITH_YOUR_API_ID|XXXXXXXXXX|' frontend/index.html
```

Example: if your ApiUrl is `https://960e4878fb.execute-api.us-east-1.amazonaws.com/Prod`, then `XXXXXXXXXX` = `960e4878fb`.

### 5. Upload index.html to S3

This pushes the patched frontend to your live S3 website bucket:

```bash
aws s3 cp frontend/index.html s3://ai-dashboard-frontend-$(aws sts get-caller-identity --query Account --output text)/index.html \
  --content-type "text/html"
```

### 6. Redeploy with the real RedirectUri

The initial deploy used a placeholder RedirectUri. This updates the Lambda with the real one so Google OAuth works correctly:

```bash
sam deploy --parameter-overrides \
  GoogleClientId="YOUR_CLIENT_ID" \
  GoogleClientSecret="YOUR_CLIENT_SECRET" \
  RedirectUri="https://XXXXXXXXXX.execute-api.us-east-1.amazonaws.com/Prod/callback"
```

## Place the credentials from output into your Google OAuth Redirected Redirect URIs / JavaScript Origins -- Add /callback.
| Field | Value |
|---|---|
| Authorized JavaScript origins | `http://ai-dashboard-frontend-XXXXXXXXXXXX.s3-website-us-east-1.amazonaws.com` |
| Authorized redirect URIs | `https://XXXXXXXXXX.execute-api.us-east-1.amazonaws.com/Prod/callback` |
<img width="1912" height="707" alt="image" src="https://github.com/user-attachments/assets/9eac829f-84d8-43d6-aed6-426e18d9caaa" />
<img width="1912" height="975" alt="image" src="https://github.com/user-attachments/assets/fbdf0b23-0a23-47b0-83b6-bbdd3783213c" />

> Note: JS origins uses **http** (S3 website), redirect URI uses **https** (API Gateway).



## Usage


1. Visit your FrontendUrl in a browser
   <img width="1903" height="997" alt="image" src="https://github.com/user-attachments/assets/92f3db48-8528-4e0a-90c2-b6b277c2007d" />

3. Click **Connect Google Account**
   <img width="1910" height="1016" alt="image" src="https://github.com/user-attachments/assets/fed55ae2-f049-44ec-bf89-d4f37142468a" />

4. Authorize Gmail and Calendar access
<img width="1917" height="1014" alt="image" src="https://github.com/user-attachments/assets/05520c8c-00c0-49ca-96af-af7b02ecd132" />

5. Ask questions like:
   - *What's on my calendar this week?*
   - *Summarize my recent emails*
<img width="1910" height="1034" alt="image" src="https://github.com/user-attachments/assets/27a8551a-7dcd-4bda-87a7-51c59694f639" />
> Bedrock free-tier token quota was hit during this demo — a quota increase request has since been submitted. The screenshot still showcases the full pipeline working end to end: Google OAuth, session creation, Gmail/Calendar data fetch, and a live Bedrock API call.<img width="1900" height="867" alt="image" src="https://github.com/user-attachments/assets/9f1e0cca-1b31-4b82-aa92-0edf3799204e" />

---

## Lastly

- All Sessions expire after 1 hour via DynamoDB TTL
- Bedrock has a daily token quota due to AWS Service Quotas
- `samconfig.toml` is intentionally excluded from this repo — but it gets created locally when you run `sam deploy --guided`
