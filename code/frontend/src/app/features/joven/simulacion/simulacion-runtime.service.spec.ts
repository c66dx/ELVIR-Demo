import { SimulacionRuntimeService } from './simulacion-runtime.service'; 
 describe('SimulacionRuntimeService', () => { 
 let service: SimulacionRuntimeService; 
 beforeEach(() => { 
 jasmine.clock().install(); 
 jasmine.clock().mockDate(new Date('2026-01-01T00:00:00Z')); 
 service = new SimulacionRuntimeService(); 
 }); 
 afterEach(() => { 
 service.stopTimer(); 
 jasmine.clock().uninstall(); 
 }); 
 it('builds close metrics only for COMPLETADA status', () => { 
 service.startTimer(() => undefined); 
 jasmine.clock().tick(5000); 
 const completeMetrics = service.buildCloseMetrics('COMPLETADA'); 
 const cancelledMetrics = service.buildCloseMetrics('CANCELADA'); 
 expect(completeMetrics).toEqual({ duration_seconds: 5 }); 
 expect(cancelledMetrics).toBeUndefined(); 
 }); 
 it('builds session summary only when status is COMPLETADA and data exists', () => { 
 const withSummary = service.buildSessionEndData({ 
 status: 'COMPLETADA',   sessionId: '123',   session: { duration_seconds: 120 } as any,   context: { jobRoleName: 'Cajero', caseName: 'Caso 1' },   youthId: '10',   returnUrl: '/joven',   motivo: 'ok',   }); 
 const withoutSummary = service.buildSessionEndData({ 
 status: 'ERROR',   sessionId: '123',   session: null,   context: null,   }); 
 expect(withSummary.sessionSummary).toEqual({ 
 duration_seconds: 120,   jobRoleName: 'Cajero',   caseName: 'Caso 1',   sessionId: '123',   }); 
 expect(withoutSummary.sessionSummary).toBeUndefined(); 
 });
});
