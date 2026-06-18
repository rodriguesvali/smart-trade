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
          <app-metric-tile label="Net Result" [value]="opNum('net_result')" hint="Simplified simulation" />
          <app-metric-tile label="Profit Factor" [value]="opNum('profit_factor')" hint="Gross profit / gross loss" />
          <app-metric-tile label="Max Drawdown" [value]="percentOp('max_drawdown')" hint="Simplified equity curve" />
          <app-metric-tile label="Trades" [value]="opNum('simulated_trades', 0)" hint="Executed entries" />
          <app-metric-tile label="Win Rate" [value]="percentOp('win_rate')" hint="Simulated trades" />
          <app-metric-tile label="Loss Streak" [value]="opNum('largest_loss_streak', 0)" hint="Consecutive losses" />
        </div>
      </section>

      <section class="surface-section">
        <div class="section-title">
          <h3>Validation Setup</h3>
        </div>
        <dl class="definition-grid">
          <div>
            <dt>Configured Threshold</dt>
            <dd>{{ configuredThreshold() }}</dd>
          </div>
          <div>
            <dt>Recommended Threshold</dt>
            <dd>{{ recommendedThreshold() }}</dd>
          </div>
          <div>
            <dt>RSI Gate</dt>
            <dd>{{ opNum('entry_rsi_threshold', 2) }}</dd>
          </div>
          <div>
            <dt>Trailing Stop</dt>
            <dd>{{ yesNo(opValue('trailing_stop_enabled')) }}</dd>
          </div>
          <div>
            <dt>Trailing Activation</dt>
            <dd>{{ percentOp('trailing_activation_pct') }}</dd>
          </div>
          <div>
            <dt>Trailing Distance</dt>
            <dd>{{ percentOp('trailing_distance_pct') }}</dd>
          </div>
          <div>
            <dt>Fee</dt>
            <dd>{{ percentOp('fee_pct') }}</dd>
          </div>
          <div>
            <dt>Slippage</dt>
            <dd>{{ percentOp('slippage_pct') }}</dd>
          </div>
        </dl>
      </section>

      <section class="surface-section">
        <div class="section-title">
          <h3>Execution Funnel</h3>
        </div>
        <div class="metrics-grid">
          <app-metric-tile label="Signals" [value]="opNum('signals_generated', 0)" hint="Model probability passed threshold" />
          <app-metric-tile label="Entry Candidates" [value]="opNum('entry_candidates', 0)" hint="Signal also passed RSI gate" />
          <app-metric-tile label="Trades" [value]="opNum('simulated_trades', 0)" hint="Candidates accepted by position state" />
          <app-metric-tile label="Blocked" [value]="opNum('blocked_by_open_position', 0)" hint="Skipped while a trade was open" />
          <app-metric-tile label="Candidate Rate" [value]="ratioPercent('entry_candidates', 'signals_generated')" hint="Candidates / signals" />
          <app-metric-tile label="Trade Rate" [value]="ratioPercent('simulated_trades', 'entry_candidates')" hint="Trades / candidates" />
        </div>
      </section>

      <section class="surface-section">
        <div class="section-title">
          <h3>Exit Reasons</h3>
        </div>
        <div class="metrics-grid">
          <app-metric-tile label="Take Profit" [value]="exitReasonValue('take_profit')" hint="Exited at target" />
          <app-metric-tile label="Stop Loss" [value]="exitReasonValue('stop_loss')" hint="Exited at initial stop" />
          <app-metric-tile label="Trailing Stop" [value]="exitReasonValue('trailing_stop')" hint="Exited after stop followed price" />
          <app-metric-tile label="Time Exit" [value]="exitReasonValue('time_exit')" hint="Exited at horizon close" />
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

      @if (thresholdRows().length) {
        <section class="surface-section">
          <div class="section-title">
            <div>
              <h3>Threshold Analysis</h3>
              <span>Recommended: {{ recommendedThreshold() }}</span>
            </div>
          </div>
          <p-table [value]="thresholdRows()" styleClass="p-datatable-sm">
            <ng-template pTemplate="header">
              <tr>
                <th>Threshold</th>
                <th>Signals</th>
                <th>Trades</th>
                <th>Net</th>
                <th>PF</th>
                <th>DD</th>
                <th>Win</th>
              </tr>
            </ng-template>
            <ng-template pTemplate="body" let-row>
              <tr>
                <td>{{ rowPercent(row, 'probability_threshold') }}</td>
                <td>{{ rowNum(row, 'signals_generated', 0) }}</td>
                <td>{{ rowNum(row, 'simulated_trades', 0) }}</td>
                <td>{{ rowNum(row, 'net_result') }}</td>
                <td>{{ rowNum(row, 'profit_factor') }}</td>
                <td>{{ rowPercent(row, 'max_drawdown') }}</td>
                <td>{{ rowPercent(row, 'win_rate') }}</td>
              </tr>
            </ng-template>
          </p-table>
        </section>
      }

      @if (walkForwardFolds().length) {
        <section class="surface-section">
          <div class="section-title">
            <div>
              <h3>Walk-Forward</h3>
              <span>
                Completed {{ walkForwardValue('completed_folds', 0) }} / {{ walkForwardValue('requested_folds', 0) }}
              </span>
            </div>
          </div>

          <div class="metrics-grid">
            <app-metric-tile label="Profitable Folds" [value]="walkForwardAggregateNum('profitable_folds', 0)" hint="Folds with positive net result" />
            <app-metric-tile label="Total Trades" [value]="walkForwardAggregateNum('total_simulated_trades', 0)" hint="Trades across folds" />
            <app-metric-tile label="Mean Net" [value]="walkForwardAggregateNum('mean_net_result')" hint="Average fold net result" />
            <app-metric-tile label="Mean Precision" [value]="walkForwardAggregatePercent('mean_positive_precision')" hint="Average positive precision" />
          </div>

          <p-table [value]="walkForwardFolds()" styleClass="p-datatable-sm" [tableStyle]="{ 'min-width': '980px' }">
            <ng-template pTemplate="header">
              <tr>
                <th>Fold</th>
                <th>Train End</th>
                <th>Validation</th>
                <th>Precision</th>
                <th>Trades</th>
                <th>Net</th>
                <th>PF</th>
                <th>DD</th>
                <th>Win</th>
              </tr>
            </ng-template>
            <ng-template pTemplate="body" let-fold>
              <tr>
                <td>{{ rowNum(fold, 'fold', 0) }}</td>
                <td>{{ rowNum(fold, 'train_end_index', 0) }}</td>
                <td>{{ indexRange(fold, 'validation_start_index', 'validation_end_index') }}</td>
                <td>{{ nestedPercent(fold, 'ml_metrics', 'positive_precision') }}</td>
                <td>{{ nestedNum(fold, 'operational_metrics', 'simulated_trades', 0) }}</td>
                <td>{{ nestedNum(fold, 'operational_metrics', 'net_result') }}</td>
                <td>{{ nestedNum(fold, 'operational_metrics', 'profit_factor') }}</td>
                <td>{{ nestedPercent(fold, 'operational_metrics', 'max_drawdown') }}</td>
                <td>{{ nestedPercent(fold, 'operational_metrics', 'win_rate') }}</td>
              </tr>
            </ng-template>
          </p-table>
        </section>
      }
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

  opValue(key: string): unknown {
    return this.operational()[key];
  }

  rowCount(): string {
    return numberValue(this.ml()['row_count'], 0);
  }

  datasetValue(key: string): string {
    const value = this.model()?.dataset_metadata?.[key];
    return value === undefined || value === null ? '-' : String(value);
  }

  thresholdRows(): Record<string, unknown>[] {
    const thresholds = this.thresholdAnalysis()['thresholds'];
    return Array.isArray(thresholds) ? (thresholds as Record<string, unknown>[]) : [];
  }

  recommendedThreshold(): string {
    const value = this.thresholdAnalysis()['recommended_probability_threshold'];
    return value === undefined || value === null ? '-' : percentValue(value);
  }

  configuredThreshold(): string {
    const value = this.thresholdAnalysis()['configured_probability_threshold'] ?? this.operational()['probability_threshold'];
    return value === undefined || value === null ? '-' : percentValue(value);
  }

  rowNum(row: Record<string, unknown>, key: string, digits = 4): string {
    return numberValue(row[key], digits);
  }

  rowPercent(row: Record<string, unknown>, key: string): string {
    return percentValue(row[key]);
  }

  ratioPercent(numeratorKey: string, denominatorKey: string): string {
    const numerator = this.toNumber(this.operational()[numeratorKey]);
    const denominator = this.toNumber(this.operational()[denominatorKey]);
    if (numerator === null || denominator === null || denominator === 0) {
      return '-';
    }
    return percentValue(numerator / denominator);
  }

  exitReasonValue(key: string): string {
    return numberValue(this.exitReasons()[key], 0);
  }

  yesNo(value: unknown): string {
    if (typeof value === 'boolean') {
      return value ? 'Yes' : 'No';
    }
    return value === undefined || value === null ? '-' : String(value);
  }

  walkForwardValue(key: string, digits = 4): string {
    return numberValue(this.walkForward()[key], digits);
  }

  walkForwardAggregateNum(key: string, digits = 4): string {
    return numberValue(this.walkForwardAggregate()[key], digits);
  }

  walkForwardAggregatePercent(key: string): string {
    return percentValue(this.walkForwardAggregate()[key]);
  }

  walkForwardFolds(): Record<string, unknown>[] {
    const folds = this.walkForward()['folds'];
    return Array.isArray(folds) ? (folds as Record<string, unknown>[]) : [];
  }

  nestedNum(row: Record<string, unknown>, section: string, key: string, digits = 4): string {
    return numberValue(this.nestedRecord(row, section)[key], digits);
  }

  nestedPercent(row: Record<string, unknown>, section: string, key: string): string {
    return percentValue(this.nestedRecord(row, section)[key]);
  }

  indexRange(row: Record<string, unknown>, startKey: string, endKey: string): string {
    const start = row[startKey];
    const end = row[endKey];
    if (start === undefined || start === null || end === undefined || end === null) {
      return '-';
    }
    return `${numberValue(start, 0)} - ${numberValue(end, 0)}`;
  }

  private ml(): Record<string, unknown> {
    return this.model()?.validation_summary?.ml_metrics ?? this.model()?.training_metrics ?? {};
  }

  private operational(): Record<string, unknown> {
    return this.model()?.validation_summary?.operational_metrics ?? {};
  }

  private thresholdAnalysis(): Record<string, unknown> {
    const metadata = this.model()?.validation_summary?.window_metadata ?? {};
    const analysis = metadata['threshold_analysis'];
    return analysis && typeof analysis === 'object' ? (analysis as Record<string, unknown>) : {};
  }

  private exitReasons(): Record<string, unknown> {
    const reasons = this.operational()['exit_reasons'];
    return reasons && typeof reasons === 'object' ? (reasons as Record<string, unknown>) : {};
  }

  private walkForward(): Record<string, unknown> {
    const metadata = this.model()?.validation_summary?.window_metadata ?? {};
    const walkForward = metadata['walk_forward'];
    return walkForward && typeof walkForward === 'object' ? (walkForward as Record<string, unknown>) : {};
  }

  private walkForwardAggregate(): Record<string, unknown> {
    const aggregate = this.walkForward()['aggregate'];
    return aggregate && typeof aggregate === 'object' ? (aggregate as Record<string, unknown>) : {};
  }

  private nestedRecord(row: Record<string, unknown>, section: string): Record<string, unknown> {
    const value = row[section];
    return value && typeof value === 'object' ? (value as Record<string, unknown>) : {};
  }

  private toNumber(value: unknown): number | null {
    const parsed = typeof value === 'number' ? value : Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
}
