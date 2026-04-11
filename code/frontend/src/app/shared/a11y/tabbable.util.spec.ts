import { getTabbableElements } from '@shared/a11y/tabbable.util';

describe('getTabbableElements', () => {
  let host: HTMLDivElement;

  beforeEach(() => {
    host = document.createElement('div');
    document.body.appendChild(host);
  });

  afterEach(() => {
    host.remove();
  });

  it('lista botones y enlaces visibles en orden de documento', () => {
    host.innerHTML = `
      <a href="/a">A</a>
      <button type="button" id="b1">Uno</button>
      <button type="button" id="b2">Dos</button>
    `;
    const tabbable = getTabbableElements(host);
    expect(tabbable.map((el) => el.id || el.textContent?.trim())).toEqual(['A', 'b1', 'b2']);
  });

  it('excluye disabled y display:none', () => {
    host.innerHTML = `
      <button type="button">Ok</button>
      <button type="button" disabled>Off</button>
      <span style="display:none"><button type="button" id="hidden-btn">X</button></span>
    `;
    const tabbable = getTabbableElements(host);
    expect(tabbable.length).toBe(1);
    expect(tabbable[0].textContent?.trim()).toBe('Ok');
  });

  it('excluye tabindex -1', () => {
    host.innerHTML = `
      <button type="button">Si</button>
      <button type="button" tabindex="-1">No tab</button>
    `;
    const tabbable = getTabbableElements(host);
    expect(tabbable.length).toBe(1);
  });
});
