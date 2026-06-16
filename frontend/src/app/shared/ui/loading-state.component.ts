import { Component, input } from '@angular/core';
import { ProgressSpinnerModule } from 'primeng/progressspinner';

@Component({
  selector: 'app-loading-state',
  standalone: true,
  imports: [ProgressSpinnerModule],
  template: `
    <div class="state-panel">
      <p-progress-spinner strokeWidth="4" ariaLabel="Loading" />
      <span>{{ label() }}</span>
    </div>
  `,
})
export class LoadingStateComponent {
  readonly label = input('Loading');
}
