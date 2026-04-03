import { Component, Input, numberAttribute } from '@angular/core'; 
 @Component({ 
 selector: 'app-form-grid',   standalone: true,   template: '<ng-content></ng-content>',   host: { 
 class: 'form-grid',   '[class.form-grid--one]': 'columns === 1',   '[class.form-grid--media]': 'variant === "media"',   },
})
export class FormGridComponent { 
 @Input({ transform: numberAttribute }) columns: 1 | 2 = 2; 
 @Input() variant: 'default' | 'media' = 'default';
}
