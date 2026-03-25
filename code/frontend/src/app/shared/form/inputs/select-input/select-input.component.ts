import { Component, forwardRef, Input } from '@angular/core';
import { ControlValueAccessor, NG_VALUE_ACCESSOR } from '@angular/forms'; 
 @Component({ 
 selector: 'app-select-input',   standalone: true,   templateUrl: './select-input.component.html',   styles: [   `   :host { 
 display: block; 
 width: 100%; 
 min-width: 0; 
 flex: 1 1 auto; 
 } 
 select.form-control { 
 width: 100%; 
 max-width: 100%; 
 padding: 0.45rem 0.7rem; 
 border: 1px solid var(--color-input-border, #d1d5db); 
 border-radius: 10px; 
 font-size: 0.85rem; 
 background: var(--color-input-bg, #ffffff); 
 color: var(--color-text, #111827); 
 min-height: 40px; 
 transition: border-color var(--motion-fast), box-shadow var(--motion-fast), background var(--motion-fast); 
 box-sizing: border-box; 
 } 
 select.form-control:focus { 
 outline: none; 
 border-color: var(--color-primary, #0f766e); 
 box-shadow: 0 0 0 3px var(--color-input-focus, rgba(15, 118, 110, 0.16)); 
 background: var(--color-surface, #ffffff); 
 } 
 select.form-control:disabled { 
 background: var(--color-surface-alt, #f3f4f6); 
 color: var(--color-text-muted, #6b7280); 
 cursor: not-allowed; 
 } 
 `,   ],   providers: [   { 
 provide: NG_VALUE_ACCESSOR,   useExisting: forwardRef(() => SelectInputComponent),   multi: true,   },   ],
})
export class SelectInputComponent implements ControlValueAccessor { 
 @Input() id?: string; 
 @Input() name?: string; 
 @Input() placeholder?: string; 
 @Input() disabledOptionLabel?: string; 
 value = ''; 
 disabled = false; 
 private onChange: (value: string) => void = () => {}; 
 private onTouched: () => void = () => {}; 
 writeValue(value: string | null): void { 
 this.value = value  ?? ''; 
 } 
 registerOnChange(fn: (value: string) => void): void { 
 this.onChange = fn; 
 } 
 registerOnTouched(fn: () => void): void { 
 this.onTouched = fn; 
 } 
 setDisabledState(isDisabled: boolean): void { 
 this.disabled = isDisabled; 
 } 
 handleChange(event: Event): void { 
 const next = (event.target as HTMLSelectElement).value; 
 this.value = next; 
 this.onChange(next); 
 } 
 handleBlur(): void { 
 this.onTouched(); 
 }
}
