import { Component, inject } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';

@Component({
  selector: 'app-topbar',
  standalone: true,
  templateUrl: './topbar.component.html',
  styleUrl: './topbar.component.scss',
})
export class TopbarComponent {
  private auth = inject(AuthService);
  private router = inject(Router);
  role = this.auth.getRole();

  onLogout(): void {
    this.auth.logout();
    this.router.navigate(['/login']);
  }
}
