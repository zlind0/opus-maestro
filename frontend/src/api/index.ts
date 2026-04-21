import type {
  TokenResponse,
  Work,
  WorkList,
  Movement,
  Version,
  AudioSegment,
  SearchResult,
  ScanStatus,
} from '@/types'

const BASE = '/api/v1'

function getToken(): string | null {
  return localStorage.getItem('token')
}

async function request<T>(url: string, options: RequestInit = {}): Promise<T> {
  const token = getToken()
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string> || {}),
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json'
  }

  const response = await fetch(url, { ...options, headers })
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }))
    throw new Error(error.detail?.detail || error.detail || response.statusText)
  }
  return response.json()
}

// Auth
export async function login(username: string, password: string): Promise<TokenResponse> {
  const body = new URLSearchParams({ username, password })
  const response = await fetch(`${BASE}/auth/token`, {
    method: 'POST',
    body,
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  })
  if (!response.ok) {
    throw new Error('登录失败')
  }
  return response.json()
}

export async function register(username: string, password: string): Promise<{ username: string; role: string }> {
  const body = new URLSearchParams({ username, password })
  const response = await fetch(`${BASE}/auth/register`, {
    method: 'POST',
    body,
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  })
  if (!response.ok) {
    const err = await response.json().catch(() => ({}))
    throw new Error(err.detail?.detail || '注册失败')
  }
  return response.json()
}

export function getMe() {
  return request<{ username: string; role: string }>(`${BASE}/auth/me`)
}

// Works
export function getWorks(params?: { limit?: number; offset?: number; composer?: string; era?: string; work_type?: string }) {
  const query = new URLSearchParams()
  if (params?.limit) query.set('limit', String(params.limit))
  if (params?.offset) query.set('offset', String(params.offset))
  if (params?.composer) query.set('composer', params.composer)
  if (params?.era) query.set('era', params.era)
  if (params?.work_type) query.set('work_type', params.work_type)
  return request<WorkList>(`${BASE}/works?${query}`)
}

export function getWork(id: string) {
  return request<Work>(`${BASE}/works/${id}`)
}

export function getWorkMovements(workId: string) {
  return request<Movement[]>(`${BASE}/works/${workId}/movements`)
}

export function getWorkVersions(workId: string) {
  return request<Version[]>(`${BASE}/works/${workId}/versions`)
}

// Search
export function search(params: { query?: string; composer?: string; era?: string; work_type?: string; limit?: number }) {
  const q = new URLSearchParams()
  if (params.query) q.set('query', params.query)
  if (params.composer) q.set('composer', params.composer)
  if (params.era) q.set('era', params.era)
  if (params.work_type) q.set('work_type', params.work_type)
  if (params.limit) q.set('limit', String(params.limit))
  return request<SearchResult>(`${BASE}/search?${q}`)
}

// Audio
export function getMovementSegments(movementId: string) {
  return request<AudioSegment[]>(`${BASE}/audio/movements/${movementId}/segments`)
}

export function getAudioStreamUrl(segmentId: string) {
  const token = getToken()
  return `${BASE}/audio/segments/${segmentId}?token=${token}`
}

// Recommendations
export function getRecommendations(movementId: string, limit: number = 5) {
  return request<Work[]>(`${BASE}/recommend/${movementId}?limit=${limit}`)
}

// Scan
export function triggerScan(mode: 'incremental' | 'with_unknowns' | 'full' = 'incremental') {
  const url = `${BASE}/scan?mode=${encodeURIComponent(mode)}`
  return request<{ message: string }>(url, { method: 'POST' })
}

export function getScanStatus() {
  return request<ScanStatus>(`${BASE}/scan/status`)
}
