export interface JobRole { 
 id: string; 
 slug: string; 
 name: string; 
 description?: string; 
 objetivo?: string; 
 area?: string;
 nivel_experiencia?: string;
 competencias?: string | string[]; 
 tecnologias?: string | string[];
 is_active: boolean;
}
