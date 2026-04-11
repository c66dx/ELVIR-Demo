import { Component, forwardRef, Input } from '@angular/core';
import { ControlValueAccessor, NG_VALUE_ACCESSOR } from '@angular/forms'; 
 @Component({ 
 selector: 'app-toggle-input',   standalone: true,   templateUrl: './toggle-input.component.html',   styles: [':host { display: inline-flex; align-items: center; }'],   providers: [   { 
 provide: NG_VALUE_ACCESSOR,   useExisting: forwardRef(() => ToggleInputComponent),   multi: true,   },   ],
})
export class ToggleInputComponent implements ControlValueAccessor { 
 @Input() ariaLabel?: string; 
 value = false; 
 disabled = false; 
 private onChange: (value: boolean) => void = () => undefined; 
 private onTouched: () => void = () => undefined; 
 writeValue(value: boolean | null): void { 
 this.value = !!value; 
 } 
 registerOnChange(fn: (value: boolean) => void): void { 
 this.onChange = fn; 
 } 
 registerOnTouched(fn: () => void): void { 
 this.onTouched = fn; 
 } 
 setDisabledState(isDisabled: boolean): void { 
 this.disabled = isDisabled; 
 } 
 handleChange(event: Event): void { 
 const next = (event.target as HTMLInputElement).checked; 
 this.value = next; 
 this.onChange(next); 
 } 
 handleBlur(): void { 
 this.onTouched(); 
 }
}
