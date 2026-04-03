import type { Role } from './types.model'; 
 export type UserRole = Role; 
 export interface User { 
 id: string; 
 email: string; 
 role: Role; 
 is_active: boolean; 
 profile_photo_url?: string; 
 created_at: string; 
 updated_at: string;
} 
 export interface AuthUser { 
 token: string; 
 role: Role;
}
