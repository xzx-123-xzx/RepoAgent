<script setup lang="ts">
defineProps<{ modelValue: string; loading?: boolean; disabled?: boolean }>()
defineEmits<{ submit: [url: string]; 'update:modelValue': [value: string] }>()
</script>

<template>
  <div class="rounded-xl border border-slate-700 bg-slate-900/80 p-6 shadow-xl">
    <label class="mb-2 block text-sm font-medium text-slate-300">GitHub 仓库地址</label>
    <div class="flex flex-col gap-3 sm:flex-row">
      <input
        :value="modelValue"
        type="url"
        placeholder="https://github.com/owner/repo（必须是仓库，不是用户主页）"
        class="flex-1 rounded-lg border border-slate-600 bg-slate-950 px-4 py-3 text-sm outline-none ring-accent focus:ring-2"
        :disabled="loading || disabled"
        @input="$emit('update:modelValue', ($event.target as HTMLInputElement).value)"
        @keyup.enter="$emit('submit', modelValue)"
      />
      <button
        class="rounded-lg bg-accent px-6 py-3 text-sm font-semibold text-white transition hover:bg-blue-600 disabled:cursor-not-allowed disabled:opacity-50"
        :disabled="loading || disabled || !modelValue.trim()"
        @click="$emit('submit', modelValue)"
      >
        {{ loading ? '分析中...' : '开始分析' }}
      </button>
    </div>
  </div>
</template>
