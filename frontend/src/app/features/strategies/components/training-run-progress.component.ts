import { Component, input } from '@angular/core';
import { ProgressBarModule } from 'primeng/progressbar';

import { StatusTagComponent } from '../../../shared/ui/status-tag.component';
import { TrainingRunRead } from '../models/strategy.model';

@Component({
  selector: 'app-training-run-progress',
  standalone: true,
  imports: [ProgressBarModule, StatusTagComponent],
  template: `
    @if (run()) {
      <section class="surface-section compact">
        <div class="section-title">
          <div>
            <h3>Latest Training Run</h3>
            <span class="mono">{{ run()!.id }}</span>
          </div>
          <app-status-tag [status]="run()!.status" />
        </div>
        <p-progressBar [value]="progressPercent()" [showValue]="true" />
        <dl class="definition-grid">
          <div>
            <dt>Phase</dt>
            <dd>{{ run()!.progress_phase ?? '-' }}</dd>
          </div>
          <div>
            <dt>Worker</dt>
            <dd>{{ run()!.worker_id ?? '-' }}</dd>
          </div>
          <div>
            <dt>Started</dt>
            <dd>{{ run()!.started_at ?? '-' }}</dd>
          </div>
          <div>
            <dt>Finished</dt>
            <dd>{{ run()!.finished_at ?? '-' }}</dd>
          </div>
        </dl>
        @if (run()!.progress_message) {
          <p class="run-message">{{ run()!.progress_message }}</p>
        }
      </section>
    }
  `,
})
export class TrainingRunProgressComponent {
  readonly run = input<TrainingRunRead | null>(null);

  progressPercent(): number {
    const pct = this.run()?.progress_pct ?? 0;
    return Math.round(pct * 100);
  }
}
