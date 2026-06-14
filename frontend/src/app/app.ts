import { HttpClient } from '@angular/common/http';
import { Component, computed, inject, signal } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { TagModule } from 'primeng/tag';

type HealthState = 'unknown' | 'ok' | 'error';

@Component({
  selector: 'app-root',
  imports: [ButtonModule, CardModule, RouterOutlet, TagModule],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class App {
  private readonly http = inject(HttpClient);

  protected readonly title = signal('Smart Trade');
  protected readonly backendStatus = signal<HealthState>('unknown');
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
}
