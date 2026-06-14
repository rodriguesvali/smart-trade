import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { forkJoin, Observable } from 'rxjs';

export type HealthState = 'unknown' | 'ok' | 'error';

export interface ApiHealth {
  status: string;
  service: string;
  environment: string;
}

export interface ConfigurationSummary {
  exchange: string;
  symbol: string;
  base_asset: string;
  quote_asset: string;
  market_type: string;
  direction: string;
  timeframe: string;
  initial_capital_usd: string;
  mode: string;
}

export interface StrategySummary {
  id: number;
  strategy_id: string;
  version: string;
  name: string;
  description: string;
  status: string;
  supported_market: string;
  supported_direction: string;
  timeframes: string[];
  required_features: string[];
  model_roles: Record<string, unknown>[];
  default_parameters: Record<string, unknown>;
}

export interface StrategiesResponse {
  selected_strategy_id: number | null;
  items: StrategySummary[];
}

export interface ModelSummary {
  id: number;
  model_id: string;
  model_role: string;
  strategy_id: string;
  strategy_version: string;
  asset_symbol: string;
  timeframe: string;
  feature_schema_id: string;
  status: string;
  artifact_uri: string | null;
  metrics: Record<string, unknown>;
  approved_at: string | null;
  created_at: string;
}

export interface ModelsResponse {
  items: ModelSummary[];
}

export interface OperationStatus {
  state: string;
  mode: string;
  exchange: string;
  symbol: string;
  timeframe: string;
  selected_strategy_id: number | null;
  approved_or_active_models: number;
  open_positions: number;
  pending_commands: number;
  blockers: string[];
}

export interface OperationalEvent {
  id: number;
  event_type: string;
  severity: string;
  source: string;
  message: string;
  details: Record<string, unknown>;
  occurred_at: string;
}

export interface EventsResponse {
  items: OperationalEvent[];
}

export interface OperatorReadModels {
  configuration: ConfigurationSummary;
  strategies: StrategiesResponse;
  models: ModelsResponse;
  operation: OperationStatus;
  events: EventsResponse;
}

@Injectable({ providedIn: 'root' })
export class OperatorApi {
  private readonly http = inject(HttpClient);

  health(): Observable<ApiHealth> {
    return this.http.get<ApiHealth>('/api/health');
  }

  readModels(eventLimit = 50): Observable<OperatorReadModels> {
    return forkJoin({
      configuration: this.http.get<ConfigurationSummary>('/api/configuration/summary'),
      strategies: this.http.get<StrategiesResponse>('/api/strategies'),
      models: this.http.get<ModelsResponse>('/api/models'),
      operation: this.http.get<OperationStatus>('/api/operation/status'),
      events: this.http.get<EventsResponse>(`/api/events?limit=${eventLimit}`),
    });
  }
}
