import { Construct } from 'constructs';
import { Chart, ChartProps } from 'cdk8s';

import * as k8s from "../../imports/k8s-1-32/imports/k8s";
import * as prometheus from '../../imports/prometheus-operator-0-58/imports/monitoring.coreos.com';

interface Props extends ChartProps {
  namespace: string;
}

export class Prometheus extends Chart {
  constructor(scope: Construct, id: string, props: Props) {
    props = { disableResourceNameHashes: true, ...props, };
    super(scope, id, props);

    new k8s.KubeNamespace(this, 'namespace', {
      metadata: {
        name: props.namespace
      }
    });

    const serviceAccount = new k8s.KubeServiceAccount(this, 'prom', {});

    const clusterRole = new k8s.KubeClusterRole(this, 'prom-role', {
      rules: [
        {
          apiGroups: [''],
          resources: ['nodes', 'nodes/proxy', 'services', 'endpoints', 'pods'],
          verbs: ['get', 'list', 'watch'],
        },
        {
          apiGroups: [''],
          resources: ['configmaps'],
          verbs: ['get'],
        },
        {
          apiGroups: ['discovery.k8s.io'],
          resources: ['endpointslices'],
          verbs: ['get', 'list', 'watch'],
        },
        {
          apiGroups: ['networking.k8s.io'],
          resources: ['ingresses'],
          verbs: ['get', 'list', 'watch'],
        },
        {
          nonResourceUrLs: ['/metrics'],
          verbs: ['get'],
        }
      ],
    });

    const clusterRoleBinding = new k8s.KubeClusterRoleBinding(this, 'prom-binding', {
      subjects: [
        {
          kind: 'ServiceAccount',
          name: serviceAccount.name,
          namespace: props.namespace,
        },
      ],
      roleRef: {
        kind: 'ClusterRole',
        name: clusterRole.name,
        apiGroup: 'rbac.authorization.k8s.io',
      },
    });

    new prometheus.Prometheus(this, "prometheus", {
      spec: {
        replicas: 1,
        //shards
        replicaExternalLabelName: "replicaExternalLabelName",
        scrapeInterval: "30s",
        scrapeTimeout: "30s",
        serviceMonitorNamespaceSelector: {},
        serviceMonitorSelector: {},
        podMonitorSelector: {},
        podMonitorNamespaceSelector: {},
        ruleNamespaceSelector: {},
        ruleSelector: {},
        disableCompaction: true,
        enableAdminApi: false,
        evaluationInterval: "30s",
        portName: "web",
        retention: "24h",
        serviceAccountName: serviceAccount.name,
      },
    });

  }
}
