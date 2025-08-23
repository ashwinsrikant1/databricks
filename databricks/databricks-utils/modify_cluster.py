#!/usr/bin/env python3
"""
Script to modify Databricks cluster configurations using the Databricks SDK.
"""

import sys
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.compute import EditClusterRequest, ClusterSpec


def modify_cluster(cluster_id: str, **modifications):
    """
    Modify a Databricks cluster configuration.
    
    Args:
        cluster_id (str): The ID of the cluster to modify
        **modifications: Keyword arguments for cluster modifications
    """
    try:
        # Initialize Databricks client
        w = WorkspaceClient()
        
        # Get current cluster configuration
        current_cluster = w.clusters.get(cluster_id=cluster_id)
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
        
        # Create modification request with current config as base
        cluster_spec = ClusterSpec(
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
        
        # Apply modifications
        edit_request = EditClusterRequest(
            cluster_id=cluster_id,
            cluster_name=cluster_spec.cluster_name,
            spark_version=cluster_spec.spark_version,
            node_type_id=cluster_spec.node_type_id,
            driver_node_type_id=cluster_spec.driver_node_type_id,
            num_workers=cluster_spec.num_workers,
            autoscale=cluster_spec.autoscale,
            spark_conf=updated_spark_conf,
            spark_env_vars=cluster_spec.spark_env_vars,
            custom_tags=cluster_spec.custom_tags,
        )
        
        w.clusters.edit(**edit_request.as_dict())
        print(f"\nCluster {cluster_id} modification request submitted successfully!")
        print("Note: Changes may take a few minutes to take effect.")
        
    except Exception as e:
        print(f"Error modifying cluster: {e}")
        sys.exit(1)


def main():
    """Main function to handle command line arguments and cluster modification."""
    if len(sys.argv) < 2:
        print("Usage: python modify_cluster.py <cluster_id> [options]")
        print("\nOptions:")
        print("  --name <name>                 New cluster name")
        print("  --workers <num>               Number of workers")
        print("  --node-type <type>            Worker node type")
        print("  --driver-node-type <type>     Driver node type") 
        print("  --spark-version <version>     Spark runtime version")
        print("  --spark-conf <key=value>      Add/update Spark configuration (can be used multiple times)")
        print("\nExamples:")
        print("  python modify_cluster.py 0123-456789-abcde --workers 5 --name 'Updated Cluster'")
        print("  python modify_cluster.py 0123-456789-abcde --spark-conf 'spark.sql.adaptive.enabled=true' --spark-conf 'spark.databricks.io.cache.enabled=true'")
        sys.exit(1)
    
    cluster_id = sys.argv[1]
    modifications = {}
    spark_conf_updates = {}
    
    # Parse command line arguments
    i = 2
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
            # Parse spark configuration in format key=value
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
    
    # Handle spark_conf updates
    if spark_conf_updates:
        modifications['spark_conf_updates'] = spark_conf_updates
    
    if not modifications:
        print("No modifications specified. Use --help for usage information.")
        sys.exit(1)
    
    print(f"Modifying cluster {cluster_id} with the following changes:")
    for key, value in modifications.items():
        if key == 'spark_conf_updates':
            print(f"  Spark configuration updates:")
            for conf_key, conf_value in value.items():
                print(f"    {conf_key} = {conf_value}")
        else:
            print(f"  {key}: {value}")
    
    modify_cluster(cluster_id, **modifications)


if __name__ == "__main__":
    main()