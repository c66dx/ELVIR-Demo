import { Component, computed, inject, signal } from "@angular/core";
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from "@angular/forms";
import { Router, RouterLink } from "@angular/router";
import { ApiService } from "../../../core/services/api.service";
import { NotificationService } from "../../../core/services/notification.service";
import { FormActionsComponent } from "../../../shared/form/form-actions/form-actions.component";
import { FormContainerComponent } from "../../../shared/form/form-container/form-container.component";
import { FormFieldComponent } from "../../../shared/form/form-field/form-field.component";
import { FormGridComponent } from "../../../shared/form/form-grid/form-grid.component";
import { FormSectionComponent } from "../../../shared/form/form-section/form-section.component";
import { TextInputComponent } from "../../../shared/form/inputs/text-input/text-input.component";

interface MeInfo {
  email: string;
  role: string;
  profile_photo_url?: string;
}

@Component({
  selector: "app-change-password",
  standalone: true,
  imports: [
    ReactiveFormsModule,
    RouterLink,
    FormContainerComponent,
    FormSectionComponent,
    FormGridComponent,
    FormFieldComponent,
    FormActionsComponent,
    TextInputComponent,
  ],
  templateUrl: "./change-password.component.html",
  styleUrl: "./change-password.component.scss",
})
export class ChangePasswordComponent {
  private fb = inject(FormBuilder);
  private api = inject(ApiService);
  private router = inject(Router);
  private notification = inject(NotificationService);

  me = signal<MeInfo | null>(null);
  photoUrl = signal<string | null>(null);
  photoError = signal<string | null>(null);
  photoLoading = signal(false);

  initials = computed(() => {
    const name = this.me()?.email || "U";
    const parts = name.trim().split(/\s+/);
    const letters = parts.slice(0, 2).map((p) => p[0]?.toUpperCase() ?? "");
    return letters.join("") || "U";
  });

  roleLabel = computed(() => {
    const role = this.me()?.role;
    switch (role) {
      case "ADMIN":
        return "Administrador";
      case "PROFESIONAL":
        return "Tutor";
      case "JOVEN":
        return "Joven";
      default:
        return role || "";
    }
  });

  form: FormGroup = this.fb.nonNullable.group({
    current_password: ["", Validators.required],
    new_password: ["", [Validators.required, Validators.minLength(6)]],
    new_password_confirm: ["", Validators.required],
  });
  submitting = false;
  errorMessage = "";

  ngOnInit(): void {
    this.api.getMe().subscribe((me) => {
      this.me.set(me as MeInfo | null);
      this.photoUrl.set(me?.profile_photo_url ?? null);
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
      if ("error" in res) {
        this.photoError.set(res.error);
        return;
      }
      this.photoUrl.set(res.url);
    });
    input.value = "";
  }

  onSubmit(): void {
    const v = this.form.getRawValue();
    if (v.new_password !== v.new_password_confirm) {
      this.form.get("new_password_confirm")?.setErrors({ mismatch: true });
      return;
    }
    if (this.form.invalid) return;
    this.errorMessage = "";
    this.submitting = true;
    this.api.changePassword(v.current_password, v.new_password).subscribe({
      next: (result) => {
        this.submitting = false;
        if ("error" in result) {
          this.errorMessage = result.error;
          return;
        }
        this.notification.success("Contrase?a actualizada correctamente");
        this.router.navigate(["/"]);
      },
      error: () => {
        this.submitting = false;
      },
    });
  }
}
