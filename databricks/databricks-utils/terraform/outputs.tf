# =============================================================================
# DATABRICKS WORKSPACE OUTPUTS
# =============================================================================

output "databricks_workspace_url" {
  description = "URL of the Databricks workspace"
  value       = databricks_mws_workspaces.this.workspace_url
  sensitive   = false
}

output "databricks_workspace_id" {
  description = "ID of the Databricks workspace"
  value       = databricks_mws_workspaces.this.workspace_id
  sensitive   = false
}

output "databricks_workspace_name" {
  description = "Name of the Databricks workspace"
  value       = databricks_mws_workspaces.this.workspace_name
  sensitive   = false
}

# =============================================================================
# UNITY CATALOG OUTPUTS
# =============================================================================

output "unity_catalog_metastore_id" {
  description = "ID of the Unity Catalog metastore"
  value       = var.enable_unity_catalog ? databricks_metastore.this[0].metastore_id : null
  sensitive   = false
}

output "unity_catalog_metastore_name" {
  description = "Name of the Unity Catalog metastore"
  value       = var.enable_unity_catalog ? databricks_metastore.this[0].name : null
  sensitive   = false
}

output "unity_catalog_storage_root" {
  description = "Storage root location of the Unity Catalog metastore"
  value       = var.enable_unity_catalog ? databricks_metastore.this[0].storage_root : null
  sensitive   = false
}

output "primary_catalog_name" {
  description = "Name of the primary Unity Catalog catalog"
  value       = var.enable_unity_catalog ? databricks_catalog.primary[0].name : null
  sensitive   = false
}

output "storage_credential_name" {
  description = "Name of the Unity Catalog storage credential"
  value       = var.enable_unity_catalog ? databricks_storage_credential.unity_catalog[0].name : null
  sensitive   = false
}

# =============================================================================
# S3 BUCKET OUTPUTS
# =============================================================================

output "root_storage_bucket" {
  description = "Name of the root storage S3 bucket for Unity Catalog"
  value       = aws_s3_bucket.unity_catalog_root.bucket
  sensitive   = false
}

output "root_storage_bucket_arn" {
  description = "ARN of the root storage S3 bucket for Unity Catalog"
  value       = aws_s3_bucket.unity_catalog_root.arn
  sensitive   = false
}

output "workspace_root_storage_bucket" {
  description = "Name of the workspace root storage S3 bucket"
  value       = aws_s3_bucket.root_storage_bucket.bucket
  sensitive   = false
}

output "workspace_root_storage_bucket_arn" {
  description = "ARN of the workspace root storage S3 bucket"
  value       = aws_s3_bucket.root_storage_bucket.arn
  sensitive   = false
}

output "external_data_bucket" {
  description = "Name of the external data S3 bucket (if created)"
  value       = var.external_data_bucket_name != null ? aws_s3_bucket.external_data[0].bucket : null
  sensitive   = false
}

output "external_data_bucket_arn" {
  description = "ARN of the external data S3 bucket (if created)"
  value       = var.external_data_bucket_name != null ? aws_s3_bucket.external_data[0].arn : null
  sensitive   = false
}

# =============================================================================
# IAM ROLE OUTPUTS
# =============================================================================

output "unity_catalog_iam_role_arn" {
  description = "ARN of the Unity Catalog IAM role"
  value       = aws_iam_role.unity_catalog.arn
  sensitive   = false
}

output "unity_catalog_iam_role_name" {
  description = "Name of the Unity Catalog IAM role"
  value       = aws_iam_role.unity_catalog.name
  sensitive   = false
}

output "cross_account_iam_role_arn" {
  description = "ARN of the Databricks cross-account IAM role"
  value       = aws_iam_role.cross_account_role.arn
  sensitive   = false
}

output "cross_account_iam_role_name" {
  description = "Name of the Databricks cross-account IAM role"
  value       = aws_iam_role.cross_account_role.name
  sensitive   = false
}

# =============================================================================
# EXTERNAL LOCATION OUTPUTS
# =============================================================================

output "root_external_location_name" {
  description = "Name of the root external location"
  value       = var.enable_unity_catalog ? databricks_external_location.root[0].name : null
  sensitive   = false
}

output "root_external_location_url" {
  description = "URL of the root external location"
  value       = var.enable_unity_catalog ? databricks_external_location.root[0].url : null
  sensitive   = false
}

output "external_data_location_name" {
  description = "Name of the external data location (if created)"
  value       = var.enable_unity_catalog && var.external_data_bucket_name != null ? databricks_external_location.external_data[0].name : null
  sensitive   = false
}

output "external_data_location_url" {
  description = "URL of the external data location (if created)"
  value       = var.enable_unity_catalog && var.external_data_bucket_name != null ? databricks_external_location.external_data[0].url : null
  sensitive   = false
}

output "additional_external_locations" {
  description = "Map of additional external location names and URLs"
  value = var.enable_unity_catalog ? {
    for k, v in databricks_external_location.additional :
    k => {
      name = v.name
      url  = v.url
    }
  } : {}
  sensitive = false
}

# =============================================================================
# NETWORKING OUTPUTS
# =============================================================================

output "vpc_id" {
  description = "VPC ID used for the Databricks workspace"
  value       = var.vpc_id != null ? var.vpc_id : (length(data.aws_vpc.default) > 0 ? data.aws_vpc.default[0].id : null)
  sensitive   = false
}

output "subnet_ids" {
  description = "Subnet IDs used for the Databricks workspace"
  value       = length(var.subnet_ids) > 0 ? var.subnet_ids : (length(data.aws_subnets.default) > 0 ? data.aws_subnets.default[0].ids : [])
  sensitive   = false
}

output "availability_zones" {
  description = "Availability zones used for deployment"
  value       = local.azs
  sensitive   = false
}

# =============================================================================
# CLUSTER OUTPUTS
# =============================================================================

output "default_cluster_id" {
  description = "ID of the default cluster (if created)"
  value       = var.create_default_cluster ? databricks_cluster.default[0].id : null
  sensitive   = false
}

output "default_cluster_name" {
  description = "Name of the default cluster (if created)"
  value       = var.create_default_cluster ? databricks_cluster.default[0].cluster_name : null
  sensitive   = false
}

# =============================================================================
# AUTHENTICATION AND ACCESS OUTPUTS
# =============================================================================

output "databricks_account_id" {
  description = "Databricks Account ID used for deployment"
  value       = var.databricks_account_id
  sensitive   = true
}

output "workspace_users" {
  description = "List of users added to the workspace"
  value       = var.workspace_users
  sensitive   = false
}

output "workspace_admins" {
  description = "List of workspace administrators"
  value       = var.workspace_admins
  sensitive   = false
}

# =============================================================================
# DEPLOYMENT INFORMATION OUTPUTS
# =============================================================================

output "deployment_region" {
  description = "AWS region used for deployment"
  value       = var.aws_region
  sensitive   = false
}

output "deployment_environment" {
  description = "Environment name for the deployment"
  value       = var.environment
  sensitive   = false
}

output "organization_name" {
  description = "Organization name used for deployment"
  value       = var.organization_name
  sensitive   = false
}

output "deployment_prefix" {
  description = "Prefix used for all resource names"
  value       = local.prefix
  sensitive   = false
}

output "random_suffix" {
  description = "Random suffix used for globally unique resources"
  value       = random_string.suffix.result
  sensitive   = false
}

# =============================================================================
# CONFIGURATION STATUS OUTPUTS
# =============================================================================

output "unity_catalog_enabled" {
  description = "Whether Unity Catalog is enabled"
  value       = var.enable_unity_catalog
  sensitive   = false
}

output "encryption_at_rest_enabled" {
  description = "Whether encryption at rest is enabled"
  value       = var.enable_encryption_at_rest
  sensitive   = false
}

output "versioning_enabled" {
  description = "Whether S3 bucket versioning is enabled"
  value       = var.enable_versioning
  sensitive   = false
}

output "monitoring_enabled" {
  description = "Whether monitoring is enabled"
  value       = var.enable_monitoring
  sensitive   = false
}

# =============================================================================
# VERIFICATION COMMANDS
# =============================================================================

output "verification_commands" {
  description = "Commands to verify the deployment"
  value = {
    workspace_url = databricks_mws_workspaces.this.workspace_url
    rest_api_test = "curl -X GET '${databricks_mws_workspaces.this.workspace_url}/api/2.0/workspace/list' -H 'Authorization: Bearer $DATABRICKS_TOKEN'"
    unity_catalog_test = var.enable_unity_catalog ? "curl -X GET '${databricks_mws_workspaces.this.workspace_url}/api/2.1/unity-catalog/catalogs' -H 'Authorization: Bearer $DATABRICKS_TOKEN'" : "N/A (Unity Catalog not enabled)"
    s3_bucket_console = "https://s3.console.aws.amazon.com/s3/buckets/${aws_s3_bucket.unity_catalog_root.bucket}/"
  }
  sensitive = false
}

# =============================================================================
# RESOURCE SUMMARY OUTPUT
# =============================================================================

output "deployment_summary" {
  description = "Summary of deployed resources"
  value = {
    workspace = {
      name = databricks_mws_workspaces.this.workspace_name
      url  = databricks_mws_workspaces.this.workspace_url
      id   = databricks_mws_workspaces.this.workspace_id
    }
    unity_catalog = var.enable_unity_catalog ? {
      metastore_name     = databricks_metastore.this[0].name
      metastore_id       = databricks_metastore.this[0].metastore_id
      primary_catalog    = databricks_catalog.primary[0].name
      storage_credential = databricks_storage_credential.unity_catalog[0].name
      root_location      = databricks_external_location.root[0].name
    } : null
    storage = {
      unity_catalog_bucket = aws_s3_bucket.unity_catalog_root.bucket
      workspace_bucket     = aws_s3_bucket.root_storage_bucket.bucket
      external_data_bucket = var.external_data_bucket_name != null ? aws_s3_bucket.external_data[0].bucket : null
    }
    networking = {
      vpc_id     = var.vpc_id != null ? var.vpc_id : (length(data.aws_vpc.default) > 0 ? data.aws_vpc.default[0].id : null)
      subnet_ids = length(var.subnet_ids) > 0 ? var.subnet_ids : (length(data.aws_subnets.default) > 0 ? data.aws_subnets.default[0].ids : [])
    }
  }
  sensitive = false
}