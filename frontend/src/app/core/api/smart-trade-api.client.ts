import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../config/environment.model';
import { AuditEventRead } from '../../features/strategies/models/audit-event.model';
import {
  ApprovalRequest,
  DeletedModelRead,
  DeleteModelRequest,
  StrategyDetail,
  StrategySummary,
  TrainedModelDetail,
  TrainedModelSummary,
  TrainingRequest,
  TrainingRunRead,
  ValidationParameters,
} from '../../features/strategies/models/strategy.model';

@Injectable({ providedIn: 'root' })
export class SmartTradeApiClient {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = environment.apiBaseUrl;

  health(): Observable<{ status: string }> {
    return this.http.get<{ status: string }>(`${this.baseUrl}/health`);
  }

  listStrategies(): Observable<StrategySummary[]> {
    return this.http.get<StrategySummary[]>(`${this.baseUrl}/api/strategies`);
  }

  getStrategy(strategyId: string): Observable<StrategyDetail> {
    return this.http.get<StrategyDetail>(`${this.baseUrl}/api/strategies/${strategyId}`);
  }

  createTrainingRun(strategyId: string, request: TrainingRequest): Observable<TrainingRunRead> {
    return this.http.post<TrainingRunRead>(`${this.baseUrl}/api/strategies/${strategyId}/training-runs`, request);
  }

  getTrainingRun(runId: string): Observable<TrainingRunRead> {
    return this.http.get<TrainingRunRead>(`${this.baseUrl}/api/training-runs/${runId}`);
  }

  listStrategyModels(strategyId: string): Observable<TrainedModelSummary[]> {
    return this.http.get<TrainedModelSummary[]>(`${this.baseUrl}/api/strategies/${strategyId}/models`);
  }

  getModel(modelId: string): Observable<TrainedModelDetail> {
    return this.http.get<TrainedModelDetail>(`${this.baseUrl}/api/models/${modelId}`);
  }

  validateModel(modelId: string, request: ValidationParameters = {}): Observable<TrainedModelDetail> {
    return this.http.post<TrainedModelDetail>(`${this.baseUrl}/api/models/${modelId}/validate`, request);
  }

  approveModel(modelId: string, request: ApprovalRequest): Observable<TrainedModelDetail> {
    return this.http.post<TrainedModelDetail>(`${this.baseUrl}/api/models/${modelId}/approve`, request);
  }

  rejectModel(modelId: string, request: ApprovalRequest): Observable<TrainedModelDetail> {
    return this.http.post<TrainedModelDetail>(`${this.baseUrl}/api/models/${modelId}/reject`, request);
  }

  deleteModel(modelId: string, request: DeleteModelRequest): Observable<DeletedModelRead> {
    return this.http.delete<DeletedModelRead>(`${this.baseUrl}/api/models/${modelId}`, { body: request });
  }

  listAuditEvents(): Observable<AuditEventRead[]> {
    return this.http.get<AuditEventRead[]>(`${this.baseUrl}/api/audit-events`);
  }
}
