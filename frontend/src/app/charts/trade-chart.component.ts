import {
  AfterViewInit,
  Component,
  ElementRef,
  OnDestroy,
  ViewChild,
} from '@angular/core';
import {
  CandlestickData,
  CandlestickSeries,
  createChart,
  createSeriesMarkers,
  IChartApi,
  ISeriesApi,
  LineData,
  LineSeries,
  SeriesMarker,
  Time,
} from 'lightweight-charts';

@Component({
  selector: 'app-trade-chart',
  template: '<div #chartHost class="chart-host" aria-label="Placeholder trading chart"></div>',
  styles: [`
    :host {
      display: block;
      min-width: 0;
    }

    .chart-host {
      width: 100%;
      height: 360px;
      min-height: 320px;
    }
  `],
})
export class TradeChartComponent implements AfterViewInit, OnDestroy {
  @ViewChild('chartHost', { static: true })
  private readonly chartHost!: ElementRef<HTMLElement>;

  private chart: IChartApi | null = null;
  private resizeObserver: ResizeObserver | null = null;

  ngAfterViewInit(): void {
    const host = this.chartHost.nativeElement;
    this.chart = createChart(host, {
      autoSize: true,
      height: host.clientHeight,
      layout: {
        background: { color: '#ffffff' },
        textColor: '#334155',
      },
      grid: {
        horzLines: { color: '#e5e7eb' },
        vertLines: { color: '#eef2f7' },
      },
      rightPriceScale: {
        borderVisible: false,
      },
      timeScale: {
        borderVisible: false,
        timeVisible: true,
      },
      crosshair: {
        mode: 1,
      },
    });

    const candles = generateCandles();
    const candleSeries = this.chart.addSeries(CandlestickSeries, {
      upColor: '#1f9d6a',
      downColor: '#d64545',
      borderVisible: false,
      wickUpColor: '#1f9d6a',
      wickDownColor: '#d64545',
    }) as ISeriesApi<'Candlestick'>;
    candleSeries.setData(candles);

    const equitySeries = this.chart.addSeries(LineSeries, {
      color: '#2563eb',
      lineWidth: 2,
      priceScaleId: 'equity',
    }) as ISeriesApi<'Line'>;
    equitySeries.setData(generateEquity(candles));
    this.chart.priceScale('equity').applyOptions({
      scaleMargins: {
        top: 0.72,
        bottom: 0.08,
      },
    });

    createSeriesMarkers(candleSeries, generateMarkers(candles));
    this.chart.timeScale().fitContent();

    this.resizeObserver = new ResizeObserver(() => {
      this.chart?.applyOptions({ height: host.clientHeight });
    });
    this.resizeObserver.observe(host);
  }

  ngOnDestroy(): void {
    this.resizeObserver?.disconnect();
    this.chart?.remove();
  }
}

function generateCandles(): CandlestickData<Time>[] {
  const start = Math.floor(Date.UTC(2026, 5, 14, 9, 0, 0) / 1000);
  const candles: CandlestickData<Time>[] = [];
  let previousClose = 67240;

  for (let index = 0; index < 64; index += 1) {
    const drift = Math.sin(index / 5) * 24 + Math.cos(index / 9) * 16;
    const open = previousClose;
    const close = open + drift + (index % 7 - 3) * 5;
    const high = Math.max(open, close) + 18 + (index % 4) * 5;
    const low = Math.min(open, close) - 18 - (index % 5) * 4;

    candles.push({
      time: (start + index * 60) as Time,
      open: roundPrice(open),
      high: roundPrice(high),
      low: roundPrice(low),
      close: roundPrice(close),
    });
    previousClose = close;
  }

  return candles;
}

function generateEquity(candles: CandlestickData<Time>[]): LineData<Time>[] {
  let equity = 1000;
  return candles.map((candle, index) => {
    equity += Math.sin(index / 6) * 0.85 + (Number(candle.close) - Number(candle.open)) / 900;
    return {
      time: candle.time,
      value: Number(equity.toFixed(2)),
    };
  });
}

function generateMarkers(candles: CandlestickData<Time>[]): SeriesMarker<Time>[] {
  return [
    {
      time: candles[14].time,
      position: 'belowBar',
      color: '#1f9d6a',
      shape: 'arrowUp',
      text: 'paper entry',
    },
    {
      time: candles[38].time,
      position: 'aboveBar',
      color: '#d64545',
      shape: 'arrowDown',
      text: 'paper exit',
    },
  ];
}

function roundPrice(value: number): number {
  return Number(value.toFixed(2));
}
