export interface SSEBaseEvent {
  event: string
  task_id: string
  timestamp: string
}

export interface ProgressEvent extends SSEBaseEvent {
  event: 'progress'
  stage: string
  status: string
  message: string
  progress_percent: number
}

export interface AgentLogEvent extends SSEBaseEvent {
  event: 'agent_log'
  agent: string
  log_type: string
  content: string
  chunk_index: number
}

export interface StageResultEvent extends SSEBaseEvent {
  event: 'stage_result'
  agent: string
  result: Record<string, unknown>
}

export interface ReportCompleteEvent extends SSEBaseEvent {
  event: 'report_complete'
  report: FinalReport
}

export interface ErrorEvent extends SSEBaseEvent {
  event: 'error'
  code: number
  stage?: string
  message: string
  recoverable: boolean
}

export interface DoneEvent extends SSEBaseEvent {
  event: 'done'
  message: string
}

export type SSEEvent =
  | ProgressEvent
  | AgentLogEvent
  | StageResultEvent
  | ReportCompleteEvent
  | ErrorEvent
  | DoneEvent
  | SSEBaseEvent

export interface DimensionScore {
  score: number
  summary: string
  issues: string[]
}

export interface Recommendation {
  priority: string
  category: string
  action: string
}

export interface FinalReport {
  repo_name: string
  repo_url: string
  analyzed_at: string
  scores: {
    total_score: number
    code_score: number
    product_score: number
    weights: { code: number; product: number }
  }
  grade: string
  summary: string
  repo_metrics: Record<string, unknown>
  code_audit: {
    overall_code_score: number
    dimensions: Record<string, DimensionScore>
    highlights: string[]
    critical_issues: string[]
    recommendations: string[]
  }
  product_analysis: {
    overall_product_score: number
    dimensions: Record<string, DimensionScore>
    highlights: string[]
    critical_issues: string[]
    recommendations: string[]
  }
  top_recommendations: Recommendation[]
  verdict: string
}
