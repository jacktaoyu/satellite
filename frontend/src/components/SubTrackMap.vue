<template>
  <div class="subtrack-map">
    <canvas ref="canvasRef"></canvas>
    <div class="map-corner mc-tl"></div>
    <div class="map-corner mc-br"></div>
  </div>
</template>

<script setup>
// 卫星星下点轨迹小地图（等距圆柱投影 Canvas）：
// 从 Cesium CZML 实体回溯一个轨道周期采样位置，ECEF→ECI 按地球自转角修正后绘制。
// 自包含：由 rAF 驱动（约 4fps 刷新轨迹），实体切换/销毁时自动重建，组件卸载时停止。
import { onMounted, onUnmounted, ref, watch } from 'vue';
import * as Cesium from 'cesium';

const props = defineProps({
  entity: { type: Object, default: null },      // 当前选中卫星的 Cesium 实体
  viewer: { type: Object, default: null },      // Cesium viewer（取时钟）
  periodMin: { type: Number, default: 95 }      // 轨道周期（分钟），由 TLE 推算传入
});

const canvasRef = ref(null);
let rafId = null;
let lastDraw = 0;
let track = [];        // [{lat, lng}]
let curPos = null;     // {lat, lng}
const EARTH_SPIN = 7.2921159e-5; // 地球自转角速度 rad/s

// 从实体在指定时刻取惯性系位置并转为经纬度（修正地球自转）
function sampleAt(time) {
  try {
    // 统一转换到地固系(FIXED)，由 Cesium 处理惯性系↔地固系的高精度旋转
    const pos = props.entity.position.getValueInReferenceFrame
      ? props.entity.position.getValueInReferenceFrame(time, Cesium.ReferenceFrame.FIXED)
      : props.entity.position.getValue(time);
    if (!pos) return null;
    const carto = Cesium.Cartographic.fromCartesian(pos);
    return {
      lat: Cesium.Math.toDegrees(carto.latitude),
      lng: Cesium.Math.toDegrees(carto.longitude)
    };
  } catch (e) {
    return null;
  }
}

// 回溯一个轨道周期采样轨迹点
function rebuildTrack() {
  if (!props.entity || !props.viewer) { track = []; return; }
  const now = props.viewer.clock.currentTime;
  const periodSec = props.periodMin * 60;
  // 采样窗口对齐数据可用区间：仿真刚开始时向前采样，保证能画出完整一圈
  let start = Cesium.JulianDate.addSeconds(now, -periodSec, new Cesium.JulianDate());
  const avail = props.entity.availability;
  if (avail) {
    if (Cesium.JulianDate.lessThan(start, avail.start)) start = Cesium.JulianDate.clone(avail.start, start);
    const maxStart = Cesium.JulianDate.addSeconds(avail.stop, -periodSec, new Cesium.JulianDate());
    if (Cesium.JulianDate.greaterThan(start, maxStart)) start = maxStart;
  }
  const pts = [];
  const N = 90;
  for (let i = 0; i <= N; i++) {
    const t = Cesium.JulianDate.addSeconds(start, periodSec * i / N, new Cesium.JulianDate());
    const p = sampleAt(t);
    if (p) pts.push(p);
  }
  track = pts;
}

let lastRebuild = -1e9;
function draw(ts) {
  rafId = requestAnimationFrame(draw);
  // 轨迹每 30s 重建一次，画面每 250ms 刷新（当前点移动）
  if (ts - lastRebuild > 30000) { rebuildTrack(); lastRebuild = ts; }
  if (ts - lastDraw < 250) return;
  lastDraw = ts;

  const canvas = canvasRef.value;
  if (!canvas) return;
  const parent = canvas.parentElement;
  const W = canvas.width = parent.clientWidth;
  const H = canvas.height = parent.clientHeight;
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, W, H);

  const toXY = (lat, lng) => [(lng + 180) / 360 * W, (90 - lat) / 180 * H];

  // 网格线（经纬各 30°）
  ctx.strokeStyle = 'rgba(0, 220, 255, 0.08)';
  ctx.lineWidth = 1;
  for (let lng = -150; lng <= 150; lng += 30) {
    const [x] = toXY(0, lng);
    ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke();
  }
  for (let lat = -60; lat <= 60; lat += 30) {
    const [, y] = toXY(lat, 0);
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke();
  }
  // 赤道与主经线略亮
  ctx.strokeStyle = 'rgba(0, 220, 255, 0.16)';
  const [, eqY] = toXY(0, 0);
  ctx.beginPath(); ctx.moveTo(0, eqY); ctx.lineTo(W, eqY); ctx.stroke();

  // 当前位置（每帧实时采样）
  if (props.entity && props.viewer) {
    curPos = sampleAt(props.viewer.clock.currentTime);
  }

  // 轨迹线：分段绘制以处理 ±180° 跳变，尾段（接近当前）更亮
  if (track.length > 1) {
    for (let i = 1; i < track.length; i++) {
      const a = track[i - 1], b = track[i];
      if (Math.abs(a.lng - b.lng) > 180) continue; // 跨日界线跳段
      const [x1, y1] = toXY(a.lat, a.lng);
      const [x2, y2] = toXY(b.lat, b.lng);
      const t = i / track.length; // 0=最旧 → 1=最新
      ctx.strokeStyle = `rgba(0, 240, 255, ${0.12 + 0.55 * t})`;
      ctx.lineWidth = 1.2;
      ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke();
    }
  }

  // 当前星下点：光点 + 扩散环
  if (curPos) {
    const [x, y] = toXY(curPos.lat, curPos.lng);
    const pulse = (ts % 2000) / 2000;
    ctx.beginPath();
    ctx.arc(x, y, 3 + pulse * 7, 0, Math.PI * 2);
    ctx.strokeStyle = `rgba(0, 240, 255, ${0.7 * (1 - pulse)})`;
    ctx.lineWidth = 1.5;
    ctx.stroke();
    ctx.beginPath();
    ctx.arc(x, y, 3, 0, Math.PI * 2);
    ctx.fillStyle = '#00f0ff';
    ctx.shadowColor = '#00f0ff';
    ctx.shadowBlur = 8;
    ctx.fill();
    ctx.shadowBlur = 0;
  }
}

watch(() => props.entity, () => {
  track = [];
  lastRebuild = -1e9;
});

onMounted(() => { rafId = requestAnimationFrame(draw); });
onUnmounted(() => { if (rafId) cancelAnimationFrame(rafId); });
</script>

<style scoped>
.subtrack-map {
  position: relative;
  height: 110px;
  margin: 4px 10px 10px;
  border: 1px solid rgba(0, 220, 255, 0.25);
  border-radius: 3px;
  background: rgba(3, 10, 24, 0.5);
  overflow: hidden;
  flex-shrink: 0;
}
canvas { width: 100%; height: 100%; display: block; }
/* HUD 对角角标 */
.map-corner {
  position: absolute;
  width: 8px;
  height: 8px;
  pointer-events: none;
}
.mc-tl { top: 0; left: 0; border-top: 2px solid rgba(0, 240, 255, 0.7); border-left: 2px solid rgba(0, 240, 255, 0.7); }
.mc-br { bottom: 0; right: 0; border-bottom: 2px solid rgba(0, 240, 255, 0.7); border-right: 2px solid rgba(0, 240, 255, 0.7); }
</style>
