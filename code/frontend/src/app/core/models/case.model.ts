import type { Difficulty } from './types.model';

export interface Case {
  id: string;
  slug: string;
  name: string;
  difficulty: Difficulty;
  prompt_instructions?: string;
  is_active: boolean;
}
