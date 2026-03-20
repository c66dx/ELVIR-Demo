import { Injectable, signal } from '@angular/core';

type ThemeMode = 'light' | 'dark';

@Injectable({ providedIn: 'root' })
export class ThemeService {
  private storageKey = 'elvir-theme';
  theme = signal<ThemeMode>('light');

  constructor() {
    this.init();
  }

  init(): void {
    const stored = this.safeGetStorage();
    const next = stored === 'dark' || stored === 'light' ? stored : 'light';
    this.applyTheme(next);
  }

  toggle(): void {
    const next = this.theme() === 'dark' ? 'light' : 'dark';
    this.applyTheme(next);
  }

  setTheme(theme: ThemeMode): void {
    this.applyTheme(theme);
  }

  private applyTheme(theme: ThemeMode): void {
    this.theme.set(theme);
    if (typeof document !== 'undefined') {
      document.body.classList.toggle('theme-dark', theme === 'dark');
    }
    this.safeSetStorage(theme);
  }

  private safeGetStorage(): ThemeMode | null {
    try {
      const value = localStorage.getItem(this.storageKey);
      if (value === 'dark' || value === 'light') return value;
      return null;
    } catch {
      return null;
    }
  }

  private safeSetStorage(value: ThemeMode): void {
    try {
      localStorage.setItem(this.storageKey, value);
    } catch {
      // ignore
    }
  }
}
