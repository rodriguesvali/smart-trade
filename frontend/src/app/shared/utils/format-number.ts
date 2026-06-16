export function numberValue(value: unknown, digits = 4): string {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return '-';
  }
  return value.toLocaleString(undefined, { maximumFractionDigits: digits });
}

export function percentValue(value: unknown, digits = 2): string {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return '-';
  }
  return `${(value * 100).toLocaleString(undefined, { maximumFractionDigits: digits })}%`;
}
