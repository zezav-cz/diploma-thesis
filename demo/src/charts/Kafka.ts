import { Construct } from 'constructs';
import { ApiObject, Chart, ChartProps } from 'cdk8s';
import * as fs from 'fs';
import * as path from 'path';

import * as k8s from "../../imports/k8s-1-32/imports/k8s";
import * as strimzi from "../../imports/strimzi-0-45";
import * as flux from "../../imports/fluxcd-2-3"
import * as prometheus from "../../imports/prometheus-operator-0-58/imports/monitoring.coreos.com";

interface Props extends ChartProps {
  namespace: string;
}

export class Kafka extends Chart {
  constructor(scope: Construct, id: string, props: Props) {
    props = { disableResourceNameHashes: true, ...props, };
    super(scope, id, props);

    new k8s.KubeNamespace(this, 'namespace', {
      metadata: {
        name: props.namespace
      }
    });

    const prometheusRepo = new flux.source.HelmRepository(this, 'prom', {
      spec: {
        interval: '24h',
        url: 'oci://ghcr.io/prometheus-community/charts',
        type: flux.source.HelmRepositorySpecType.OCI,
        provider: flux.source.HelmRepositorySpecProvider.GENERIC,
      }
    });

    const kafkaUIRepo = new flux.source.HelmRepository(this, 'repo', {
      spec: {
        interval: '24h',
        url: 'https://ui.charts.kafbat.io/',
        type: flux.source.HelmRepositorySpecType.DEFAULT,
        provider: flux.source.HelmRepositorySpecProvider.GENERIC,
      }
    });

    const kafkaMetricsConfig = fs.readFileSync(
      path.join(__dirname, 'kafka-metrics-config.yaml'),
      'utf8'
    );

    const kafkaMetrics = new k8s.KubeConfigMap(this, 'kafka-metrics', {
      metadata: {
        name: 'kafka-metrics',
        namespace: props.namespace
      },
      data: {
        'kafka-metrics-config.yml': kafkaMetricsConfig
      }
    });


    const cluster = new strimzi.kafka.Kafka(this, 'cluster', {
      metadata: {
        annotations: {
          "strimzi.io/kraft": "enabled",
          "strimzi.io/node-pools": "enabled"
        }
      },
      spec: {
        kafka: {
          version: "4.1.0",
          replicas: 3,
          listeners: [
            { name: "plain", port: 9092, type: strimzi.kafka.KafkaSpecKafkaListenersType.INTERNAL, tls: false },
            { name: "tls", port: 9093, type: strimzi.kafka.KafkaSpecKafkaListenersType.INTERNAL, tls: false }
          ],
          config: {
          },
          metricsConfig: {
            type: strimzi.kafka.KafkaSpecKafkaMetricsConfigType.JMX_PROMETHEUS_EXPORTER,
            valueFrom: {
              configMapKeyRef: {
                name: kafkaMetrics.name,
                key: 'kafka-metrics-config.yml'
              }
            }
          }
        },
        entityOperator: {
          topicOperator: {},
          userOperator: {}
        }
      }
    });

    new strimzi.kafka.KafkaNodePool(this, 'main', {
      metadata: {
        labels: {
          "strimzi.io/cluster": cluster.metadata.name!,
        }
      },
      spec: {
        replicas: 3,
        roles: [strimzi.kafka.KafkaNodePoolSpecRoles.BROKER, strimzi.kafka.KafkaNodePoolSpecRoles.CONTROLLER],
        storage: {
          type: strimzi.kafka.KafkaNodePoolSpecStorageType.PERSISTENT_HYPHEN_CLAIM,
          size: "10Gi",
          deleteClaim: false,
        }
      }
    });
    new flux.helm.HelmRelease(this, 'prometheus-kafka-exporter', {
      spec: {
        interval: '5m',
        timeout: '2m',
        chart: {
          spec: {
            chart: 'prometheus-kafka-exporter',
            version: '3.0.0',
            interval: '5m',
            reconcileStrategy: flux.helm.HelmReleaseSpecChartSpecReconcileStrategy.CHART_VERSION,
            sourceRef: {
              kind: flux.helm.HelmReleaseSpecChartSpecSourceRefKind.HELM_REPOSITORY,
              name: prometheusRepo.name,
              namespace: prometheusRepo.metadata.namespace,
            }
          }
        },
        values: {
          kafkaServer: [`${cluster.name}-kafka-brokers.${cluster.metadata.namespace}.svc:9092`],
          prometheus: {
            serviceMonitor: {
              enabled: true,
              namespace: props.namespace,
            },
          },
        },
      }
    });


    new flux.helm.HelmRelease(this, 'ui', {
      spec: {
        interval: '5m',
        timeout: '2m',
        chart: {
          spec: {
            chart: 'kafka-ui',
            version: '1.4.x',
            interval: '5m',
            reconcileStrategy: flux.helm.HelmReleaseSpecChartSpecReconcileStrategy.CHART_VERSION,
            sourceRef: {
              kind: flux.helm.HelmReleaseSpecChartSpecSourceRefKind.HELM_REPOSITORY,
              name: kafkaUIRepo.name,
              namespace: kafkaUIRepo.metadata.namespace,
            }
          }
        },
        values: {
          env: [],
          replicaCount: 1,
          volumeMounts: [],
          volumes: [],
          yamlApplicationConfig: {
            kafka: {
              auth: {
                type: "disabled"
              },
              clusters: [
                {
                  bootstrapServers: `${cluster.name}-kafka-brokers.${cluster.metadata.namespace}.svc:9092`,
                  name: `${cluster.name}-kafka-brokers.${cluster.metadata.namespace}.svc`,
                }
              ],
              management: {
                health: {
                  ldap: {
                    "enabled": false
                  }
                }
              }
            }
          }
        },
      }
    });

    new strimzi.kafka.KafkaTopic(this, 'downloader', {
      metadata: {
        labels: {
          "strimzi.io/cluster": cluster.metadata.name!,
        }
      },
      spec: {
        topicName: 'downloader',
        partitions: 6,
        replicas: 1,
        config: {}
      }
    });

    new prometheus.PodMonitor(this, 'kafka', {
      spec: {
        selector: {
          matchLabels: {
            "strimzi.io/cluster": cluster.metadata.name!,
            "strimzi.io/broker-role": "true"
          }
        },
        podMetricsEndpoints: [
          {
            path: '/metrics',
            port: 'tcp-prometheus',
          }
        ]
      }
    });

    new strimzi.kafka.KafkaTopic(this, 'embeder', {
      metadata: {
        labels: {
          "strimzi.io/cluster": cluster.metadata.name!,
        }
      },
      spec: {
        topicName: 'embeder',
        partitions: 20,
        replicas: 1,
        config: {}
      }
    });



  }
}
