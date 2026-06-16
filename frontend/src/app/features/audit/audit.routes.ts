import { Routes } from '@angular/router';

export const AUDIT_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () => import('./pages/audit-events.page').then((m) => m.AuditEventsPage),
  },
];
