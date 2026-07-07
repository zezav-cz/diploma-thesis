import { Construct } from 'constructs';
import { ApiObject, Chart, ChartProps } from 'cdk8s';

import * as k8s from "../../imports/k8s-1-32/imports/k8s";
import * as flux from "../../imports/fluxcd-2-3"

interface Props extends ChartProps {
  helmSource: ApiObject;
  namespace: string;
}

export class Operators extends Chart {
  

}
