# Image Processing Pipeline Demo

This project provides a complete setup for an image processing pipeline designed to run in a local Kubernetes environment. It is intended for demonstration purposes.

## Overview

- **Local Environment**: Runs entirely on a local machine using [Kind (Kubernetes in Docker)](https://kind.sigs.k8s.io/).
- **Infrastructure as Code**: Uses [cdk8s](https://cdk8s.io/) (Cloud Development Kit for Kubernetes) to programmatically generate Kubernetes manifests.
- **Pipeline Scripts**: Includes a set of scripts and components to start and manage the image processing pipeline.

## Prerequisites

Ensure you have the following installed:

- **[Mise](https://mise.jdx.dev/)** (Task runner and tool manager)
- **Docker**
- **Kubectl**

## Quick Start

Follow these steps to spin up the cluster and deploy the application.

### 1. Install Dependencies & Setup Environment

Use `mise` to install project tools and dependencies.

```bash
mise run install
```

### 2. Start Local Cluster

Initialize the Kind cluster.

```bash
mise run up
```

### 3. Initialize Infrastructure

This step loads necessary Docker images into the cluster and installs core infrastructure components like Flux.

```bash
mise run init
```

### 4. Build Manifests

Generate the Kubernetes YAML manifests using cdk8s.

```bash
mise run build
```

<!-- ### 5. Build & Load Application Images

Build the custom Docker images for the pipeline and load them into the Kind cluster.

```bash
mise run build-programs
mise run load-programs
``` -->

### 6. Deploy Components

Apply the generated manifests to the cluster in the following order.

**Deploy Operators & Core Infra:**
```bash
kubectl apply -k src/dist/operator-prometheus-*
kubectl apply -k src/dist/operator-grafana-*
kubectl apply -k src/dist/keda-*
kubectl apply -k src/dist/strimzi-*
kubectl apply -k src/dist/telepresence-*
```

*> Wait a moment for operators to initialize (approx 5-10 seconds).*

**Deploy Application & Middleware:**
```bash
kubectl apply -k src/dist/kafka-*
kubectl apply -k src/dist/grafana-*
kubectl apply -k src/dist/prometheus-*
kubectl apply -k src/dist/downloader-*
kubectl apply -k src/dist/image-reactor-*
kubectl apply -k src/dist/embeder-*
```

---
```bash
telepresence quit
telepresence connect
./generate_kafka_messages.py -d 60 -n 600
```
