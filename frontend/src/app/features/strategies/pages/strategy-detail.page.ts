import { Component, DestroyRef, ViewChild, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router } from '@angular/router';
import { interval, Subscription, switchMap, takeWhile } from 'rxjs';
import { MessageService } from 'primeng/api';
import { ButtonModule } from 'primeng/button';

import { SmartTradeApiClient } from '../../../core/api/smart-trade-api.client';
import { EmptyStateComponent } from '../../../shared/ui/empty-state.component';
import { LoadingStateComponent } from '../../../shared/ui/loading-state.component';
import { MetricTileComponent } from '../../../shared/ui/metric-tile.component';
import { StatusTagComponent } from '../../../shared/ui/status-tag.component';
import { TrainedModelsTableComponent } from '../components/trained-models-table.component';
import { TrainingRequestDialogComponent } from '../components/training-request-dialog.component';
import { TrainingRunProgressComponent } from '../components/training-run-progress.component';
import {
  StrategyDetail,
  TrainedModelSummary,
  TrainingRequest,
  TrainingRunRead,
} from '../models/strategy.model';

@Component({
  selector: 'app-strategy-detail-page',
  standalone: true,
  imports: [
    ButtonModule,
    EmptyStateComponent,
    LoadingStateComponent,
    MetricTileComponent,
    StatusTagComponent,
    TrainedModelsTableComponent,
    TrainingRequestDialogComponent,
    TrainingRunProgressComponent,
  ],
  template: `
    @if (loading()) {
      <app-loading-state label="Loading strategy" />
    } @else if (!strategy()) {
      <app-empty-state title="Strategy not found" description="The backend did not return this strategy." />
    } @else {
      <div class="page-heading">
        <div>
          <span class="eyebrow">Strategy</span>
          <h2>{{ strategy()!.name }}</h2>
        </div>
        <div class="button-row">
          <p-button icon="pi pi-arrow-left" label="Back" size="small" severity="secondary" (onClick)="back()" />
          <p-button icon="pi pi-refresh" label="Refresh" size="small" severity="secondary" (onClick)="load()" />
          <p-button icon="pi pi-play" label="Start Training" size="small" (onClick)="trainingDialog.open(strategy()!.default_parameters)" />
        </div>
      </div>

      <section class="surface-section">
        <div class="section-title">
          <div>
            <h3>{{ strategy()!.name }}</h3>
            <span>{{ strategy()!.description }}</span>
          </div>
          <app-status-tag [status]="strategy()!.status" />
        </div>
        <div class="metrics-grid">
          <app-metric-tile label="Model" [value]="strategy()!.model_family" />
          <app-metric-tile label="Version" [value]="strategy()!.version" />
          <app-metric-tile label="Default Timeframe" [value]="strategy()!.default_parameters.timeframe" />
          <app-metric-tile label="Calculated Rows" [value]="strategy()!.default_parameters.training_rows" />
        </div>
      </section>

      <app-training-run-progress [run]="activeRun()" />

      <section class="surface-section">
        <div class="section-title">
          <h3>Trained Models</h3>
        </div>
        @if (!models().length) {
          <app-empty-state title="No models yet" description="Start a training run to generate the first model." />
        } @else {
          <app-trained-models-table [models]="models()" (open)="openModel($event)" />
        }
      </section>

      <app-training-request-dialog #trainingDialog (submitted)="startTraining($event)" />
    }
  `,
})
export class StrategyDetailPage {
  @ViewChild('trainingDialog') trainingDialog!: TrainingRequestDialogComponent;

  private readonly api = inject(SmartTradeApiClient);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly messages = inject(MessageService);
  private readonly destroyRef = inject(DestroyRef);
  private polling?: Subscription;

  readonly strategy = signal<StrategyDetail | null>(null);
  readonly models = signal<TrainedModelSummary[]>([]);
  readonly activeRun = signal<TrainingRunRead | null>(null);
  readonly loading = signal(true);

  constructor() {
    this.load();
  }

  load(): void {
    const strategyId = this.route.snapshot.paramMap.get('strategyId')!;
    this.loading.set(true);
    this.api.getStrategy(strategyId).subscribe({
      next: (strategy) => {
        this.strategy.set(strategy);
        this.models.set(strategy.trained_models);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  startTraining(request: TrainingRequest): void {
    const strategy = this.strategy();
    if (!strategy) {
      return;
    }
    this.api.createTrainingRun(strategy.id, request).subscribe({
      next: (run) => {
        this.activeRun.set(run);
        this.messages.add({ severity: 'success', summary: 'Training queued', detail: run.id });
        this.pollRun(run.id);
      },
      error: (error) => this.messages.add({ severity: 'error', summary: 'Training failed to start', detail: error.message }),
    });
  }

  openModel(model: TrainedModelSummary): void {
    void this.router.navigate(['/strategies', model.strategy_id, 'models', model.id]);
  }

  back(): void {
    void this.router.navigate(['/strategies']);
  }

  private pollRun(runId: string): void {
    this.polling?.unsubscribe();
    this.polling = interval(3000)
      .pipe(
        switchMap(() => this.api.getTrainingRun(runId)),
        takeWhile((run) => ['PENDING', 'RUNNING'].includes(run.status), true),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((run) => {
        this.activeRun.set(run);
        if (run.status === 'TRAINED' || run.status === 'FAILED') {
          this.load();
        }
      });
  }
}
