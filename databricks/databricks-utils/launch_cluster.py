#!/usr/bin/env python3

from databricks.sdk import WorkspaceClient
from databricks.sdk.service import compute

CLUSTER_CONFIG = {
    "cluster_name": "ashwin-test-cluster",
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

def launch_cluster(config=None):
    if config is None:
        config = CLUSTER_CONFIG
    
    w = WorkspaceClient()
    
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
    cluster = w.clusters.create_and_wait(cluster_spec)
    print(f"Cluster launched successfully! Cluster ID: {cluster.cluster_id}")
    print(f"Cluster state: {cluster.state}")
    
    return cluster

def main():
    w = WorkspaceClient()
    print("Databricks SDK initialized successfully!")
    cluster = launch_cluster()
    print(f"Cluster is ready!")

if __name__ == "__main__":
    main()
