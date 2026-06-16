import { Routes } from '@angular/router';

export const STRATEGIES_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () => import('./pages/strategy-list.page').then((m) => m.StrategyListPage),
  },
  {
    path: ':strategyId',
    loadComponent: () => import('./pages/strategy-detail.page').then((m) => m.StrategyDetailPage),
  },
  {
    path: ':strategyId/models/:modelId',
    loadComponent: () => import('./pages/model-detail.page').then((m) => m.ModelDetailPage),
  },
];
