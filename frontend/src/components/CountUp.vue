<template>
  <span class="count-up">{{ display }}</span>
</template>

<script setup>
// 数字滚动组件：数值变化时从旧值平滑滚动到新值
// 用法：<CountUp :value="42" /> 或 <CountUp :value="95.6" :decimals="1" suffix="%" />
import { ref, watch, onUnmounted } from 'vue';

const props = defineProps({
  value: { type: [Number, String], default: 0 },
  duration: { type: Number, default: 800 },   // 滚动时长 ms
  decimals: { type: Number, default: 0 },
  suffix: { type: String, default: '' }
});

const display = ref('--');
let rafId = null;
let currentVal = null; // 当前已渲染的数值（首次为 null → 直接显示）

function easeOut(t) { return 1 - Math.pow(1 - t, 3); }

function format(v) {
  return v.toFixed(props.decimals) + props.suffix;
}

function animateTo(target) {
  // 非数值占位符（如 '--' 或解析失败的 NaN）：直接显示占位符，不进入滚动逻辑
  if (typeof target !== 'number' || isNaN(target)) {
    display.value = '--';
    currentVal = null;
    return;
  }
  // 首次渲染或非数值切换时直接显示，避免 '--' → 0 → target 的怪异滚动
  if (currentVal === null) {
    currentVal = target;
    display.value = format(target);
    return;
  }
  const from = currentVal;
  const diff = target - from;
  if (diff === 0) return;
  if (rafId) cancelAnimationFrame(rafId);
  const start = performance.now();
  const step = (now) => {
    const t = Math.min(1, (now - start) / props.duration);
    const v = from + diff * easeOut(t);
    display.value = format(v);
    if (t < 1) {
      rafId = requestAnimationFrame(step);
    } else {
      currentVal = target;
      rafId = null;
    }
  };
  rafId = requestAnimationFrame(step);
}

watch(() => props.value, (v) => animateTo(typeof v === 'string' ? parseFloat(v) : v), { immediate: true });

onUnmounted(() => { if (rafId) cancelAnimationFrame(rafId); });
</script>

<style scoped>
.count-up {
  font-variant-numeric: tabular-nums;
}
</style>
