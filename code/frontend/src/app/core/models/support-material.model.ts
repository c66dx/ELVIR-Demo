import type { MaterialType } from '@core/models/types.model'; 
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
