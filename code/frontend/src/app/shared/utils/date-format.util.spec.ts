import {
  durationBetween,
  formatDate,
  formatDuration,
  formatStatusLabel,
  SESSION_STATUS_LABELS,
} from '@shared/utils/date-format.util';

describe('date-format.util', () => {
  describe('formatDate', () => {
    it('devuelve guión sin fecha', () => {
      expect(formatDate(undefined)).toBe('-');
      expect(formatDate('')).toBe('-');
    });

    it('formatea una ISO válida (locale es-CL)', () => {
      const s = formatDate('2020-06-15T14:30:00.000Z');
      expect(s).not.toBe('-');
      expect(s.length).toBeGreaterThan(5);
      expect(s).toMatch(/2020/);
    });
  });

  describe('formatDuration', () => {
    it('devuelve guión sin duración', () => {
      expect(formatDuration(undefined)).toBe('-');
      expect(formatDuration(0)).toBe('-');
    });

    it('segundos menores a 60', () => {
      expect(formatDuration(45)).toBe('45 s');
    });

    it('minutos con o sin segundos restantes', () => {
      expect(formatDuration(60)).toBe('1 min');
      expect(formatDuration(90)).toBe('1 min 30 s');
      expect(formatDuration(120)).toBe('2 min');
    });
  });

  describe('durationBetween', () => {
    it('calcula segundos entre dos ISO', () => {
      expect(
        durationBetween('2020-01-01T00:00:00.000Z', '2020-01-01T00:01:05.000Z'),
      ).toBe(65);
    });
  });

  describe('formatStatusLabel', () => {
    it('usa etiquetas conocidas', () => {
      expect(formatStatusLabel('EN_CURSO')).toBe(SESSION_STATUS_LABELS['EN_CURSO']);
      expect(formatStatusLabel('COMPLETADA')).toBe('Completada');
    });

    it('devuelve el valor crudo si no hay mapeo', () => {
      expect(formatStatusLabel('OTRO')).toBe('OTRO');
    });
  });
});
