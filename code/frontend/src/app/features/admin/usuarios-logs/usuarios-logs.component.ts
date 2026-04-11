import { Component, DestroyRef, inject, OnInit } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { EMPTY, map, Subject, switchMap } from 'rxjs';
import { AdminApiService } from '@core/services/admin-api.service';
import type { AdminYouthLogRow, AdminProfessionalLogRow, AdminYouthLogs } from '@core/services/admin-api.types';
import { formatDate, formatStatusLabel } from '@shared/utils/date-format.util';
import { UploadUrlPipe } from '@core/pipes/upload-url.pipe';
import { ModalDialogDirective } from '@shared/a11y/modal-dialog.directive';

@Component({
  selector: 'app-usuarios-logs',
  standalone: true,
  imports: [UploadUrlPipe, ModalDialogDirective],
  templateUrl: './usuarios-logs.component.html',
  styleUrl: './usuarios-logs.component.scss',
})
export class UsuariosLogsComponent implements OnInit {
  private adminApi = inject(AdminApiService);
  private destroyRef = inject(DestroyRef);

  private readonly tabLoad$ = new Subject<'youths' | 'professionals'>();
  private readonly logsFetch$ = new Subject<void>();

  youths: AdminYouthLogRow[] = [];
  professionals: AdminProfessionalLogRow[] = [];
  loading = true;
  activeTab: 'youths' | 'professionals' = 'youths';
  readonly pageSize = 25;
  youthsPage = 1;
  professionalsPage = 1;
  youthsTotal = 0;
  professionalsTotal = 0;
  logsOpen = false;
  logsLoading = false;
  logsError = '';
  selectedYouthName = '';
  selectedYouthId: string | null = null;
  youthLogs: AdminYouthLogs = { platform_sessions: [], interviews: [] };
  platformPage = 1;
  platformPageSize = 20;
  platformTotal = 0;
  interviewsPage = 1;
  interviewsPageSize = 20;
  interviewsTotal = 0;

  ngOnInit(): void {
    this.tabLoad$
      .pipe(
        switchMap((tab) => {
          this.loading = true;
          const page = tab === 'youths' ? this.youthsPage : this.professionalsPage;
          return this.adminApi
            .getAdminUsersOverview({ tab, page, page_size: this.pageSize })
            .pipe(map((res) => ({ tab, res })));
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: ({ tab, res }) => {
          if (tab === 'youths') {
            this.youths = res.youths;
            this.youthsTotal = res.meta?.youths?.total ?? res.youths.length;
          } else {
            this.professionals = res.professionals;
            this.professionalsTotal = res.meta?.professionals?.total ?? res.professionals.length;
          }
          this.loading = false;
        },
        error: () => {
          this.loading = false;
        },
      });

    this.logsFetch$
      .pipe(
        switchMap(() => {
          if (!this.selectedYouthId) {
            return EMPTY;
          }
          this.logsLoading = true;
          this.logsError = '';
          return this.adminApi.getAdminYouthLogs(this.selectedYouthId, {
            platform_page: this.platformPage,
            platform_page_size: this.platformPageSize,
            interviews_page: this.interviewsPage,
            interviews_page_size: this.interviewsPageSize,
          });
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (res) => {
          this.youthLogs = res;
          this.platformTotal = res.meta?.platform?.total ?? res.platform_sessions.length;
          this.interviewsTotal = res.meta?.interviews?.total ?? res.interviews.length;
          this.logsLoading = false;
        },
        error: () => {
          this.logsError = 'No fue posible cargar los logs.';
          this.logsLoading = false;
        },
      });

    this.loadTab(this.activeTab);
  }

  loadTab(tab: 'youths' | 'professionals'): void {
    this.tabLoad$.next(tab);
  }

  setTab(tab: 'youths' | 'professionals'): void {
    this.activeTab = tab;
    this.loadTab(tab);
  }

  openLogs(youth: AdminYouthLogRow): void {
    this.logsOpen = true;
    this.logsLoading = true;
    this.logsError = '';
    this.selectedYouthName = youth.display_name;
    this.selectedYouthId = youth.id;
    this.youthLogs = { platform_sessions: [], interviews: [] };
    this.platformPage = 1;
    this.interviewsPage = 1;
    this.fetchLogs();
  }

  fetchLogs(): void {
    this.logsFetch$.next();
  }

  closeLogs(): void {
    this.logsOpen = false;
    this.selectedYouthName = '';
    this.selectedYouthId = null;
    this.logsError = '';
    this.platformPage = 1;
    this.interviewsPage = 1;
  }

  /** Escape en el overlay (incluye burbujeo desde el panel); no cerrar con otras teclas para no interferir con el contenido. */
  onLogsOverlayKeydown(e: KeyboardEvent): void {
    if (e.key === 'Escape') {
      this.closeLogs();
    }
  }

  /** Junto al `click` del panel (ESLint); Escape debe seguir burbujando al overlay. */
  onLogsModalPanelKeydown(e: KeyboardEvent): void {
    if (e.key !== 'Escape') {
      e.stopPropagation();
    }
  }

  onDeleteYouth(youth: AdminYouthLogRow): void {
    if (!confirm(`¿Desactivar a ${youth.display_name}? Esta acción desactiva la cuenta y libera el correo.`)) return;
    this.adminApi
      .deleteYouthAsAdmin(youth.id)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (res) => {
          if ('error' in res) return;
          this.loadTab(this.activeTab);
        },
      });
  }

  onHardDeleteYouth(youth: AdminYouthLogRow): void {
    const confirmText =
      prompt(
        `Eliminar definitivamente a ${youth.display_name}.` +
          `\nSe borrarán todos sus datos (entrevistas, registros, invitaciones) y no se puede deshacer.` +
          `\nEscribe ELIMINAR para confirmar.`,
      );
    if (confirmText !== 'ELIMINAR') return;
    this.adminApi
      .deleteYouthHardAsAdmin(youth.id)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (res) => {
          if ('error' in res) return;
          if (this.selectedYouthId === youth.id) {
            this.closeLogs();
          }
          this.loadTab(this.activeTab);
        },
      });
  }

  totalPages(total: number): number {
    return Math.max(1, Math.ceil(total / this.pageSize));
  }

  canPrev(tab: 'youths' | 'professionals'): boolean {
    return tab === 'youths' ? this.youthsPage > 1 : this.professionalsPage > 1;
  }

  canNext(tab: 'youths' | 'professionals'): boolean {
    const total = tab === 'youths' ? this.youthsTotal : this.professionalsTotal;
    const page = tab === 'youths' ? this.youthsPage : this.professionalsPage;
    return page < this.totalPages(total);
  }

  prevPage(tab: 'youths' | 'professionals'): void {
    if (!this.canPrev(tab)) return;
    if (tab === 'youths') {
      this.youthsPage -= 1;
    } else {
      this.professionalsPage -= 1;
    }
    this.loadTab(tab);
  }

  nextPage(tab: 'youths' | 'professionals'): void {
    if (!this.canNext(tab)) return;
    if (tab === 'youths') {
      this.youthsPage += 1;
    } else {
      this.professionalsPage += 1;
    }
    this.loadTab(tab);
  }

  logsTotalPages(total: number, pageSize: number): number {
    return Math.max(1, Math.ceil(total / pageSize));
  }

  canPrevLogs(section: 'platform' | 'interviews'): boolean {
    return section === 'platform' ? this.platformPage > 1 : this.interviewsPage > 1;
  }

  canNextLogs(section: 'platform' | 'interviews'): boolean {
    const total = section === 'platform' ? this.platformTotal : this.interviewsTotal;
    const page = section === 'platform' ? this.platformPage : this.interviewsPage;
    const size = section === 'platform' ? this.platformPageSize : this.interviewsPageSize;
    return page < this.logsTotalPages(total, size);
  }

  prevLogsPage(section: 'platform' | 'interviews'): void {
    if (!this.canPrevLogs(section)) return;
    if (section === 'platform') {
      this.platformPage -= 1;
    } else {
      this.interviewsPage -= 1;
    }
    this.fetchLogs();
  }

  nextLogsPage(section: 'platform' | 'interviews'): void {
    if (!this.canNextLogs(section)) return;
    if (section === 'platform') {
      this.platformPage += 1;
    } else {
      this.interviewsPage += 1;
    }
    this.fetchLogs();
  }

  loginTypeLabel(type: string): string {
    switch (type) {
      case 'HABILITADO':
        return 'Habilitado';
      case 'NO_HABILITADO':
        return 'No habilitado';
      default:
        return type || '-';
    }
  }

  formatDateCompact(iso?: string): string {
    if (!iso) return '-';
    return new Date(iso)
      .toLocaleString('es-CL', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        hour12: false,
      })
      .replace(',', '');
  }

  initials(name?: string | null): string {
    if (!name) return 'J';
    const parts = name.trim().split(/\s+/).filter(Boolean);
    if (parts.length === 0) return 'J';
    if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
    return (parts[0][0] + parts[1][0]).toUpperCase();
  }

  readonly formatDate = formatDate;
  readonly formatStatusLabel = formatStatusLabel;
}


