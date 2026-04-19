export interface User {
  username: string
  role: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  user: User
}

export interface Work {
  id: string
  composer: string
  era?: string
  work_type?: string
  catalog_number?: string
  title: string
  movement_count: number
  canonical_string?: string
  summary?: string
}

export interface WorkList {
  total: number
  items: Work[]
}

export interface Movement {
  id: string
  work_id: string
  version_id?: string
  movement_number: number
  title?: string
  mood?: string
  description?: string
}

export interface Version {
  id: string
  work_id: string
  conductor?: string
  ensemble?: string
  soloists?: string
  year?: number
  label?: string
}

export interface AudioSegment {
  id: string
  file_id: string
  movement_id?: string
  start_time_ms: number
  end_time_ms?: number
  is_virtual: boolean
}

export interface SearchResult {
  type: 'semantic' | 'precise'
  results: Work[]
}

export interface ScanStatus {
  status: string
  total: number
  current: number
  message?: string
}
