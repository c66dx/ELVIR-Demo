import { Component } from '@angular/core';

/**
 * Placeholder para la ruta raíz. El redirectToDashboardGuard redirige antes de renderizar.
 * Angular requiere un component cuando no se usa redirectTo con canActivate.
 */
@Component({
  selector: 'app-redirect-placeholder',
  standalone: true,
  template: '',
  styles: [],
})
export class RedirectPlaceholderComponent {}

