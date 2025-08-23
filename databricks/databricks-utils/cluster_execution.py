#!/usr/bin/env python3

import os
import time
from pathlib import Path
from databricks.sdk import WorkspaceClient
from databricks.sdk.service import compute
from databricks.sdk.service.compute import Language, CommandStatus

# Load environment variables from .env.local if it exists
def load_env_local():
    env_file = Path(__file__).parent / '.env.local'
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

load_env_local()

# Databricks configuration - loads from environment or .env.local
DATABRICKS_HOST = os.getenv('DATABRICKS_HOST', 'https://your-workspace.cloud.databricks.com')

def get_e2_demo_client():
    """Initialize Databricks client - works both locally and in Databricks notebooks"""
    
    # Check if we're in a Databricks environment by looking for specific env vars
    if 'DATABRICKS_RUNTIME_VERSION' in os.environ or 'DB_HOME' in os.environ:
        print("Running in Databricks environment - using default authentication")
        try:
            # In Databricks notebooks, use default auth
            return WorkspaceClient()
        except Exception as e:
            print(f"Default auth failed, trying with explicit host: {e}")
            return WorkspaceClient(host="https://e2-demo-field-eng.cloud.databricks.com")
    else:
        # We're running locally - use PAT token
        print("Running locally - using PAT token authentication")
        
        # Get token at function call time (not module import time)
        databricks_e2_demo_token = os.getenv('E2_DEMO_FIELD_ENG_PAT')
        
        # Check if token is available
        if not databricks_e2_demo_token:
            raise ValueError("E2_DEMO_FIELD_ENG_PAT environment variable is not set or is None. Please check your environment configuration.")
        
        # Set environment variables from constants
        os.environ['DATABRICKS_TOKEN'] = databricks_e2_demo_token
        os.environ['DATABRICKS_HOST'] = DATABRICKS_HOST
        
        print(f"Connecting to Databricks at: {DATABRICKS_HOST}")
        return WorkspaceClient(host=DATABRICKS_HOST, token=databricks_e2_demo_token)

def get_or_create_cluster(client, cluster_name="ashwin-test-cluster"):
    """Get existing cluster or create a new one if not found"""
    
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
    
    cluster_config = {
        "cluster_name": cluster_name,
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
    
    cluster_spec = compute.CreateCluster(
        cluster_name=cluster_config["cluster_name"],
        spark_version=cluster_config["spark_version"],
        node_type_id=cluster_config["node_type_id"],
        num_workers=cluster_config["num_workers"],
        driver_node_type_id=cluster_config.get("driver_node_type_id"),
        autotermination_minutes=cluster_config.get("autotermination_minutes"),
        enable_elastic_disk=cluster_config.get("enable_elastic_disk"),
        disk_spec=compute.DiskSpec(**cluster_config["disk_spec"]) if "disk_spec" in cluster_config else None
    )
    
    print(f"Launching cluster: {cluster_config['cluster_name']}")
    cluster = client.clusters.create_and_wait(cluster_spec)
    print(f"Cluster launched successfully! Cluster ID: {cluster.cluster_id}")
    print(f"Cluster state: {cluster.state}")
    
    return cluster.cluster_id

def get_cluster_info(client, cluster_id="0819-033442-njp866rg"):
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


def execute_query_on_cluster(client, query, cluster_id="0819-033442-njp866rg", cluster_name="ashwin-test-cluster"):
    """
    Execute a SQL query on an All Purpose cluster
    
    Args:
        client: WorkspaceClient instance
        query: SQL query string to execute
        cluster_id: Optional cluster ID. If not provided, will use cluster_name
        cluster_name: Cluster name to find/create if cluster_id not provided
    
    Returns:
        Query results as a list of dictionaries
    """
    try:
        # Use the provided cluster ID directly
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
    """Test cluster execution"""
    try:
        print("Starting Databricks connection...")
        client = get_e2_demo_client()
        print("Databricks E2_DEMO client initialized successfully!")
        
        # Test query
        test_query = "SELECT 1 as test_column"
        result = execute_query_on_cluster(client, test_query)
        
        print(f"Test query result: {result}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()