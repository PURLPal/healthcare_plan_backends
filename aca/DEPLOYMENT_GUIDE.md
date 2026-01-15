# ACA API Deployment Guide

Complete step-by-step guide to deploy the ACA Plan API to AWS.

---

## Prerequisites

- AWS account with appropriate permissions
- AWS CLI configured with profile
- PostgreSQL client installed
- Python 3.11+

---

## Step 1: Create RDS PostgreSQL Database

### Create the database instance

```bash
# Set variables
export DB_PASSWORD="<GENERATE_STRONG_PASSWORD>"
export AWS_PROFILE="silverman"  # or your AWS profile
export AWS_REGION="us-east-1"

# Create RDS instance
aws rds create-db-instance \
  --db-instance-identifier aca-plans-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --engine-version 15.4 \
  --master-username aca_admin \
  --master-user-password "$DB_PASSWORD" \
  --allocated-storage 20 \
  --storage-type gp3 \
  --publicly-accessible \
  --backup-retention-period 7 \
  --vpc-security-group-ids <YOUR_SECURITY_GROUP> \
  --region $AWS_REGION \
  --profile $AWS_PROFILE
```

### Wait for database to be available

```bash
aws rds wait db-instance-available \
  --db-instance-identifier aca-plans-db \
  --region $AWS_REGION \
  --profile $AWS_PROFILE
```

### Get database endpoint

```bash
export DB_ENDPOINT=$(aws rds describe-db-instances \
  --db-instance-identifier aca-plans-db \
  --region $AWS_REGION \
  --profile $AWS_PROFILE \
  --query 'DBInstances[0].Endpoint.Address' \
  --output text)

echo "Database endpoint: $DB_ENDPOINT"
```

---

## Step 2: Initialize Database Schema

### Test connection

```bash
psql -h $DB_ENDPOINT -U aca_admin -d postgres
# Enter password when prompted
# Type \q to exit
```

### Create database (if needed)

```bash
psql -h $DB_ENDPOINT -U aca_admin -d postgres -c "CREATE DATABASE aca_plans;"
```

### Load schema

```bash
psql -h $DB_ENDPOINT -U aca_admin -d aca_plans -f database/schema.sql
```

**Verify tables created:**
```bash
psql -h $DB_ENDPOINT -U aca_admin -d aca_plans -c "\dt"
```

Expected output:
```
             List of relations
 Schema |        Name         | Type  |   Owner   
--------+---------------------+-------+-----------
 public | benefits            | table | aca_admin
 public | counties            | table | aca_admin
 public | plan_service_areas  | table | aca_admin
 public | plans               | table | aca_admin
 public | rates               | table | aca_admin
 public | service_areas       | table | aca_admin
 public | zip_counties        | table | aca_admin
```

---

## Step 3: Load Data into Database

### Install Python dependencies

```bash
pip3 install psycopg2-binary
```

### Run data loader

```bash
python3 database/load_data.py "host=$DB_ENDPOINT dbname=aca_plans user=aca_admin password=$DB_PASSWORD"
```

**Expected output:**
```
============================================================
ACA Plan Data Loader
============================================================

=== Loading Counties and ZIP Mapping ===
Loading county reference data...
Inserting 3,234 counties...
Loading ZIP-to-county mapping...
Inserting 50,000+ ZIP-county mappings...
✓ Loaded 3,234 counties, 50,000+ ZIP mappings

=== Loading Service Areas ===
Inserting 8,202 service areas...
✓ Loaded 8,202 service areas

=== Loading Plans ===
Inserting 19,272 plans...
✓ Loaded 19,272 plans

=== Loading Rates ===
Processing rate file...
Inserting 800,000+ rate records...
✓ Loaded 800,000+ rate records

=== Database Summary ===
Counties: 3,234
ZIP Codes: 39,298
Service Areas: 8,202
Plans: 19,272
Rates: 800,000+
States with Plans: 32

Plans by Metal Level:
  Silver: 6,500
  Bronze: 5,200
  Gold: 4,800
  Platinum: 2,500
  Catastrophic: 272
```

### Verify data loaded

```bash
psql -h $DB_ENDPOINT -U aca_admin -d aca_plans -c "SELECT COUNT(*) FROM plans;"
psql -h $DB_ENDPOINT -U aca_admin -d aca_plans -c "SELECT state_code, COUNT(*) FROM plans GROUP BY state_code ORDER BY state_code LIMIT 10;"
```

---

## Step 4: Create Lambda Deployment Package

### Prepare Lambda package

```bash
cd lambda

# Create package directory
mkdir -p package

# Install pg8000 (PostgreSQL driver)
pip3 install --target ./package pg8000

# Copy Lambda function
cp aca_api.py package/

# Create deployment package
cd package
zip -r ../aca-api.zip .
cd ..

# Verify package
ls -lh aca-api.zip
```

---

## Step 5: Create IAM Role for Lambda

### Create trust policy

```bash
cat > lambda-trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
```

### Create IAM role

```bash
aws iam create-role \
  --role-name ACA_API_Lambda_Role \
  --assume-role-policy-document file://lambda-trust-policy.json \
  --profile $AWS_PROFILE
```

### Attach basic Lambda execution policy

```bash
aws iam attach-role-policy \
  --role-name ACA_API_Lambda_Role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole \
  --profile $AWS_PROFILE
```

### Get role ARN

```bash
export LAMBDA_ROLE_ARN=$(aws iam get-role \
  --role-name ACA_API_Lambda_Role \
  --query 'Role.Arn' \
  --output text \
  --profile $AWS_PROFILE)

echo "Lambda Role ARN: $LAMBDA_ROLE_ARN"
```

---

## Step 6: Deploy Lambda Function

### Create Lambda function

```bash
cd lambda

aws lambda create-function \
  --function-name ACA_API \
  --runtime python3.11 \
  --handler aca_api.lambda_handler \
  --role $LAMBDA_ROLE_ARN \
  --zip-file fileb://aca-api.zip \
  --environment Variables="{DB_HOST=$DB_ENDPOINT,DB_PORT=5432,DB_NAME=aca_plans,DB_USER=aca_admin,DB_PASSWORD=$DB_PASSWORD}" \
  --timeout 30 \
  --memory-size 512 \
  --region $AWS_REGION \
  --profile $AWS_PROFILE
```

### Test Lambda function

```bash
aws lambda invoke \
  --function-name ACA_API \
  --payload '{"rawPath":"/aca/states.json","requestContext":{"http":{"method":"GET"}}}' \
  --region $AWS_REGION \
  --profile $AWS_PROFILE \
  response.json

cat response.json | jq '.'
```

---

## Step 7: Create API Gateway

### Create HTTP API

```bash
aws apigatewayv2 create-api \
  --name "ACA Plan API" \
  --protocol-type HTTP \
  --region $AWS_REGION \
  --profile $AWS_PROFILE
```

### Get API ID

```bash
export API_ID=$(aws apigatewayv2 get-apis \
  --query "Items[?Name=='ACA Plan API'].ApiId" \
  --output text \
  --region $AWS_REGION \
  --profile $AWS_PROFILE)

echo "API ID: $API_ID"
```

### Create Lambda integration

```bash
export LAMBDA_ARN=$(aws lambda get-function \
  --function-name ACA_API \
  --query 'Configuration.FunctionArn' \
  --output text \
  --region $AWS_REGION \
  --profile $AWS_PROFILE)

aws apigatewayv2 create-integration \
  --api-id $API_ID \
  --integration-type AWS_PROXY \
  --integration-uri $LAMBDA_ARN \
  --payload-format-version 2.0 \
  --region $AWS_REGION \
  --profile $AWS_PROFILE
```

### Get integration ID

```bash
export INTEGRATION_ID=$(aws apigatewayv2 get-integrations \
  --api-id $API_ID \
  --query 'Items[0].IntegrationId' \
  --output text \
  --region $AWS_REGION \
  --profile $AWS_PROFILE)
```

### Create route

```bash
aws apigatewayv2 create-route \
  --api-id $API_ID \
  --route-key 'ANY /aca/{proxy+}' \
  --target "integrations/$INTEGRATION_ID" \
  --region $AWS_REGION \
  --profile $AWS_PROFILE
```

### Create stage

```bash
aws apigatewayv2 create-stage \
  --api-id $API_ID \
  --stage-name prod \
  --auto-deploy \
  --region $AWS_REGION \
  --profile $AWS_PROFILE
```

### Grant API Gateway permission to invoke Lambda

```bash
aws lambda add-permission \
  --function-name ACA_API \
  --statement-id apigateway-invoke \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:$AWS_REGION:*:$API_ID/*/*/aca/*" \
  --region $AWS_REGION \
  --profile $AWS_PROFILE
```

### Get API endpoint

```bash
export API_ENDPOINT=$(aws apigatewayv2 get-api \
  --api-id $API_ID \
  --query 'ApiEndpoint' \
  --output text \
  --region $AWS_REGION \
  --profile $AWS_PROFILE)

echo "API Endpoint: $API_ENDPOINT"
```

---

## Step 8: Test Deployed API

### Test states endpoint

```bash
curl "$API_ENDPOINT/prod/aca/states.json" | jq '.state_count'
```

### Test ZIP code endpoint

```bash
curl "$API_ENDPOINT/prod/aca/zip/02108.json" | jq '{zip_code, plan_count, plan_counts_by_metal_level}'
```

### Test metal level filtering

```bash
curl "$API_ENDPOINT/prod/aca/zip/02108_Silver.json" | jq '{plan_count, metal_level: .plans[0].metal_level}'
```

---

## Step 9: Configure Custom Domain (Optional)

### Create custom domain

```bash
aws apigatewayv2 create-domain-name \
  --domain-name aca.purlpal-api.com \
  --domain-name-configurations CertificateArn=<YOUR_ACM_CERT_ARN> \
  --region $AWS_REGION \
  --profile $AWS_PROFILE
```

### Create API mapping

```bash
aws apigatewayv2 create-api-mapping \
  --domain-name aca.purlpal-api.com \
  --api-id $API_ID \
  --stage prod \
  --api-mapping-key aca \
  --region $AWS_REGION \
  --profile $AWS_PROFILE
```

### Update Route 53

Get the API Gateway domain name and create a CNAME record pointing to it.

---

## Updating the API

### Update Lambda code

```bash
cd lambda

# Make changes to aca_api.py

# Repackage
cp aca_api.py package/
cd package
zip -r ../aca-api.zip .
cd ..

# Update Lambda
aws lambda update-function-code \
  --function-name ACA_API \
  --zip-file fileb://aca-api.zip \
  --region $AWS_REGION \
  --profile $AWS_PROFILE
```

### Wait for update to complete

```bash
aws lambda wait function-updated \
  --function-name ACA_API \
  --region $AWS_REGION \
  --profile $AWS_PROFILE
```

---

## Monitoring

### View CloudWatch Logs

```bash
aws logs tail /aws/lambda/ACA_API --follow --region $AWS_REGION --profile $AWS_PROFILE
```

### Check Lambda metrics

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=ACA_API \
  --start-time 2026-01-01T00:00:00Z \
  --end-time 2026-01-15T00:00:00Z \
  --period 3600 \
  --statistics Sum \
  --region $AWS_REGION \
  --profile $AWS_PROFILE
```

---

## Troubleshooting

### Lambda timeout errors

Increase timeout:
```bash
aws lambda update-function-configuration \
  --function-name ACA_API \
  --timeout 60 \
  --region $AWS_REGION \
  --profile $AWS_PROFILE
```

### Database connection errors

1. Check security group allows Lambda to reach RDS
2. Verify environment variables are correct
3. Check RDS is publicly accessible or Lambda is in same VPC

### 404 errors

Verify API Gateway routes are configured correctly:
```bash
aws apigatewayv2 get-routes --api-id $API_ID --region $AWS_REGION --profile $AWS_PROFILE
```

---

## Cost Optimization

### Use Reserved Capacity for RDS

If running 24/7, consider Reserved Instances to save 30-50%.

### Adjust Lambda Memory

Monitor Lambda performance and adjust memory allocation:
```bash
aws lambda update-function-configuration \
  --function-name ACA_API \
  --memory-size 256 \
  --region $AWS_REGION \
  --profile $AWS_PROFILE
```

---

## Cleanup (if needed)

```bash
# Delete API Gateway
aws apigatewayv2 delete-api --api-id $API_ID --region $AWS_REGION --profile $AWS_PROFILE

# Delete Lambda
aws lambda delete-function --function-name ACA_API --region $AWS_REGION --profile $AWS_PROFILE

# Delete RDS
aws rds delete-db-instance \
  --db-instance-identifier aca-plans-db \
  --skip-final-snapshot \
  --region $AWS_REGION \
  --profile $AWS_PROFILE
```

---

## Summary Checklist

- [ ] RDS database created and accessible
- [ ] Database schema loaded
- [ ] Data loaded successfully (19,272 plans)
- [ ] Lambda function created and tested
- [ ] API Gateway configured
- [ ] API endpoints tested
- [ ] Custom domain configured (optional)
- [ ] CloudWatch logging enabled
- [ ] Documentation updated

---

## Next Steps

1. Run comprehensive tests with `tests/quick_test.sh`
2. Create API documentation
3. Set up monitoring alerts
4. Configure backup retention
5. Implement rate limiting if needed
