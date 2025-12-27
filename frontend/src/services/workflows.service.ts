import api from './api';
import { Workflow } from '../types';

class WorkflowsService {
  async getAll(): Promise<Workflow[]> {
    const response = await api.get('/workflows');
    return response.data.workflows || [];
  }

  async getById(id: string): Promise<Workflow> {
    const response = await api.get(`/workflows/${id}`);
    return response.data;
  }

  async create(workflow: Partial<Workflow>): Promise<Workflow> {
    const response = await api.post('/workflows', workflow);
    return response.data;
  }

  async update(id: string, workflow: Partial<Workflow>): Promise<Workflow> {
    const response = await api.put(`/workflows/${id}`, workflow);
    return response.data;
  }

  async delete(id: string): Promise<void> {
    await api.delete(`/workflows/${id}`);
  }

  async activate(id: string): Promise<Workflow> {
    const response = await api.post(`/workflows/${id}/activate`);
    return response.data;
  }

  async pause(id: string): Promise<Workflow> {
    const response = await api.post(`/workflows/${id}/pause`);
    return response.data;
  }

  async getExecutions(id: string) {
    const response = await api.get(`/workflows/${id}/executions`);
    return response.data.executions || [];
  }

  async getStats(id: string) {
    const response = await api.get(`/workflows/${id}/stats`);
    return response.data;
  }
}

export default new WorkflowsService();

