# ⚡ Cloud Strife — Kuda Bank AWS Architecture Prototype

> *"Built under pressure. Forged in the cloud."*

A production-grade AWS cloud architecture prototype for a Nigerian neobank, built as a capstone project under the **Cloud Strife** personal brand. This project demonstrates automated KYC verification, real-time fraud detection, and resilient banking infrastructure across a 29-service, 6-layer AWS architecture aligned with the AWS Well-Architected Framework (all 6 pillars including Sustainability).

---

## Architecture Overview

![Cloud Strife Architecture](architecture/kuda-architecture.png)

**6 Layers:** Presentation · Application · Security · Data · Compute · Observability  
**29 AWS Services** · Region: `eu-west-1` (Ireland)  
**Framework:** AWS Well-Architected (Operational Excellence, Security, Reliability, Performance, Cost Optimization, Sustainability)

---

## Demo Scenarios

### Scenario 1 — Smooth Automated KYC Match ✅
Demonstrates immediate customer onboarding with AI-powered identity verification.

- ID document and selfie uploaded to S3
- Step Functions pipeline executes automatically
- Rekognition `CompareFaces` returns similarity ≥ 80%
- Execution graph ends at **ApproveKYC**
- DynamoDB persists `kycStatus = APPROVED` with similarity score and audit log

### Scenario 2 — Identity Spoofing Caught 🚫
Validates the system blocks bad actors automatically at the door.

- Different face uploaded as selfie vs ID document
- Step Functions routes through `KYCDecision` → **FlagIdentityMismatch**
- DynamoDB audit record shows `kycStatus = REJECTED`, `reason = IDENTITY_MISMATCH_FLAGGED`
- Full execution history preserved for compliance

### Scenario 3 — Real-Time Threat Ingestion ⚠️
Simulates transaction volume processing with streaming risk analysis.

- Normal transactions (< NGN 500,000) processed and logged silently
- High-value transaction (NGN 750,000) triggers automatic flagging
- Flagged transaction routed to SQS queue for review
- SNS alert fires instantly to the fraud operations team

---

## Services Used

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
│   └── kuda-kyc-pipeline.json        # State machine ASL definition
├── architecture/
│   └── kuda-architecture.png         # Full 6-layer architecture diagram
├── docs/
│   └── Cloud_Strife_Kuda_SOW_v3.docx # Statement of Work (v3)
└── README.md
```

---

## Key Design Decisions

**Why Step Functions over direct Lambda chaining?**  
Step Functions provides a visual execution graph, built-in error handling, and a full audit trail of every state transition — essential for a regulated fintech environment.

**Why eu-west-1?**  
Amazon Rekognition is not available in af-south-1 (Cape Town). eu-west-1 (Ireland) offers the lowest latency from Nigeria among supported regions.

**Why DynamoDB for KYC records?**  
Serverless, schema-flexible, and permanently free tier. KYC records have variable attributes per document type — DynamoDB handles this naturally.

**Similarity threshold: 80%**  
Balances false rejection rate against security. Tunable per compliance requirements.

---

## Prototype vs Production

This repository is a **functional prototype** demonstrating the critical path of the architecture. Expensive services (ECS Fargate, RDS, ElastiCache, CloudFront) are documented in the SOW rather than provisioned, keeping this build within AWS Free Tier.

| Service | Prototype | Production |
|---|---|---|
| KYC Pipeline | ✅ Fully deployed | ✅ |
| Fraud Detection | ✅ Fully deployed | ✅ |
| Frontend | — | CloudFront + Amplify |
| Database | DynamoDB (demo) | RDS + ElastiCache |
| Container Workloads | — | ECS Fargate |

---

## Built By

**Abdulmujeeb** · Computer Engineering Undergraduate, University of Ilorin  
AWS Cloud Club Unilorin · AWS Cloud Club Bootcamp 2026

*Cloud Strife is a personal brand built on the philosophy of growth through struggle —  
named after the Final Fantasy VII protagonist who carried the weight of the world and kept moving.*

🔗 [LinkedIn](https://linkedin.com/in/YOUR_LINKEDIN) · [X / Twitter](https://x.com/YOUR_HANDLE)

---

> *This project is part of the Cloud Strife portfolio series — real architecture, real AWS, real proof of work.*
