import { Construct } from 'constructs';
import { Chart, ChartProps } from 'cdk8s';
import * as fs from 'fs';

import * as k8s from "../../imports/k8s-1-32/imports/k8s";
import * as grafana from '../../imports/grafana-5-19';
import path from 'path';

interface Props extends ChartProps {
  namespace: string;
  prometheusUrl: string;
}

export class Grafana extends Chart {
  constructor(scope: Construct, id: string, props: Props) {
    props = { disableResourceNameHashes: true, ...props, };
    super(scope, id, props);

    new k8s.KubeNamespace(this, 'namespace', {
      metadata: {
        name: props.namespace
      }
    });

    new grafana.GrafanaDatasource(this, "prometheus", {
      spec: {
        instanceSelector: {
          matchLabels: {
            mylabel: "my-label-value"
          }
        },
        datasource: {
          name: "Prometheus",
          type: "prometheus",
          access: "proxy",
          url: props.prometheusUrl,
          isDefault: true,
        }
      }
    });

    const downloaderDashboard = fs.readFileSync(
      path.join(__dirname, 'dashboard.json'),
      'utf8'
    );

    const dashboardCm = new k8s.KubeConfigMap(this, 'kafka-metrics', {
      metadata: {
        name: 'kafka-metrics',
        namespace: props.namespace
      },
      data: {
        'downloader-dashboard.json': downloaderDashboard
      }
    });

    new grafana.GrafanaDashboard(this, "downloader", {
      spec: {
        instanceSelector: {
          matchLabels: {
            mylabel: "my-label-value"
          }
        },
        configMapRef: {
          name: dashboardCm.name,
          key: 'downloader-dashboard.json'
        }
      }
    });

    new grafana.Grafana(this, "instance", {
      metadata: {
        labels: {
          mylabel: "my-label-value",
        },
        namespace: props.namespace,
      },
      spec: {
        config: {
          security: {
            admin_user: "admin",
            admin_password: 'admin',
          },
        },

      },
    });


  }
}
