export interface ParsedSummary {
  general: string;
  strengths: string[];
  suggestions: string[];
}

export function parseSummary(text?: string): ParsedSummary {
  if (!text) {
    return { general: '', strengths: [], suggestions: [] };
  }
  const cleaned = text.replace(/\r/g, '').trim();
  const lower = cleaned.toLowerCase();
  const strengthsIndex = lower.indexOf('puntos fuertes');
  const suggestionsIndex = lower.indexOf('sugerencias');

  const firstIndex = [strengthsIndex, suggestionsIndex].filter((i) => i >= 0).sort((a, b) => a - b)[0];
  const general = firstIndex != null ? cleaned.slice(0, firstIndex).trim() : cleaned;

  const strengthsText = extractSection(cleaned, strengthsIndex, suggestionsIndex);
  const suggestionsText = extractSection(cleaned, suggestionsIndex, -1);

  return {
    general,
    strengths: parseList(strengthsText),
    suggestions: parseList(suggestionsText),
  };
}

function extractSection(text: string, startIndex: number, nextIndex: number): string {
  if (startIndex < 0) return '';
  const colon = text.indexOf(':', startIndex);
  const sectionStart = colon >= 0 ? colon + 1 : startIndex;
  const sectionEnd = nextIndex > startIndex ? nextIndex : text.length;
  return text.slice(sectionStart, sectionEnd).trim();
}

function parseList(text: string): string[] {
  if (!text) return [];
  return text
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => line.replace(/^[-*\\u2022]\\s*/, '').trim())
    .filter(Boolean);
}
