import { api } from './client';

export interface Work {
  work_id: string;
  composer: string | null;
  era: string | null;
  work_type: string | null;
  catalog_number: string | null;
  title: string | null;
  movement_count: number | null;
  canonical_string: string | null;
  language: string;
  metadata: any;
  movements: Movement[];
}

export interface Movement {
  movement_id: string;
  movement_number: number;
  movement_title: string | null;
  emotion: string | null;
  description: string | null;
}

export class MusicAPI {
  static async search(query: string, lang?: string): Promise<Work[]> {
    const params = new URLSearchParams({ query });
    if (lang) params.append('lang', lang);
    const response = await api.get(`/api/v1/search/?${params}`);
    return response.data;
  }

  static async listWorks(limit = 50, offset = 0): Promise<Work[]> {
    const response = await api.get('/api/v1/works', {
      params: { limit, offset },
    });
    return response.data;
  }

  static async getWork(workId: string): Promise<Work> {
    const response = await api.get(`/api/v1/works/${workId}`);
    return response.data;
  }

  static async getMovements(workId: string): Promise<Movement[]> {
    const response = await api.get(`/api/v1/works/${workId}/movements`);
    return response.data;
  }

  static async getRecommendations(workId: string, lang?: string): Promise<Work[]> {
    const params = new URLSearchParams();
    if (lang) params.append('lang', lang);
    const response = await api.get(`/api/v1/works/${workId}/recommendations?${params}`);
    return response.data;
  }

  static async streamSegment(segmentId: string, format = 'flac'): Promise<Blob> {
    const response = await api.get(`/api/v1/audio/segments/${segmentId}`, {
      params: { target_format: format },
      responseType: 'blob',
    });
    return response.data;
  }

  static async getSegmentUrl(segmentId: string, format = 'flac'): Promise<string> {
    const token = localStorage.getItem('token') || '';
    return `${api.defaults.baseURL}/api/v1/audio/segments/${segmentId}?target_format=${format}&Authorization=Bearer%20${token}`;
  }
}
