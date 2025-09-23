#!/usr/bin/env python3
"""
Databricks Cluster Utilities

This script provides comprehensive cluster management functionality for Databricks workspaces.
It consolidates cluster operations into a single, configurable utility with both programmatic
and command-line interfaces.

Features:
---------
- List all clusters in the workspace
- Get detailed information about specific clusters
- Launch new clusters with customizable configurations
- Get existing clusters or create new ones if not found
- Execute SQL queries on All Purpose clusters
- Modify cluster configurations (workers, node types, Spark config, etc.)

Authentication:
--------------
- Supports both local PAT token authentication and Databricks notebook default auth
- Automatically detects environment and uses appropriate authentication method
- Configurable workspace URL and token at the top of the file

Command Line Usage:
------------------
python cluster_utils.py list                          # List all clusters
python cluster_utils.py info <cluster_id>             # Get cluster information
python cluster_utils.py launch [cluster_name]         # Launch a new cluster
python cluster_utils.py get-or-create [cluster_name]  # Get existing or create new cluster
python cluster_utils.py execute <cluster_id> <query>  # Execute SQL query on cluster
python cluster_utils.py modify <cluster_id> <options> # Modify cluster configuration

Programmatic Usage:
------------------
from cluster_utils import get_databricks_client, list_clusters, launch_cluster

client = get_databricks_client()
clusters = list_clusters(client)
cluster = launch_cluster(client, custom_config)

Configuration:
-------------
Modify the DATABRICKS_HOST and DATABRICKS_TOKEN variables at the top of this file,
or set them via environment variables. The DEFAULT_CLUSTER_CONFIG can also be
customized for your preferred cluster specifications.

Dependencies:
------------
- databricks-sdk
- Standard Python libraries (os, time, sys, pathlib)
"""

import os
import time
import sys
from pathlib import Path
from databricks.sdk import WorkspaceClient
from databricks.sdk.service import compute
from databricks.sdk.service.compute import Language, CommandStatus

# =============================================================================
# CONFIGURATION - Modify these values as needed
# =============================================================================

# Databricks workspace configuration
DATABRICKS_HOST = "https://your-workspace.cloud.databricks.com"
DATABRICKS_TOKEN = "your-databricks-token"

# Default cluster configuration
DEFAULT_CLUSTER_CONFIG = {
    "cluster_name": "test-cluster",
    "spark_version": "13.3.x-scala2.12",
    "node_type_id": "i3.2xlarge",
    "num_workers": 4,
    "driver_node_type_id": "i3.2xlarge",
    "autotermination_minutes": 30,
    "enable_elastic_disk": True,
    "disk_spec": {
        "disk_type": {
            "ebs_volume_type": "GENERAL_PURPOSE_SSD"
        },
        "disk_size": 100,
        "disk_count": 1
    }
}

# =============================================================================
# IMPLEMENTATION - Generally no need to modify below this line
# =============================================================================

def load_env_local():
    """Load environment variables from .env.local if it exists"""
    env_file = Path(__file__).parent / '.env.local'
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

def get_databricks_client():
    """Initialize Databricks client - works both locally and in Databricks notebooks"""

    # Load any local env file first
    load_env_local()

    # Check if we're in a Databricks environment by looking for specific env vars
    if 'DATABRICKS_RUNTIME_VERSION' in os.environ or 'DB_HOME' in os.environ:
        print("Running in Databricks environment - using default authentication")
        try:
            # In Databricks notebooks, use default auth
            return WorkspaceClient()
        except Exception as e:
            print(f"Default auth failed, trying with explicit host: {e}")
            return WorkspaceClient(host=DATABRICKS_HOST)
    else:
        # We're running locally - use PAT token
        print("Running locally - using PAT token authentication")

        # Use configured token or try environment variable
        token = DATABRICKS_TOKEN or os.getenv('DATABRICKS_TOKEN') or os.getenv('E2_DEMO_FIELD_ENG_PAT')
        host = DATABRICKS_HOST or os.getenv('DATABRICKS_HOST')

        # Check if token is available
        if not token:
            raise ValueError("DATABRICKS_TOKEN is not configured. Please set it in the configuration section or environment variables.")

        if not host:
            raise ValueError("DATABRICKS_HOST is not configured. Please set it in the configuration section or environment variables.")

        # Set environment variables
        os.environ['DATABRICKS_TOKEN'] = token
        os.environ['DATABRICKS_HOST'] = host

        print(f"Connecting to Databricks at: {host}")
        return WorkspaceClient(host=host, token=token)

def list_clusters(client):
    """List all clusters in the workspace"""
    try:
        clusters = list(client.clusters.list())
        print(f"Found {len(clusters)} clusters:")
        for cluster in clusters:
            print(f"  - {cluster.cluster_name} (ID: {cluster.cluster_id}, State: {cluster.state})")
        return clusters
    except Exception as e:
        print(f"Error listing clusters: {e}")
        return []

def get_cluster_info(client, cluster_id):
    """
    Get detailed cluster configuration information.

    Args:
        client: WorkspaceClient instance
        cluster_id: ID of the cluster to get info for

    Returns:
        Dictionary with cluster configuration details
    """
    try:
        cluster = client.clusters.get(cluster_id)

        cluster_info = {
            "cluster_id": cluster.cluster_id,
            "cluster_name": cluster.cluster_name,
            "spark_version": cluster.spark_version,
            "node_type_id": cluster.node_type_id,
            "driver_node_type_id": cluster.driver_node_type_id,
            "num_workers": cluster.num_workers,
            "autotermination_minutes": cluster.autotermination_minutes,
            "state": str(cluster.state),
            "runtime_engine": str(cluster.runtime_engine) if cluster.runtime_engine else "Standard",
            "data_security_mode": str(cluster.data_security_mode) if cluster.data_security_mode else "None"
        }

        # Add AWS-specific attributes if available
        if hasattr(cluster, 'aws_attributes') and cluster.aws_attributes:
            cluster_info["aws_zone_id"] = cluster.aws_attributes.zone_id
            cluster_info["aws_instance_profile_arn"] = cluster.aws_attributes.instance_profile_arn

        # Add autoscaling info if available
        if hasattr(cluster, 'autoscale') and cluster.autoscale:
            cluster_info["autoscale_min_workers"] = cluster.autoscale.min_workers
            cluster_info["autoscale_max_workers"] = cluster.autoscale.max_workers
            cluster_info["num_workers"] = f"{cluster.autoscale.min_workers}-{cluster.autoscale.max_workers} (autoscale)"

        return cluster_info

    except Exception as e:
        print(f"Error getting cluster info: {e}")
        return {"error": str(e), "cluster_id": cluster_id}

def launch_cluster(client, config=None):
    """Launch a new cluster with the given configuration"""
    if config is None:
        config = DEFAULT_CLUSTER_CONFIG

    cluster_spec = compute.CreateCluster(
        cluster_name=config["cluster_name"],
        spark_version=config["spark_version"],
        node_type_id=config["node_type_id"],
        num_workers=config["num_workers"],
        driver_node_type_id=config.get("driver_node_type_id"),
        autotermination_minutes=config.get("autotermination_minutes"),
        enable_elastic_disk=config.get("enable_elastic_disk"),
        disk_spec=compute.DiskSpec(**config["disk_spec"]) if "disk_spec" in config else None
    )

    print(f"Launching cluster: {config['cluster_name']}")
    cluster = client.clusters.create_and_wait(cluster_spec)
    print(f"Cluster launched successfully! Cluster ID: {cluster.cluster_id}")
    print(f"Cluster state: {cluster.state}")

    return cluster

def get_or_create_cluster(client, cluster_name=None):
    """Get existing cluster or create a new one if not found"""
    if cluster_name is None:
        cluster_name = DEFAULT_CLUSTER_CONFIG["cluster_name"]

    # First, try to find existing cluster
    clusters = list(client.clusters.list())

    for cluster in clusters:
        if cluster.cluster_name == cluster_name:
            print(f"Found existing cluster: {cluster_name} (ID: {cluster.cluster_id})")
            print(f"Cluster state: {cluster.state}")

            # If cluster is terminated, start it
            if cluster.state in ["TERMINATED", "TERMINATING"]:
                print("Starting terminated cluster...")
                client.clusters.start(cluster.cluster_id)
                # Wait for cluster to start
                cluster = client.clusters.wait_get_cluster_running(cluster.cluster_id)
                print(f"Cluster started successfully! State: {cluster.state}")
            elif cluster.state == "RUNNING":
                print("Cluster is already running!")
            else:
                print(f"Cluster is in state: {cluster.state}, waiting for it to be ready...")
                cluster = client.clusters.wait_get_cluster_running(cluster.cluster_id)

            return cluster.cluster_id

    # Cluster not found, create a new one
    print(f"Cluster '{cluster_name}' not found. Creating new cluster...")

    config = DEFAULT_CLUSTER_CONFIG.copy()
    config["cluster_name"] = cluster_name
    cluster = launch_cluster(client, config)

    return cluster.cluster_id

def modify_cluster(client, cluster_id, **modifications):
    """
    Modify a Databricks cluster configuration.

    Args:
        client: WorkspaceClient instance
        cluster_id (str): The ID of the cluster to modify
        **modifications: Keyword arguments for cluster modifications
    """
    try:
        # Get current cluster configuration
        current_cluster = client.clusters.get(cluster_id=cluster_id)
        print(f"Current cluster '{current_cluster.cluster_name}' configuration:")
        print(f"  Node type: {current_cluster.node_type_id}")
        print(f"  Driver node type: {current_cluster.driver_node_type_id}")
        print(f"  Num workers: {current_cluster.num_workers}")
        print(f"  Autoscale: {current_cluster.autoscale}")
        print(f"  Runtime version: {current_cluster.spark_version}")
        if current_cluster.spark_conf:
            print(f"  Current Spark config: {current_cluster.spark_conf}")
        else:
            print("  Current Spark config: None")

        # Handle Spark configuration updates
        updated_spark_conf = current_cluster.spark_conf.copy() if current_cluster.spark_conf else {}
        if 'spark_conf_updates' in modifications:
            updated_spark_conf.update(modifications['spark_conf_updates'])
            print(f"\nUpdated Spark config will be: {updated_spark_conf}")

        # Apply modifications directly
        client.clusters.edit(
            cluster_id=cluster_id,
            cluster_name=modifications.get('cluster_name', current_cluster.cluster_name),
            spark_version=modifications.get('spark_version', current_cluster.spark_version),
            node_type_id=modifications.get('node_type_id', current_cluster.node_type_id),
            driver_node_type_id=modifications.get('driver_node_type_id', current_cluster.driver_node_type_id),
            num_workers=modifications.get('num_workers', current_cluster.num_workers),
            autoscale=modifications.get('autoscale', current_cluster.autoscale),
            spark_conf=updated_spark_conf,
            spark_env_vars=modifications.get('spark_env_vars', current_cluster.spark_env_vars),
            custom_tags=modifications.get('custom_tags', current_cluster.custom_tags),
        )
        print(f"\nCluster {cluster_id} modification request submitted successfully!")
        print("Note: Changes may take a few minutes to take effect.")

    except Exception as e:
        print(f"Error modifying cluster: {e}")
        raise

def execute_query_on_cluster(client, query, cluster_id):
    """
    Execute a SQL query on an All Purpose cluster

    Args:
        client: WorkspaceClient instance
        query: SQL query string to execute
        cluster_id: Cluster ID to execute on

    Returns:
        Query results as a dictionary
    """
    try:
        print(f"Using cluster ID: {cluster_id}")
        print(f"Executing query on cluster {cluster_id}")
        print(f"Query: {query.strip()}")

        # Create execution context first and wait for it to be ready
        context_response = client.command_execution.create(
            cluster_id=cluster_id,
            language=Language.SQL
        )

        # Wait for the context to be created
        context = context_response.result()
        context_id = context.id

        print(f"Created execution context: {context_id}")

        # Execute command on cluster
        result = client.command_execution.execute(
            cluster_id=cluster_id,
            context_id=context_id,
            language=Language.SQL,
            command=query
        )

        print("Query completed successfully!")

        # Wait for the command to complete
        command_result = result.result()

        # Parse results
        print(f"Command result: {command_result}")
        print(f"Command status: {command_result.status}")

        if command_result.status == CommandStatus.FINISHED:
            output = getattr(command_result, 'results', {})
            print(f"Query output: {output}")
            return {"raw_output": str(output), "status": "success"}
        else:
            print(f"Command failed with status: {command_result.status}")
            return {"raw_output": "", "status": "error", "error": str(command_result.status)}

    except Exception as e:
        print(f"Error executing query: {e}")
        raise

def main():
    """Main function demonstrating cluster utilities"""
    if len(sys.argv) < 2:
        print("Usage: python cluster_utils.py <command> [options]")
        print("\nCommands:")
        print("  list                          List all clusters")
        print("  info <cluster_id>             Get cluster information")
        print("  launch [cluster_name]         Launch a new cluster")
        print("  get-or-create [cluster_name]  Get existing or create new cluster")
        print("  execute <cluster_id> <query>  Execute SQL query on cluster")
        print("  modify <cluster_id> <options> Modify cluster configuration")
        print("\nModify options:")
        print("  --name <name>                 New cluster name")
        print("  --workers <num>               Number of workers")
        print("  --node-type <type>            Worker node type")
        print("  --driver-node-type <type>     Driver node type")
        print("  --spark-version <version>     Spark runtime version")
        print("  --spark-conf <key=value>      Add/update Spark configuration")
        print("\nExamples:")
        print("  python cluster_utils.py list")
        print("  python cluster_utils.py info 0123-456789-abcde")
        print("  python cluster_utils.py launch my-test-cluster")
        print("  python cluster_utils.py execute 0123-456789-abcde 'SELECT 1 as test'")
        print("  python cluster_utils.py modify 0123-456789-abcde --workers 5 --name 'Updated Cluster'")
        sys.exit(1)

    command = sys.argv[1]

    try:
        print("Starting Databricks connection...")
        client = get_databricks_client()
        print("Databricks client initialized successfully!")

        if command == "list":
            list_clusters(client)

        elif command == "info":
            if len(sys.argv) < 3:
                print("Error: cluster_id required for info command")
                sys.exit(1)
            cluster_id = sys.argv[2]
            info = get_cluster_info(client, cluster_id)
            print(f"\nCluster Information:")
            for key, value in info.items():
                print(f"  {key}: {value}")

        elif command == "launch":
            cluster_name = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_CLUSTER_CONFIG["cluster_name"]
            config = DEFAULT_CLUSTER_CONFIG.copy()
            config["cluster_name"] = cluster_name
            cluster = launch_cluster(client, config)
            print(f"Cluster launched with ID: {cluster.cluster_id}")

        elif command == "get-or-create":
            cluster_name = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_CLUSTER_CONFIG["cluster_name"]
            cluster_id = get_or_create_cluster(client, cluster_name)
            print(f"Using cluster ID: {cluster_id}")

        elif command == "execute":
            if len(sys.argv) < 4:
                print("Error: cluster_id and query required for execute command")
                sys.exit(1)
            cluster_id = sys.argv[2]
            query = sys.argv[3]
            result = execute_query_on_cluster(client, query, cluster_id)
            print(f"Query result: {result}")

        elif command == "modify":
            if len(sys.argv) < 3:
                print("Error: cluster_id required for modify command")
                sys.exit(1)
            cluster_id = sys.argv[2]

            # Parse modification arguments
            modifications = {}
            spark_conf_updates = {}
            i = 3
            while i < len(sys.argv):
                if sys.argv[i] == '--name' and i + 1 < len(sys.argv):
                    modifications['cluster_name'] = sys.argv[i + 1]
                    i += 2
                elif sys.argv[i] == '--workers' and i + 1 < len(sys.argv):
                    modifications['num_workers'] = int(sys.argv[i + 1])
                    i += 2
                elif sys.argv[i] == '--node-type' and i + 1 < len(sys.argv):
                    modifications['node_type_id'] = sys.argv[i + 1]
                    i += 2
                elif sys.argv[i] == '--driver-node-type' and i + 1 < len(sys.argv):
                    modifications['driver_node_type_id'] = sys.argv[i + 1]
                    i += 2
                elif sys.argv[i] == '--spark-version' and i + 1 < len(sys.argv):
                    modifications['spark_version'] = sys.argv[i + 1]
                    i += 2
                elif sys.argv[i] == '--spark-conf' and i + 1 < len(sys.argv):
                    conf_pair = sys.argv[i + 1]
                    if '=' not in conf_pair:
                        print(f"Invalid spark-conf format: {conf_pair}. Expected format: key=value")
                        sys.exit(1)
                    key, value = conf_pair.split('=', 1)
                    spark_conf_updates[key.strip()] = value.strip()
                    i += 2
                else:
                    print(f"Unknown option: {sys.argv[i]}")
                    sys.exit(1)

            if spark_conf_updates:
                modifications['spark_conf_updates'] = spark_conf_updates

            if not modifications:
                print("No modifications specified.")
                sys.exit(1)

            modify_cluster(client, cluster_id, **modifications)

        else:
            print(f"Unknown command: {command}")
            sys.exit(1)

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()