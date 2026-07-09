import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../services/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './login.component.html',
  styleUrl: './login.component.scss',
})
export class LoginComponent {
  isRegisterMode = signal(false);
  email = '';
  password = '';
  errorMessage = signal('');
  isSubmitting = signal(false);

  constructor(private auth: AuthService, private router: Router) {}

  toggleMode(): void {
    this.isRegisterMode.update((v) => !v);
    this.errorMessage.set('');
  }

  async submit(): Promise<void> {
    if (!this.email || !this.password) {
      this.errorMessage.set('Enter both email and password.');
      return;
    }

    this.isSubmitting.set(true);
    this.errorMessage.set('');

    try {
      if (this.isRegisterMode()) {
        await this.auth.register(this.email, this.password);
      } else {
        await this.auth.login(this.email, this.password);
      }
      this.router.navigate(['/']);
    } catch (err: any) {
      this.errorMessage.set(err.message || 'Something went wrong. Try again.');
    } finally {
      this.isSubmitting.set(false);
    }
  }
}
