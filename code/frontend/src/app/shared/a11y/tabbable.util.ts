/** Selectores de elementos normalmente enfocables con Tab (visibles y habilitados). */
const TABBABLE_SELECTOR = [
  'a[href]',
  'button:not([disabled])',
  'textarea:not([disabled])',
  'input:not([disabled])',
  'select:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(',');

function isVisible(el: HTMLElement): boolean {
  if (el.hidden) return false;
  const style = typeof window !== 'undefined' ? window.getComputedStyle(el) : null;
  if (style && (style.visibility === 'hidden' || style.display === 'none')) return false;
  return el.offsetParent !== null || (el.getClientRects?.().length ?? 0) > 0;
}

/** Lista de nodos enfocables dentro de `container`, en orden de documento. */
export function getTabbableElements(container: HTMLElement): HTMLElement[] {
  const nodes = Array.from(container.querySelectorAll<HTMLElement>(TABBABLE_SELECTOR));
  return nodes.filter(
    (el) => isVisible(el) && !el.hasAttribute('disabled') && el.tabIndex !== -1,
  );
}
