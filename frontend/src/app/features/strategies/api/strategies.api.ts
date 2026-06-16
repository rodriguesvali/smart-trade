import { inject, Injectable } from '@angular/core';

import { SmartTradeApiClient } from '../../../core/api/smart-trade-api.client';

@Injectable({ providedIn: 'root' })
export class StrategiesApi {
  readonly client = inject(SmartTradeApiClient);
}
