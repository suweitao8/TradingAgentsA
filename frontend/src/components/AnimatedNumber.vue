<template>
  <span>{{ display }}</span>
</template>

<script setup lang="ts">
/**
 * 数字滚动动画组件
 * 当 value 变化时，显示值用 tween 平滑过渡到目标值（不瞬跳）。
 * 用于股票价格、涨跌幅等需要平滑过渡的场景。
 */
import { computed, ref, watch } from 'vue'
import { useTransition } from '@vueuse/core'

const props = withDefaults(defineProps<{
  value: number
  duration?: number  // 过渡时长 ms，默认 600
  decimals?: number  // 保留小数位，默认 2
  prefix?: string    // 前缀（如 +）
  suffix?: string    // 后缀（如 %）
}>(), {
  duration: 600,
  decimals: 2,
  prefix: '',
  suffix: '',
})

// useTransition 的 source（起始值用当前 value 避免首次从 0 滚动）
const source = ref(props.value)

const output = useTransition(source, {
  duration: props.duration,
  transition: [0.25, 0.1, 0.25, 1], // easeInOut 类似
})

// value 变化时驱动过渡
watch(() => props.value, (newVal) => {
  if (Number.isFinite(newVal)) {
    source.value = newVal
  }
})

const display = computed(() => {
  const n = output.value
  if (!Number.isFinite(n)) return '-'
  return `${props.prefix}${n.toFixed(props.decimals)}${props.suffix}`
})
</script>
