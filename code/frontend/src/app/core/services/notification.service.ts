import { Injectable } from '@angular/core';
import { Subject } from 'rxjs'; 
 export type ToastType = 'success' | 'error' | 'info'; 
 export interface ToastMessage { 
 id: number; 
 message: string; 
 type: ToastType;
} 
 @Injectable({ providedIn: 'root' })
export class NotificationService { 
 private nextId = 0; 
 private readonly messages$ = new Subject<ToastMessage>(); 
 readonly messages = this.messages$.asObservable(); 
 success(message: string): void { 
 this.messages$.next({ id: ++this.nextId, message, type: 'success' }); 
 } 
 error(message: string): void { 
 this.messages$.next({ id: ++this.nextId, message, type: 'error' }); 
 } 
 info(message: string): void { 
 this.messages$.next({ id: ++this.nextId, message, type: 'info' }); 
 }
}
