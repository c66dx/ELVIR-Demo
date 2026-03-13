import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ApiService } from '../../../core/services/api.service';
import type { Professional } from '../../../core/models/professional.model';

interface MeInfo {
  user_id: string;
  role: string;
  email: string;
  professional_id?: string;
  profile_photo_url?: string;
}

@Component({
  selector: 'app-professional-account',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './professional-account.component.html',
  styleUrl: './professional-account.component.scss',
})
export class ProfessionalAccountComponent implements OnInit {
  private api = inject(ApiService);

  me = signal<MeInfo | null>(null);
  professional = signal<Professional | null>(null);
  loading = signal(true);

  photoUrl = signal<string | null>(null);
  photoError = signal<string | null>(null);
  photoLoading = signal(false);

  initials = computed(() => {
    const name = this.professional()?.display_name || this.me()?.email || 'U';
    const parts = name.trim().split(/\s+/);
    const letters = parts.slice(0, 2).map((p) => p[0]?.toUpperCase() ?? '');
    return letters.join('') || 'U';
  });

  ngOnInit(): void {
    this.api.getMe().subscribe((me) => {
      this.me.set(me as MeInfo | null);
      this.photoUrl.set(me?.profile_photo_url ?? null);
      if (me?.professional_id) {
        this.api.getProfessional(me.professional_id).subscribe((p) => this.professional.set(p));
      }
      this.loading.set(false);
    });
  }

  onPhotoSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;
    this.photoError.set(null);
    this.photoLoading.set(true);
    this.api.uploadProfilePhoto(file).subscribe((res) => {
      this.photoLoading.set(false);
      if ('error' in res) {
        this.photoError.set(res.error);
        return;
      }
      this.photoUrl.set(res.url);
    });
    input.value = '';
  }
}
