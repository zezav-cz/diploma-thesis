import { Construct } from 'constructs';
import { Chart, ChartProps } from 'cdk8s';

import * as k8s from "../../imports/k8s-1-32/imports/k8s";
import * as keda from "../../imports/keda-2-18";

interface Props extends ChartProps {
  namespace: string;
  imageName: string;
}

export class Embedder extends Chart {
  constructor(scope: Construct, id: string, props: Props) {
    props = { disableResourceNameHashes: true, ...props, };
    super(scope, id, props);

    new k8s.KubeNamespace(this, 'namespace', {
      metadata: {
        name: props.namespace
      }
    });

    const depl = this.deployment(props.imageName);
    new keda.keda.ScaledObject(this, 'embedder-scaledobject', {
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
              bootstrapServers: 'kafka-cluster-kafka-bootstrap.kafka.svc:9092', // TODO: Make configurable
              consumerGroup: 'embeder-group',
              topic: 'embeder',
              lagThreshold: '40', // Target value for the total lag (sum of all partition lags) to trigger scaling actions.
              activationLagThreshold: '0',
              scaleToZeroOnInvalidOffset: 'true',
              limitToPartitionsWithLag: 'true',
            },
          },
        ],
      }
    });

  }

  deployment(imageName: string): k8s.KubeDeployment {
    return new k8s.KubeDeployment(this, 'embedder-deployment', {
      spec: {
        selector: {
          matchLabels: {
            app: 'embedder'
          }
        },
        template: {
          metadata: {
            labels: {
              app: 'embedder'
            }
          },
          spec: {
            terminationGracePeriodSeconds: 60,
            containers: [
              {
                name: 'embedder',
                image: imageName,
                imagePullPolicy: 'Never',
                env: [
                  { name: 'LOG_LEVEL', value: 'DEBUG' },
                  { name: 'LOG_FORMAT', value: 'TXT' },
                  { name: 'KAFKA_BROKERS', value: 'kafka-cluster-kafka-bootstrap.kafka.svc:9092' },
                  { name: 'KAFKA_TOPIC', value: 'embeder' },
                  { name: 'KAFKA_CONSUMER_GROUP', value: 'embeder-group' },
                  { name: 'SEAWEEDFS_ADDRESS', value: 'redacted' },
                ],
                // livenessProbe: {
                // },
                // readinessProbe: {
                // },
                // startupProbe: {
                // }
              }
            ]
          }
        }
      }
    });

  }
}
