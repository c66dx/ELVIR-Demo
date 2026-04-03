import { Component, inject } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { ToastComponent } from './core/components/toast/toast.component';
import { ThemeService } from './core/services/theme.service'; 
 @Component({ 
 selector: 'app-root',   standalone: true,   imports: [RouterOutlet, ToastComponent],   template: `   <router-outlet></router-outlet>   <app-toast></app-toast>   `,   styles: [],
})
export class AppComponent { 
 private _theme = inject(ThemeService);
}
