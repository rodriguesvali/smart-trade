import { Component, DestroyRef, inject, output, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { ButtonModule } from 'primeng/button';
import { DialogModule } from 'primeng/dialog';
import { InputNumberModule } from 'primeng/inputnumber';
import { TooltipModule } from 'primeng/tooltip';
import { ToggleSwitchModule } from 'primeng/toggleswitch';

import { TrainedModelDetail, ValidationParameters } from '../models/strategy.model';

@Component({
  selector: 'app-validation-request-dialog',
  standalone: true,
  imports: [ButtonModule, DialogModule, InputNumberModule, ReactiveFormsModule, TooltipModule, ToggleSwitchModule],
  template: `
    <p-dialog
      header="Validate Model"
      [modal]="true"
      [visible]="visible()"
      (visibleChange)="visible.set($event)"
      [style]="{ width: '760px', maxWidth: '96vw' }"
      [draggable]="false"
    >
      <form class="form-grid" [formGroup]="form" (ngSubmit)="submit()">
        <label>
          <span class="field-label">
            Confidence Threshold
            <i class="pi pi-info-circle field-help" tabindex="0" [pTooltip]="tips.confidenceThreshold" tooltipPosition="top" tooltipStyleClass="field-help-tooltip" aria-label="Confidence Threshold help"></i>
          </span>
          <p-inputNumber
            formControlName="probability_threshold_percent"
            mode="decimal"
            suffix="%"
            [min]="1"
            [max]="99"
            [minFractionDigits]="0"
            [maxFractionDigits]="2"
          />
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
        <label>
          <span class="field-label">
            Take Profit (%)
            <i class="pi pi-info-circle field-help" tabindex="0" [pTooltip]="tips.takeProfit" tooltipPosition="top" tooltipStyleClass="field-help-tooltip" aria-label="Take Profit help"></i>
          </span>
          <p-inputNumber
            formControlName="take_profit_percent"
            mode="decimal"
            suffix="%"
            [min]="0.0001"
            [max]="99.9999"
            [minFractionDigits]="2"
            [maxFractionDigits]="4"
          />
        </label>
        <label>
          <span class="field-label">
            Stop Loss (%)
            <i class="pi pi-info-circle field-help" tabindex="0" [pTooltip]="tips.stopLoss" tooltipPosition="top" tooltipStyleClass="field-help-tooltip" aria-label="Stop Loss help"></i>
          </span>
          <p-inputNumber
            formControlName="stop_loss_percent"
            mode="decimal"
            suffix="%"
            [min]="0.0001"
            [max]="99.9999"
            [minFractionDigits]="2"
            [maxFractionDigits]="4"
          />
        </label>
        <label>
          <span class="field-label">
            Trailing Activation (%)
            <i class="pi pi-info-circle field-help" tabindex="0" [pTooltip]="tips.trailingActivation" tooltipPosition="top" tooltipStyleClass="field-help-tooltip" aria-label="Trailing Activation help"></i>
          </span>
          <p-inputNumber
            formControlName="trailing_activation_percent"
            mode="decimal"
            suffix="%"
            [min]="0.0001"
            [max]="99.9999"
            [minFractionDigits]="2"
            [maxFractionDigits]="4"
          />
        </label>
        <label>
          <span class="field-label">
            Trailing Distance (%)
            <i class="pi pi-info-circle field-help" tabindex="0" [pTooltip]="tips.trailingDistance" tooltipPosition="top" tooltipStyleClass="field-help-tooltip" aria-label="Trailing Distance help"></i>
          </span>
          <p-inputNumber
            formControlName="trailing_distance_percent"
            mode="decimal"
            suffix="%"
            [min]="0.0001"
            [max]="99.9999"
            [minFractionDigits]="2"
            [maxFractionDigits]="4"
          />
        </label>
        <label>
          <span class="field-label">
            Fee (%)
            <i class="pi pi-info-circle field-help" tabindex="0" [pTooltip]="tips.fee" tooltipPosition="top" tooltipStyleClass="field-help-tooltip" aria-label="Fee help"></i>
          </span>
          <p-inputNumber
            formControlName="fee_percent"
            mode="decimal"
            suffix="%"
            [min]="0"
            [max]="99.9999"
            [minFractionDigits]="0"
            [maxFractionDigits]="4"
          />
        </label>
        <label>
          <span class="field-label">
            Slippage (%)
            <i class="pi pi-info-circle field-help" tabindex="0" [pTooltip]="tips.slippage" tooltipPosition="top" tooltipStyleClass="field-help-tooltip" aria-label="Slippage help"></i>
          </span>
          <p-inputNumber
            formControlName="slippage_percent"
            mode="decimal"
            suffix="%"
            [min]="0"
            [max]="99.9999"
            [minFractionDigits]="0"
            [maxFractionDigits]="4"
          />
        </label>
        <label>
          <span class="field-label">
            Minimum Trades
            <i class="pi pi-info-circle field-help" tabindex="0" [pTooltip]="tips.minimumTrades" tooltipPosition="top" tooltipStyleClass="field-help-tooltip" aria-label="Minimum Trades help"></i>
          </span>
          <p-inputNumber formControlName="threshold_min_trades" [min]="1" [max]="10000" [showButtons]="true" />
        </label>
        <label>
          <span class="field-label">
            Walk-Forward Folds
            <i class="pi pi-info-circle field-help" tabindex="0" [pTooltip]="tips.walkForwardFolds" tooltipPosition="top" tooltipStyleClass="field-help-tooltip" aria-label="Walk-Forward Folds help"></i>
          </span>
          <p-inputNumber formControlName="walk_forward_folds" [min]="1" [max]="20" [showButtons]="true" />
        </label>
        <label>
          <span class="field-label">
            Embargo Rows
            <i class="pi pi-info-circle field-help" tabindex="0" [pTooltip]="tips.embargoRows" tooltipPosition="top" tooltipStyleClass="field-help-tooltip" aria-label="Embargo Rows help"></i>
          </span>
          <p-inputNumber formControlName="walk_forward_embargo_rows" [min]="0" [max]="10000" [showButtons]="true" />
        </label>
        <div class="switch-row">
          <span class="field-label">
            Trailing Stop
            <i class="pi pi-info-circle field-help" tabindex="0" [pTooltip]="tips.trailingStop" tooltipPosition="top" tooltipStyleClass="field-help-tooltip" aria-label="Trailing Stop help"></i>
          </span>
          <p-toggleswitch formControlName="trailing_stop_enabled" />
        </div>

        <footer>
          <p-button label="Cancel" severity="secondary" [text]="true" type="button" (onClick)="visible.set(false)" />
          <p-button label="Validate" icon="pi pi-check-circle" type="submit" [disabled]="form.invalid" />
        </footer>
      </form>
    </p-dialog>
  `,
})
export class ValidationRequestDialogComponent {
  private readonly destroyRef = inject(DestroyRef);

  readonly submitted = output<ValidationParameters>();
  readonly visible = signal(false);

  readonly tips = {
    confidenceThreshold:
      'Minimum model confidence required to count an inference as a signal. Minimum: 1%. Maximum: 99%. Default: 55%. Higher values are stricter and usually reduce signals.',
    oversoldRsi:
      'RSI threshold used by validation to allow long entries. Minimum: 0. Maximum: 100. Default: model target threshold or 30. Lower values are stricter.',
    takeProfit:
      'Profit target for the simulated long trade. Minimum: 0.0001%. Maximum: 99.9999%. Example: 0.25% exits when price reaches +0.25%.',
    stopLoss:
      'Initial loss limit for the simulated long trade. Minimum: 0.0001%. Maximum: 99.9999%. Example: 0.20% exits when price reaches -0.20%.',
    trailingActivation:
      'Favorable move required before trailing stop starts following price. Minimum: 0.0001%. Maximum: 99.9999%. Disabled when Trailing Stop is off.',
    trailingDistance:
      'Distance below the best favorable price after trailing is active. Minimum: 0.0001%. Maximum: 99.9999%. Disabled when Trailing Stop is off.',
    fee:
      'Exchange fee estimate per side, expressed as percent. Minimum: 0%. Maximum: 99.9999%. Validation subtracts round-trip fee from each simulated trade.',
    slippage:
      'Execution price drift estimate per side, expressed as percent. Minimum: 0%. Maximum: 99.9999%. Validation subtracts round-trip slippage from each trade.',
    minimumTrades:
      'Minimum number of simulated trades required for a threshold to be eligible as recommended. Minimum: 1. Maximum: 10000. Default: 10.',
    walkForwardFolds:
      'Number of temporal folds used before holdout to check stability. Minimum: 1. Maximum: 20. Default: 3. More folds add evidence and cost more training time.',
    embargoRows:
      'Gap between walk-forward training and validation windows to reduce label leakage. Minimum: 0. Maximum: 10000. Initial value: last validation value when available; otherwise the model target_n.',
    trailingStop:
      'When enabled, stop loss can move upward after price moves favorably. When disabled, Trailing Activation and Trailing Distance are ignored and not sent.',
  };

  readonly form = new FormGroup({
    probability_threshold_percent: new FormControl(55, { nonNullable: true, validators: [Validators.min(1), Validators.max(99)] }),
    rsi_oversold_threshold: new FormControl(30, { nonNullable: true, validators: [Validators.min(0), Validators.max(100)] }),
    take_profit_percent: new FormControl(0.15, { nonNullable: true, validators: [Validators.min(0.0001), Validators.max(99.9999)] }),
    stop_loss_percent: new FormControl(0.1, { nonNullable: true, validators: [Validators.min(0.0001), Validators.max(99.9999)] }),
    trailing_stop_enabled: new FormControl(true, { nonNullable: true }),
    trailing_activation_percent: new FormControl(0.1, { nonNullable: true, validators: [Validators.min(0.0001), Validators.max(99.9999)] }),
    trailing_distance_percent: new FormControl(0.1, { nonNullable: true, validators: [Validators.min(0.0001), Validators.max(99.9999)] }),
    fee_percent: new FormControl(0, { nonNullable: true, validators: [Validators.min(0), Validators.max(99.9999)] }),
    slippage_percent: new FormControl(0, { nonNullable: true, validators: [Validators.min(0), Validators.max(99.9999)] }),
    threshold_min_trades: new FormControl(10, { nonNullable: true, validators: [Validators.min(1), Validators.max(10000)] }),
    walk_forward_folds: new FormControl(3, { nonNullable: true, validators: [Validators.min(1), Validators.max(20)] }),
    walk_forward_embargo_rows: new FormControl(15, { nonNullable: true, validators: [Validators.min(0), Validators.max(10000)] }),
  });

  constructor() {
    this.form.controls.trailing_stop_enabled.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => this.syncTrailingControls());
    this.syncTrailingControls();
  }

  open(model: TrainedModelDetail): void {
    const operational = model.validation_summary?.operational_metrics ?? {};
    const windowMetadata = model.validation_summary?.window_metadata ?? {};
    const thresholdAnalysis = this.record(windowMetadata['threshold_analysis']);
    const walkForward = this.record(windowMetadata['walk_forward']);
    const targetN = this.num(model.target_parameters['target_n'], 15);

    this.form.patchValue({
      probability_threshold_percent: this.toPercent(this.num(operational['probability_threshold'], this.num(thresholdAnalysis['configured_probability_threshold'], 0.55))),
      rsi_oversold_threshold: this.num(operational['entry_rsi_threshold'], this.num(model.target_parameters['rsi_oversold_threshold'], 30)),
      trailing_stop_enabled: this.bool(operational['trailing_stop_enabled'], true),
      trailing_activation_percent: this.toPercent(this.num(operational['trailing_activation_pct'], 0.001)),
      trailing_distance_percent: this.toPercent(this.num(operational['trailing_distance_pct'], 0.001)),
      fee_percent: this.toPercent(this.num(operational['fee_pct'], 0)),
      slippage_percent: this.toPercent(this.num(operational['slippage_pct'], 0)),
      threshold_min_trades: this.num(thresholdAnalysis['minimum_trades'], 10),
      walk_forward_folds: this.num(walkForward['requested_folds'], 3),
      walk_forward_embargo_rows: this.num(walkForward['embargo_rows'], targetN),
    });
    this.syncTrailingControls();
    this.visible.set(true);
  }

  submit(): void {
    if (this.form.invalid) {
      return;
    }
    const value = this.form.getRawValue();
    const request: ValidationParameters = {
      probability_threshold: this.fromPercent(value.probability_threshold_percent),
      rsi_oversold_threshold: value.rsi_oversold_threshold,
      take_profit_pct: this.fromPercent(value.take_profit_percent),
      stop_loss_pct: this.fromPercent(value.stop_loss_percent),
      trailing_stop_enabled: value.trailing_stop_enabled,
      fee_pct: this.fromPercent(value.fee_percent),
      slippage_pct: this.fromPercent(value.slippage_percent),
      threshold_min_trades: value.threshold_min_trades,
      walk_forward_folds: value.walk_forward_folds,
      walk_forward_embargo_rows: value.walk_forward_embargo_rows,
    };
    if (value.trailing_stop_enabled) {
      request.trailing_activation_pct = this.fromPercent(value.trailing_activation_percent);
      request.trailing_distance_pct = this.fromPercent(value.trailing_distance_percent);
    }
    this.submitted.emit(request);
    this.visible.set(false);
  }

  trailingEnabled(): boolean {
    return this.form.controls.trailing_stop_enabled.value;
  }

  private syncTrailingControls(): void {
    const controls = [this.form.controls.trailing_activation_percent, this.form.controls.trailing_distance_percent];
    controls.forEach((control) => {
      if (this.trailingEnabled()) {
        control.enable({ emitEvent: false });
      } else {
        control.disable({ emitEvent: false });
      }
    });
  }

  private toPercent(value: number): number {
    return Number((value * 100).toFixed(4));
  }

  private fromPercent(value: number): number {
    return Number((value / 100).toFixed(8));
  }

  private num(value: unknown, fallback: number): number {
    const parsed = typeof value === 'number' ? value : Number(value);
    return Number.isFinite(parsed) ? parsed : fallback;
  }

  private bool(value: unknown, fallback: boolean): boolean {
    return typeof value === 'boolean' ? value : fallback;
  }

  private record(value: unknown): Record<string, unknown> {
    return value && typeof value === 'object' ? (value as Record<string, unknown>) : {};
  }
}
