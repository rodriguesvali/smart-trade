import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { ConfirmationService, MessageService } from 'primeng/api';
import { ButtonModule } from 'primeng/button';
import { DialogModule } from 'primeng/dialog';
import { TextareaModule } from 'primeng/textarea';

import { SmartTradeApiClient } from '../../../core/api/smart-trade-api.client';
import { EmptyStateComponent } from '../../../shared/ui/empty-state.component';
import { LoadingStateComponent } from '../../../shared/ui/loading-state.component';
import { StatusTagComponent } from '../../../shared/ui/status-tag.component';
import { ModelScorecardComponent } from '../components/model-scorecard.component';
import { TrainedModelDetail } from '../models/strategy.model';

@Component({
  selector: 'app-model-detail-page',
  standalone: true,
  imports: [
    ButtonModule,
    DialogModule,
    EmptyStateComponent,
    FormsModule,
    LoadingStateComponent,
    ModelScorecardComponent,
    StatusTagComponent,
    TextareaModule,
  ],
  template: `
    @if (loading()) {
      <app-loading-state label="Loading model" />
    } @else if (!model()) {
      <app-empty-state title="Model not found" description="The backend did not return this model." />
    } @else {
      <div class="page-heading">
        <div>
          <span class="eyebrow">Model</span>
          <h2 class="mono">{{ model()!.id }}</h2>
        </div>
        <div class="button-row">
          <p-button icon="pi pi-arrow-left" label="Back" size="small" severity="secondary" (onClick)="back()" />
          <p-button icon="pi pi-check-circle" label="Validate" size="small" [disabled]="model()!.status === 'APPROVED' || model()!.status === 'REJECTED' || validating()" (onClick)="validate()" />
          <p-button icon="pi pi-thumbs-up" label="Approve" size="small" severity="success" [disabled]="model()!.status !== 'VALIDATED'" (onClick)="approve()" />
          <p-button icon="pi pi-thumbs-down" label="Reject" size="small" severity="danger" [disabled]="model()!.status === 'APPROVED' || model()!.status === 'REJECTED'" (onClick)="rejectVisible.set(true)" />
        </div>
      </div>

      <section class="surface-section compact">
        <div class="section-title">
          <div>
            <h3>Lifecycle</h3>
            <span>{{ model()!.artifact_format }} · {{ model()!.artifact_path }}</span>
          </div>
          <app-status-tag [status]="model()!.status" />
        </div>
      </section>

      <app-model-scorecard [model]="model()" />

      <p-dialog header="Reject Model" [modal]="true" [visible]="rejectVisible()" (visibleChange)="rejectVisible.set($event)" [style]="{ width: '560px', maxWidth: '96vw' }">
        <label class="stacked-label">
          Rejection comments
          <textarea pTextarea rows="5" [(ngModel)]="rejectComments"></textarea>
        </label>
        <footer class="dialog-actions">
          <p-button label="Cancel" severity="secondary" [text]="true" (onClick)="rejectVisible.set(false)" />
          <p-button label="Reject" severity="danger" icon="pi pi-times" [disabled]="!rejectComments.trim()" (onClick)="confirmReject()" />
        </footer>
      </p-dialog>
    }
  `,
})
export class ModelDetailPage {
  private readonly api = inject(SmartTradeApiClient);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly confirmation = inject(ConfirmationService);
  private readonly messages = inject(MessageService);

  readonly model = signal<TrainedModelDetail | null>(null);
  readonly loading = signal(true);
  readonly validating = signal(false);
  readonly rejectVisible = signal(false);
  rejectComments = '';

  constructor() {
    this.load();
  }

  load(): void {
    const modelId = this.route.snapshot.paramMap.get('modelId')!;
    this.loading.set(true);
    this.api.getModel(modelId).subscribe({
      next: (model) => {
        this.model.set(model);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  validate(): void {
    const model = this.model();
    if (!model) {
      return;
    }
    this.validating.set(true);
    this.api.validateModel(model.id).subscribe({
      next: (updated) => {
        this.model.set(updated);
        this.validating.set(false);
        this.messages.add({ severity: 'success', summary: 'Model validated', detail: updated.id });
      },
      error: (error) => {
        this.validating.set(false);
        this.messages.add({ severity: 'error', summary: 'Validation failed', detail: error.message });
      },
    });
  }

  approve(): void {
    const model = this.model();
    if (!model) {
      return;
    }
    this.confirmation.confirm({
      header: 'Approve model',
      message: 'Approve this validated model for future operational use?',
      icon: 'pi pi-exclamation-triangle',
      accept: () => {
        this.api.approveModel(model.id, { operator: 'dashboard-user' }).subscribe({
          next: (updated) => {
            this.model.set(updated);
            this.messages.add({ severity: 'success', summary: 'Model approved', detail: updated.id });
          },
          error: (error) => this.messages.add({ severity: 'error', summary: 'Approval failed', detail: error.message }),
        });
      },
    });
  }

  confirmReject(): void {
    const model = this.model();
    if (!model) {
      return;
    }
    this.api.rejectModel(model.id, { operator: 'dashboard-user', comments: this.rejectComments.trim() }).subscribe({
      next: (updated) => {
        this.model.set(updated);
        this.rejectVisible.set(false);
        this.messages.add({ severity: 'success', summary: 'Model rejected', detail: updated.id });
      },
      error: (error) => this.messages.add({ severity: 'error', summary: 'Rejection failed', detail: error.message }),
    });
  }

  back(): void {
    const strategyId = this.route.snapshot.paramMap.get('strategyId')!;
    void this.router.navigate(['/strategies', strategyId]);
  }
}
