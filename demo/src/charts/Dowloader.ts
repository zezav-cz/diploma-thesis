import { Construct } from 'constructs';
import { Chart, ChartProps } from 'cdk8s';

import * as k8s from "../../imports/k8s-1-32/imports/k8s";
import * as prometheus from "../../imports/prometheus-operator-0-58/imports/monitoring.coreos.com";
import * as keda from "../../imports/keda-2-18";

interface Props extends ChartProps {
  namespace: string;
  imageName: string;
}

export class Downloader extends Chart {
  constructor(scope: Construct, id: string, props: Props) {
    props = { disableResourceNameHashes: true, ...props, };
    super(scope, id, props);

    new k8s.KubeNamespace(this, 'namespace', {
      metadata: {
        name: props.namespace
      }
    });

    const depl = this.deployment(props.imageName);
    new keda.keda.ScaledObject(this, 'downloader-scaledobject', {
      metadata: {
        annotations: {
          "autoscaling.keda.sh/paused": "false"
        },
      },
      spec: {
        scaleTargetRef: {
          name: depl.name,
          apiVersion: depl.apiVersion,
          kind: depl.kind,
        },
        pollingInterval: 5, // How often (in seconds) KEDA will check the metric values for scaling
        cooldownPeriod: 0, // How long (in seconds) KEDA will wait after the last metric trigger before scaling down
        minReplicaCount: 1,
        fallback: { // Fallback behavior when scaler is in error state
          behavior: keda.keda.ScaledObjectSpecFallbackBehavior.STATIC,
          replicas: 3,
          failureThreshold: 3,
        },
        advanced: {
          horizontalPodAutoscalerConfig: {
            behavior: {
              scaleDown: { // Scaling down behavior
                stabilizationWindowSeconds: 10, // The period (in seconds) for which past recommendations should be considered while scaling down
                policies: [
                  { // Scaling policies - how fast to scale down and how often
                    type: 'Percent',
                    value: 100,
                    periodSeconds: 15,
                  }
                ]
              }
            }
          }
        },
        triggers: [
          {
            type: 'kafka',
            metadata: {
              bootstrapServers: 'kafka-cluster-kafka-bootstrap.kafka.svc:9092',
              consumerGroup: 'downloader-group',
              topic: 'downloader',
              lagThreshold: '40', // Target value for the total lag (sum of all partition lags) to trigger scaling actions.
              activationLagThreshold: '0',
              scaleToZeroOnInvalidOffset: 'true',
              limitToPartitionsWithLag: 'true',
            },
          },
        ],
      }
    });

    new k8s.KubeService(this, 'downloader-service', {
      metadata: {
        labels: {
          app: 'downloader'
        }
      },
      spec: {
        selector: {
          app: 'downloader'
        },
        ports: [
          {
            port: 9090,
            targetPort: k8s.IntOrString.fromNumber(9090),
            name: 'http-metrics',
            protocol: 'TCP'
          }
        ],
        type: 'ClusterIP'
      }
    });

    new prometheus.ServiceMonitor(this, 'downloader-servicemonitor', {
      spec: {
        selector: {
          matchLabels: {
            app: 'downloader'
          }
        },
        endpoints: [
          {
            port: 'http-metrics',
            interval: '15s',
            scrapeTimeout: '10s',
          }
        ]
      }
    });


  }

  deployment(imageName: string) : k8s.KubeDeployment {
    return new k8s.KubeDeployment(this, 'downloader-deployment', {
      spec: {
        selector: {
          matchLabels: {
            app: 'downloader'
          }
        },
        template: {
          metadata: {
            labels: {
              app: 'downloader'
            }
          },
          spec: {
            terminationGracePeriodSeconds: 60,
            containers: [
              {
                name: 'downloader',
                image: imageName,
                imagePullPolicy: 'Never',
                ports: [{ containerPort: 8080 }],
                env: [
                  { name: 'LOGGING_LEVEL', value: 'debug' },
                  { name: 'LOGGING_FORMAT', value: 'txt' },
                  { name: 'DOWNLOADER_MAX_WORKERS', value: '10' },
                  { name: 'DOWNLOADER_TIMEOUT_SECONDS', value: '30' },
                  { name: 'KAFKA_TOPIC', value: 'downloader' },
                  { name: 'KAFKA_PRODUCER_TOPIC', value: 'embeder' },
                  { name: 'KAFKA_CONSUMER_GROUP', value: 'downloader-group' },
                  { name: 'HEALTH_PORT', value: '8081' },
                  { name: 'HEALTH_KAFKA_CHECK_TIMEOUT_SECONDS', value: '5' },
                  { name: 'HEALTH_STARTUP_GRACE_PERIOD_SECONDS', value: '30' },
                  { name: 'METRICS_PORT', value: '9090' },
                  { name: 'KAFKA_BROKERS', value: 'kafka-cluster-kafka-bootstrap.kafka.svc:9092' },
                  // { name: 'seaweedfs_timeout_seconds', value: '30' },
                  // { name: 'seaweedfs_chunk_size_mb', value: '4' },
                  { name: 'SEAWEEDFS_MASTER_URL', value: 'redacted' },
                  { name: 'SEAWEEDFS_FILER_URL', value: 'redacted' },
                  { name: 'SEAWEEDFS_USE_MOCK', value: 'false' },
                  { name: 'SEAWEEDFS_USE_FAKE', value: 'false' },
                  { name: 'DATABASE_API_URL', value: 'http://image-reactor.image-reactor.svc:9000' },
                ],
                livenessProbe: {
                  httpGet: {
                    path: '/healthz',
                    port: k8s.IntOrString.fromNumber(8081)
                  },
                  initialDelaySeconds: 10,
                  periodSeconds: 10
                },
                readinessProbe: {
                  httpGet: {
                    path: '/readyz',
                    port: k8s.IntOrString.fromNumber(8081)
                  },
                  initialDelaySeconds: 5,
                  periodSeconds: 5
                },
                startupProbe: {
                  exec: {
                    command: ['test', '-f', '/tmp/start']
                  },
                  initialDelaySeconds: 0,
                  periodSeconds: 2,
                  failureThreshold: 30
                }
              }
            ]
          }
        }
      }
    });

  }
}
