import { Component, computed, inject, OnInit, signal } from '@angular/core';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { TagModule } from 'primeng/tag';

import { HealthState, OperatorApi, OperatorReadModels } from './api/operator-api';
import { TradeChartComponent } from './charts/trade-chart.component';
import { EventsViewComponent } from './events-view.component';
import { ModelsViewComponent } from './models-view.component';

@Component({
  selector: 'app-root',
  imports: [ButtonModule, CardModule, EventsViewComponent, ModelsViewComponent, TagModule, TradeChartComponent],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class App implements OnInit {
  private readonly operatorApi = inject(OperatorApi);

  protected readonly title = signal('Smart Trade');
  protected readonly backendStatus = signal<HealthState>('unknown');
  protected readonly readModels = signal<OperatorReadModels | null>(null);
  protected readonly readModelError = signal(false);
  protected readonly loadingReadModels = signal(false);
  protected activeTab = 'operation';
  protected readonly navigation = [
    { id: 'operation', label: 'Operation', icon: 'pi pi-chart-line' },
    { id: 'models', label: 'Models', icon: 'pi pi-verified' },
    { id: 'training', label: 'Training', icon: 'pi pi-database' },
    { id: 'logs', label: 'Events', icon: 'pi pi-list' },
  ];
  protected readonly backendLabel = computed(() => {
    const status = this.backendStatus();
    if (status === 'ok') {
      return 'Backend online';
    }
    if (status === 'error') {
      return 'Backend offline';
    }
    return 'Backend unchecked';
  });
  protected readonly backendSeverity = computed(() => {
    const status = this.backendStatus();
    if (status === 'ok') {
      return 'success';
    }
    if (status === 'error') {
      return 'danger';
    }
    return 'warn';
  });
  protected readonly operationSeverity = computed(() => {
    const state = this.readModels()?.operation.state;
    if (state === 'IDLE') {
      return 'success';
    }
    if (state === 'NOT_READY') {
      return 'warn';
    }
    if (state === 'BLOCKED') {
      return 'danger';
    }
    return 'info';
  });
  protected readonly selectedStrategy = computed(() => {
    const readModels = this.readModels();
    if (!readModels?.strategies.selected_strategy_id) {
      return null;
    }
    return readModels.strategies.items.find(
      (strategy) => strategy.id === readModels.strategies.selected_strategy_id
    ) ?? null;
  });
  protected readonly activeModelCount = computed(() => {
    return this.readModels()?.models.items.filter((model) => {
      return model.status === 'APPROVED' || model.status === 'ACTIVE';
    }).length ?? 0;
  });
  protected readonly marketLabel = computed(() => {
    const configuration = this.readModels()?.configuration;
    return `${configuration?.exchange || 'Bybit'} / ${configuration?.symbol || 'BTC/USDT'} / ${configuration?.timeframe || 'M1'}`;
  });
  protected readonly readinessLabel = computed(() => {
    const blockers = this.readModels()?.operation.blockers.length ?? 0;
    if (blockers > 0) {
      return `${blockers} blocker${blockers > 1 ? 's' : ''}`;
    }
    return 'Gate clear';
  });

  ngOnInit(): void {
    this.refresh();
  }

  protected checkBackend(): void {
    this.backendStatus.set('unknown');
    this.operatorApi.health().subscribe({
      next: (response) => {
        this.backendStatus.set(response.status === 'ok' ? 'ok' : 'error');
      },
      error: () => {
        this.backendStatus.set('error');
      },
    });
  }

  protected refresh(): void {
    this.checkBackend();
    this.refreshReadModels();
  }

  protected selectTab(tabId: string): void {
    this.activeTab = tabId;
  }

  private refreshReadModels(): void {
    this.loadingReadModels.set(true);
    this.readModelError.set(false);

    this.operatorApi.readModels().subscribe({
      next: (readModels) => {
        this.readModels.set(readModels);
        this.loadingReadModels.set(false);
      },
      error: () => {
        this.readModelError.set(true);
        this.loadingReadModels.set(false);
      },
    });
  }
}
