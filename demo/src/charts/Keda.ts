import { Construct } from 'constructs';
import { ApiObject, Chart, ChartProps } from 'cdk8s';

import * as k8s from "../../imports/k8s-1-32/imports/k8s";
import * as flux from "../../imports/fluxcd-2-3"

interface Props extends ChartProps {
  namespace: string;
}

export class Keda extends Chart {
  constructor(scope: Construct, id: string, props: Props) {
    props = { disableResourceNameHashes: true, ...props, };
    super(scope, id, props);

    new k8s.KubeNamespace(this, 'namespace', {
      metadata: {
        name: props.namespace,
      }
    });
    const repo = new flux.source.HelmRepository(this, 'repo', {
      spec: {
        interval: '24h',
        url: 'https://kedacore.github.io/charts',
        type: flux.source.HelmRepositorySpecType.DEFAULT,
        provider: flux.source.HelmRepositorySpecProvider.GENERIC,
      }
    });

    new flux.helm.HelmRelease(this, '-', {
      spec: {
        interval: '5m',
        timeout: '2m',
        chart: {
          spec: {
            chart: 'keda',
            version: '2.18.x',
            interval: '5m',
            reconcileStrategy: flux.helm.HelmReleaseSpecChartSpecReconcileStrategy.CHART_VERSION,
            sourceRef: {
              kind: flux.helm.HelmReleaseSpecChartSpecSourceRefKind.HELM_REPOSITORY,
              name: repo.name,
              namespace: repo.metadata.namespace,
            }
          }
        },
        values: {
        },
      }
    });

  }
}
