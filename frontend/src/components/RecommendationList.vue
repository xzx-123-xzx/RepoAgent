<script setup lang="ts">
import type { Recommendation } from '../types/report'

defineProps<{ recommendations: Recommendation[] }>()

const priorityClass: Record<string, string> = {
  high: 'border-red-500/50 bg-red-500/10 text-red-300',
  medium: 'border-amber-500/50 bg-amber-500/10 text-amber-200',
  low: 'border-slate-500/50 bg-slate-500/10 text-slate-300',
}
</script>

<template>
  <div class="rounded-xl border border-slate-700 bg-slate-900/80 p-4">
    <h4 class="mb-3 font-semibold text-slate-100">优化建议清单</h4>
    <ul class="space-y-2">
      <li
        v-for="(item, idx) in recommendations"
        :key="idx"
        class="rounded-lg border px-3 py-2 text-sm"
        :class="priorityClass[item.priority] || priorityClass.medium"
      >
        <span class="mr-2 text-xs uppercase opacity-70">{{ item.priority }}</span>
        <span class="mr-2 text-xs opacity-70">[{{ item.category }}]</span>
        {{ item.action }}
      </li>
    </ul>
  </div>
</template>
