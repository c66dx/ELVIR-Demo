import type { MaterialType } from './types.model';

export interface SupportMaterial {
  id: string;
  title: string;
  description?: string;
  type: MaterialType;
  url: string;
  job_role_id?: string;
  case_id?: string;
  active: boolean;
  created_at: string;
  updated_at: string;
}
