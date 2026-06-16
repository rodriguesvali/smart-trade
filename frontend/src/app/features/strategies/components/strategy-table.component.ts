import { Component, input, output } from '@angular/core';
import { ButtonModule } from 'primeng/button';
import { TableModule } from 'primeng/table';

import { StatusTagComponent } from '../../../shared/ui/status-tag.component';
import { StrategySummary } from '../models/strategy.model';

@Component({
  selector: 'app-strategy-table',
  standalone: true,
  imports: [ButtonModule, TableModule, StatusTagComponent],
  template: `
    <p-table [value]="strategies()" styleClass="p-datatable-sm" [tableStyle]="{ 'min-width': '920px' }">
      <ng-template pTemplate="header">
        <tr>
          <th>Name</th>
          <th>ID</th>
          <th>Version</th>
          <th>Model</th>
          <th>Status</th>
          <th class="actions-col"></th>
        </tr>
      </ng-template>
      <ng-template pTemplate="body" let-strategy>
        <tr>
          <td>
            <strong>{{ strategy.name }}</strong>
            <small>{{ strategy.description }}</small>
          </td>
          <td class="mono">{{ strategy.id }}</td>
          <td>{{ strategy.version }}</td>
          <td>{{ strategy.model_family }}</td>
          <td><app-status-tag [status]="strategy.status" /></td>
          <td class="actions-col">
            <p-button icon="pi pi-folder-open" label="Open" size="small" (onClick)="open.emit(strategy)" />
          </td>
        </tr>
      </ng-template>
    </p-table>
  `,
})
export class StrategyTableComponent {
  readonly strategies = input.required<StrategySummary[]>();
  readonly open = output<StrategySummary>();
}
