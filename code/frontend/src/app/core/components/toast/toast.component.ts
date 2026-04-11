import { Component, inject, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { NotificationService, ToastMessage } from '@core/services/notification.service';
import { Subscription } from 'rxjs'; 
 @Component({ 
 selector: 'app-toast',   standalone: true,   imports: [CommonModule],   template: `   <div class="toast-container"> 
 @for (msg of messages; track msg.id) { 
 <div class="toast toast-{{ msg.type }}">   {{ msg.message }} 
 </div>   } 
 </div>   `,   styles: [`   .toast-container { 
 position: fixed; 
 bottom: var(--space-6); 
 left: 50%; 
 transform: translateX(-50%); 
 z-index: 9999; 
 display: flex; 
 flex-direction: column; 
 gap: var(--space-2); 
 pointer-events: none; 
 } 
 .toast { 
 padding: var(--space-3) var(--space-5); 
 border-radius: var(--radius-md); 
 font-weight: 500; 
 font-size: 0.95rem; 
 box-shadow: var(--shadow-lg); 
 pointer-events: auto; 
 animation: slideUp 0.3s ease; 
 } 
 .toast-success { 
 background: var(--color-success); 
 color: white; 
 } 
 .toast-error { 
 background: var(--color-danger); 
 color: white; 
 } 
 .toast-info { 
 background: var(--color-primary); 
 color: white; 
 } 
 @keyframes slideUp { 
 from { 
 opacity: 0; 
 transform: translateY(10px); 
 } 
 to { 
 opacity: 1; 
 transform: translateY(0); 
 } 
 } 
 `],
})
export class ToastComponent implements OnInit, OnDestroy { 
 private notification = inject(NotificationService); 
 private sub?: Subscription; 
 messages: ToastMessage[] = []; 
 ngOnInit(): void { 
 this.sub = this.notification.messages.subscribe((msg) => { 
 this.messages.push(msg); 
 setTimeout(() => { 
 this.messages = this.messages.filter((m) => m.id !== msg.id); 
 }, 3500); 
 }); 
 } 
 ngOnDestroy(): void { 
 this.sub?.unsubscribe(); 
 }
}
