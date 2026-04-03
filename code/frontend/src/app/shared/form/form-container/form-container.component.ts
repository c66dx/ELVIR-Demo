import { Component, Input } from '@angular/core'; 
 @Component({ 
 selector: 'app-form-container',   standalone: true,   templateUrl: './form-container.component.html',   host: { 
 class: 'form-page',   },
})
export class FormContainerComponent { 
 @Input() title?: string; 
 @Input() subtitle?: string;
}
