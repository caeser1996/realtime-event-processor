// Event types
export type EventType =
  | 'user_action'
  | 'page_view'
  | 'click'
  | 'form_submit'
  | 'purchase'
  | 'error'
  | 'custom';

export interface Event {
  id: string;
  event_type: EventType;
  user_id: string | null;
  session_id: string | null;
  payload: Record<string, unknown>;
  metadata: Record<string, unknown>;
  timestamp: string;
  processed_at: string | null;
  source_ip: string | null;
  user_agent: string | null;
}

export interface EventCreate {
  event_type: EventType;
  user_id?: string;
  session_id?: string;
  payload?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
}

// Analytics types
export interface RealTimeMetrics {
  timestamp: string;
  events_last_minute: number;
  events_last_hour: number;
  active_users: number;
  active_sessions: number;
  events_per_second: number;
  processing_lag_ms: number;
  kafka_lag: number;
  error_count: number;
  top_event_types: TopEventType[];
}

export interface TopEventType {
  type: string;
  count: number;
}

export interface TimeSeriesData {
  timestamp: string;
  event_count: number;
  unique_users: number;
}

export interface EventStats {
  total_events: number;
  unique_users: number;
  unique_sessions: number;
  events_by_type: Record<string, number>;
  time_range: {
    start: string | null;
    end: string | null;
  };
}

export interface DashboardData {
  realtime: RealTimeMetrics;
  timeseries: {
    interval: string;
    data: TimeSeriesData[];
  };
  stats: EventStats;
  updated_at: string;
}

// WebSocket types
export interface WebSocketMessage {
  type: 'metrics' | 'initial' | 'keepalive' | 'pong' | 'error';
  data?: RealTimeMetrics;
  timestamp?: string;
  message?: string;
}

// API Response types
export interface EventsListResponse {
  events: Event[];
  total: number;
  limit: number;
  offset: number;
}

export interface GenerateEventsResponse {
  status: string;
  generated: number;
  message: string;
}

// Connection status
export type ConnectionStatus = 'connected' | 'disconnected' | 'connecting';
