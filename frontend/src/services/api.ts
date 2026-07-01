const API_BASE = import.meta.env.VITE_API_BASE || ''

export interface AnalyzeResponse {
  task_id: string
  stream_url: string
  status: string
  created_at: string
}

export async function startAnalysis(repoUrl: string): Promise<AnalyzeResponse> {
  const res = await fetch(`${API_BASE}/api/v1/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ repo_url: repoUrl }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || err.message || '分析请求失败')
  }
  return res.json()
}

export function createSSEConnection(
  streamUrl: string,
  onEvent: (eventType: string, data: Record<string, unknown>) => void,
  onError: (err: Event) => void,
): EventSource {
  const url = streamUrl.startsWith('http') ? streamUrl : `${API_BASE}${streamUrl}`
  const es = new EventSource(url)

  const handlers = ['connected', 'progress', 'agent_log', 'stage_result', 'report_complete', 'cache_hit', 'error', 'done']
  handlers.forEach((type) => {
    es.addEventListener(type, (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data)
        onEvent(type, data)
      } catch {
        onEvent(type, { raw: e.data })
      }
    })
  })

  es.onerror = onError
  return es
}
