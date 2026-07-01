<script setup lang="ts">
import type { FinalReport } from '../types/report'
import ScoreGauge from './ScoreGauge.vue'
import DimensionCard from './DimensionCard.vue'
import RecommendationList from './RecommendationList.vue'

defineProps<{ report: FinalReport }>()
</script>

<template>
  <div class="space-y-6">
    <div class="rounded-xl border border-slate-700 bg-gradient-to-br from-slate-900 to-slate-800 p-6">
      <div class="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 class="text-xl font-bold text-white">{{ report.repo_name }}</h2>
          <a :href="report.repo_url" target="_blank" class="text-sm text-blue-400 hover:underline">{{ report.repo_url }}</a>
          <p class="mt-2 text-sm text-slate-300">{{ report.summary }}</p>
        </div>
        <div class="rounded-lg border border-slate-600 px-4 py-2 text-center">
          <div class="text-2xl font-bold text-emerald-400">{{ report.grade }}</div>
          <div class="text-xs text-slate-400">综合等级</div>
        </div>
      </div>
      <div class="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div class="rounded-lg bg-slate-950/60 p-3 text-center">
          <div class="text-lg font-semibold">{{ report.repo_metrics.stars }}</div>
          <div class="text-xs text-slate-400">Stars</div>
        </div>
        <div class="rounded-lg bg-slate-950/60 p-3 text-center">
          <div class="text-lg font-semibold">{{ report.repo_metrics.forks }}</div>
          <div class="text-xs text-slate-400">Forks</div>
        </div>
        <div class="rounded-lg bg-slate-950/60 p-3 text-center">
          <div class="text-lg font-semibold">{{ report.repo_metrics.primary_language }}</div>
          <div class="text-xs text-slate-400">主语言</div>
        </div>
        <div class="rounded-lg bg-slate-950/60 p-3 text-center">
          <div class="text-lg font-semibold">{{ report.repo_metrics.contributors_count }}</div>
          <div class="text-xs text-slate-400">贡献者</div>
        </div>
      </div>
    </div>

    <div class="grid gap-4 sm:grid-cols-3">
      <ScoreGauge :score="report.scores.total_score" label="综合总分" />
      <ScoreGauge :score="report.scores.code_score" label="代码维度" color="#8b5cf6" />
      <ScoreGauge :score="report.scores.product_score" label="产品维度" color="#06b6d4" />
    </div>

    <div class="grid gap-4 lg:grid-cols-2">
      <DimensionCard title="代码审计结论" :dimensions="report.code_audit.dimensions" />
      <DimensionCard title="产品价值分析" :dimensions="report.product_analysis.dimensions" />
    </div>

    <div class="grid gap-4 lg:grid-cols-2">
      <div class="rounded-xl border border-slate-700 bg-slate-900/80 p-4">
        <h4 class="mb-2 font-semibold">代码亮点 & 问题</h4>
        <ul class="mb-3 list-inside list-disc text-sm text-emerald-400">
          <li v-for="(h, i) in report.code_audit.highlights" :key="'ch'+i">{{ h }}</li>
        </ul>
        <ul class="list-inside list-disc text-sm text-red-400">
          <li v-for="(c, i) in report.code_audit.critical_issues" :key="'ci'+i">{{ c }}</li>
        </ul>
      </div>
      <div class="rounded-xl border border-slate-700 bg-slate-900/80 p-4">
        <h4 class="mb-2 font-semibold">产品亮点 & 问题</h4>
        <ul class="mb-3 list-inside list-disc text-sm text-emerald-400">
          <li v-for="(h, i) in report.product_analysis.highlights" :key="'ph'+i">{{ h }}</li>
        </ul>
        <ul class="list-inside list-disc text-sm text-red-400">
          <li v-for="(c, i) in report.product_analysis.critical_issues" :key="'pi'+i">{{ c }}</li>
        </ul>
      </div>
    </div>

    <RecommendationList :recommendations="report.top_recommendations" />

    <div class="rounded-xl border border-slate-700 bg-slate-900/80 p-4">
      <h4 class="mb-2 font-semibold text-slate-100">综合结论</h4>
      <p class="text-sm leading-relaxed text-slate-300">{{ report.verdict }}</p>
    </div>
  </div>
</template>
