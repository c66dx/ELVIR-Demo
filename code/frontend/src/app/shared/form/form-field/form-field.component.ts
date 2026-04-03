import { Component, Input } from '@angular/core'; 
 @Component({ 
 selector: 'app-form-field',   standalone: true,   templateUrl: './form-field.component.html',   host: { 
 class: 'form-field',   '[class.form-field--span]': 'span === "full"',   '[class.form-field--inline]': 'inline',   '[class.form-field--error]': '!!error',   },
})
export class FormFieldComponent { 
 @Input() label?: string; 
 @Input() hint?: string | null; 
 @Input() error?: string | null; 
 @Input() required = false; 
 @Input() forId?: string; 
 @Input() span: 'auto' | 'full' = 'auto'; 
 @Input() inline = false;
}
