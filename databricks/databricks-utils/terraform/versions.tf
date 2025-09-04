terraform {
  required_version = ">= 1.13.0"

  required_providers {
    databricks = {
      source  = "databricks/databricks"
      version = ">= 1.81.0"
    }
    aws = {
      source  = "hashicorp/aws"
      version = ">= 6.0.0"
    }
    random = {
      source  = "hashicorp/random"
      version = ">= 3.6.0"
    }
  }
}