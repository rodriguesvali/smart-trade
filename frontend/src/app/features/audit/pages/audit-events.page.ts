import { JsonPipe } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { ButtonModule } from 'primeng/button';
import { DialogModule } from 'primeng/dialog';
import { TableModule } from 'primeng/table';

import { SmartTradeApiClient } from '../../../core/api/smart-trade-api.client';
import { EmptyStateComponent } from '../../../shared/ui/empty-state.component';
import { LoadingStateComponent } from '../../../shared/ui/loading-state.component';
import { AuditEventRead } from '../../strategies/models/audit-event.model';

@Component({
  selector: 'app-audit-events-page',
  standalone: true,
  imports: [ButtonModule, DialogModule, EmptyStateComponent, JsonPipe, LoadingStateComponent, TableModule],
  template: `
    <div class="page-heading">
      <div>
        <span class="eyebrow">Traceability</span>
        <h2>Audit Events</h2>
      </div>
      <p-button icon="pi pi-refresh" label="Refresh" size="small" (onClick)="load()" />
    </div>

    <section class="surface-section">
      @if (loading()) {
        <app-loading-state label="Loading audit events" />
      } @else if (!events().length) {
        <app-empty-state title="No events" description="No audit event was returned by the backend." />
      } @else {
        <p-table [value]="events()" styleClass="p-datatable-sm" [tableStyle]="{ 'min-width': '900px' }">
          <ng-template pTemplate="header">
            <tr>
              <th>Created</th>
              <th>Type</th>
              <th>Message</th>
              <th class="actions-col"></th>
            </tr>
          </ng-template>
          <ng-template pTemplate="body" let-event>
            <tr>
              <td>{{ event.created_at }}</td>
              <td class="mono">{{ event.event_type }}</td>
              <td>{{ event.message }}</td>
              <td class="actions-col">
                <p-button icon="pi pi-code" label="Payload" size="small" severity="secondary" (onClick)="openPayload(event)" />
              </td>
            </tr>
          </ng-template>
        </p-table>
      }
    </section>

    <p-dialog header="Audit Payload" [modal]="true" [visible]="payloadVisible()" (visibleChange)="payloadVisible.set($event)" [style]="{ width: '760px', maxWidth: '96vw' }">
      <pre class="json-block">{{ selectedPayload() | json }}</pre>
    </p-dialog>
  `,
})
export class AuditEventsPage {
  private readonly api = inject(SmartTradeApiClient);

  readonly events = signal<AuditEventRead[]>([]);
  readonly loading = signal(true);
  readonly payloadVisible = signal(false);
  readonly selectedPayload = signal<Record<string, unknown> | null>(null);

  constructor() {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.api.listAuditEvents().subscribe({
      next: (events) => {
        this.events.set(events);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  openPayload(event: AuditEventRead): void {
    this.selectedPayload.set(event.payload);
    this.payloadVisible.set(true);
  }
}
