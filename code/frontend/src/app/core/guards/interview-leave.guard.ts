import { CanDeactivateFn } from '@angular/router';
import { SimulacionDetailComponent } from '@features/joven/simulacion/simulacion-detail.component';

export const interviewLeaveGuard: CanDeactivateFn<SimulacionDetailComponent> = (component) => {
  return component.canDeactivate();
};
