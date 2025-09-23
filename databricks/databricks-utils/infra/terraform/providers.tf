# AWS Provider Configuration
provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Environment   = var.environment
      Project       = "databricks-unity-catalog"
      Organization  = var.organization_name
      ManagedBy     = "terraform"
      CreatedDate   = timestamp()
    }
  }
}

# Databricks Provider for Account-Level Operations
provider "databricks" {
  alias      = "account"
  host       = "https://accounts.cloud.databricks.com"
  account_id = var.databricks_account_id
}

# Databricks Provider for Workspace-Level Operations
provider "databricks" {
  alias = "workspace"
  host  = databricks_mws_workspaces.this.workspace_url
}

# Random Provider for generating unique resource names
provider "random" {}