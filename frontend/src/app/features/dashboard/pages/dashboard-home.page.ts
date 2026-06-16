import { CommonModule } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { ButtonModule } from 'primeng/button';
import { MessageModule } from 'primeng/message';

import { SmartTradeApiClient } from '../../../core/api/smart-trade-api.client';
import { MetricTileComponent } from '../../../shared/ui/metric-tile.component';
import { AuditEventRead } from '../../strategies/models/audit-event.model';
import { StrategySummary } from '../../strategies/models/strategy.model';

@Component({
  selector: 'app-dashboard-home-page',
  standalone: true,
  imports: [CommonModule, ButtonModule, MessageModule, MetricTileComponent],
  template: `
    <div class="page-heading">
      <div>
        <span class="eyebrow">Overview</span>
        <h2>Dashboard</h2>
      </div>
      <p-button icon="pi pi-refresh" label="Refresh" size="small" (onClick)="load()" />
    </div>

    <div class="metrics-grid">
      <app-metric-tile label="API" [value]="apiStatus()" hint="Backend health" />
      <app-metric-tile label="Strategies" [value]="strategies().length" hint="Catalog entries" />
      <app-metric-tile label="Last Event" [value]="latestEventType()" hint="Audit stream" />
    </div>

    <section class="surface-section">
      <div class="section-title">
        <h3>Operational Notes</h3>
      </div>
      <p-message severity="info">
        This console is focused on training lifecycle operations: strategies, training runs, validation evidence, approval decisions, and audit events.
      </p-message>
    </section>
  `,
})
export class DashboardHomePage {
  private readonly api = inject(SmartTradeApiClient);

  readonly apiStatus = signal('checking');
  readonly strategies = signal<StrategySummary[]>([]);
  readonly auditEvents = signal<AuditEventRead[]>([]);

  constructor() {
    this.load();
  }

  load(): void {
    this.api.health().subscribe({
      next: (health) => this.apiStatus.set(health.status),
      error: () => this.apiStatus.set('offline'),
    });
    this.api.listStrategies().subscribe({
      next: (items) => this.strategies.set(items),
      error: () => this.strategies.set([]),
    });
    this.api.listAuditEvents().subscribe({
      next: (items) => this.auditEvents.set(items),
      error: () => this.auditEvents.set([]),
    });
  }

  latestEventType(): string {
    return this.auditEvents()[0]?.event_type ?? '-';
  }
}
