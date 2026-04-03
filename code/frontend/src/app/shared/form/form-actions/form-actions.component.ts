import { Component, Input } from '@angular/core'; 
 @Component({ 
 selector: 'app-form-actions',   standalone: true,   templateUrl: './form-actions.component.html',   host: { 
 class: 'form-actions',   '[class.form-actions--static]': '!sticky',   '[class.form-actions--align-start]': 'align === "start"',   },
})
export class FormActionsComponent { 
 @Input() sticky = true; 
 @Input() align: 'start' | 'end' = 'end';
}
