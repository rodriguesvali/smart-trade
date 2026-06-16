import { Component, input } from '@angular/core';

@Component({
  selector: 'app-empty-state',
  standalone: true,
  template: `
    <div class="state-panel">
      <i class="pi pi-inbox"></i>
      <strong>{{ title() }}</strong>
      <span>{{ description() }}</span>
    </div>
  `,
})
export class EmptyStateComponent {
  readonly title = input('No data');
  readonly description = input('There is nothing to display yet.');
}
