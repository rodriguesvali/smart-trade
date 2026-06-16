import { Component, input } from '@angular/core';

@Component({
  selector: 'app-metric-tile',
  standalone: true,
  template: `
    <div class="metric-tile">
      <span>{{ label() }}</span>
      <strong>{{ value() }}</strong>
      @if (hint()) {
        <small>{{ hint() }}</small>
      }
    </div>
  `,
})
export class MetricTileComponent {
  readonly label = input.required<string>();
  readonly value = input.required<string | number>();
  readonly hint = input<string | null>(null);
}
