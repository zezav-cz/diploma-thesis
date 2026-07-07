# Master's Thesis — Jan Troják

This repository contains my master's thesis:

**Design and Implementation of a Scalable, On-Premise Infrastructure for Large-Scale Data
Gathering, Processing, and Storage in Machine Learning Applications**

- **Author:** Bc. Jan Troják
- **Supervisor:** Ing. Tomáš Vondra, Ph.D.
- **University:** Czech Technical University in Prague, Faculty of Information Technology

## Assignment

The official assignment is in [`text/trojaj12-assignment.pdf`](text/trojaj12-assignment.pdf):

1. Analyze the storage and processing requirements for ML-driven evaluation of small binary
   file datasets, specifically image files ranging from ~10 KiB to ~1 MiB.
2. Research fault-tolerant distributed file systems (DFS) and evaluate open-source solutions
   that meet the specified requirements.
3. Choose and deploy a scalable, fault-tolerant, distributed open-source storage
   infrastructure optimized for small binary file storage.
4. Develop an on-demand job execution pipeline for data retrieval, storage, and ML operations
   on the stored data.
5. Deploy the necessary infrastructure to support and orchestrate the pipeline.

## Repository contents

Each folder has its own README with details:

- [`text/`](text/) — LaTeX source of the thesis text and the assignment PDF
- [`downloader/`](downloader/README.md) — image download service
- [`image-reactor/`](image-reactor/README.md) — image metadata service
- [`embedder/`](embedder/README.md) — embedding workload service
- [`image-store-bolt/`](image-store-bolt/README.md) — SeaweedFS storage deployment
- [`demo/`](demo/README.md) — end-to-end pipeline demo on local Kubernetes
