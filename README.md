# ⚡ Cloud Strife — Kuda Bank AWS Architecture Prototype

> *"Built under pressure. Forged in the cloud."*

An AWS cloud architecture prototype for a Nigerian neobank, built as a capstone project under the **Cloud Strife** personal brand. The full design spans 29 services across 6 layers, aligned with the AWS Well-Architected Framework (all 6 pillars including Sustainability). The critical path — automated KYC verification and real-time fraud detection — is deployed and reproducible from this repo with Terraform.

> **Disclaimer:** This is an independent learning project. It is not affiliated with, endorsed by, or built for Kuda Microfinance Bank. "Kuda" is used only as the reference scenario for a Nigerian neobank.

---

## Architecture Overview

![Cloud Strife Architecture](<architecture/Cloud Strife Architectural Diagram-Page-1.drawio.png>)

**6 Layers:** Presentation · Application · Security · Data · Compute · Observability  
**29 AWS Services** · Region: `eu-west-1` (Ireland)  
**Framework:** AWS Well-Architected (Operational Excellence, Security, Reliability, Performance, Cost Optimization, Sustainability)

---

## Demo Scenarios

### Scenario 1 — Smooth Automated KYC Match ✅
Demonstrates immediate customer onboarding with AI-powered identity verification.

- ID document and selfie uploaded to S3
- Step Functions pipeline is started for the customer's `userId`
- Rekognition `CompareFaces` returns similarity ≥ 80% (configurable)
- Execution graph ends at **ApproveKYC**
- DynamoDB persists `kycStatus = APPROVED` with similarity score and audit log

### Scenario 2 — Identity Spoofing Caught 🚫
Validates the system blocks bad actors automatically at the door.

- Different face uploaded as selfie vs ID document
- Step Functions routes through `KYCDecision` → **FlagIdentityMismatch**
- DynamoDB audit record shows `kycStatus = REJECTED`, `reason = IDENTITY_MISMATCH_FLAGGED`
- A selfie or ID image with no detectable face is also rejected cleanly (`reason = NO_FACE_DETECTED`) instead of crashing the pipeline
- Full execution history preserved for compliance

### Scenario 3 — Real-Time Threat Ingestion ⚠️
Simulates transaction volume processing with streaming risk analysis.

- Normal transactions (< NGN 500,000) processed and logged silently
- High-value transaction (NGN 750,000) triggers automatic flagging
- Flagged transaction routed to SQS queue for review (with a dead-letter queue)
- SNS alert fires instantly to the fraud operations team
- Invalid input (missing, zero or negative amounts) is rejected before anything is written

---

## Services Used

**Deployed by this repo (Terraform):** Lambda, Step Functions, S3, DynamoDB, Rekognition, SQS, SNS, IAM, CloudWatch.  
The remaining services are part of the full design documented in the SOW.

| Layer | Services |
|---|---|
| Compute | AWS Lambda, Amazon ECS Fargate |
| Orchestration | AWS Step Functions |
| Storage | Amazon S3, Amazon DynamoDB, Amazon RDS, Amazon ElastiCache |
| AI / ML | Amazon Rekognition, Amazon Textract |
| Messaging | Amazon SNS, Amazon SQS, Amazon EventBridge |
| Security | AWS IAM, Amazon Cognito, AWS WAF, AWS Shield, AWS KMS, Amazon GuardDuty, AWS Macie, AWS Secrets Manager |
| Networking | Amazon VPC, Amazon Route 53, Amazon CloudFront, API Gateway |
| Observability | Amazon CloudWatch, AWS CloudTrail, AWS Config |
| Management | AWS Systems Manager, AWS Cost Explorer |

---

## Repository Structure

```
cloud-strife-kuda/
├── lambdas/
│   ├── kyc_validate_uploads.py       # Validates S3 uploads before processing
│   ├── kyc_compare_faces.py          # Rekognition face comparison
│   ├── kyc_update_status.py          # Persists KYC decision to DynamoDB
│   └── transaction_processor.py     # Routes transactions, triggers SQS + SNS
├── step-functions/
│   └── kuda-kyc-pipeline.json        # State machine ASL template (ARNs filled by Terraform)
├── infra/terraform/                  # Infrastructure as code for the deployed critical path
│   ├── storage.tf                    # S3, DynamoDB, SQS (+ DLQ), SNS
│   ├── lambda.tf                     # 4 Lambdas, each with its own least-privilege IAM role
│   ├── stepfunctions.tf              # KYC state machine + logging
│   ├── variables.tf / outputs.tf
│   └── terraform.tfvars.example
├── architecture/
│   └── Cloud Strife Architectural Diagram-Page-1.drawio.png   # Full 6-layer architecture diagram
├── docs/
│   └── Cloud Strife Kuda SOW v4.docx # Statement of Work (v4)
└── README.md
```

---

## Deploy It Yourself

Requires Terraform ≥ 1.6 and AWS credentials for an account you own. Everything runs within (or close to) the AWS Free Tier; Rekognition is billed per image comparison after the free tier.

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars   # optional: set fraud_alert_email
terraform init
terraform apply
```

**Run Scenario 1 / 2 (KYC):**

```bash
BUCKET=$(terraform output -raw kyc_bucket_name)
aws s3 cp id.jpg     s3://$BUCKET/kyc/user-001/id-document.jpg
aws s3 cp selfie.jpg s3://$BUCKET/kyc/user-001/selfie.jpg

aws stepfunctions start-execution \
  --state-machine-arn "$(terraform output -raw kyc_state_machine_arn)" \
  --input "{\"bucket\": \"$BUCKET\", \"userId\": \"user-001\"}"
```

**Run Scenario 3 (fraud detection):**

```bash
aws lambda invoke \
  --function-name "$(terraform output -raw transaction_processor_function_name)" \
  --cli-binary-format raw-in-base64-out \
  --payload '{"userId": "user-001", "amount": 750000}' response.json
```

Tear everything down with `terraform destroy`. The KYC bucket is versioned, so empty it (including old versions) first.

No account IDs or ARNs are hardcoded: Lambdas read their table names, queue URL, topic ARN and thresholds from environment variables set by Terraform.

---

## Key Design Decisions

**Why Step Functions over direct Lambda chaining?**  
Step Functions provides a visual execution graph, built-in error handling, and a full audit trail of every state transition — essential for a regulated fintech environment.

**Why eu-west-1?**  
Amazon Rekognition is not available in af-south-1 (Cape Town). eu-west-1 (Ireland) offers the lowest latency from Nigeria among supported regions.

**Why DynamoDB for KYC records?**  
Serverless, schema-flexible, and permanently free tier. KYC records have variable attributes per document type — DynamoDB handles this naturally.

**Similarity threshold: 80%**  
Balances false rejection rate against security. Tunable per compliance requirements via the `similarity_threshold` Terraform variable. The threshold is applied in exactly one place (`kyc_compare_faces`), which emits a `faceMatch` boolean that the state machine and status Lambda both read, so the two can never disagree.

**Retries vs. failures**  
Transient Lambda and Rekognition errors (throttling, service exceptions) are retried with exponential backoff. Missing uploads fail fast to `UploadError`; anything unexpected goes to `ProcessingError`, so the two are never confused.

**Least privilege**  
Each Lambda has its own IAM role scoped to exactly the bucket prefix, table, queue or topic it touches. The KYC bucket blocks public access, enforces TLS, and is encrypted and versioned. Step Functions logging excludes execution data to keep customer PII out of CloudWatch.

---

## Prototype vs Production

This repository is a **functional prototype** demonstrating the critical path of the architecture. Expensive services (ECS Fargate, RDS, ElastiCache, CloudFront) are documented in the SOW rather than provisioned, keeping this build within AWS Free Tier.

| Service | Prototype | Production |
|---|---|---|
| KYC Pipeline | ✅ Deployed via Terraform | ✅ |
| Fraud Detection | ✅ Deployed via Terraform | ✅ |
| Frontend | — | CloudFront + Amplify |
| Database | DynamoDB (demo) | RDS + ElastiCache |
| Container Workloads | — | ECS Fargate |

---

## Built By

**Abdulmujeeb** · Computer Engineering Undergraduate, University of Ilorin  
AWS Cloud Club Unilorin · AWS Cloud Club Bootcamp 2026

*Cloud Strife is a personal brand built on the philosophy of growth through struggle —  
named after the Final Fantasy VII protagonist who carried the weight of the world and kept moving.*

🔗 [GitHub](https://github.com/abdulmujeebusman)
<!-- TODO: add LinkedIn and X links here, e.g. · [LinkedIn](https://linkedin.com/in/<your-handle>) · [X / Twitter](https://x.com/<your-handle>) -->


---

> *This project is part of the Cloud Strife portfolio series — real architecture, real AWS, real proof of work.*
