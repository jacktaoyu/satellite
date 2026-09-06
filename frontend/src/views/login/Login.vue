<template>
  <div class="login-container">
      <!-- 星空粒子层（最底层） -->
      <Starfield :density="1.2" :opacity="0.7" />
      <!-- Cesium 3D 地球动态背景 -->
      <div ref="earthBg" class="earth-bg"></div>
      <!-- 地球外围轨道装饰环 -->
      <div class="orbit-ring ring-outer"><i class="orbit-sat"></i></div>
      <div class="orbit-ring ring-inner"></div>
      <!-- 背景装饰光斑 -->
      <div class="glow-orb orb-1"></div>
      <div class="glow-orb orb-2"></div>

      <!-- 左上角返回首页 -->
      <div class="back-portal" @click="$router.push('/portal')">← 返回首页</div>

      <!-- 左侧标语区 -->
      <div class="intro-panel">
          <div class="intro-badge">SATELLITE CLUSTER COLLABORATIVE PLATFORM</div>
          <h1 class="intro-title">智能星簇<br/><span class="intro-title-grad">协同运行验证系统</span></h1>
          <p class="intro-desc">三维组网可视化 · 任务协同规划 · 运行效能评估</p>
          <div class="intro-metrics">
              <div class="im-item"><i class="im-dot"></i>实时态势监控</div>
              <div class="im-item"><i class="im-dot"></i>多星协同规划</div>
              <div class="im-item"><i class="im-dot"></i>算法效能评估</div>
          </div>
      </div>

      <LoginCard />
  </div>
</template>

<script>
import * as Cesium from "cesium";
import LoginCard from "./LoginCard.vue";
import Starfield from "@/components/Starfield.vue";

export default {
  name: "login",
  components: { LoginCard, Starfield },

  mounted() {
      // 初始化 Cesium 3D 地球动态背景
      const viewer = new Cesium.Viewer(this.$refs.earthBg, {
          baseLayer: false, // 禁用默认 Ion 底图（避免 401 报错），底图改用下方高德瓦片
          animation: false,
          timeline: false,
          geocoder: false,
          homeButton: false,
          sceneModePicker: false,
          baseLayerPicker: false,
          navigationHelpButton: false,
          fullscreenButton: false,
          infoBox: false,
          selectionIndicator: false,
          contextOptions: {
              webgl: { alpha: true }
          }
      });
      // 去掉版权信息
      viewer._cesiumWidget._creditContainer.style.display = "none";
      // 高德卫星影像图层（与卫星网络页保持一致，避免默认图层加载失败）
      viewer.imageryLayers.removeAll();
      viewer.imageryLayers.addImageryProvider(new Cesium.UrlTemplateImageryProvider({
          url: 'https://webst0{s}.is.autonavi.com/appmaptile?style=6&x={x}&y={y}&z={z}',
          subdomains: ['1', '2', '3', '4']
      }));
      // 禁用鼠标交互，作为纯展示背景
      const controller = viewer.scene.screenSpaceCameraController;
      controller.enableRotate = false;
      controller.enableTranslate = false;
      controller.enableZoom = false;
      controller.enableTilt = false;
      controller.enableLook = false;
      // 开启昼夜光照效果
      viewer.scene.globe.enableLighting = true;
      // 初始视角（相机高度配合 40vw 正方形容器，地球直径约为屏宽的 18.6%，只随屏宽缩放）
      viewer.camera.setView({
          destination: Cesium.Cartesian3.fromDegrees(105, 20, 20000000)
      });
      // 缓慢自转
      viewer.clock.onTick.addEventListener(() => {
          viewer.scene.camera.rotate(Cesium.Cartesian3.UNIT_Z, -0.0002);
      });
      this.viewer = viewer;
  },

  beforeUnmount() {
      if (this.viewer) {
          this.viewer.destroy();
          this.viewer = null;
      }
  }
}
</script>

<style scoped>
.login-container {
  background: #050b1a; /* Cesium 地球背景加载前的底色 */
  display: flex;
  justify-content: center; /* 内容收拢为居中带，避免超宽屏上元素过于分散 */
  align-items: center;
  gap: clamp(240px, 30vw, 700px); /* 间隙按屏宽自适应，始终大于地球直径，避免重叠 */
  min-height: 100vh;
  width: 100%;
  padding: 20px 60px;
  position: relative;
  overflow: hidden;
}

/* Cesium 3D 地球背景层：正方形容器且边长按屏幕宽度 vw 计算，
   使地球尺寸只随屏宽变化，不再随屏高膨胀而压到两侧内容 */
.earth-bg {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 40vw;
  height: 40vw;
  z-index: 0;
  /* 边缘径向渐隐，隐藏 Cesium 画布的方形边界，只保留圆形星空光晕 */
  -webkit-mask-image: radial-gradient(circle, #000 55%, transparent 78%);
  mask-image: radial-gradient(circle, #000 55%, transparent 78%);
}

/* 深色渐变蒙层，让地球背景与卡片融合 */
.login-container::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(100deg, rgba(3, 8, 24, 0.88) 0%, rgba(5, 12, 32, 0.62) 40%, rgba(3, 8, 24, 0.75) 64%, rgba(3, 8, 24, 0.97) 100%);
  z-index: 1;
  pointer-events: none;
}

/* 装饰光斑 */
.glow-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(90px);
  opacity: 0.4;
  z-index: 1;
  pointer-events: none;
  animation: float 10s ease-in-out infinite;
}

.orb-1 {
  width: 420px;
  height: 420px;
  background: radial-gradient(circle, rgba(64, 158, 255, 0.55), transparent 70%);
  top: -120px;
  left: -100px;
}

.orb-2 {
  width: 380px;
  height: 380px;
  background: radial-gradient(circle, rgba(124, 77, 255, 0.45), transparent 70%);
  bottom: -120px;
  right: -80px;
  animation-delay: -5s;
}

@keyframes float {
  0%, 100% { transform: translate(0, 0); }
  50% { transform: translate(30px, -30px); }
}

/* 地球外围轨道装饰环：与地球同中心，纯装饰 */
.orbit-ring {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  border-radius: 50%;
  border: 1px dashed rgba(0, 220, 255, 0.22);
  z-index: 1;
  pointer-events: none;
}
.ring-outer {
  width: 52vw;
  height: 52vw;
  animation: orbit-spin 90s linear infinite;
}
.ring-inner {
  width: 46vw;
  height: 46vw;
  border-style: solid;
  border-color: rgba(0, 220, 255, 0.1);
  border-top-color: rgba(0, 240, 255, 0.45);
  animation: orbit-spin 40s linear infinite reverse;
}
/* 外环上一颗绕行"卫星"光点 */
.orbit-sat {
  position: absolute;
  top: -4px;
  left: 50%;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #00f0ff;
  box-shadow: 0 0 12px rgba(0, 240, 255, 0.9), 0 0 30px rgba(0, 240, 255, 0.4);
}
@keyframes orbit-spin {
  from { transform: translate(-50%, -50%) rotate(0deg); }
  to { transform: translate(-50%, -50%) rotate(360deg); }
}

/* 标语区底部能力标签 */
.intro-metrics {
  margin-top: 34px;
  display: flex;
  gap: 22px;
  flex-wrap: wrap;
}
.im-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  letter-spacing: 2px;
  color: rgba(160, 200, 245, 0.75);
  padding: 7px 14px;
  border: 1px solid rgba(0, 220, 255, 0.18);
  border-radius: 999px;
  background: rgba(0, 220, 255, 0.04);
  backdrop-filter: blur(6px);
}
.im-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #00f0ff;
  box-shadow: 0 0 8px rgba(0, 240, 255, 0.8);
  animation: im-breathe 2.2s ease-in-out infinite;
}
.im-item:nth-child(2) .im-dot { animation-delay: -0.7s; }
.im-item:nth-child(3) .im-dot { animation-delay: -1.4s; }
@keyframes im-breathe {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

@keyframes card-in {
  from { opacity: 0; transform: translateY(24px); }
  to { opacity: 1; transform: translateY(0); }
}

/* 地球区域右侧边缘渐隐过渡，与卡片区域自然衔接 */
.login-container::after {
  content: '';
  position: absolute;
  top: 0;
  bottom: 0;
  left: 58%;
  width: 14%;
  background: linear-gradient(90deg, transparent 0%, rgba(3, 8, 24, 0.9) 100%);
  z-index: 1;
  pointer-events: none;
}

/* 左侧标语区 */
.intro-panel {
  position: relative;
  z-index: 2;
  max-width: 560px;
  animation: card-in 0.7s ease-out;
}

.intro-badge {
  display: inline-block;
  padding: 6px 16px;
  border-radius: 999px;
  border: 1px solid rgba(120, 180, 255, 0.35);
  background: rgba(64, 158, 255, 0.08);
  font-size: 10px;
  letter-spacing: 3px;
  color: rgba(160, 200, 250, 0.85);
}

.intro-title {
  margin: 24px 0 0;
  font-size: 46px;
  line-height: 1.3;
  font-weight: 700;
  letter-spacing: 4px;
  color: #e8f1ff;
  text-shadow: 0 2px 18px rgba(3, 8, 24, 0.9);
}

.intro-title-grad {
  background: linear-gradient(90deg, #4fc3f7, #7c9eff, #b47cff);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

.intro-desc {
  margin-top: 20px;
  font-size: 15px;
  letter-spacing: 2px;
  color: rgba(190, 210, 245, 0.7);
  text-shadow: 0 1px 12px rgba(3, 8, 24, 0.9);
}

/* 登录卡片层级 */
.login-container :deep(.box-card) {
  z-index: 2;
}

/* 左上角返回首页 */
.back-portal {
  position: absolute;
  top: 28px;
  left: 40px;
  z-index: 3;
  font-size: 13px;
  letter-spacing: 1px;
  color: rgba(190, 215, 250, 0.7);
  cursor: pointer;
  padding: 8px 16px;
  border-radius: 999px;
  border: 1px solid rgba(120, 180, 255, 0.25);
  background: rgba(10, 18, 40, 0.35);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  transition: all 0.25s ease;
}

.back-portal:hover {
  color: #ffffff;
  border-color: rgba(120, 180, 255, 0.6);
  box-shadow: 0 0 16px rgba(64, 158, 255, 0.25);
}

/* 中等宽度屏：缩小内边距与间隙，给标语区留足宽度避免标题换行 */
@media (max-width: 1400px) and (min-width: 1101px) {
  .login-container { gap: 260px; padding: 20px; }
}

@media (max-width: 1100px) {
  .intro-panel { display: none; }
  .login-container { justify-content: center; padding: 20px; }
  .earth-bg { top: 0; left: 0; transform: none; width: 100%; height: 100%; }
  /* 窄屏隐藏轨道环，避免与地球背景错位 */
  .orbit-ring { display: none; }
}
</style>
