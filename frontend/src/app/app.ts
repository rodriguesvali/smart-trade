import { HttpClient } from '@angular/common/http';
import { Component, computed, inject, OnInit, signal } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { TagModule } from 'primeng/tag';
import { forkJoin } from 'rxjs';

type HealthState = 'unknown' | 'ok' | 'error';

interface ConfigurationSummary {
  exchange: string;
  symbol: string;
  timeframe: string;
  initial_capital_usd: string;
  mode: string;
}

interface StrategiesResponse {
  selected_strategy_id: number | null;
  items: unknown[];
}

interface ModelsResponse {
  items: unknown[];
}

interface OperationStatus {
  state: string;
  mode: string;
  approved_or_active_models: number;
  open_positions: number;
  pending_commands: number;
  blockers: string[];
}

interface EventsResponse {
  items: unknown[];
}

interface OperatorReadModels {
  configuration: ConfigurationSummary;
  strategies: StrategiesResponse;
  models: ModelsResponse;
  operation: OperationStatus;
  events: EventsResponse;
}

@Component({
  selector: 'app-root',
  imports: [ButtonModule, CardModule, RouterOutlet, TagModule],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class App implements OnInit {
  private readonly http = inject(HttpClient);

  protected readonly title = signal('Smart Trade');
  protected readonly backendStatus = signal<HealthState>('unknown');
  protected readonly readModels = signal<OperatorReadModels | null>(null);
  protected readonly readModelError = signal(false);
  protected readonly loadingReadModels = signal(false);
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

  ngOnInit(): void {
    this.refresh();
  }

  protected checkBackend(): void {
    this.backendStatus.set('unknown');
    this.http.get<{ status: string }>('/api/health').subscribe({
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

  private refreshReadModels(): void {
    this.loadingReadModels.set(true);
    this.readModelError.set(false);

    forkJoin({
      configuration: this.http.get<ConfigurationSummary>('/api/configuration/summary'),
      strategies: this.http.get<StrategiesResponse>('/api/strategies'),
      models: this.http.get<ModelsResponse>('/api/models'),
      operation: this.http.get<OperationStatus>('/api/operation/status'),
      events: this.http.get<EventsResponse>('/api/events?limit=10'),
    }).subscribe({
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
