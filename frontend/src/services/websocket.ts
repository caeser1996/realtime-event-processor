import { RealTimeMetrics, WebSocketMessage, ConnectionStatus } from '../types';

type MetricsCallback = (metrics: RealTimeMetrics) => void;
type StatusCallback = (status: ConnectionStatus) => void;

class WebSocketService {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private metricsCallbacks: Set<MetricsCallback> = new Set();
  private statusCallbacks: Set<StatusCallback> = new Set();
  private pingInterval: NodeJS.Timeout | null = null;

  private get wsUrl(): string {
    const baseUrl = process.env.REACT_APP_WS_URL || 'ws://localhost:8000';
    return `${baseUrl}/ws/events`;
  }

  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      return;
    }

    this.notifyStatus('connecting');

    try {
      this.ws = new WebSocket(this.wsUrl);

      this.ws.onopen = this.handleOpen.bind(this);
      this.ws.onmessage = this.handleMessage.bind(this);
      this.ws.onerror = this.handleError.bind(this);
      this.ws.onclose = this.handleClose.bind(this);
    } catch (error) {
      console.error('WebSocket connection error:', error);
      this.scheduleReconnect();
    }
  }

  disconnect(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }

    this.notifyStatus('disconnected');
  }

  private handleOpen(): void {
    console.log('WebSocket connected');
    this.reconnectAttempts = 0;
    this.notifyStatus('connected');

    // Start ping interval
    this.pingInterval = setInterval(() => {
      this.send({ type: 'ping' });
    }, 25000);
  }

  private handleMessage(event: MessageEvent): void {
    try {
      const message: WebSocketMessage = JSON.parse(event.data);

      switch (message.type) {
        case 'metrics':
        case 'initial':
          if (message.data) {
            this.notifyMetrics(message.data);
          }
          break;
        case 'keepalive':
        case 'pong':
          // Connection is alive
          break;
        case 'error':
          console.error('WebSocket error message:', message.message);
          break;
        default:
          console.log('Unknown message type:', message);
      }
    } catch (error) {
      console.error('Error parsing WebSocket message:', error);
    }
  }

  private handleError(event: Event): void {
    console.error('WebSocket error:', event);
  }

  private handleClose(event: CloseEvent): void {
    console.log('WebSocket closed:', event.code, event.reason);
    this.notifyStatus('disconnected');

    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }

    this.scheduleReconnect();
  }

  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached');
      return;
    }

    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts);
    console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts + 1})`);

    setTimeout(() => {
      this.reconnectAttempts++;
      this.connect();
    }, delay);
  }

  private send(data: object): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  private notifyMetrics(metrics: RealTimeMetrics): void {
    this.metricsCallbacks.forEach((callback) => callback(metrics));
  }

  private notifyStatus(status: ConnectionStatus): void {
    this.statusCallbacks.forEach((callback) => callback(status));
  }

  onMetrics(callback: MetricsCallback): () => void {
    this.metricsCallbacks.add(callback);
    return () => this.metricsCallbacks.delete(callback);
  }

  onStatusChange(callback: StatusCallback): () => void {
    this.statusCallbacks.add(callback);
    return () => this.statusCallbacks.delete(callback);
  }

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}

export const wsService = new WebSocketService();
