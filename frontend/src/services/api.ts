import axios, { AxiosInstance } from 'axios';
import {
  DashboardData,
  Event,
  EventCreate,
  EventsListResponse,
  EventStats,
  GenerateEventsResponse,
  RealTimeMetrics,
  TimeSeriesData,
} from '../types';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

class ApiService {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: `${API_BASE_URL}/api/v1`,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        console.error('API Error:', error.response?.data || error.message);
        return Promise.reject(error);
      }
    );
  }

  // Events API
  async createEvent(event: EventCreate): Promise<Event> {
    const response = await this.client.post('/events', event);
    return response.data;
  }

  async getEvents(params?: {
    event_type?: string;
    user_id?: string;
    start_time?: string;
    end_time?: string;
    limit?: number;
    offset?: number;
  }): Promise<EventsListResponse> {
    const response = await this.client.get('/events', { params });
    return response.data;
  }

  async getEvent(eventId: string): Promise<Event> {
    const response = await this.client.get(`/events/${eventId}`);
    return response.data;
  }

  async generateEvents(params: {
    count: number;
    event_type?: string;
    user_count?: number;
    delay_ms?: number;
  }): Promise<GenerateEventsResponse> {
    const response = await this.client.post('/events/generate', params);
    return response.data;
  }

  // Analytics API
  async getStats(params?: {
    start_time?: string;
    end_time?: string;
  }): Promise<EventStats> {
    const response = await this.client.get('/analytics/stats', { params });
    return response.data;
  }

  async getRealTimeMetrics(): Promise<RealTimeMetrics> {
    const response = await this.client.get('/analytics/realtime');
    return response.data;
  }

  async getTimeSeries(params?: {
    interval?: string;
    start_time?: string;
    end_time?: string;
  }): Promise<{ interval: string; data: TimeSeriesData[]; summary: any }> {
    const response = await this.client.get('/analytics/timeseries', { params });
    return response.data;
  }

  async getTopEvents(params?: {
    hours?: number;
    limit?: number;
  }): Promise<{ time_window_hours: number; total_events: number; events: any[] }> {
    const response = await this.client.get('/analytics/top-events', { params });
    return response.data;
  }

  async getDashboard(): Promise<DashboardData> {
    const response = await this.client.get('/analytics/dashboard');
    return response.data;
  }

  // Health check
  async checkHealth(): Promise<{ status: string; timestamp: string }> {
    const response = await axios.get(`${API_BASE_URL}/health`);
    return response.data;
  }
}

export const api = new ApiService();
