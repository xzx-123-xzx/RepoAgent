import { ref } from 'vue'
import { createSSEConnection, startAnalysis } from '../services/api'
import type { FinalReport } from '../types/report'

export interface LogEntry {
  id: number
  agent?: string
  type: string
  content: string
  timestamp: string
}

export function useAnalyze() {
  const loading = ref(false)
  const progress = ref(0)
  const stageMessage = ref('')
  const logs = ref<LogEntry[]>([])
  const report = ref<FinalReport | null>(null)
  const error = ref('')
  let logId = 0
  let eventSource: EventSource | null = null

  function addLog(type: string, content: string, agent?: string) {
    logs.value.push({
      id: logId++,
      type,
      content,
      agent,
      timestamp: new Date().toLocaleTimeString(),
    })
  }

  function closeStream() {
    eventSource?.close()
    eventSource = null
  }

  async function analyze(repoUrl: string) {
    loading.value = true
    error.value = ''
    report.value = null
    logs.value = []
    progress.value = 0
    stageMessage.value = ''
    closeStream()

    try {
      const { stream_url } = await startAnalysis(repoUrl)
      addLog('system', '分析任务已创建，正在连接 SSE...')

      eventSource = createSSEConnection(
        stream_url,
        (eventType, data) => {
          if (eventType === 'connected') {
            addLog('system', String(data.message || 'SSE 已连接'))
          } else if (eventType === 'progress') {
            progress.value = Number(data.progress_percent || 0)
            stageMessage.value = String(data.message || '')
            addLog('progress', `[${data.stage}] ${data.message}`)
          } else if (eventType === 'agent_log') {
            addLog('agent', String(data.content), String(data.agent))
          } else if (eventType === 'stage_result') {
            addLog('result', `${data.agent} 阶段分析完成`, String(data.agent))
          } else if (eventType === 'report_complete') {
            report.value = data.report as FinalReport
            progress.value = 100
            addLog('system', '最终报告已生成')
          } else if (eventType === 'cache_hit') {
            addLog('system', String(data.message || '命中缓存'))
          } else if (eventType === 'error') {
            error.value = String(data.message || '分析失败')
            addLog('error', error.value)
          } else if (eventType === 'done') {
            loading.value = false
            closeStream()
          }
        },
        () => {
          if (loading.value) {
            error.value = error.value || 'SSE 连接中断'
            loading.value = false
          }
        },
      )
    } catch (e) {
      error.value = e instanceof Error ? e.message : '未知错误'
      loading.value = false
    }
  }

  return { loading, progress, stageMessage, logs, report, error, analyze }
}
