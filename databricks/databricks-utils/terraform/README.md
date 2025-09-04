# Databricks AWS Deployment with Unity Catalog - Complete Guide

This guide provides step-by-step instructions for deploying a complete Databricks infrastructure in AWS using **100% Terraform**, including workspace creation, Unity Catalog setup with storage credentials and external locations.

## 🎯 **Terraform-First Approach**

This guide follows a **Terraform-first approach**:
1. **AWS Marketplace**: Create and link Databricks account only (NO workspace creation)
2. **Service Principal**: Set up authentication for Terraform
3. **Terraform**: Deploy ALL infrastructure including first workspace, Unity Catalog, storage, and networking
4. **Verification**: Test complete setup via SQL and REST API

**Key Principle**: Once your Databricks account exists, everything else is managed as code via Terraform.

## Prerequisites

### Required Software
- **Terraform CLI**: 1.13.1+ (latest stable) or 1.14.0+ (alpha)
- **Git**: For cloning and version control

### Required Permissions

#### AWS Account Requirements
- Permission to provision IAM roles and policies
- Permission to create S3 buckets
- Permission to create cross-account trust relationships
- Available service quotas in your target AWS region
- Available VPC and NAT gateway

#### Databricks Account Requirements
- **Databricks Premium plan or above** (required for Unity Catalog)
- Account admin permissions for initial setup
- Ability to create service principals

## Deployment Workflow Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────────┐    ┌──────────────────┐
│  AWS Marketplace │───▶│  Databricks      │───▶│  Terraform          │───▶│  Verification    │
│  Account Setup   │    │  Authentication  │    │  Infrastructure     │    │  & Testing       │
└─────────────────┘    └──────────────────┘    └─────────────────────┘    └──────────────────┘
 • Subscribe only     • Create service     • Workspace creation   • SQL queries
 • Link accounts        principal          • Unity Catalog       • REST API calls
 • NO workspaces!     • Generate OAuth     • Storage & IAM       • End-to-end tests
                        credentials        • Networking setup
```

## Step 1: AWS Marketplace Account Setup (Account Only)

### 1.1 Subscribe to Databricks via AWS Marketplace

1. Navigate to the [Databricks Data Intelligence Platform on AWS Marketplace](https://aws.amazon.com/marketplace/pp/prodview-wtyi5lgtce6n6)
2. Choose **Try for free** or **View purchase options**
3. Choose **Subscribe** (processing may take a few minutes)

### 1.2 Create Databricks Account (Account Only)

1. Choose **Create account** - you'll be redirected to Databricks registration
2. Follow on-screen prompts to register with Databricks
3. Return to AWS Marketplace and confirm account linking success message

### 1.3 ⚠️ **CRITICAL: Stop Here - Do NOT Create Workspace**

**🛑 STOP**: If you see workspace creation options:
- **DO NOT** click "Configure workspace"
- **DO NOT** create any workspaces through the UI
- **DO NOT** proceed with quickstart workspace deployment

**✅ SUCCESS**: You should now have:
- A Databricks account created
- Account linked to your AWS account  
- Access to the Databricks account console
- **NO workspaces created yet**

**🎯 Next**: All workspace creation and infrastructure will be handled by Terraform in Step 4.

## Step 2: Service Principal Setup

### 2.1 Create Service Principal

1. In the Databricks account console, go to **User management** → **Service principals**
2. Click **Add service principal**
3. Enter name: `terraform-sp-{YOUR_ORG_NAME}`
4. Click **Add**
5. Generate OAuth client credentials:
   - Click on the service principal name
   - Go to **OAuth secrets** tab
   - Click **Generate secret**
   - **Save the Client ID and Client Secret securely**

### 2.2 Assign Account Admin Role

1. Go to **User management** → **Service principals**
2. Click on your service principal
3. Go to **Roles** tab
4. Click **Add role**
5. Select **Account admin**
6. Click **Save**

## Step 3: Environment Setup

### 3.1 Required Environment Variables

Create a `.env` file or set these environment variables:

```bash
# Databricks Authentication
export DATABRICKS_CLIENT_ID="your-client-id-here"
export DATABRICKS_CLIENT_SECRET="your-client-secret-here"
export DATABRICKS_ACCOUNT_ID="your-account-id-here"

# AWS Configuration
export AWS_ACCESS_KEY_ID="your-aws-access-key"
export AWS_SECRET_ACCESS_KEY="your-aws-secret-key"
export AWS_REGION="us-east-1"  # or your preferred region

# Terraform Variables
export TF_VAR_databricks_account_id="your-account-id-here"
export TF_VAR_aws_region="us-east-1"
```

### 3.2 Install Terraform

```bash
# Install Terraform (latest version)
curl -fsSL https://apt.releases.hashicorp.com/gpg | sudo apt-key add -
sudo apt-add-repository "deb [arch=amd64] https://apt.releases.hashicorp.com $(lsb_release -cs) main"
sudo apt-get update && sudo apt-get install terraform

# Alternative: Download from HashiCorp releases
# Visit: https://releases.hashicorp.com/terraform/

# Verify installation
terraform --version
```

## Step 4: Terraform Infrastructure Deployment

This step creates **ALL** Databricks infrastructure including:
- ✅ **First workspace** (no manual workspace creation needed)
- ✅ **Unity Catalog metastore** with root storage location  
- ✅ **Storage credentials** and external locations
- ✅ **S3 buckets** with proper encryption and policies
- ✅ **IAM roles** with correct trust relationships
- ✅ **Primary catalog** and default schema
- ✅ **Networking** configuration (VPC, subnets, security groups)

### 4.1 Navigate to Configuration Directory and Initialize Terraform

```bash
# Navigate to the Terraform configuration directory
cd databricks-utils/terraform

# Initialize Terraform (downloads required providers)
terraform init
```

### 4.2 Customize Variables

1. Copy the example variables file:
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   ```

2. Edit `terraform.tfvars` with your specific values:
   ```hcl
   # Customer-specific values
   organization_name = "your-company"
   aws_region        = "us-east-1"
   
   # Unity Catalog Configuration
   metastore_name = "your-company-metastore"
   catalog_name   = "your_company_catalog"
   
   # Storage Configuration
   root_storage_bucket_name = "your-company-databricks-root-storage"
   
   # Admin Configuration
   unity_admin_group = "unity-catalog-admins"
   ```

### 4.3 Validate Configuration

```bash
terraform validate
```

### 4.4 Plan Deployment

```bash
terraform plan
```

Review the planned changes carefully before proceeding.

### 4.5 Deploy Infrastructure

```bash
terraform apply
```

Type `yes` when prompted to confirm the deployment.

**🎉 Upon Successful Deployment**, Terraform will have created:
- Your **first Databricks workspace** (accessible via browser)
- Complete **Unity Catalog** infrastructure with metastore and root storage
- **Storage credentials** for S3 access
- **External locations** for data access
- **IAM roles and policies** with proper permissions
- **S3 buckets** with encryption and security controls
- **Primary catalog** with default schema ready for use

You can now access your workspace URL (shown in Terraform outputs) and begin using Unity Catalog immediately.

## Step 5: Verification and Testing

### 5.1 Verify Workspace Access

1. **Navigate to Workspace**: Open your browser and go to the workspace URL:
   ```bash
   echo "Workspace URL: $(terraform output -raw databricks_workspace_url)"
   ```

2. **Login**: Use your Databricks account credentials to log into the workspace

### 5.2 Verify Unity Catalog Setup

#### 5.2.1 SQL Commands (via Databricks SQL Editor)

```sql
-- List available catalogs
SHOW CATALOGS;

-- Verify metastore assignment and root location
SELECT current_metastore();

-- Check metastore details including root location
DESCRIBE METASTORE;

-- Verify metastore has a root location configured
SELECT 
  metastore_id,
  name,
  storage_root,
  owner,
  region
FROM system.information_schema.metastores;

-- Check external locations
SHOW EXTERNAL LOCATIONS;

-- Test storage credential access
DESCRIBE STORAGE CREDENTIAL `<your-storage-credential-name>`;

-- Verify all storage credentials
SHOW STORAGE CREDENTIALS;
```

#### 5.2.2 REST API Verification

First, obtain an access token from your Databricks workspace:
1. Go to **User Settings** → **Developer** → **Access tokens**
2. Click **Generate new token**
3. Copy the token for use in API calls

```bash
# Set your access token as an environment variable
export DATABRICKS_TOKEN="your-access-token-here"

# Get workspace information
curl -X GET \
  "$(terraform output -raw databricks_workspace_url)/api/2.0/workspace/list" \
  -H "Authorization: Bearer $DATABRICKS_TOKEN"

# List Unity Catalog metastores (requires account-level token)
curl -X GET \
  "https://accounts.cloud.databricks.com/api/2.0/unity-catalog/metastores" \
  -H "Authorization: Bearer $DATABRICKS_ACCOUNT_TOKEN"

# List external locations
curl -X GET \
  "$(terraform output -raw databricks_workspace_url)/api/2.1/unity-catalog/external-locations" \
  -H "Authorization: Bearer $DATABRICKS_TOKEN"

# List storage credentials
curl -X GET \
  "$(terraform output -raw databricks_workspace_url)/api/2.1/unity-catalog/storage-credentials" \
  -H "Authorization: Bearer $DATABRICKS_TOKEN"

# Get catalog information
curl -X GET \
  "$(terraform output -raw databricks_workspace_url)/api/2.1/unity-catalog/catalogs" \
  -H "Authorization: Bearer $DATABRICKS_TOKEN"
```

### 5.3 Comprehensive Unity Catalog Testing

#### 5.3.1 Create Additional Storage Credential and External Location via REST API

```bash
# Create a new storage credential for testing
curl -X POST \
  "$(terraform output -raw databricks_workspace_url)/api/2.1/unity-catalog/storage-credentials" \
  -H "Authorization: Bearer $DATABRICKS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test-storage-credential",
    "comment": "Test storage credential for verification",
    "aws_iam_role": {
      "role_arn": "'$(terraform output -raw unity_catalog_iam_role_arn)'"
    }
  }'

# Create a new external location for testing
curl -X POST \
  "$(terraform output -raw databricks_workspace_url)/api/2.1/unity-catalog/external-locations" \
  -H "Authorization: Bearer $DATABRICKS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test-external-location",
    "url": "s3://'$(terraform output -raw root_storage_bucket)'/test-data/",
    "credential_name": "test-storage-credential",
    "comment": "Test external location for verification"
  }'
```

#### 5.3.2 Test Managed Catalog Operations (Writing to Catalog)

```sql
-- Create a schema in your managed catalog
CREATE SCHEMA IF NOT EXISTS `<your-catalog>`.managed_test_schema;

-- Create managed table (stored in catalog's managed storage)
CREATE TABLE IF NOT EXISTS `<your-catalog>`.managed_test_schema.managed_table (
    id BIGINT,
    name STRING,
    category STRING,
    amount DECIMAL(10,2),
    created_at TIMESTAMP
) USING DELTA;

-- Insert test data to managed table
INSERT INTO `<your-catalog>`.managed_test_schema.managed_table VALUES 
(1, 'Managed Record 1', 'Category A', 100.50, current_timestamp()),
(2, 'Managed Record 2', 'Category B', 250.75, current_timestamp()),
(3, 'Managed Record 3', 'Category A', 75.25, current_timestamp());

-- Test writing operations (UPDATE, DELETE)
UPDATE `<your-catalog>`.managed_test_schema.managed_table 
SET amount = 150.00 
WHERE id = 1;

-- Verify managed table data and operations
SELECT 
    category,
    COUNT(*) as record_count,
    SUM(amount) as total_amount,
    AVG(amount) as avg_amount
FROM `<your-catalog>`.managed_test_schema.managed_table 
GROUP BY category;

-- Check table location (should be in managed storage)
DESCRIBE DETAIL `<your-catalog>`.managed_test_schema.managed_table;
```

#### 5.3.3 Test External Location Operations

```sql
-- Create schema for external data
CREATE SCHEMA IF NOT EXISTS `<your-catalog>`.external_test_schema;

-- Create external table using the external location
CREATE TABLE IF NOT EXISTS `<your-catalog>`.external_test_schema.external_table (
    id BIGINT,
    name STRING,
    status STRING,
    value DOUBLE,
    created_at TIMESTAMP
) USING DELTA
LOCATION 'test-external-location/external_table/';

-- Test writing to external location
INSERT INTO `<your-catalog>`.external_test_schema.external_table VALUES 
(101, 'External Record 1', 'active', 99.99, current_timestamp()),
(102, 'External Record 2', 'inactive', 149.99, current_timestamp()),
(103, 'External Record 3', 'active', 199.99, current_timestamp());

-- Test reading from external location
SELECT 
    status,
    COUNT(*) as count,
    AVG(value) as avg_value
FROM `<your-catalog>`.external_test_schema.external_table 
GROUP BY status;

-- Verify external table location
DESCRIBE DETAIL `<your-catalog>`.external_test_schema.external_table;

-- Test direct access to external location path
LIST 'test-external-location/external_table/';

-- Test reading specific files from external location
SELECT * FROM delta.`test-external-location/external_table/` LIMIT 5;
```

#### 5.3.4 Advanced External Location Testing

```sql
-- Create additional external table with different data format
CREATE TABLE IF NOT EXISTS `<your-catalog>`.external_test_schema.parquet_table (
    product_id STRING,
    product_name STRING,
    price DECIMAL(10,2),
    inventory_count INT
) USING PARQUET
LOCATION 'test-external-location/parquet_data/';

-- Insert data into parquet external table
INSERT INTO `<your-catalog>`.external_test_schema.parquet_table VALUES 
('PROD001', 'Product A', 29.99, 100),
('PROD002', 'Product B', 39.99, 75),
('PROD003', 'Product C', 19.99, 150);

-- Test complex operations on external data
WITH external_summary AS (
  SELECT 
    'external' as table_type,
    COUNT(*) as record_count,
    SUM(value) as total_value
  FROM `<your-catalog>`.external_test_schema.external_table
),
managed_summary AS (
  SELECT 
    'managed' as table_type,
    COUNT(*) as record_count,
    SUM(amount) as total_value
  FROM `<your-catalog>`.managed_test_schema.managed_table
)
SELECT * FROM external_summary
UNION ALL
SELECT * FROM managed_summary;
```

#### 5.3.5 Cross-Location Data Operations

```sql
-- Test joining data between managed and external tables
SELECT 
    m.category,
    e.status,
    COUNT(*) as combined_count,
    AVG(m.amount) as avg_managed_amount,
    AVG(e.value) as avg_external_value
FROM `<your-catalog>`.managed_test_schema.managed_table m
CROSS JOIN `<your-catalog>`.external_test_schema.external_table e
GROUP BY m.category, e.status;

-- Test CTAS (Create Table As Select) from external to managed
CREATE OR REPLACE TABLE `<your-catalog>`.managed_test_schema.derived_table
USING DELTA
AS SELECT 
    status,
    COUNT(*) as status_count,
    SUM(value) as total_value,
    current_timestamp() as created_at
FROM `<your-catalog>`.external_test_schema.external_table
GROUP BY status;

-- Verify the derived table
SELECT * FROM `<your-catalog>`.managed_test_schema.derived_table;
```

#### 5.3.6 Permissions and Access Control Verification

```sql
-- Check current user permissions on catalog
SHOW GRANT ON CATALOG `<your-catalog>`;

-- Check permissions on specific schemas
SHOW GRANT ON SCHEMA `<your-catalog>`.managed_test_schema;
SHOW GRANT ON SCHEMA `<your-catalog>`.external_test_schema;

-- Check permissions on external locations
SHOW GRANT ON EXTERNAL LOCATION `test-external-location`;

-- Test table-level permissions
SHOW GRANT ON TABLE `<your-catalog>`.managed_test_schema.managed_table;
SHOW GRANT ON TABLE `<your-catalog>`.external_test_schema.external_table;

-- Verify storage access patterns
LIST '<your-root-external-location-path>/catalog/<your-catalog>/managed_test_schema/';
LIST 'test-external-location/external_table/';
```

### 5.4 Verification Summary Checklist

Use this checklist to ensure all Unity Catalog functionality is working correctly:

#### ✅ **Metastore Root Location Verification**
```sql
-- Confirm metastore has root location configured
SELECT 
  metastore_id,
  name,
  storage_root,
  CASE 
    WHEN storage_root IS NOT NULL THEN '✅ Root location configured'
    ELSE '❌ Root location missing'
  END as status
FROM system.information_schema.metastores;
```

#### ✅ **Storage Credential and External Location Creation**
- REST API creation of storage credential: `test-storage-credential` ✅
- REST API creation of external location: `test-external-location` ✅
- Verification via SQL commands ✅

#### ✅ **Managed Catalog Operations**
- Create managed schema and tables ✅
- Insert, update operations on managed tables ✅
- Verify data stored in catalog's managed storage ✅

#### ✅ **External Location Operations**
- Create external tables using external location ✅
- Write data to external location ✅
- Read data from external location ✅
- Direct path access to external files ✅

#### ✅ **Cross-Location Data Operations**
- Join between managed and external tables ✅
- CTAS operations from external to managed ✅
- Complex queries across storage locations ✅

#### ✅ **Access Control Verification**
- Catalog, schema, table, and external location permissions ✅
- Storage access pattern verification ✅

### 5.5 Performance and Configuration Verification

#### 5.5.1 Create Test Cluster via REST API

```bash
# Create a simple cluster for testing using REST API
curl -X POST \
  "$(terraform output -raw databricks_workspace_url)/api/2.0/clusters/create" \
  -H "Authorization: Bearer $DATABRICKS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "cluster_name": "unity-catalog-test-cluster",
    "spark_version": "13.3.x-scala2.12",
    "node_type_id": "i3.xlarge",
    "num_workers": 1,
    "data_security_mode": "USER_ISOLATION",
    "autotermination_minutes": 30
  }'

# Check cluster status
curl -X GET \
  "$(terraform output -raw databricks_workspace_url)/api/2.0/clusters/list" \
  -H "Authorization: Bearer $DATABRICKS_TOKEN"
```

#### 5.5.2 Test Data Access Patterns

```python
# Python notebook cell to test Unity Catalog integration
import pyspark.sql.functions as F

# Test catalog access
spark.sql("SHOW CATALOGS").show()

# Test external location access
df = spark.read.format("delta").load("<your-external-location-path>/test_table/")
df.show()

# Test write operations
test_df = spark.createDataFrame([(3, "Test Record 3")], ["id", "name"])
test_df.write.format("delta").mode("append").saveAsTable("<your-catalog>.test_schema.test_table")
```

## Step 6: Post-Deployment Configuration

### 6.1 User Management

1. **Add Users to Workspace via REST API**:
   ```bash
   # Add user to workspace
   curl -X POST \
     "$(terraform output -raw databricks_workspace_url)/api/2.0/scim/v2/Users" \
     -H "Authorization: Bearer $DATABRICKS_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
       "userName": "user@company.com",
       "displayName": "New User"
     }'
   ```

2. **Grant Catalog Permissions via SQL**:
   ```sql
   GRANT USE CATALOG ON CATALOG `<your-catalog>` TO `user@company.com`;
   GRANT CREATE SCHEMA ON CATALOG `<your-catalog>` TO `user@company.com`;
   ```

### 6.2 Additional External Locations

To add more external locations for different data sources:

```bash
# Add to your terraform.tfvars
additional_external_locations = {
  "raw_data" = "s3://your-company-raw-data/"
  "processed_data" = "s3://your-company-processed-data/"
}
```

Then run:
```bash
terraform plan
terraform apply
```

## Step 7: Monitoring and Maintenance

### 7.1 Regular Health Checks

Create a monitoring script using REST API calls (`health_check.sh`):

```bash
#!/bin/bash
echo "=== Databricks Unity Catalog Health Check ==="

WORKSPACE_URL=$(terraform output -raw databricks_workspace_url)

# Check workspace accessibility
echo "Testing workspace access..."
response=$(curl -s -o /dev/null -w "%{http_code}" \
  "$WORKSPACE_URL/api/2.0/workspace/list" \
  -H "Authorization: Bearer $DATABRICKS_TOKEN")
if [ "$response" = "200" ]; then
    echo "✓ Workspace accessible"
else
    echo "✗ Workspace access failed (HTTP $response)"
fi

# Check Unity Catalog external locations
echo "Testing external locations..."
response=$(curl -s -o /dev/null -w "%{http_code}" \
  "$WORKSPACE_URL/api/2.1/unity-catalog/external-locations" \
  -H "Authorization: Bearer $DATABRICKS_TOKEN")
if [ "$response" = "200" ]; then
    echo "✓ External locations accessible"
else
    echo "✗ External locations access failed (HTTP $response)"
fi

# Check catalogs
echo "Testing catalogs..."
response=$(curl -s -o /dev/null -w "%{http_code}" \
  "$WORKSPACE_URL/api/2.1/unity-catalog/catalogs" \
  -H "Authorization: Bearer $DATABRICKS_TOKEN")
if [ "$response" = "200" ]; then
    echo "✓ Catalogs accessible"
else
    echo "✗ Catalogs access failed (HTTP $response)"
fi

echo "Health check complete!"
```

### 7.2 Backup and Disaster Recovery

```sql
-- Regular backup verification
DESCRIBE HISTORY `<your-catalog>`.test_schema.test_table;

-- Test point-in-time recovery
SELECT * FROM `<your-catalog>`.test_schema.test_table VERSION AS OF 1;
```

## Troubleshooting

### Common Issues and Solutions

#### Issue: "Metastore not found"
**Solution**: Check metastore assignment to workspace via REST API:
```bash
# Check metastore assignments
curl -X GET \
  "https://accounts.cloud.databricks.com/api/2.0/unity-catalog/workspaces" \
  -H "Authorization: Bearer $DATABRICKS_ACCOUNT_TOKEN"
```

**Alternative**: Verify via SQL in the workspace:
```sql
-- Check current metastore
SELECT current_metastore();
```

#### Issue: "Storage credential access denied"
**Solution**: Verify IAM role trust relationship and policies via AWS Console:

1. **Check IAM Role in AWS Console**:
   - Go to AWS IAM Console → Roles
   - Find the Unity Catalog role: `$(terraform output -raw unity_catalog_iam_role_name)`
   - Verify Trust Relationship includes Databricks account ID
   - Verify attached policies include S3 permissions

2. **Check Storage Credential via REST API**:
   ```bash
   curl -X GET \
     "$(terraform output -raw databricks_workspace_url)/api/2.1/unity-catalog/storage-credentials" \
     -H "Authorization: Bearer $DATABRICKS_TOKEN"
   ```

#### Issue: "External location validation failed"
**Solution**: Check S3 bucket permissions via AWS Console:

1. **Check S3 Bucket in AWS Console**:
   - Go to AWS S3 Console
   - Find bucket: `$(terraform output -raw root_storage_bucket)`
   - Verify bucket exists and has correct permissions
   - Check bucket policy allows Databricks IAM role access

2. **Check External Location via REST API**:
   ```bash
   curl -X GET \
     "$(terraform output -raw databricks_workspace_url)/api/2.1/unity-catalog/external-locations" \
     -H "Authorization: Bearer $DATABRICKS_TOKEN"
   ```

## Cleanup

To destroy all resources:

```bash
# Optional: Remove external locations first via REST API
curl -X DELETE \
  "$(terraform output -raw databricks_workspace_url)/api/2.1/unity-catalog/external-locations/<external-location-name>" \
  -H "Authorization: Bearer $DATABRICKS_TOKEN"

# Destroy Terraform resources
terraform destroy
```

**Warning**: This will permanently delete all Databricks resources and data. Ensure you have backups if needed.

## Support and Additional Resources

- [Databricks Unity Catalog Documentation](https://docs.databricks.com/data-governance/unity-catalog/)
- [Databricks Terraform Provider Documentation](https://registry.terraform.io/providers/databricks/databricks/latest/docs)
- [AWS Databricks Best Practices](https://docs.databricks.com/administration-guide/cloud-configurations/aws/)

For technical support, contact your Databricks representative or visit the [Databricks Community Forums](https://community.databricks.com/).