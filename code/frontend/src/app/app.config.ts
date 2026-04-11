import { ApplicationConfig, provideZoneChangeDetection } from '@angular/core';
import { provideRouter, TitleStrategy } from '@angular/router';
import { provideHttpClient, withFetch, withInterceptors } from '@angular/common/http';
import { routes } from './app.routes';
import { authInterceptor } from './core/interceptors/auth.interceptor';
import { errorInterceptor } from './core/interceptors/error.interceptor';
import { ElvirTitleStrategy } from './core/title/elvir-title.strategy';

export const appConfig: ApplicationConfig = {
  providers: [
    provideZoneChangeDetection(),
    provideRouter(routes),
    provideHttpClient(withFetch(), withInterceptors([authInterceptor, errorInterceptor])),
    { provide: TitleStrategy, useClass: ElvirTitleStrategy },
  ],
};
