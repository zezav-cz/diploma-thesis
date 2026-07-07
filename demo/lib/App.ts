import path from 'path';

import { AppProps, App as CDKApp, Names, Yaml, YamlOutputType } from 'cdk8s';

export class App extends CDKApp {
  public constructor(props: AppProps = {}) {
    super({
      outputFileExtension: '.yaml',
      yamlOutputType: YamlOutputType.FOLDER_PER_CHART_FILE_PER_RESOURCE,
      recordConstructMetadata: true,
      ...props,
    });
  }

  public synth(): void {
    super.synth();

    const fluxcdCharts = this.charts.filter((chart) =>
      chart.node.metadata.some((m) => m.type === 'fluxcd.io/root' && m.data === 'true'),
    );

    if (fluxcdCharts) {
      Yaml.save(path.join(this.outdir, 'kustomization.yaml'), [
        {
          apiVersion: 'kustomize.config.k8s.io/v1beta1',
          kind: 'Kustomization',
          resources: fluxcdCharts.map((chart) => Names.toDnsLabel(chart)),
        },
      ]);
    }
  }
}
