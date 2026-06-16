import { Component, input, output } from '@angular/core';
import { ButtonModule } from 'primeng/button';
import { TableModule } from 'primeng/table';

import { StatusTagComponent } from '../../../shared/ui/status-tag.component';
import { TrainedModelSummary } from '../models/strategy.model';

@Component({
  selector: 'app-trained-models-table',
  standalone: true,
  imports: [ButtonModule, TableModule, StatusTagComponent],
  template: `
    <p-table [value]="models()" styleClass="p-datatable-sm" [tableStyle]="{ 'min-width': '980px' }">
      <ng-template pTemplate="header">
        <tr>
          <th>Model</th>
          <th>Run</th>
          <th>Status</th>
          <th>Format</th>
          <th>Created</th>
          <th class="actions-col"></th>
        </tr>
      </ng-template>
      <ng-template pTemplate="body" let-model>
        <tr>
          <td class="mono">{{ model.id }}</td>
          <td class="mono">{{ model.run_id }}</td>
          <td><app-status-tag [status]="model.status" /></td>
          <td>{{ model.artifact_format }}</td>
          <td>{{ model.created_at }}</td>
          <td class="actions-col">
            <p-button icon="pi pi-eye" label="Open" size="small" (onClick)="open.emit(model)" />
          </td>
        </tr>
      </ng-template>
    </p-table>
  `,
})
export class TrainedModelsTableComponent {
  readonly models = input.required<TrainedModelSummary[]>();
  readonly open = output<TrainedModelSummary>();
}
