<script setup lang="ts">
import { ref } from 'vue'
import UrlInput from '../components/UrlInput.vue'
import StreamLogPanel from '../components/StreamLogPanel.vue'
import ReportDashboard from '../components/ReportDashboard.vue'
import { useAnalyze } from '../composables/useAnalyze'

const repoUrl = ref('https://github.com/fastapi/fastapi')
const { loading, progress, stageMessage, logs, report, error, analyze } = useAnalyze()

function handleSubmit(url: string) {
  if (url.trim()) analyze(url.trim())
}
</script>

<template>
  <div class="min-h-screen bg-slate-950">
    <header class="border-b border-slate-800 bg-slate-900/50 backdrop-blur">
      <div class="mx-auto flex max-w-7xl items-center justify-between px-4 py-4">
        <div>
          <h1 class="text-2xl font-bold tracking-tight text-white">RepoAgent</h1>
          <p class="text-sm text-slate-400">GitHub 仓库智能体检 · 三 Agent 流水线 · SSE 实时推送</p>
        </div>
      </div>
    </header>

    <main class="mx-auto max-w-7xl space-y-6 px-4 py-6">
      <UrlInput v-model="repoUrl" :loading="loading" @submit="handleSubmit" />

      <div v-if="error" class="rounded-lg border border-red-500/50 bg-red-500/10 px-4 py-3 text-sm text-red-300">
        {{ error }}
      </div>

      <div class="grid gap-6 lg:grid-cols-2">
        <StreamLogPanel :logs="logs" :progress="progress" :stage-message="stageMessage" class="min-h-[420px]" />
        <div class="min-h-[420px] overflow-y-auto rounded-xl border border-dashed border-slate-700 p-4">
          <ReportDashboard v-if="report" :report="report" />
          <div v-else class="flex h-full items-center justify-center text-slate-500">
            分析完成后在此展示体检报告
          </div>
        </div>
      </div>
    </main>
  </div>
</template>
