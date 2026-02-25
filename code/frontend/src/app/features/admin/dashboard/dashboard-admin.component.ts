import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

/** Dashboard Admin: crear profesionales, subir material general. */
@Component({
  selector: 'app-dashboard-admin',
  standalone: true,
  imports: [RouterLink],
  templateUrl: './dashboard-admin.component.html',
  styleUrl: './dashboard-admin.component.scss',
})
export class DashboardAdminComponent {}
