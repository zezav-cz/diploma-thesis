import { Construct } from 'constructs';
import { Chart, ChartProps } from 'cdk8s';

import * as k8s from "../../imports/k8s-1-32/imports/k8s";
import * as prometheus from "../../imports/prometheus-operator-0-58/imports/monitoring.coreos.com";
import * as keda from "../../imports/keda-2-18";

interface Props extends ChartProps {
  namespace: string;
  imageName: string;
}

export class ImageReactor extends Chart {
  constructor(scope: Construct, id: string, props: Props) {
    props = { disableResourceNameHashes: true, ...props, };
    super(scope, id, props);

    new k8s.KubeNamespace(this, 'namespace', {
      metadata: {
        name: props.namespace
      }
    });

    new k8s.KubeService(this, 'service', {
      metadata: {
        namespace: props.namespace,
        name: 'image-reactor',
        labels: {
          app: 'image-reactor',
        }
      },
      spec: {
        selector: {
          app: 'image-reactor',
        },
        ports: [
          {
            port: 9000,
            targetPort: k8s.IntOrString.fromNumber(9000),
            protocol: 'TCP',
            name: 'http',
          }
        ],
        type: 'ClusterIP',
      }
    });

    const depl = new k8s.KubeDeployment(this, 'depl', {
      metadata: {
        namespace: props.namespace,
        name: 'image-reactor',
      },
      spec: {
        selector: {
          matchLabels: {
            app: 'image-reactor',
          }
        },
        replicas: 1,
        template: {
          metadata: {
            labels: {
              app: 'image-reactor',
            }
          },
          spec: {
            containers: [
              {
                name: 'image-reactor',
                image: props.imageName,
                imagePullPolicy: 'Never',
                ports: [{ containerPort: 9000, protocol: 'TCP', name: 'http' }],
                env: [
                  { name: "IR_DATABASE_URL", value: "redacted" },
                  { name: "IR_DB_POOL_MIN_SIZE", value: "5", },
                  { name: "IR_DB_POOL_MAX_SIZE", value: "15", },
                  { name: "IR_LOG_LEVEL", value: "DEBUG", },
                  { name: "IR_LOG_FORMAT", value: "TXT", },
                  { name: "IR_HOST", value: "0.0.0.0", },
                  { name: "IR_PORT", value: "9000", },
                  { name: "IR_VERBOSE_API_EXCEPTIONS", value: "true", },
                  { name: "IR_DB_POOL_MAX_QUERIES", value: "50000", },
                  { name: "IR_DB_POOL_MAX_INACTIVE_CONNECTION_LIFETIME", value: "300.0", },
                ],
                livenessProbe: {
                  httpGet: {
                    path: '/health/live',
                    port: k8s.IntOrString.fromNumber(9000)
                  },
                  initialDelaySeconds: 10,
                  periodSeconds: 10
                },
                readinessProbe: {
                  httpGet: {
                    path: '/health/ready',
                    port: k8s.IntOrString.fromNumber(9000)
                  },
                  initialDelaySeconds: 5,
                  periodSeconds: 5
                },
              }
            ]
          }
        }
      }
    });


    new prometheus.ServiceMonitor(this, 'sm', {
      spec: {
        selector: {
          matchLabels: {
            app: 'image-reactor',
          }
        },
        endpoints: [
          {
            port: 'http',
            interval: '15s',
            scrapeTimeout: '10s',
          }
        ]
      }
    });



  }
}
