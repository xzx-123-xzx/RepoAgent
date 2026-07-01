<script setup lang="ts">
import type { DimensionScore } from '../types/report'

defineProps<{ title: string; dimensions: Record<string, DimensionScore> }>()

const labels: Record<string, string> = {
  directory_structure: '目录规范性',
  architecture_quality: '架构合理性',
  tech_debt: '技术债务',
  dependency_risk: '依赖风险',
  code_standards: '代码规范',
  documentation: '文档完整性',
  practicality: '项目实用性',
  open_source_activity: '开源活跃度',
  maintainability: '维护可持续性',
  popularity: '传播度',
}
</script>

<template>
  <div class="rounded-xl border border-slate-700 bg-slate-900/80 p-4">
    <h4 class="mb-3 font-semibold text-slate-100">{{ title }}</h4>
    <div class="space-y-3">
      <div v-for="(dim, key) in dimensions" :key="key">
        <div class="mb-1 flex justify-between text-xs">
          <span class="text-slate-300">{{ labels[key] || key }}</span>
          <span class="font-mono text-blue-400">{{ dim.score }}</span>
        </div>
        <div class="h-1.5 overflow-hidden rounded-full bg-slate-800">
          <div class="h-full rounded-full bg-blue-500" :style="{ width: `${dim.score}%` }" />
        </div>
        <p class="mt-1 text-xs text-slate-500">{{ dim.summary }}</p>
      </div>
    </div>
  </div>
</template>
