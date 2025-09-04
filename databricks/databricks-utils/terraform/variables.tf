# =============================================================================
# CUSTOMER CONFIGURATION VARIABLES
# =============================================================================

# Organization and Environment Configuration
variable "organization_name" {
  description = "Name of your organization (used in resource naming)"
  type        = string
  default     = "your-company"

  validation {
    condition     = can(regex("^[a-zA-Z0-9-]+$", var.organization_name))
    error_message = "Organization name must contain only alphanumeric characters and hyphens."
  }
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "prod"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}

# =============================================================================
# AWS CONFIGURATION
# =============================================================================

variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "availability_zones" {
  description = "List of availability zones to use"
  type        = list(string)
  default     = []
}

# =============================================================================
# DATABRICKS ACCOUNT CONFIGURATION
# =============================================================================

variable "databricks_account_id" {
  description = "Databricks Account ID (found in Account Settings)"
  type        = string

  validation {
    condition     = can(regex("^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$", var.databricks_account_id))
    error_message = "Databricks Account ID must be a valid UUID format."
  }
}

variable "databricks_workspace_name" {
  description = "Name for the Databricks workspace"
  type        = string
  default     = null
}

# =============================================================================
# UNITY CATALOG CONFIGURATION
# =============================================================================

variable "metastore_name" {
  description = "Name for the Unity Catalog metastore"
  type        = string
  default     = null
}

variable "catalog_name" {
  description = "Name for the primary Unity Catalog catalog"
  type        = string
  default     = null

  validation {
    condition     = var.catalog_name == null || can(regex("^[a-z][a-z0-9_]*$", var.catalog_name))
    error_message = "Catalog name must start with lowercase letter and contain only lowercase letters, numbers, and underscores."
  }
}

variable "unity_admin_group" {
  description = "Name of the admin group for Unity Catalog metastore"
  type        = string
  default     = "unity-catalog-admins"
}

variable "enable_unity_catalog" {
  description = "Enable Unity Catalog features"
  type        = bool
  default     = true
}

# =============================================================================
# STORAGE CONFIGURATION
# =============================================================================

variable "root_storage_bucket_name" {
  description = "Name for the root storage S3 bucket (must be globally unique)"
  type        = string
  default     = null

  validation {
    condition = var.root_storage_bucket_name == null || (
      length(var.root_storage_bucket_name) >= 3 &&
      length(var.root_storage_bucket_name) <= 63 &&
      can(regex("^[a-z0-9][a-z0-9-]*[a-z0-9]$", var.root_storage_bucket_name))
    )
    error_message = "Bucket name must be between 3-63 characters, start/end with alphanumeric, and contain only lowercase letters, numbers, and hyphens."
  }
}

variable "external_data_bucket_name" {
  description = "Name for external data S3 bucket (optional)"
  type        = string
  default     = null

  validation {
    condition = var.external_data_bucket_name == null || (
      length(var.external_data_bucket_name) >= 3 &&
      length(var.external_data_bucket_name) <= 63 &&
      can(regex("^[a-z0-9][a-z0-9-]*[a-z0-9]$", var.external_data_bucket_name))
    )
    error_message = "Bucket name must be between 3-63 characters, start/end with alphanumeric, and contain only lowercase letters, numbers, and hyphens."
  }
}

variable "additional_external_locations" {
  description = "Map of additional external locations to create"
  type = map(object({
    url         = string
    comment     = optional(string)
    read_only   = optional(bool, false)
    skip_validation = optional(bool, false)
  }))
  default = {}

  validation {
    condition = alltrue([
      for name, config in var.additional_external_locations :
      can(regex("^s3://[a-z0-9][a-z0-9-]*[a-z0-9]/.*", config.url))
    ])
    error_message = "All external location URLs must be valid S3 paths starting with 's3://'."
  }
}

# =============================================================================
# NETWORKING CONFIGURATION
# =============================================================================

variable "vpc_id" {
  description = "VPC ID to use for Databricks workspace (if not provided, will use default VPC)"
  type        = string
  default     = null
}

variable "subnet_ids" {
  description = "List of subnet IDs for Databricks workspace"
  type        = list(string)
  default     = []
}

variable "security_group_ids" {
  description = "List of additional security group IDs"
  type        = list(string)
  default     = []
}

variable "enable_private_subnets" {
  description = "Enable private subnets for Databricks workspace"
  type        = bool
  default     = false
}

# =============================================================================
# WORKSPACE CONFIGURATION
# =============================================================================

variable "workspace_users" {
  description = "List of users to add to the workspace"
  type        = list(string)
  default     = []

  validation {
    condition = alltrue([
      for email in var.workspace_users :
      can(regex("^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$", email))
    ])
    error_message = "All workspace users must be valid email addresses."
  }
}

variable "workspace_admins" {
  description = "List of users to assign workspace admin role"
  type        = list(string)
  default     = []

  validation {
    condition = alltrue([
      for email in var.workspace_admins :
      can(regex("^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$", email))
    ])
    error_message = "All workspace admins must be valid email addresses."
  }
}

variable "enable_workspace_access_control" {
  description = "Enable workspace-level access control"
  type        = bool
  default     = true
}

# =============================================================================
# CLUSTER CONFIGURATION
# =============================================================================

variable "default_cluster_config" {
  description = "Default cluster configuration"
  type = object({
    spark_version      = optional(string, "13.3.x-scala2.12")
    node_type_id       = optional(string, "i3.xlarge")
    driver_node_type_id = optional(string)
    num_workers        = optional(number, 1)
    autotermination_minutes = optional(number, 20)
    data_security_mode = optional(string, "USER_ISOLATION")
  })
  default = {}
}

variable "create_default_cluster" {
  description = "Create a default cluster for testing"
  type        = bool
  default     = false
}

# =============================================================================
# SECURITY AND COMPLIANCE
# =============================================================================

variable "enable_encryption_at_rest" {
  description = "Enable encryption at rest for S3 buckets"
  type        = bool
  default     = true
}

variable "kms_key_id" {
  description = "KMS key ID for encryption (if not provided, will use AWS managed keys)"
  type        = string
  default     = null
}

variable "enable_cloudtrail_logging" {
  description = "Enable CloudTrail logging for audit purposes"
  type        = bool
  default     = true
}

variable "allowed_ip_ranges" {
  description = "List of IP ranges allowed to access the workspace"
  type        = list(string)
  default     = []

  validation {
    condition = alltrue([
      for cidr in var.allowed_ip_ranges :
      can(cidrhost(cidr, 0))
    ])
    error_message = "All IP ranges must be valid CIDR blocks."
  }
}

# =============================================================================
# RESOURCE TAGGING
# =============================================================================

variable "additional_tags" {
  description = "Additional tags to apply to all resources"
  type        = map(string)
  default     = {}
}

variable "cost_center" {
  description = "Cost center for billing purposes"
  type        = string
  default     = "data-platform"
}

variable "owner_email" {
  description = "Email of the resource owner"
  type        = string
  default     = null

  validation {
    condition     = var.owner_email == null || can(regex("^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$", var.owner_email))
    error_message = "Owner email must be a valid email address."
  }
}

# =============================================================================
# FEATURE FLAGS
# =============================================================================

variable "enable_monitoring" {
  description = "Enable CloudWatch monitoring for resources"
  type        = bool
  default     = true
}

variable "enable_backup" {
  description = "Enable automatic backup for S3 buckets"
  type        = bool
  default     = true
}

variable "enable_versioning" {
  description = "Enable versioning for S3 buckets"
  type        = bool
  default     = true
}

variable "backup_retention_days" {
  description = "Number of days to retain backups"
  type        = number
  default     = 30

  validation {
    condition     = var.backup_retention_days >= 1 && var.backup_retention_days <= 365
    error_message = "Backup retention days must be between 1 and 365."
  }
}