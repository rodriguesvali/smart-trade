import { DOCUMENT } from '@angular/common';
import { effect, inject, Injectable, signal } from '@angular/core';

import { ThemeMode } from './theme.model';

const STORAGE_KEY = 'smart-trade.theme';

@Injectable({ providedIn: 'root' })
export class ThemeService {
  private readonly document = inject(DOCUMENT);
  readonly mode = signal<ThemeMode>(this.readInitialMode());

  constructor() {
    effect(() => {
      const mode = this.mode();
      localStorage.setItem(STORAGE_KEY, mode);
      this.applyTheme(mode);
    });
  }

  setMode(mode: ThemeMode): void {
    this.mode.set(mode);
  }

  toggleDarkLight(): void {
    const active = this.activeMode();
    this.setMode(active === 'dark' ? 'light' : 'dark');
  }

  activeMode(): 'light' | 'dark' {
    const mode = this.mode();
    if (mode !== 'system') {
      return mode;
    }
    return matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }

  private applyTheme(mode: ThemeMode): void {
    const dark = mode === 'dark' || (mode === 'system' && matchMedia('(prefers-color-scheme: dark)').matches);
    this.document.documentElement.classList.toggle('app-dark', dark);
    this.document.documentElement.dataset['theme'] = dark ? 'dark' : 'light';
  }

  private readInitialMode(): ThemeMode {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === 'light' || stored === 'dark' || stored === 'system') {
      return stored;
    }
    return 'system';
  }
}
