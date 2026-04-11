import { Component, forwardRef, Input } from '@angular/core';
import { ControlValueAccessor, NG_VALUE_ACCESSOR } from '@angular/forms'; 
 type ChecklistItem = Record<string, unknown>; 
 @Component({ 
 selector: 'app-checkbox-group',   standalone: true,   templateUrl: './checkbox-group.component.html',   styles: [':host { display: block; width: 100%; }'],   providers: [   { 
 provide: NG_VALUE_ACCESSOR,   useExisting: forwardRef(() => CheckboxGroupComponent),   multi: true,   },   ],
})
export class CheckboxGroupComponent implements ControlValueAccessor { 
 @Input() items: ChecklistItem[] = []; 
 @Input() valueKey = 'value'; 
 @Input() labelKey = 'label'; 
 @Input() descriptionKey?: string; 
 value: string[] = []; 
 disabled = false; 
 private onChange: (value: string[]) => void = () => undefined; 
 private onTouched: () => void = () => undefined; 
 writeValue(value: string[] | null): void { 
 this.value = Array.isArray(value) ? value : []; 
 } 
 registerOnChange(fn: (value: string[]) => void): void { 
 this.onChange = fn; 
 } 
 registerOnTouched(fn: () => void): void { 
 this.onTouched = fn; 
 } 
 setDisabledState(isDisabled: boolean): void { 
 this.disabled = isDisabled; 
 } 
 getItemValue(item: ChecklistItem): string { 
 return String(item?.[this.valueKey]  ?? ''); 
 } 
 getItemLabel(item: ChecklistItem): string { 
 return String(item?.[this.labelKey]  ?? ''); 
 } 
 getItemDescription(item: ChecklistItem): string | null { 
 if (!this.descriptionKey) return null; 
 const value = item?.[this.descriptionKey]; 
 return value ?  String(value) : null; 
 } 
 isSelected(value: string): boolean { 
 return this.value.includes(value); 
 } 
 toggle(value: string): void { 
 if (this.disabled) return; 
 const next = this.isSelected(value)   ?  this.value.filter((item) => item !== value)   : [...this.value, value]; 
 this.value = next; 
 this.onChange(next); 
 this.onTouched(); 
 }
}
