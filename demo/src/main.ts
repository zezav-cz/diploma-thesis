import { Construct } from 'constructs';

import { App } from '../lib/App';
import { Kafka } from './charts/Kafka';
import { OperatorKafka } from './charts/OperatorKafka';
import { Telepresence } from './charts/Telepresence';
import { Keda } from './charts/Keda';
import { OperatorGrafana} from './charts/OperatorGrafana';
import { OperatorPrometheus } from './charts/OperatorPrometehus';
import { Grafana } from './charts/Grafana';
import { Prometheus } from './charts/Prometheus';
import { Downloader } from './charts/Dowloader';
import { ImageReactor } from './charts/ImageReactor';
import { Embedder } from './charts/Embeder';

export class Cluster extends Construct {
  constructor(scope: Construct, id: string) {
    super(scope, id);
    new OperatorKafka(this, 'strimzi', { namespace: 'strimzi' });
    new Telepresence(this, 'telepresence', { namespace: 'telepresence' });
    new Kafka(this, 'kafka', { namespace: 'kafka' });
    new Keda(this, 'keda', { namespace: 'keda' });
    new OperatorGrafana(this, 'operator-grafana', { namespace: 'op-grafana' });
    new OperatorPrometheus(this, 'operator-prometheus', { namespace: 'op-prometheus' });
    new Prometheus(this, 'prometheus', { namespace: 'prometheus' });
    new Grafana(this, 'grafana', { namespace: 'grafana', prometheusUrl: 'http://prometheus-operated.prometheus.svc:9090' });

    new Downloader(this, 'downloader', {
      namespace: 'image-downloader',
      imageName: 'downloader:latest',
    });
    new ImageReactor(this, 'image-reactor', {
      namespace: 'image-reactor',
      imageName: 'image-reactor:latest',
    });
    new Embedder(this, 'embeder', {
      namespace: 'image-embeder',
      imageName: 'embeder:latest',
    });
    // new ImageDownloader(this, 'image-downloader', {
    //   namespace: 'image-downloader',
    //   kafkaPort: 9092,
    //   kafkaSvc: 'kafka-cluster-kafka-bootstrap.kafka.svc',
    //   kafkaTopic: 'downloader',
    // });
  }
}

const app = new App();
new Cluster(app, '-');
app.synth();
