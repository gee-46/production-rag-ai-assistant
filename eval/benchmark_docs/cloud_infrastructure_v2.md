# Cloud Infrastructure Specification & Architecture v2

## 1. Cluster Compute Configuration
The enterprise cluster `CLUSTER-DELTA-9` operates across 3 availability zones in `us-east-1`. Compute nodes run hardened Ubuntu 22.04 LTS instances with 64 vCPUs and 256 GB ECC RAM per node. The primary orchestrator is Kubernetes v1.28 with Calico CNI.

## 2. VPC Networking & Firewall Rules
- **Management Port**: Ingress on TCP port `8443` is restricted strictly to the corporate bastion subnet (`10.240.0.0/16`).
- **MTU Configuration**: Jumbo frames are enabled with an MTU of `9000` bytes on private VPC interconnects.
- **Egress Filtering**: Direct public internet egress is denied by default. All external API traffic routes via the forward proxy `proxy.corp.internal:3128`.

## 3. Data Backup and Retention Policies
- **Standard Snapshots**: Automated differential snapshots are captured every 4 hours and retained for `30 days`.
- **Compliance Archive**: Immutable WORM (Write Once, Read Many) cold archives are sealed monthly and retained for `7 years`.
- **RTO / RPO Objectives**: Target Recovery Time Objective (RTO) is `15 minutes`, and Recovery Point Objective (RPO) is `5 minutes`.
