import { Component, output, signal } from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { ButtonModule } from 'primeng/button';
import { DialogModule } from 'primeng/dialog';
import { InputNumberModule } from 'primeng/inputnumber';
import { InputTextModule } from 'primeng/inputtext';
import { MessageModule } from 'primeng/message';
import { SelectModule } from 'primeng/select';
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
      <form class="form-grid" [formGroup]="form" (ngSubmit)="submit()">
        <label>
          Exchange
          <input pInputText formControlName="exchange_id" />
        </label>
        <label>
          Data Mode
          <p-select formControlName="data_mode" [options]="dataModes" optionLabel="label" optionValue="value" />
        </label>
        <label>
          Symbol
          <input pInputText formControlName="symbol" />
        </label>
        <label>
          Sentiment Symbol
          <input pInputText formControlName="sentiment_symbol" placeholder="BTC/USDT:USDT" />
        </label>
        <label>
          Timeframe
          <p-select formControlName="timeframe" [options]="timeframes" optionLabel="label" optionValue="value" />
        </label>
        <label>
          Target N
          <p-inputNumber formControlName="target_n" [min]="2" [max]="240" [showButtons]="true" />
        </label>
        <label>
          Take Profit (%)
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
          Stop Loss (%)
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
        <div class="switch-row">
          <span>Sentiment Required</span>
          <p-toggleswitch formControlName="sentiment_required" />
        </div>
        <div class="switch-row">
          <span>Auto Validate</span>
          <p-toggleswitch formControlName="auto_validate" />
        </div>

        <p-message severity="info">
          {{ calculatedWindowSummary() }}
        </p-message>

        @if (showBinanceRetentionWarning()) {
          <p-message severity="warn">
            Binance public sentiment data is limited to roughly 30 days. The backend keeps the raw candle request inside that window.
          </p-message>
        }

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

  readonly form = new FormGroup({
    auto_validate: new FormControl(false, { nonNullable: true }),
    exchange_id: new FormControl('binance', { nonNullable: true, validators: [Validators.required] }),
    data_mode: new FormControl<'real' | 'synthetic'>('real', { nonNullable: true, validators: [Validators.required] }),
    sentiment_required: new FormControl(true, { nonNullable: true }),
    symbol: new FormControl('BTC/USDT', { nonNullable: true, validators: [Validators.required] }),
    sentiment_symbol: new FormControl('BTC/USDT:USDT', { nonNullable: true }),
    timeframe: new FormControl('M5', { nonNullable: true, validators: [Validators.required] }),
    target_n: new FormControl(15, { nonNullable: true, validators: [Validators.min(2), Validators.max(240)] }),
    take_profit_percent: new FormControl(0.15, { nonNullable: true, validators: [Validators.min(0.0001), Validators.max(99.9999)] }),
    stop_loss_percent: new FormControl(0.1, { nonNullable: true, validators: [Validators.min(0.0001), Validators.max(99.9999)] }),
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
      take_profit_percent: this.toPercent(defaults.take_profit_pct),
      stop_loss_percent: this.toPercent(defaults.stop_loss_pct),
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
      take_profit_pct: this.fromPercent(value.take_profit_percent),
      stop_loss_pct: this.fromPercent(value.stop_loss_percent),
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

  private toPercent(value: number): number {
    return Number((value * 100).toFixed(4));
  }

  private fromPercent(value: number): number {
    return Number((value / 100).toFixed(8));
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
