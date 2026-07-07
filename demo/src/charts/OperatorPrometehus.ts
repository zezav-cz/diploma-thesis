import { Construct } from 'constructs';
import { ApiObject, Chart, ChartProps } from 'cdk8s';

import * as k8s from "../../imports/k8s-1-32/imports/k8s";
import * as flux from "../../imports/fluxcd-2-3"

interface Props extends ChartProps {
  namespace: string;
}

export class OperatorPrometheus extends Chart {
  constructor(scope: Construct, id: string, props: Props) {
    props = { disableResourceNameHashes: true, ...props, };
    super(scope, id, props);

    new k8s.KubeNamespace(this, 'namespace', {
      metadata: {
        name: props.namespace,
      }
    });

    const repo = new flux.source.HelmRepository(this, "repo", {
      spec: {
        type: flux.source.HelmRepositorySpecType.DEFAULT,
        interval: "30m",
        url: "https://prometheus-community.github.io/helm-charts",
      },
    });

    new flux.helm.HelmRelease(this, '-', {
      spec: {
        chart: {
          spec: {
            chart: "kube-prometheus-stack",
            version: '76.4.x',
            sourceRef: {
              kind: flux.helm.HelmReleaseSpecChartSpecSourceRefKind
                .HELM_REPOSITORY,
              name: repo.name,
              namespace: repo.metadata.namespace,
            },
          },
        },
        interval: "10m",
        values: {
          crds: { enabled: true },
          alertmanager: { enabled: false },
          defaultRules: { enabled: false },
          grafana: { enabled: false },
          kubeControllerManager: { enabled: false },
          kubeProxy: { enabled: false },
          kubeScheduler: { enabled: false },
          kubeStateMetrics: { enabled: false },
          prometheus: { enabled: false },
          prometheusOperator: {
            enabled: true,
          },
          nameOverride: "prometheus",
        },
      },
    });

  }
}
