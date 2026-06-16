export interface StrategySummary {
  id: string;
  name: string;
  version: string;
  description: string;
  model_family: string;
  status: string;
}

export interface StrategyDetail extends StrategySummary {
  feature_contract: Record<string, unknown>;
  default_parameters: TrainingParameters;
  trained_models: TrainedModelSummary[];
}

export interface TrainingParameters {
  exchange_id: string;
  data_mode: 'real' | 'synthetic';
  sentiment_required: boolean;
  symbol: string;
  sentiment_symbol?: string;
  timeframe: string;
  target_n: number;
  take_profit_pct: number;
  stop_loss_pct: number;
  training_rows: number;
  validation_ratio: number;
  holdout_ratio: number;
  probability_threshold: number;
  xgboost?: Record<string, number>;
}

export interface TrainingRequest {
  auto_validate?: boolean;
  exchange_id?: string;
  data_mode?: 'real' | 'synthetic';
  sentiment_required?: boolean;
  symbol?: string;
  sentiment_symbol?: string;
  timeframe?: string;
  target_n?: number;
  take_profit_pct?: number;
  stop_loss_pct?: number;
  training_rows?: number;
}

export interface TrainingRunRead {
  id: string;
  strategy_id: string;
  strategy_version: string;
  status: string;
  requested_parameters: TrainingParameters;
  window_configuration: Record<string, unknown>;
  started_at: string | null;
  finished_at: string | null;
  failure_reason: string | null;
  created_at: string;
  model_id: string | null;
  auto_validate: boolean;
  progress_phase: string | null;
  progress_pct: number | null;
  progress_message: string | null;
  worker_id: string | null;
  locked_at: string | null;
  heartbeat_at: string | null;
}

export interface TrainedModelSummary {
  id: string;
  run_id: string;
  strategy_id: string;
  strategy_version: string;
  status: string;
  artifact_format: string;
  created_at: string;
  updated_at: string;
}

export interface TrainedModelDetail extends TrainedModelSummary {
  artifact_path: string;
  dataset_metadata: Record<string, unknown>;
  feature_schema: Record<string, unknown>;
  target_parameters: Record<string, unknown>;
  training_metrics: Record<string, unknown>;
  validation_summary: ValidationSummary | null;
  validation_results: ValidationResultRead[];
}

export interface ValidationSummary {
  latest_validation_result_id: string;
  ml_metrics: Record<string, unknown>;
  operational_metrics: Record<string, unknown>;
}

export interface ValidationResultRead {
  id: string;
  validation_type: string;
  window_metadata: Record<string, unknown>;
  ml_metrics: Record<string, unknown>;
  operational_metrics: Record<string, unknown>;
  created_at: string;
}

export interface ApprovalRequest {
  operator: string;
  comments?: string | null;
}
