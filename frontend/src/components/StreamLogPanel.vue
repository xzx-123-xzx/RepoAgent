<script setup lang="ts">
import type { LogEntry } from '../composables/useAnalyze'

defineProps<{ logs: LogEntry[]; progress: number; stageMessage: string }>()
</script>

<template>
  <div class="flex h-full flex-col rounded-xl border border-slate-700 bg-slate-900/80 shadow-xl">
    <div class="border-b border-slate-700 px-4 py-3">
      <div class="flex items-center justify-between">
        <h3 class="font-semibold text-slate-100">实时分析日志</h3>
        <span class="text-xs text-slate-400">{{ progress }}%</span>
      </div>
      <div class="mt-2 h-2 overflow-hidden rounded-full bg-slate-800">
        <div
          class="h-full rounded-full bg-gradient-to-r from-blue-500 to-cyan-400 transition-all duration-500"
          :style="{ width: `${progress}%` }"
        />
      </div>
      <p v-if="stageMessage" class="mt-2 text-xs text-slate-400">{{ stageMessage }}</p>
    </div>
    <div class="flex-1 overflow-y-auto p-4 font-mono text-xs leading-relaxed">
      <div v-if="!logs.length" class="text-slate-500">等待分析开始...</div>
      <div
        v-for="log in logs"
        :key="log.id"
        class="mb-2 rounded px-2 py-1"
        :class="{
          'text-slate-300': log.type === 'agent',
          'text-emerald-400': log.type === 'result' || log.type === 'system',
          'text-amber-300': log.type === 'progress',
          'text-red-400': log.type === 'error',
        }"
      >
        <span class="text-slate-500">[{{ log.timestamp }}]</span>
        <span v-if="log.agent" class="ml-1 text-blue-400">{{ log.agent }}</span>
        {{ log.content }}
      </div>
    </div>
  </div>
</template>
