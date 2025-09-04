# =============================================================================
# LOCAL VALUES AND DATA SOURCES
# =============================================================================

locals {
  # Generate resource names based on organization and environment
  prefix = "${var.organization_name}-${var.environment}"
  
  # Resource names with defaults
  workspace_name         = var.databricks_workspace_name != null ? var.databricks_workspace_name : "${local.prefix}-workspace"
  metastore_name        = var.metastore_name != null ? var.metastore_name : "${local.prefix}-metastore"
  catalog_name          = var.catalog_name != null ? var.catalog_name : replace("${var.organization_name}_catalog", "-", "_")
  root_bucket_name      = var.root_storage_bucket_name != null ? var.root_storage_bucket_name : "${local.prefix}-databricks-root-storage"
  external_bucket_name  = var.external_data_bucket_name != null ? var.external_data_bucket_name : "${local.prefix}-databricks-external-data"
  
  # Availability zones
  azs = length(var.availability_zones) > 0 ? var.availability_zones : data.aws_availability_zones.available.names
  
  # Common tags
  common_tags = merge({
    Environment    = var.environment
    Project       = "databricks-unity-catalog"
    Organization  = var.organization_name
    ManagedBy     = "terraform"
    CostCenter    = var.cost_center
    OwnerEmail    = var.owner_email
  }, var.additional_tags)
}

# Get available AZs
data "aws_availability_zones" "available" {
  state = "available"
}

# Get current AWS account ID
data "aws_caller_identity" "current" {}

# Get current AWS region
data "aws_region" "current" {}

# Generate random suffix for globally unique resources
resource "random_string" "suffix" {
  length  = 8
  upper   = false
  special = false
}

# =============================================================================
# S3 BUCKETS FOR UNITY CATALOG
# =============================================================================

# Root storage bucket for Unity Catalog metastore
resource "aws_s3_bucket" "unity_catalog_root" {
  bucket        = "${local.root_bucket_name}-${random_string.suffix.result}"
  force_destroy = true

  tags = merge(local.common_tags, {
    Name = "Unity Catalog Root Storage"
    Type = "metastore-root-storage"
  })
}

# Versioning for root bucket
resource "aws_s3_bucket_versioning" "unity_catalog_root" {
  count  = var.enable_versioning ? 1 : 0
  bucket = aws_s3_bucket.unity_catalog_root.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Encryption for root bucket
resource "aws_s3_bucket_server_side_encryption_configuration" "unity_catalog_root" {
  count  = var.enable_encryption_at_rest ? 1 : 0
  bucket = aws_s3_bucket.unity_catalog_root.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = var.kms_key_id != null ? "aws:kms" : "AES256"
      kms_master_key_id = var.kms_key_id
    }
    bucket_key_enabled = var.kms_key_id != null
  }
}

# Block public access for root bucket
resource "aws_s3_bucket_public_access_block" "unity_catalog_root" {
  bucket = aws_s3_bucket.unity_catalog_root.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# External data bucket (optional)
resource "aws_s3_bucket" "external_data" {
  count         = var.external_data_bucket_name != null ? 1 : 0
  bucket        = "${local.external_bucket_name}-${random_string.suffix.result}"
  force_destroy = true

  tags = merge(local.common_tags, {
    Name = "External Data Storage"
    Type = "external-data-storage"
  })
}

resource "aws_s3_bucket_versioning" "external_data" {
  count  = var.external_data_bucket_name != null && var.enable_versioning ? 1 : 0
  bucket = aws_s3_bucket.external_data[0].id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "external_data" {
  count  = var.external_data_bucket_name != null && var.enable_encryption_at_rest ? 1 : 0
  bucket = aws_s3_bucket.external_data[0].id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = var.kms_key_id != null ? "aws:kms" : "AES256"
      kms_master_key_id = var.kms_key_id
    }
    bucket_key_enabled = var.kms_key_id != null
  }
}

resource "aws_s3_bucket_public_access_block" "external_data" {
  count  = var.external_data_bucket_name != null ? 1 : 0
  bucket = aws_s3_bucket.external_data[0].id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# =============================================================================
# IAM ROLES AND POLICIES FOR UNITY CATALOG
# =============================================================================

# Unity Catalog IAM Role
resource "aws_iam_role" "unity_catalog" {
  name = "${local.prefix}-unity-catalog-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Sid    = ""
        Principal = {
          AWS = "arn:aws:iam::414351767826:root"  # Databricks AWS Account ID
        }
        Condition = {
          StringEquals = {
            "sts:ExternalId" = var.databricks_account_id
          }
        }
      },
    ]
  })

  tags = merge(local.common_tags, {
    Name = "Unity Catalog IAM Role"
  })
}

# Unity Catalog IAM Policy
resource "aws_iam_role_policy" "unity_catalog" {
  name = "${local.prefix}-unity-catalog-policy"
  role = aws_iam_role.unity_catalog.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:GetObjectVersion",
          "s3:PutObject",
          "s3:PutObjectAcl",
          "s3:DeleteObject",
          "s3:ListBucket",
          "s3:GetBucketLocation"
        ]
        Resource = [
          aws_s3_bucket.unity_catalog_root.arn,
          "${aws_s3_bucket.unity_catalog_root.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:GetObjectVersion",
          "s3:PutObject",
          "s3:PutObjectAcl",
          "s3:DeleteObject",
          "s3:ListBucket",
          "s3:GetBucketLocation"
        ]
        Resource = var.external_data_bucket_name != null ? [
          aws_s3_bucket.external_data[0].arn,
          "${aws_s3_bucket.external_data[0].arn}/*"
        ] : []
      },
      {
        Effect = "Allow"
        Action = [
          "sts:AssumeRole"
        ]
        Resource = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${local.prefix}-unity-catalog-role"
      }
    ]
  })
}

# =============================================================================
# UNITY CATALOG RESOURCES
# =============================================================================

# Unity Catalog Metastore
resource "databricks_metastore" "this" {
  count         = var.enable_unity_catalog ? 1 : 0
  provider      = databricks.account
  name          = local.metastore_name
  storage_root  = "s3://${aws_s3_bucket.unity_catalog_root.bucket}/metastore"
  owner         = var.unity_admin_group
  region        = var.aws_region
  force_destroy = true

  depends_on = [
    aws_s3_bucket.unity_catalog_root,
    aws_iam_role.unity_catalog
  ]
}

# Storage Credential for Unity Catalog
resource "databricks_storage_credential" "unity_catalog" {
  count    = var.enable_unity_catalog ? 1 : 0
  provider = databricks.account
  name     = "${local.prefix}-storage-credential"
  comment  = "Storage credential for Unity Catalog metastore"

  aws_iam_role {
    role_arn = aws_iam_role.unity_catalog.arn
  }

  depends_on = [databricks_metastore.this]
}

# Metastore Data Access Configuration
resource "databricks_metastore_data_access" "this" {
  count            = var.enable_unity_catalog ? 1 : 0
  provider         = databricks.account
  metastore_id     = databricks_metastore.this[0].id
  name             = "${local.prefix}-data-access"
  aws_iam_role {
    role_arn = aws_iam_role.unity_catalog.arn
  }
  is_default = true

  depends_on = [databricks_storage_credential.unity_catalog]
}

# =============================================================================
# DATABRICKS WORKSPACE
# =============================================================================

# Get the default VPC if none specified
data "aws_vpc" "default" {
  count   = var.vpc_id == null ? 1 : 0
  default = true
}

# Get subnets if none specified
data "aws_subnets" "default" {
  count = length(var.subnet_ids) == 0 ? 1 : 0
  filter {
    name   = "vpc-id"
    values = [var.vpc_id != null ? var.vpc_id : data.aws_vpc.default[0].id]
  }
  filter {
    name   = "default-for-az"
    values = ["true"]
  }
}

# Databricks Workspace
resource "databricks_mws_workspaces" "this" {
  provider                   = databricks.account
  account_id                = var.databricks_account_id
  workspace_name            = local.workspace_name
  deployment_name           = local.workspace_name
  aws_region                = var.aws_region
  credentials_id            = databricks_mws_credentials.this.credentials_id
  storage_configuration_id  = databricks_mws_storage_configurations.this.storage_configuration_id
  network_id               = var.vpc_id != null ? databricks_mws_networks.this[0].network_id : null

  depends_on = [
    databricks_mws_credentials.this,
    databricks_mws_storage_configurations.this
  ]
}

# Databricks Cross-Account IAM Role
resource "aws_iam_role" "cross_account_role" {
  name = "${local.prefix}-crossaccount-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Sid    = ""
        Principal = {
          AWS = "arn:aws:iam::414351767826:root"  # Databricks AWS Account ID
        }
        Condition = {
          StringEquals = {
            "sts:ExternalId" = var.databricks_account_id
          }
        }
      },
    ]
  })

  tags = merge(local.common_tags, {
    Name = "Databricks Cross Account Role"
  })
}

# Cross-Account Role Policy
resource "aws_iam_role_policy" "cross_account_policy" {
  name = "${local.prefix}-crossaccount-policy"
  role = aws_iam_role.cross_account_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ec2:*",
          "iam:CreateServiceLinkedRole",
          "iam:PutRolePolicy"
        ]
        Resource = "*"
      }
    ]
  })
}

# Databricks Credentials Configuration
resource "databricks_mws_credentials" "this" {
  provider         = databricks.account
  account_id       = var.databricks_account_id
  credentials_name = "${local.prefix}-credentials"
  role_arn         = aws_iam_role.cross_account_role.arn
}

# Root S3 Bucket for Databricks Workspace
resource "aws_s3_bucket" "root_storage_bucket" {
  bucket        = "${local.prefix}-workspace-root-storage-${random_string.suffix.result}"
  force_destroy = true

  tags = merge(local.common_tags, {
    Name = "Databricks Workspace Root Storage"
  })
}

resource "aws_s3_bucket_versioning" "root_storage_bucket" {
  count  = var.enable_versioning ? 1 : 0
  bucket = aws_s3_bucket.root_storage_bucket.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "root_storage_bucket" {
  count  = var.enable_encryption_at_rest ? 1 : 0
  bucket = aws_s3_bucket.root_storage_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = var.kms_key_id != null ? "aws:kms" : "AES256"
      kms_master_key_id = var.kms_key_id
    }
    bucket_key_enabled = var.kms_key_id != null
  }
}

resource "aws_s3_bucket_public_access_block" "root_storage_bucket" {
  bucket = aws_s3_bucket.root_storage_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Storage Configuration
resource "databricks_mws_storage_configurations" "this" {
  provider                   = databricks.account
  account_id                = var.databricks_account_id
  storage_configuration_name = "${local.prefix}-storage"
  bucket_name               = aws_s3_bucket.root_storage_bucket.bucket
}

# Network Configuration (optional)
resource "databricks_mws_networks" "this" {
  count            = var.vpc_id != null ? 1 : 0
  provider         = databricks.account
  account_id       = var.databricks_account_id
  network_name     = "${local.prefix}-network"
  vpc_id           = var.vpc_id
  subnet_ids       = length(var.subnet_ids) > 0 ? var.subnet_ids : data.aws_subnets.default[0].ids
  security_group_ids = var.security_group_ids
}

# =============================================================================
# UNITY CATALOG WORKSPACE ASSIGNMENT
# =============================================================================

# Assign metastore to workspace
resource "databricks_metastore_assignment" "this" {
  count                = var.enable_unity_catalog ? 1 : 0
  provider             = databricks.account
  workspace_id         = databricks_mws_workspaces.this.workspace_id
  metastore_id         = databricks_metastore.this[0].id
  default_catalog_name = "hive_metastore"

  depends_on = [databricks_mws_workspaces.this]
}

# =============================================================================
# EXTERNAL LOCATIONS
# =============================================================================

# Root external location
resource "databricks_external_location" "root" {
  count           = var.enable_unity_catalog ? 1 : 0
  provider        = databricks.workspace
  name            = "${local.prefix}-root-location"
  url             = "s3://${aws_s3_bucket.unity_catalog_root.bucket}/"
  credential_name = databricks_storage_credential.unity_catalog[0].name
  comment         = "Root external location for Unity Catalog"

  depends_on = [
    databricks_metastore_assignment.this,
    databricks_storage_credential.unity_catalog
  ]
}

# External data location (if bucket exists)
resource "databricks_external_location" "external_data" {
  count           = var.enable_unity_catalog && var.external_data_bucket_name != null ? 1 : 0
  provider        = databricks.workspace
  name            = "${local.prefix}-external-data-location"
  url             = "s3://${aws_s3_bucket.external_data[0].bucket}/"
  credential_name = databricks_storage_credential.unity_catalog[0].name
  comment         = "External data location for Unity Catalog"

  depends_on = [
    databricks_metastore_assignment.this,
    databricks_storage_credential.unity_catalog
  ]
}

# Additional external locations
resource "databricks_external_location" "additional" {
  for_each        = var.enable_unity_catalog ? var.additional_external_locations : {}
  provider        = databricks.workspace
  name            = "${local.prefix}-${each.key}"
  url             = each.value.url
  credential_name = databricks_storage_credential.unity_catalog[0].name
  comment         = each.value.comment
  read_only       = each.value.read_only
  skip_validation = each.value.skip_validation

  depends_on = [
    databricks_metastore_assignment.this,
    databricks_storage_credential.unity_catalog
  ]
}

# =============================================================================
# UNITY CATALOG CATALOG AND SCHEMA
# =============================================================================

# Create primary catalog
resource "databricks_catalog" "primary" {
  count           = var.enable_unity_catalog ? 1 : 0
  provider        = databricks.workspace
  name            = local.catalog_name
  comment         = "Primary catalog for ${var.organization_name}"
  storage_root    = "s3://${aws_s3_bucket.unity_catalog_root.bucket}/catalog/${local.catalog_name}"
  isolation_mode  = "ISOLATED"
  
  depends_on = [
    databricks_metastore_assignment.this,
    databricks_external_location.root
  ]
}

# Create default schema
resource "databricks_schema" "default" {
  count            = var.enable_unity_catalog ? 1 : 0
  provider         = databricks.workspace
  catalog_name     = databricks_catalog.primary[0].name
  name            = "default"
  comment         = "Default schema for ${local.catalog_name}"
  storage_root    = "s3://${aws_s3_bucket.unity_catalog_root.bucket}/catalog/${local.catalog_name}/default"

  depends_on = [databricks_catalog.primary]
}

# =============================================================================
# WORKSPACE USERS AND PERMISSIONS (Optional)
# =============================================================================

# Add users to workspace
resource "databricks_user" "workspace_users" {
  count    = length(var.workspace_users)
  provider = databricks.workspace
  user_name = var.workspace_users[count.index]

  depends_on = [databricks_mws_workspaces.this]
}

# Grant catalog permissions to users
resource "databricks_grants" "catalog_grants" {
  count    = var.enable_unity_catalog && length(var.workspace_users) > 0 ? 1 : 0
  provider = databricks.workspace
  catalog  = databricks_catalog.primary[0].name

  dynamic "grant" {
    for_each = var.workspace_users
    content {
      principal  = grant.value
      privileges = ["USE_CATALOG", "USE_SCHEMA", "CREATE_SCHEMA"]
    }
  }

  depends_on = [
    databricks_user.workspace_users,
    databricks_catalog.primary
  ]
}

# =============================================================================
# DEFAULT CLUSTER (Optional)
# =============================================================================

# Create default cluster for testing
resource "databricks_cluster" "default" {
  count       = var.create_default_cluster ? 1 : 0
  provider    = databricks.workspace
  cluster_name = "${local.prefix}-default-cluster"

  spark_version                = var.default_cluster_config.spark_version
  node_type_id                = var.default_cluster_config.node_type_id
  driver_node_type_id         = var.default_cluster_config.driver_node_type_id
  num_workers                 = var.default_cluster_config.num_workers
  autotermination_minutes     = var.default_cluster_config.autotermination_minutes
  data_security_mode          = var.default_cluster_config.data_security_mode

  depends_on = [
    databricks_mws_workspaces.this,
    databricks_metastore_assignment.this
  ]
}