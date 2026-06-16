import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    pathMatch: 'full',
    redirectTo: 'dashboard',
  },
  {
    path: 'dashboard',
    loadComponent: () =>
      import('./features/dashboard/pages/dashboard-home.page').then((m) => m.DashboardHomePage),
  },
  {
    path: 'strategies',
    loadChildren: () => import('./features/strategies/strategies.routes').then((m) => m.STRATEGIES_ROUTES),
  },
  {
    path: 'audit-events',
    loadChildren: () => import('./features/audit/audit.routes').then((m) => m.AUDIT_ROUTES),
  },
  {
    path: '**',
    redirectTo: 'dashboard',
  },
];
