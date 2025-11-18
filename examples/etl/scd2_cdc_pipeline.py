# Databricks notebook source
# MAGIC %md
# MAGIC # SCD Type 2 CDC Pipeline with DLT
# MAGIC
# MAGIC This notebook processes Change Data Capture (CDC) data from S3 and applies SCD Type 2 transformations
# MAGIC using Lakehouse Declarative Pipelines.

# COMMAND ----------

from pyspark import pipelines as dp
from pyspark.sql.functions import col, expr

# COMMAND ----------

# MAGIC %md
# MAGIC ## Bronze Layer: Ingest Raw CDC Data from S3

# COMMAND ----------

@dp.table(
    name="raw_cdc_source"
)
def raw_cdc_source():
    """
    Read raw CDC data from S3 bucket with automatic schema inference.
    Replace S3_BUCKET_PATH with your actual S3 path.
    """
    S3_BUCKET_PATH = "s3://your-bucket/path/to/cdc/data/"

    return (
        spark.read
        .format("cloudFiles")
        .option("cloudFiles.format", "json")
        .option("cloudFiles.inferColumnTypes", "true")  # Auto-infer column types
        .load(S3_BUCKET_PATH)
    )

# COMMAND ----------

# MAGIC %md
# MAGIC ## Silver Layer: Parse and Explode JSON

# COMMAND ----------

@dp.table(
    name="parsed_cdc_data",
    comment="Parsed CDC data with exploded JSON columns"
)
def parsed_cdc_data():
    """
    Explode the nested JSON in fbobj_new_data and fbobj_old_data columns.
    Schema is automatically inferred from the JSON strings.
    Handle INSERT, UPDATE, and DELETE operations.
    """
    df = dp.read("raw_cdc_source")

    # Get field names from the inferred schema to add prefixes
    new_data_fields = df.schema["fbobj_new_data"].dataType.fieldNames()
    old_data_fields = df.schema["fbobj_old_data"].dataType.fieldNames()

    return (
        df.select(
            col("op").alias("operation"),
            col("mutation_timestamp_ms"),
            col("wh_note"),
            # Explode all new_data fields with prefix
            *[col(f"fbobj_new_data.{field}").alias(f"new_{field}") for field in new_data_fields],
            # Explode all old_data fields with prefix
            *[col(f"fbobj_old_data.{field}").alias(f"old_{field}") for field in old_data_fields]
        )
    )

# COMMAND ----------

# MAGIC %md
# MAGIC ## Intermediate View: Prepare for CDC

# COMMAND ----------

@dp.table(
    name = "cdc_prepared"
)
def cdc_prepared():
    """
    Prepare data for SCD Type 2 processing.
    For INSERT/UPDATE: use new_data fields
    For DELETE: use old_data fields
    """
    return (
        dp.read_stream("parsed_cdc_data")
        .withColumn(
            "oid",
            expr("CASE WHEN operation IN ('INSERT', 'UPDATE') THEN new_oid ELSE old_oid END")
        )
        .withColumn(
            "type",
            expr("CASE WHEN operation IN ('INSERT', 'UPDATE') THEN new_type ELSE old_type END")
        )
        .withColumn(
            "campaign_reach_estimate",
            expr("CASE WHEN operation IN ('INSERT', 'UPDATE') THEN new_campaign_reach_estimate ELSE old_campaign_reach_estimate END")
        )
        .withColumn(
            "ad_duplication_scenario",
            expr("CASE WHEN operation IN ('INSERT', 'UPDATE') THEN new_ad_duplication_scenario ELSE old_ad_duplication_scenario END")
        )
        .withColumn(
            "bid_type",
            expr("CASE WHEN operation IN ('INSERT', 'UPDATE') THEN new_bid_type ELSE old_bid_type END")
        )
        .withColumn(
            "time_updated",
            expr("CASE WHEN operation IN ('INSERT', 'UPDATE') THEN new_time_updated ELSE old_time_updated END")
        )
        .withColumn(
            "time_created",
            expr("CASE WHEN operation IN ('INSERT', 'UPDATE') THEN new_time_created ELSE old_time_created END")
        )
        .withColumn(
            "parent_campaign_id",
            expr("CASE WHEN operation IN ('INSERT', 'UPDATE') THEN new_parent_campaign_id ELSE old_parent_campaign_id END")
        )
        .withColumn(
            "account_id",
            expr("CASE WHEN operation IN ('INSERT', 'UPDATE') THEN new_account_id ELSE old_account_id END")
        )
        .withColumn(
            "creative_media_type",
            expr("CASE WHEN operation IN ('INSERT', 'UPDATE') THEN new_creative_media_type ELSE old_creative_media_type END")
        )
        .withColumn(
            "creative_id",
            expr("CASE WHEN operation IN ('INSERT', 'UPDATE') THEN new_creative_id ELSE old_creative_id END")
        )
        .withColumn(
            "account_admarket_id",
            expr("CASE WHEN operation IN ('INSERT', 'UPDATE') THEN new_account_admarket_id ELSE old_account_admarket_id END")
        )
        .withColumn(
            "is_donation_enabled",
            expr("CASE WHEN operation IN ('INSERT', 'UPDATE') THEN new_is_donation_enabled ELSE old_is_donation_enabled END")
        )
        .withColumn(
            "www_request_id",
            expr("CASE WHEN operation IN ('INSERT', 'UPDATE') THEN new_www_request_id ELSE old_www_request_id END")
        )
        .withColumn(
            "run_status",
            expr("CASE WHEN operation IN ('INSERT', 'UPDATE') THEN new_run_status ELSE old_run_status END")
        )
        .withColumn(
            "audit_version",
            expr("CASE WHEN operation IN ('INSERT', 'UPDATE') THEN new_audit_version ELSE old_audit_version END")
        )
        .withColumn(
            "target_spec_id",
            expr("CASE WHEN operation IN ('INSERT', 'UPDATE') THEN new_target_spec_id ELSE old_target_spec_id END")
        )
        .withColumn(
            "backend_creative_type",
            expr("CASE WHEN operation IN ('INSERT', 'UPDATE') THEN new_backend_creative_type ELSE old_backend_creative_type END")
        )
        .withColumn(
            "location",
            expr("CASE WHEN operation IN ('INSERT', 'UPDATE') THEN new_location ELSE old_location END")
        )
        .withColumn(
            "delivery_id",
            expr("CASE WHEN operation IN ('INSERT', 'UPDATE') THEN new_delivery_id ELSE old_delivery_id END")
        )
        .withColumn(
            "creator_id",
            expr("CASE WHEN operation IN ('INSERT', 'UPDATE') THEN new_creator_id ELSE old_creator_id END")
        )
        .withColumn(
            "parent_campaign_group_id",
            expr("CASE WHEN operation IN ('INSERT', 'UPDATE') THEN new_parent_campaign_group_id ELSE old_parent_campaign_group_id END")
        )
        .withColumn(
            "parent_adgroup_id",
            expr("CASE WHEN operation IN ('INSERT', 'UPDATE') THEN new_parent_adgroup_id ELSE old_parent_adgroup_id END")
        )
    )

# COMMAND ----------

# MAGIC %md
# MAGIC ## Gold Layer: SCD Type 2 Target Table

# COMMAND ----------

dp.create_streaming_table(
    name="fbobj_scd2_target",
    comment="SCD Type 2 table tracking historical changes for Facebook objects"
)

dp.create_auto_cdc_flow(
    target="fbobj_scd2_target",
    source="cdc_prepared",
    keys=["oid"],  # Primary key for tracking records
    sequence_by=col("mutation_timestamp_ms"),  # Use mutation timestamp for ordering
    apply_as_deletes=expr("operation = 'DELETE'"),  # Mark deletes
    except_column_list=["operation"],  # Exclude operation column from final table
    stored_as_scd_type="2"  # Enable SCD Type 2
)
