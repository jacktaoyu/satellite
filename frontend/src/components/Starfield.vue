<template>
  <canvas ref="canvasRef" class="starfield-canvas" :style="{ opacity }"></canvas>
</template>

<script setup>
// 通用星空粒子背景组件：Canvas 绘制，星星闪烁 + 缓慢漂移 + 偶发流星
// 用法：<Starfield :density="1" :meteor="true" /> 覆盖在父容器（position:relative）之上
import { onMounted, onUnmounted, ref } from 'vue';

const props = defineProps({
  density: { type: Number, default: 1 },      // 星星密度系数（1 ≈ 每 9000px² 一颗）
  meteor: { type: Boolean, default: true },   // 是否偶发流星
  opacity: { type: Number, default: 1 }       // 整体透明度
});

const canvasRef = ref(null);
let ctx = null;
let rafId = null;
let stars = [];
let meteors = [];
let W = 0, H = 0;
let resizeObserver = null;

function initStars() {
  const count = Math.round((W * H) / 9000 * props.density);
  stars = Array.from({ length: count }, () => ({
    x: Math.random() * W,
    y: Math.random() * H,
    r: Math.random() * 1.3 + 0.3,
    // 基准透明度与闪烁相位/速度
    baseA: Math.random() * 0.5 + 0.25,
    phase: Math.random() * Math.PI * 2,
    speed: Math.random() * 0.015 + 0.005,
    // 缓慢漂移方向
    dx: (Math.random() - 0.5) * 0.06,
    dy: (Math.random() - 0.5) * 0.04,
    // 少量暖色星，增加层次
    warm: Math.random() < 0.12
  }));
}

function spawnMeteor() {
  const fromLeft = Math.random() < 0.5;
  meteors.push({
    x: fromLeft ? Math.random() * W * 0.4 : W * 0.5 + Math.random() * W * 0.5,
    y: Math.random() * H * 0.35,
    vx: (fromLeft ? 1 : -1) * (5 + Math.random() * 4),
    vy: 2.5 + Math.random() * 2,
    life: 1
  });
}

let tickCount = 0;
function tick() {
  tickCount++;
  ctx.clearRect(0, 0, W, H);

  // 星星：闪烁 + 漂移（出界回绕）
  for (const s of stars) {
    s.phase += s.speed;
    s.x += s.dx; s.y += s.dy;
    if (s.x < 0) s.x += W; if (s.x > W) s.x -= W;
    if (s.y < 0) s.y += H; if (s.y > H) s.y -= H;
    const a = s.baseA * (0.55 + 0.45 * Math.sin(s.phase));
    ctx.beginPath();
    ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
    ctx.fillStyle = s.warm
      ? `rgba(255, 214, 160, ${a})`
      : `rgba(180, 225, 255, ${a})`;
    ctx.fill();
  }

  // 流星：约每 6~10 秒一颗
  if (props.meteor && tickCount % 60 === 0 && Math.random() < 0.22 && meteors.length < 2) {
    spawnMeteor();
  }
  for (let i = meteors.length - 1; i >= 0; i--) {
    const m = meteors[i];
    m.x += m.vx; m.y += m.vy; m.life -= 0.02;
    if (m.life <= 0 || m.y > H) { meteors.splice(i, 1); continue; }
    const tailX = m.x - m.vx * 12;
    const tailY = m.y - m.vy * 12;
    const grad = ctx.createLinearGradient(m.x, m.y, tailX, tailY);
    grad.addColorStop(0, `rgba(160, 235, 255, ${0.9 * m.life})`);
    grad.addColorStop(1, 'rgba(160, 235, 255, 0)');
    ctx.strokeStyle = grad;
    ctx.lineWidth = 1.4;
    ctx.beginPath();
    ctx.moveTo(m.x, m.y);
    ctx.lineTo(tailX, tailY);
    ctx.stroke();
  }

  rafId = requestAnimationFrame(tick);
}

onMounted(() => {
  const canvas = canvasRef.value;
  const parent = canvas.parentElement;
  ctx = canvas.getContext('2d');
  const resize = () => {
    W = canvas.width = parent.clientWidth;
    H = canvas.height = parent.clientHeight;
    initStars();
  };
  resize();
  resizeObserver = new ResizeObserver(resize);
  resizeObserver.observe(parent);
  rafId = requestAnimationFrame(tick);
});

onUnmounted(() => {
  if (rafId) cancelAnimationFrame(rafId);
  if (resizeObserver) resizeObserver.disconnect();
});
</script>

<style scoped>
.starfield-canvas {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 0;
}
</style>
