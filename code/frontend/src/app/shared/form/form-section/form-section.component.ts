import { Component, Input } from '@angular/core'; 
 @Component({ 
 selector: 'app-form-section',   standalone: true,   templateUrl: './form-section.component.html',   host: { 
 class: 'form-section',   },
})
export class FormSectionComponent { 
 @Input() title?: string; 
 @Input() description?: string;
}
