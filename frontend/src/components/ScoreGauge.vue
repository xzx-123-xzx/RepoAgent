<script setup lang="ts">
defineProps<{ score: number; label: string; color?: string }>()

function scoreColor(score: number) {
  if (score >= 90) return '#22c55e'
  if (score >= 70) return '#3b82f6'
  if (score >= 50) return '#f59e0b'
  return '#ef4444'
}
</script>

<template>
  <div class="flex flex-col items-center rounded-xl border border-slate-700 bg-slate-900/80 p-4">
    <svg viewBox="0 0 120 70" class="h-24 w-40">
      <path d="M10,60 A50,50 0 0 1 110,60" fill="none" stroke="#334155" stroke-width="8" stroke-linecap="round" />
      <path
        d="M10,60 A50,50 0 0 1 110,60"
        fill="none"
        :stroke="color || scoreColor(score)"
        stroke-width="8"
        stroke-linecap="round"
        :stroke-dasharray="157"
        :stroke-dashoffset="157 - (score / 100) * 157"
      />
      <text x="60" y="55" text-anchor="middle" fill="white" font-size="18" font-weight="bold">{{ score }}</text>
    </svg>
    <p class="text-sm text-slate-300">{{ label }}</p>
  </div>
</template>
