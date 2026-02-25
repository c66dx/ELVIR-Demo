export type AssignmentStatus = 'ACTIVO' | 'INACTIVO';

export interface Assignment {
  id: string;
  youth_id: string;
  professional_id: string;
  status: AssignmentStatus;
  assigned_at: string;
  ended_at?: string;
}
