import { DOCUMENT } from '@angular/common';
import { AfterViewInit, Directive, ElementRef, HostListener, OnDestroy, inject } from '@angular/core';
import { getTabbableElements } from '@shared/a11y/tabbable.util';

/**
 * Modal ligero sin CDK: al montarse enfoca el primer control enfocable y atrapa Tab;
 * al destruirse devuelve el foco al elemento activo previo (p. ej. botón que abrió el modal).
 */
@Directive({
  selector: '[appModalDialog]',
  standalone: true,
})
export class ModalDialogDirective implements AfterViewInit, OnDestroy {
  private readonly el = inject(ElementRef<HTMLElement>);
  private readonly doc = inject(DOCUMENT);
  private previous: HTMLElement | null = null;

  ngAfterViewInit(): void {
    this.previous = this.doc.activeElement as HTMLElement | null;
    queueMicrotask(() => this.moveFocusInside());
  }

  private moveFocusInside(): void {
    const root = this.el.nativeElement;
    const list = getTabbableElements(root);
    if (list.length > 0) {
      list[0].focus();
    } else {
      root.focus();
    }
  }

  @HostListener('keydown', ['$event'])
  onKeydown(e: KeyboardEvent): void {
    if (e.key !== 'Tab') return;
    const root = this.el.nativeElement;
    const list = getTabbableElements(root);
    if (list.length === 0) return;
    const first = list[0];
    const last = list[list.length - 1];
    const active = this.doc.activeElement as HTMLElement | null;
    if (e.shiftKey) {
      if (active === first || !root.contains(active)) {
        e.preventDefault();
        last.focus();
      }
    } else {
      if (active === last || !root.contains(active)) {
        e.preventDefault();
        first.focus();
      }
    }
  }

  ngOnDestroy(): void {
    this.previous?.focus?.();
  }
}
