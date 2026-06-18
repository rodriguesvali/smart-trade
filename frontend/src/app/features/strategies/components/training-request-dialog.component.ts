import { Component, output, signal } from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { ButtonModule } from 'primeng/button';
import { DialogModule } from 'primeng/dialog';
import { InputNumberModule } from 'primeng/inputnumber';
import { InputTextModule } from 'primeng/inputtext';
import { MessageModule } from 'primeng/message';
import { SelectModule } from 'primeng/select';
import { TabsModule } from 'primeng/tabs';
import { TooltipModule } from 'primeng/tooltip';
import { ToggleSwitchModule } from 'primeng/toggleswitch';

import { TrainingParameters, TrainingRequest } from '../models/strategy.model';

@Component({
  selector: 'app-training-request-dialog',
  standalone: true,
  imports: [
    ButtonModule,
    DialogModule,
    InputNumberModule,
    InputTextModule,
    MessageModule,
    ReactiveFormsModule,
    SelectModule,
    TabsModule,
    TooltipModule,
    ToggleSwitchModule,
  ],
  template: `
    <p-dialog
      header="Start Training"
      [modal]="true"
      [visible]="visible()"
      (visibleChange)="visible.set($event)"
      [style]="{ width: '760px', maxWidth: '96vw' }"
      [draggable]="false"
    >
      <form class="dialog-form" [formGroup]="form" (ngSubmit)="submit()">
        <p-tabs value="data">
          <p-tablist>
            <p-tab value="data">Data</p-tab>
            <p-tab value="target">Target</p-tab>
            <p-tab value="xgboost">XGBoost</p-tab>
          </p-tablist>
          <p-tabpanels>
            <p-tabpanel value="data">
              <div class="form-grid">
                <label>
                  <span class="field-label">
                    Exchange
                    <i class="pi pi-info-circle field-help" tabindex="0" [pTooltip]="tips.exchange" tooltipPosition="top" tooltipStyleClass="field-help-tooltip" aria-label="Exchange help"></i>
                  </span>
                  <input pInputText formControlName="exchange_id" />
                </label>
                <label>
                  <span class="field-label">
                    Data Mode
                    <i class="pi pi-info-circle field-help" tabindex="0" [pTooltip]="tips.dataMode" tooltipPosition="top" tooltipStyleClass="field-help-tooltip" aria-label="Data Mode help"></i>
                  </span>
                  <p-select formControlName="data_mode" [options]="dataModes" optionLabel="label" optionValue="value" />
                </label>
                <label>
                  <span class="field-label">
                    Symbol
                    <i class="pi pi-info-circle field-help" tabindex="0" [pTooltip]="tips.symbol" tooltipPosition="top" tooltipStyleClass="field-help-tooltip" aria-label="Symbol help"></i>
                  </span>
                  <input pInputText formControlName="symbol" />
                </label>
                <label>
                  <span class="field-label">
                    Sentiment Symbol
                    <i class="pi pi-info-circle field-help" tabindex="0" [pTooltip]="tips.sentimentSymbol" tooltipPosition="top" tooltipStyleClass="field-help-tooltip" aria-label="Sentiment Symbol help"></i>
                  </span>
                  <input pInputText formControlName="sentiment_symbol" placeholder="BTC/USDT:USDT" />
                </label>
                <div class="switch-row">
                  <span class="field-label">
                    Sentiment Required
                    <i class="pi pi-info-circle field-help" tabindex="0" [pTooltip]="tips.sentimentRequired" tooltipPosition="top" tooltipStyleClass="field-help-tooltip" aria-label="Sentiment Required help"></i>
                  </span>
                  <p-toggleswitch formControlName="sentiment_required" />
                </div>
                <div class="switch-row">
                  <span class="field-label">
                    Auto Validate
                    <i class="pi pi-info-circle field-help" tabindex="0" [pTooltip]="tips.autoValidate" tooltipPosition="top" tooltipStyleClass="field-help-tooltip" aria-label="Auto Validate help"></i>
                  </span>
                  <p-toggleswitch formControlName="auto_validate" />
                </div>
                @if (showBinanceRetentionWarning()) {
                  <p-message severity="warn">
                    Binance public sentiment data is limited to roughly 30 days. The backend keeps the raw candle request inside that window.
                  </p-message>
                }
              </div>
            </p-tabpanel>
            <p-tabpanel value="target">
              <div class="form-grid">
                <label>
                  <span class="field-label">
                    Timeframe
                    <i class="pi pi-info-circle field-help" tabindex="0" [pTooltip]="tips.timeframe" tooltipPosition="top" tooltipStyleClass="field-help-tooltip" aria-label="Timeframe help"></i>
                  </span>
                  <p-select formControlName="timeframe" [options]="timeframes" optionLabel="label" optionValue="value" />
                </label>
                <label>
                  <span class="field-label">
                    Target N
                    <i class="pi pi-info-circle field-help" tabindex="0" [pTooltip]="tips.targetN" tooltipPosition="top" tooltipStyleClass="field-help-tooltip" aria-label="Target N help"></i>
                  </span>
                  <p-inputNumber formControlName="target_n" [min]="2" [max]="240" [showButtons]="true" />
                </label>
                <label>
                  <span class="field-label">
                    Oversold RSI
                    <i class="pi pi-info-circle field-help" tabindex="0" [pTooltip]="tips.oversoldRsi" tooltipPosition="top" tooltipStyleClass="field-help-tooltip" aria-label="Oversold RSI help"></i>
                  </span>
                  <p-inputNumber
                    formControlName="rsi_oversold_threshold"
                    mode="decimal"
                    [min]="0"
                    [max]="100"
                    [minFractionDigits]="0"
                    [maxFractionDigits]="2"
                  />
                </label>
                <p-message severity="info">
                  {{ calculatedWindowSummary() }}
                </p-message>
              </div>
            </p-tabpanel>
            <p-tabpanel value="xgboost">
              <div class="form-grid">
                <label>
                  <span class="field-label">
                    Max Depth
                    <i class="pi pi-info-circle field-help" tabindex="0" [pTooltip]="tips.maxDepth" tooltipPosition="top" tooltipStyleClass="field-help-tooltip" aria-label="Max Depth help"></i>
                  </span>
                  <p-inputNumber formControlName="xgboost_max_depth" [min]="1" [max]="16" [showButtons]="true" />
                </label>
                <label>
                  <span class="field-label">
                    Learning Rate
                    <i class="pi pi-info-circle field-help" tabindex="0" [pTooltip]="tips.learningRate" tooltipPosition="top" tooltipStyleClass="field-help-tooltip" aria-label="Learning Rate help"></i>
                  </span>
                  <p-inputNumber
                    formControlName="xgboost_learning_rate"
                    mode="decimal"
                    [min]="0.001"
                    [max]="1"
                    [minFractionDigits]="3"
                    [maxFractionDigits]="4"
                  />
                </label>
                <label>
                  <span class="field-label">
                    Estimators
                    <i class="pi pi-info-circle field-help" tabindex="0" [pTooltip]="tips.estimators" tooltipPosition="top" tooltipStyleClass="field-help-tooltip" aria-label="Estimators help"></i>
                  </span>
                  <p-inputNumber formControlName="xgboost_n_estimators" [min]="1" [max]="2000" [showButtons]="true" />
                </label>
                <label>
                  <span class="field-label">
                    Subsample
                    <i class="pi pi-info-circle field-help" tabindex="0" [pTooltip]="tips.subsample" tooltipPosition="top" tooltipStyleClass="field-help-tooltip" aria-label="Subsample help"></i>
                  </span>
                  <p-inputNumber
                    formControlName="xgboost_subsample"
                    mode="decimal"
                    [min]="0.1"
                    [max]="1"
                    [minFractionDigits]="2"
                    [maxFractionDigits]="4"
                  />
                </label>
                <label>
                  <span class="field-label">
                    Column Sample
                    <i class="pi pi-info-circle field-help" tabindex="0" [pTooltip]="tips.columnSample" tooltipPosition="top" tooltipStyleClass="field-help-tooltip" aria-label="Column Sample help"></i>
                  </span>
                  <p-inputNumber
                    formControlName="xgboost_colsample_bytree"
                    mode="decimal"
                    [min]="0.1"
                    [max]="1"
                    [minFractionDigits]="2"
                    [maxFractionDigits]="4"
                  />
                </label>
              </div>
            </p-tabpanel>
          </p-tabpanels>
        </p-tabs>

        <footer>
          <p-button label="Cancel" severity="secondary" [text]="true" type="button" (onClick)="visible.set(false)" />
          <p-button label="Start Training" icon="pi pi-play" type="submit" [disabled]="form.invalid" />
        </footer>
      </form>
    </p-dialog>
  `,
})
export class TrainingRequestDialogComponent {
  readonly submitted = output<TrainingRequest>();
  readonly visible = signal(false);

  readonly dataModes = [
    { label: 'real', value: 'real' },
    { label: 'synthetic', value: 'synthetic' },
  ];
  readonly timeframes = ['M5', 'M15', 'M30', 'H1', 'H4', 'D1'].map((value) => ({ label: value, value }));

  readonly tips = {
    exchange:
      'Exchange id used by CCXT. Default: binance. Use the exact adapter id supported by the backend; changing it also changes which public market and sentiment endpoints are used.',
    dataMode:
      'Data source mode. real uses exchange candles and public sentiment data. synthetic is for development/test runs only and should not be used to approve production models.',
    symbol:
      'Spot pair used for price candles and future long-only operation. Example: BTC/USDT. For this MVP, keep this aligned with the configured asset.',
    sentimentSymbol:
      'Derivative/perpetual market used only for sentiment features. Example for BTC spot: BTC/USDT:USDT. It does not change the traded spot symbol.',
    sentimentRequired:
      'If enabled, training fails when Open Interest, Long/Short Ratio, or Taker Buy/Sell Ratio cannot be fetched. Disable only to allow OHLCV proxy features.',
    autoValidate:
      'If enabled, the worker validates immediately after training using default validation parameters. Leave disabled when you want to choose validation parameters manually.',
    timeframe:
      'Candle interval used for features, labels, and window calculation. Supported values: M5, M15, M30, H1, H4, D1. Smaller intervals produce more rows inside the 30-day window.',
    targetN:
      'Future horizon in candles used to confirm the training target. Minimum: 2. Maximum: 240. Example: 15 on M5 checks whether price rose within the next 75 minutes after oversold RSI.',
    oversoldRsi:
      'RSI threshold for long-only reversal labels. Minimum: 0. Maximum: 100. Default: 30. Lower values are stricter and usually create fewer, cleaner setups.',
    maxDepth:
      'Maximum tree depth. Minimum: 1. Maximum: 16. Default: 3. Higher values capture more interactions but increase overfitting risk.',
    learningRate:
      'Boosting step size. Minimum: 0.001. Maximum: 1. Default: 0.08. Lower values are more conservative and often require more estimators.',
    estimators:
      'Number of boosted trees. Minimum: 1. Maximum: 2000. Default: 60. More trees can improve fit, but also increase training time and overfitting risk.',
    subsample:
      'Fraction of rows sampled per tree. Minimum: 0.10. Maximum: 1.00. Default: 0.90. Lower values add regularization and can reduce overfitting.',
    columnSample:
      'Fraction of features sampled per tree. Minimum: 0.10. Maximum: 1.00. Default: 0.90. Lower values regularize the model when features are noisy or correlated.',
  };

  readonly form = new FormGroup({
    auto_validate: new FormControl(false, { nonNullable: true }),
    exchange_id: new FormControl('binance', { nonNullable: true, validators: [Validators.required] }),
    data_mode: new FormControl<'real' | 'synthetic'>('real', { nonNullable: true, validators: [Validators.required] }),
    sentiment_required: new FormControl(true, { nonNullable: true }),
    symbol: new FormControl('BTC/USDT', { nonNullable: true, validators: [Validators.required] }),
    sentiment_symbol: new FormControl('BTC/USDT:USDT', { nonNullable: true }),
    timeframe: new FormControl('M5', { nonNullable: true, validators: [Validators.required] }),
    target_n: new FormControl(15, { nonNullable: true, validators: [Validators.min(2), Validators.max(240)] }),
    rsi_oversold_threshold: new FormControl(30, { nonNullable: true, validators: [Validators.min(0), Validators.max(100)] }),
    xgboost_max_depth: new FormControl(3, { nonNullable: true, validators: [Validators.min(1), Validators.max(16)] }),
    xgboost_learning_rate: new FormControl(0.08, { nonNullable: true, validators: [Validators.min(0.001), Validators.max(1)] }),
    xgboost_n_estimators: new FormControl(60, { nonNullable: true, validators: [Validators.min(1), Validators.max(2000)] }),
    xgboost_subsample: new FormControl(0.9, { nonNullable: true, validators: [Validators.min(0.1), Validators.max(1)] }),
    xgboost_colsample_bytree: new FormControl(0.9, { nonNullable: true, validators: [Validators.min(0.1), Validators.max(1)] }),
  });

  open(defaults: TrainingParameters): void {
    this.form.patchValue({
      auto_validate: false,
      exchange_id: defaults.exchange_id,
      data_mode: defaults.data_mode,
      sentiment_required: defaults.sentiment_required,
      symbol: defaults.symbol,
      sentiment_symbol: defaults.sentiment_symbol ?? `${defaults.symbol}:USDT`,
      timeframe: defaults.timeframe,
      target_n: defaults.target_n,
      rsi_oversold_threshold: defaults.rsi_oversold_threshold ?? 30,
      xgboost_max_depth: defaults.xgboost?.['max_depth'] ?? 3,
      xgboost_learning_rate: defaults.xgboost?.['learning_rate'] ?? 0.08,
      xgboost_n_estimators: defaults.xgboost?.['n_estimators'] ?? 60,
      xgboost_subsample: defaults.xgboost?.['subsample'] ?? 0.9,
      xgboost_colsample_bytree: defaults.xgboost?.['colsample_bytree'] ?? 0.9,
    });
    this.visible.set(true);
  }

  submit(): void {
    if (this.form.invalid) {
      return;
    }
    const value = this.form.getRawValue();
    this.submitted.emit({
      auto_validate: value.auto_validate,
      exchange_id: value.exchange_id,
      data_mode: value.data_mode,
      sentiment_required: value.sentiment_required,
      symbol: value.symbol,
      sentiment_symbol: value.sentiment_symbol || undefined,
      timeframe: value.timeframe,
      target_n: value.target_n,
      rsi_oversold_threshold: value.rsi_oversold_threshold,
      xgboost: {
        max_depth: value.xgboost_max_depth,
        learning_rate: value.xgboost_learning_rate,
        n_estimators: value.xgboost_n_estimators,
        subsample: value.xgboost_subsample,
        colsample_bytree: value.xgboost_colsample_bytree,
      },
    });
    this.visible.set(false);
  }

  calculatedWindowSummary(): string {
    const value = this.form.getRawValue();
    const minutes = this.timeframeMinutes(value.timeframe);
    if (!minutes) {
      return 'Window will be calculated by the backend from the selected timeframe.';
    }
    const rawRows = Math.floor((30 * 24 * 60) / minutes);
    const holdoutRows = Math.floor((72 * 60) / minutes);
    const usableRows = rawRows - 80 - value.target_n;
    const trainValidationRows = usableRows - holdoutRows;
    if (trainValidationRows <= 0) {
      return 'Selected timeframe is too coarse for the 30-day window and 72h holdout.';
    }
    return `Backend window: ${rawRows} raw candles, ${usableRows} usable rows, ${trainValidationRows} train/validation rows, ${holdoutRows} holdout rows.`;
  }

  showBinanceRetentionWarning(): boolean {
    const value = this.form.getRawValue();
    return value.exchange_id === 'binance' && value.sentiment_required;
  }

  private timeframeMinutes(timeframe: string): number | null {
    const values: Record<string, number> = {
      M5: 5,
      M15: 15,
      M30: 30,
      H1: 60,
      H4: 240,
      D1: 1440,
    };
    return values[timeframe] ?? null;
  }
}
