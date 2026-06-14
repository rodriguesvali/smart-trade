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
  parameter_schema: Record<string, unknown>;
  required_features: string[];
  model_roles: Record<string, unknown>[];
  default_parameters: Record<string, unknown>;
  compatibility: {
    compatible: boolean;
    reasons: string[];
    risk_rules: Record<string, unknown>[];
  };
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
  parameters: Record<string, unknown>;
  training_window_start: string | null;
  training_window_end: string | null;
  holdout_start: string | null;
  holdout_end: string | null;
  approved_at: string | null;
  created_at: string;
}

export interface ModelsResponse {
  items: ModelSummary[];
}

export interface ModelTrainingRunSummary {
  id: number;
  model_id: string;
  model_role: string;
  strategy_id: string;
  strategy_version: string;
  feature_schema_id: string;
  status: string;
  started_at: string;
  completed_at: string | null;
  training_rows: number;
  holdout_rows: number;
  metrics: Record<string, unknown>;
  error_message: string | null;
}

export interface ModelTrainingRunsResponse {
  items: ModelTrainingRunSummary[];
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

export interface PaperPositionSummary {
  id: number;
  asset_symbol: string;
  status: string;
  side: string;
  quantity: string;
  average_entry_price: string;
  stop_loss_price: string | null;
  take_profit_price: string | null;
  opened_at: string;
  closed_at: string | null;
  close_reason: string | null;
  strategy_id: string;
  strategy_version: string;
  model_refs: Record<string, unknown>[];
}

export interface PaperEquitySummary {
  id: number;
  asset_symbol: string;
  equity_usd: string;
  cash_usd: string;
  position_value_usd: string;
  snapshot_at: string;
  source: string;
}

export interface PaperDecisionSummary {
  id: number;
  strategy_id: string;
  strategy_version: string;
  asset_symbol: string;
  timeframe: string;
  action: string;
  reason: string;
  confidence: string | null;
  participating_models: Record<string, unknown>[];
  risk_updates: Record<string, unknown>;
  decided_at: string;
}

export interface PaperOrderSummary {
  id: number;
  client_order_id: string;
  exchange_order_id: string | null;
  position_id: number | null;
  decision_id: number | null;
  asset_symbol: string;
  side: string;
  order_type: string;
  status: string;
  requested_quantity: string;
  requested_price: string | null;
  submitted_at: string | null;
  raw_request: Record<string, unknown>;
  raw_response: Record<string, unknown>;
}

export interface PaperStatusResponse {
  open_position: PaperPositionSummary | null;
  latest_equity: PaperEquitySummary | null;
  recent_decisions: PaperDecisionSummary[];
  recent_orders: PaperOrderSummary[];
}

export interface LiveReadinessReviewSummary {
  id: number;
  status: string;
  requested_by: string;
  reviewed_at: string;
  enabled_at: string | null;
  checks: Record<string, unknown>[];
  evidence: Record<string, unknown>;
  failure_reasons: string[];
}

export interface LiveReadinessStatusResponse {
  ready: boolean;
  checks: Record<string, unknown>[];
  failure_reasons: string[];
  latest_review: LiveReadinessReviewSummary | null;
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

export interface FeatureSchemaSummary {
  schema_id: string;
  name: string;
  version: string;
  timeframe: string;
  features: string[];
  parameters: Record<string, unknown>;
  created_at: string;
}

export interface DataIngestionRunSummary {
  id: number;
  exchange: string;
  symbol: string;
  timeframe: string;
  status: string;
  started_at: string;
  completed_at: string | null;
  since_ms: number | null;
  until_ms: number | null;
  requested_limit: number | null;
  fetched_count: number;
  inserted_count: number;
  feature_rows_upserted: number;
  first_open_time_ms: number | null;
  last_open_time_ms: number | null;
  error_message: string | null;
}

export interface MarketDataStatus {
  exchange: string;
  symbol: string;
  timeframe: string;
  candle_count: number;
  feature_count: number;
  latest_candle_opened_at: string | null;
  latest_candle_open_time_ms: number | null;
  latest_feature_opened_at: string | null;
  latest_feature_schema_id: string | null;
  feature_schemas: FeatureSchemaSummary[];
  latest_ingestion_run: DataIngestionRunSummary | null;
}

export interface OperatorReadModels {
  configuration: ConfigurationSummary;
  strategies: StrategiesResponse;
  models: ModelsResponse;
  operation: OperationStatus;
  events: EventsResponse;
  marketData: MarketDataStatus;
  trainingRuns: ModelTrainingRunsResponse;
  paper: PaperStatusResponse;
  liveReadiness: LiveReadinessStatusResponse;
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
      marketData: this.http.get<MarketDataStatus>('/api/data/status'),
      trainingRuns: this.http.get<ModelTrainingRunsResponse>('/api/models/training-runs'),
      paper: this.http.get<PaperStatusResponse>('/api/paper/status'),
      liveReadiness: this.http.get<LiveReadinessStatusResponse>('/api/live-readiness/status'),
    });
  }
}
