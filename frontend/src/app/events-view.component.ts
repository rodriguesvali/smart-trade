import { DatePipe } from '@angular/common';
import { Component, Input } from '@angular/core';
import { CardModule } from 'primeng/card';
import { TableModule } from 'primeng/table';
import { TagModule } from 'primeng/tag';

import { OperationalEvent } from './api/operator-api';

@Component({
  selector: 'app-events-view',
  imports: [CardModule, DatePipe, TableModule, TagModule],
  template: `
    <p-card header="Operational Events">
      <p-table [value]="events" [tableStyle]="{ 'min-width': '54rem' }">
        <ng-template pTemplate="header">
          <tr>
            <th>Time</th>
            <th>Severity</th>
            <th>Source</th>
            <th>Event</th>
            <th>Message</th>
          </tr>
        </ng-template>
        <ng-template pTemplate="body" let-event>
          <tr>
            <td>{{ event.occurred_at | date:'medium' }}</td>
            <td><p-tag [severity]="event.severity === 'ERROR' ? 'danger' : event.severity === 'WARNING' ? 'warn' : 'info'" [value]="event.severity" /></td>
            <td>{{ event.source }}</td>
            <td>{{ event.event_type }}</td>
            <td>{{ event.message }}</td>
          </tr>
        </ng-template>
        <ng-template pTemplate="emptymessage">
          <tr>
            <td colspan="5">No operational events recorded yet.</td>
          </tr>
        </ng-template>
      </p-table>
    </p-card>
  `,
})
export class EventsViewComponent {
  @Input() events: OperationalEvent[] = [];
}
