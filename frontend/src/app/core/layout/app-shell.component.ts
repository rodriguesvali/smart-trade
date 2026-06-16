import { CommonModule } from '@angular/common';
import { Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { interval, startWith, switchMap, catchError, of } from 'rxjs';
import { ButtonModule } from 'primeng/button';
import { ConfirmDialogModule } from 'primeng/confirmdialog';
import { TagModule } from 'primeng/tag';
import { ToastModule } from 'primeng/toast';
import { TooltipModule } from 'primeng/tooltip';

import { SmartTradeApiClient } from '../api/smart-trade-api.client';
import { ThemeService } from '../theme/theme.service';

@Component({
  selector: 'app-shell',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    RouterLinkActive,
    RouterOutlet,
    ButtonModule,
    ConfirmDialogModule,
    TagModule,
    ToastModule,
    TooltipModule,
  ],
  template: `
    <p-toast />
    <p-confirmDialog />

    <div class="app-shell">
      <aside class="sidebar">
        <div class="brand">
          <div class="brand-mark">ST</div>
          <div>
            <strong>Smart Trade</strong>
            <span>Training Console</span>
          </div>
        </div>

        <nav class="nav">
          <a routerLink="/dashboard" routerLinkActive="active">
            <i class="pi pi-chart-line"></i>
            Dashboard
          </a>
          <a routerLink="/strategies" routerLinkActive="active">
            <i class="pi pi-sitemap"></i>
            XGBoost Strategies
          </a>
          <a routerLink="/audit-events" routerLinkActive="active">
            <i class="pi pi-history"></i>
            Audit Events
          </a>
        </nav>
      </aside>

      <main class="workspace">
        <header class="topbar">
          <div>
            <span class="eyebrow">MVP</span>
            <h1>Operational Dashboard</h1>
          </div>
          <div class="topbar-actions">
            <p-tag
              [severity]="apiOnline() ? 'success' : 'danger'"
              [value]="apiOnline() ? 'API online' : 'API offline'"
            />
            <p-button
              [rounded]="true"
              [text]="true"
              [icon]="theme.activeMode() === 'dark' ? 'pi pi-moon' : 'pi pi-sun'"
              pTooltip="Toggle light/dark theme"
              (onClick)="theme.toggleDarkLight()"
            />
          </div>
        </header>

        <section class="content">
          <router-outlet />
        </section>
      </main>
    </div>
  `,
})
export class AppShellComponent {
  readonly theme = inject(ThemeService);
  private readonly api = inject(SmartTradeApiClient);
  private readonly destroyRef = inject(DestroyRef);

  readonly apiOnline = signal(false);

  constructor() {
    interval(30_000)
      .pipe(
        startWith(0),
        switchMap(() => this.api.health().pipe(catchError(() => of({ status: 'offline' })))),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((health) => this.apiOnline.set(health.status === 'ok'));
  }
}
