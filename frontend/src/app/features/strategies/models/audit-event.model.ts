export interface AuditEventRead {
  id: string;
  event_type: string;
  message: string;
  payload: Record<string, unknown>;
  created_at: string;
}
