export interface ApiError {
  status: number;
  message: string;
}

export function apiErrorMessage(error: unknown): string {
  if (typeof error === 'object' && error !== null && 'message' in error) {
    return String((error as { message: unknown }).message);
  }
  return 'Unexpected API error';
}
