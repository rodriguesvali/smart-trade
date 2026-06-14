import { DatePipe } from '@angular/common';
import { Component, Input } from '@angular/core';
import { CardModule } from 'primeng/card';
import { TableModule } from 'primeng/table';
import { TagModule } from 'primeng/tag';

import { ModelSummary, StrategySummary } from './api/operator-api';

@Component({
  selector: 'app-models-view',
  imports: [CardModule, DatePipe, TableModule, TagModule],
  template: `
    <section class="console-grid two-column-grid">
      <p-card header="Model Registry">
        <p-table [value]="models" [tableStyle]="{ 'min-width': '46rem' }">
          <ng-template pTemplate="header">
            <tr>
              <th>Model</th>
              <th>Role</th>
              <th>Strategy</th>
              <th>Status</th>
              <th>Precision</th>
              <th>Trades</th>
              <th>Net PnL</th>
              <th>Holdout</th>
              <th>Created</th>
            </tr>
          </ng-template>
          <ng-template pTemplate="body" let-model>
            <tr>
              <td>{{ model.model_id }}</td>
              <td>{{ model.model_role }}</td>
              <td>{{ model.strategy_id }} {{ model.strategy_version }}</td>
              <td>
                <p-tag
                  [severity]="model.status === 'APPROVED' || model.status === 'ACTIVE' ? 'success' : model.status === 'REJECTED' ? 'danger' : 'info'"
                  [value]="model.status"
                />
              </td>
              <td>{{ metric(model, 'precision_class_1') }}</td>
              <td>{{ metric(model, 'trade_count') }}</td>
              <td>{{ metric(model, 'net_pnl') }}</td>
              <td>{{ model.holdout_start ? (model.holdout_start | date:'short') : 'Unavailable' }}</td>
              <td>{{ model.created_at | date:'short' }}</td>
            </tr>
          </ng-template>
          <ng-template pTemplate="emptymessage">
            <tr>
              <td colspan="9">No models registered yet.</td>
            </tr>
          </ng-template>
        </p-table>
      </p-card>

      <p-card header="Strategy Registry">
        <p-table [value]="strategies" [tableStyle]="{ 'min-width': '40rem' }">
          <ng-template pTemplate="header">
            <tr>
              <th>Name</th>
              <th>Version</th>
              <th>Status</th>
              <th>Roles</th>
              <th>Features</th>
              <th>Compatibility</th>
            </tr>
          </ng-template>
          <ng-template pTemplate="body" let-strategy>
            <tr>
              <td>{{ strategy.name }}</td>
              <td>{{ strategy.version }}</td>
              <td><p-tag [severity]="strategy.id === selectedStrategyId ? 'success' : 'info'" [value]="strategy.status" /></td>
              <td>{{ roleLabels(strategy) }}</td>
              <td>{{ strategy.required_features.length }}</td>
              <td>
                <p-tag
                  [severity]="strategy.compatibility.compatible ? 'success' : 'warn'"
                  [value]="strategy.compatibility.compatible ? 'READY' : 'BLOCKED'"
                />
              </td>
            </tr>
          </ng-template>
          <ng-template pTemplate="emptymessage">
            <tr>
              <td colspan="6">No strategies registered yet.</td>
            </tr>
          </ng-template>
        </p-table>
      </p-card>
    </section>
  `,
})
export class ModelsViewComponent {
  @Input() models: ModelSummary[] = [];
  @Input() strategies: StrategySummary[] = [];
  @Input() selectedStrategyId: number | null = null;

  roleLabels(strategy: StrategySummary): string {
    return strategy.model_roles
      .map((role) => String(role['role'] ?? 'role'))
      .join(', ');
  }

  metric(model: ModelSummary, key: string): string {
    const value = model.metrics[key];
    if (value === null || value === undefined || value === '') {
      return 'Unavailable';
    }
    if (typeof value === 'number') {
      return Number.isInteger(value) ? String(value) : value.toFixed(4);
    }
    return String(value);
  }
}
