import { Pipe, PipeTransform } from '@angular/core';

import { resolveUploadUrl } from '../utils/media-url.util';

@Pipe({
  name: 'uploadUrl',
  standalone: true,
})
export class UploadUrlPipe implements PipeTransform {
  transform(value: string | null | undefined): string | null {
    return resolveUploadUrl(value);
  }
}
