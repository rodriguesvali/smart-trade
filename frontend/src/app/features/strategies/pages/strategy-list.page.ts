import { Component, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { ButtonModule } from 'primeng/button';

import { EmptyStateComponent } from '../../../shared/ui/empty-state.component';
import { LoadingStateComponent } from '../../../shared/ui/loading-state.component';
import { SmartTradeApiClient } from '../../../core/api/smart-trade-api.client';
import { StrategyTableComponent } from '../components/strategy-table.component';
import { StrategySummary } from '../models/strategy.model';

@Component({
  selector: 'app-strategy-list-page',
  standalone: true,
  imports: [ButtonModule, EmptyStateComponent, LoadingStateComponent, StrategyTableComponent],
  template: `
    <div class="page-heading">
      <div>
        <span class="eyebrow">Training</span>
        <h2>XGBoost Strategies</h2>
      </div>
      <p-button icon="pi pi-refresh" label="Refresh" size="small" (onClick)="load()" />
    </div>

    <section class="surface-section">
      @if (loading()) {
        <app-loading-state label="Loading strategies" />
      } @else if (!strategies().length) {
        <app-empty-state title="No strategies" description="No training strategies were returned by the backend." />
      } @else {
        <app-strategy-table [strategies]="strategies()" (open)="openStrategy($event)" />
      }
    </section>
  `,
})
export class StrategyListPage {
  private readonly api = inject(SmartTradeApiClient);
  private readonly router = inject(Router);

  readonly strategies = signal<StrategySummary[]>([]);
  readonly loading = signal(true);

  constructor() {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.api.listStrategies().subscribe({
      next: (strategies) => {
        this.strategies.set(strategies);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  openStrategy(strategy: StrategySummary): void {
    void this.router.navigate(['/strategies', strategy.id]);
  }
}
