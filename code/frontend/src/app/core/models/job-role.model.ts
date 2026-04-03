export interface JobRole { 
 id: string; 
 slug: string; 
 name: string; 
 description?: string; 
 objetivo?: string; 
 competencias?: string | string[]; 
 is_active: boolean;
}
