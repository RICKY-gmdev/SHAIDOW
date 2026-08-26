import { Injectable, signal } from '@angular/core';

const API_BASE = 'https://shaidow-api-new-bjgeh2e4axe3dxhc.centralindia-01.azurewebsites.net/auth';
const TOKEN_KEY = 'shaidow_token';

@Injectable({ providedIn: 'root' })
export class AuthService {
  // Signal so components can reactively show/hide login UI without manual subscriptions.
  isAuthenticated = signal<boolean>(!!this.getToken());

  async register(email: string, password: string): Promise<void> {
    await this.authRequest('register', email, password);
  }

  async login(email: string, password: string): Promise<void> {
    await this.authRequest('login', email, password);
  }

  private async authRequest(endpoint: 'register' | 'login', email: string, password: string): Promise<void> {
    const res = await fetch(`${API_BASE}/auth/${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });

    if (!res.ok) {
      const message = await res.text();
      throw new Error(message || `${endpoint} failed`);
    }

    const data = await res.json();
    localStorage.setItem(TOKEN_KEY, data.token);
    this.isAuthenticated.set(true);
  }

  logout(): void {
    localStorage.removeItem(TOKEN_KEY);
    this.isAuthenticated.set(false);
  }

  getToken(): string | null {
    return localStorage.getItem(TOKEN_KEY);
  }

  authHeader(): Record<string, string> {
    const token = this.getToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
  }
}
