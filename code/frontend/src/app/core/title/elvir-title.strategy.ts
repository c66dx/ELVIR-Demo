import { inject, Injectable } from '@angular/core';
import { Title } from '@angular/platform-browser';
import { DefaultTitleStrategy, RouterStateSnapshot } from '@angular/router';

const DEFAULT_DOC_TITLE = 'ELVIR - Entrenador Laboral Virtual';

/**
 * Añade sufijo de marca a la pestaña del navegador según `title` en cada ruta.
 * @see https://angular.dev/guide/routing/common-router-tasks#setting-the-page-title
 */
@Injectable()
export class ElvirTitleStrategy extends DefaultTitleStrategy {
  constructor() {
    super(inject(Title));
  }

  override updateTitle(snapshot: RouterStateSnapshot): void {
    const pageTitle = this.buildTitle(snapshot);
    if (pageTitle) {
      this.title.setTitle(`${pageTitle} | ELVIR`);
    } else {
      this.title.setTitle(DEFAULT_DOC_TITLE);
    }
  }
}
