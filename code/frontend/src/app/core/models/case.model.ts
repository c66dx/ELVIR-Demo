import type { Difficulty } from '@core/models/types.model'; 
 export interface Case { 
 id: string; 
 slug: string; 
 name: string; 
 difficulty: Difficulty; 
 prompt_instructions?: string; 
 description?: string;
 intervencion_regulacion_emocional?: string;
 intervencion_presentacion_personal?: string;
 intervencion_expectativas_empresa?: string;
 is_active: boolean;
}
