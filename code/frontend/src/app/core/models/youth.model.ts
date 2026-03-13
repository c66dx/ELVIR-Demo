export interface Youth {
  id: string;
  user_id?: string;
  login_enabled: boolean;
  display_name: string;
  identifier?: string;
  rut?: string;
  email?: string;
  profile_photo_url?: string;
  phone?: string;
  year_of_birth?: number;
  diagnosis?: string;
  is_active: boolean;
  general_notes?: string;
  profile_checklist?: string[];
  created_at: string;
  updated_at: string;
}

/** Perfil postulante: checklist de competencias/características para inserción laboral. */
export const PROFILE_CHECKLIST_ITEMS: { slug: string; label: string }[] = [
  { slug: 'comunicacion', label: 'Comunicación efectiva' },
  { slug: 'trabajo_equipo', label: 'Trabajo en equipo' },
  { slug: 'puntualidad', label: 'Puntualidad' },
  { slug: 'responsabilidad', label: 'Responsabilidad' },
  { slug: 'autonomia', label: 'Autonomía' },
  { slug: 'iniciativa', label: 'Iniciativa' },
  { slug: 'resolucion_problemas', label: 'Resolución de problemas' },
  { slug: 'adaptabilidad', label: 'Adaptabilidad' },
  { slug: 'presentacion_personal', label: 'Presentación personal' },
];

