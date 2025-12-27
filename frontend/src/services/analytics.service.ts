import api from './api';

class AnalyticsService {
  async getAutomationMetrics(range: 'day' | 'week' | 'month' = 'week') {
    const response = await api.get('/analytics/automation-metrics', { params: { range } });
    return response.data;
  }

  async getProcessingTrends(period: string) {
    const response = await api.get('/analytics/trends', { params: { period } });
    return response.data;
  }

  async getDocumentStats() {
    const response = await api.get('/analytics/documents/stats');
    return response.data;
  }

  async getEntityStats() {
    const response = await api.get('/analytics/entities/stats');
    return response.data;
  }

  async getPerformanceMetrics() {
    const response = await api.get('/analytics/performance');
    return response.data;
  }

  async getCostSavings() {
    const response = await api.get('/analytics/cost-savings');
    return response.data;
  }

  async exportData(format: 'csv' | 'json', dateRange?: { from: string; to: string }) {
    const response = await api.post('/analytics/export', { format, ...dateRange }, {
      responseType: 'blob'
    });
    return response.data;
  }
}

export default new AnalyticsService();

