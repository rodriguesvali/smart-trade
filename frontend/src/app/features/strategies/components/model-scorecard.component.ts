import { Component, input } from '@angular/core';
import { TableModule } from 'primeng/table';

import { MetricTileComponent } from '../../../shared/ui/metric-tile.component';
import { StatusTagComponent } from '../../../shared/ui/status-tag.component';
import { numberValue, percentValue } from '../../../shared/utils/format-number';
import { TrainedModelDetail } from '../models/strategy.model';

@Component({
  selector: 'app-model-scorecard',
  standalone: true,
  imports: [MetricTileComponent, StatusTagComponent, TableModule],
  template: `
    @if (model()) {
      <section class="surface-section">
        <div class="section-title">
          <div>
            <h3>Model Scorecard</h3>
            <span class="mono">{{ model()!.id }}</span>
          </div>
          <app-status-tag [status]="model()!.status" />
        </div>

        <div class="metrics-grid">
          <app-metric-tile label="Precision" [value]="percent('positive_precision')" hint="Positive class" />
          <app-metric-tile label="F1" [value]="num('f1_score')" hint="Holdout metric" />
          <app-metric-tile label="Log Loss" [value]="num('log_loss')" hint="Probability quality" />
          <app-metric-tile label="Rows" [value]="rowCount()" hint="Holdout rows" />
        </div>

        <div class="metrics-grid">
          <app-metric-tile label="Signals" [value]="opNum('signals_generated', 0)" hint="Thresholded predictions" />
          <app-metric-tile label="Net Result" [value]="opNum('net_result')" hint="Simplified simulation" />
          <app-metric-tile label="Profit Factor" [value]="opNum('profit_factor')" hint="Gross profit / gross loss" />
          <app-metric-tile label="Max Drawdown" [value]="percentOp('max_drawdown')" hint="Simplified equity curve" />
          <app-metric-tile label="Win Rate" [value]="percentOp('win_rate')" hint="Simulated trades" />
          <app-metric-tile label="Loss Streak" [value]="opNum('largest_loss_streak', 0)" hint="Consecutive losses" />
        </div>
      </section>

      <section class="surface-section">
        <div class="section-title">
          <h3>Dataset</h3>
        </div>
        <dl class="definition-grid">
          <div>
            <dt>Mode</dt>
            <dd>{{ datasetValue('mode') }}</dd>
          </div>
          <div>
            <dt>Exchange</dt>
            <dd>{{ datasetValue('exchange_id') }}</dd>
          </div>
          <div>
            <dt>Symbol</dt>
            <dd>{{ datasetValue('symbol') }}</dd>
          </div>
          <div>
            <dt>Timeframe</dt>
            <dd>{{ datasetValue('timeframe') }}</dd>
          </div>
          <div>
            <dt>Sentiment</dt>
            <dd>{{ datasetValue('sentiment_status') }}</dd>
          </div>
          <div>
            <dt>Usable Rows</dt>
            <dd>{{ datasetValue('usable_rows') }}</dd>
          </div>
        </dl>
      </section>
    }
  `,
})
export class ModelScorecardComponent {
  readonly model = input<TrainedModelDetail | null>(null);

  num(key: string): string {
    return numberValue(this.ml()[key]);
  }

  percent(key: string): string {
    return percentValue(this.ml()[key]);
  }

  opNum(key: string, digits = 4): string {
    return numberValue(this.operational()[key], digits);
  }

  percentOp(key: string): string {
    return percentValue(this.operational()[key]);
  }

  rowCount(): string {
    return numberValue(this.ml()['row_count'], 0);
  }

  datasetValue(key: string): string {
    const value = this.model()?.dataset_metadata?.[key];
    return value === undefined || value === null ? '-' : String(value);
  }

  private ml(): Record<string, unknown> {
    return this.model()?.validation_summary?.ml_metrics ?? this.model()?.training_metrics ?? {};
  }

  private operational(): Record<string, unknown> {
    return this.model()?.validation_summary?.operational_metrics ?? {};
  }
}
