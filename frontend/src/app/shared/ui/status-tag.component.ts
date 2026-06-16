import { Component, input } from '@angular/core';
import { TagModule } from 'primeng/tag';

@Component({
  selector: 'app-status-tag',
  standalone: true,
  imports: [TagModule],
  template: `<p-tag [severity]="severity()" [value]="status()" />`,
})
export class StatusTagComponent {
  readonly status = input.required<string>();

  severity(): 'success' | 'secondary' | 'info' | 'warn' | 'danger' | 'contrast' {
    switch (this.status()) {
      case 'APPROVED':
      case 'VALIDATED':
      case 'TRAINED':
        return 'success';
      case 'RUNNING':
      case 'VALIDATING':
        return 'info';
      case 'PENDING':
        return 'secondary';
      case 'FAILED':
      case 'REJECTED':
        return 'danger';
      default:
        return 'contrast';
    }
  }
}
