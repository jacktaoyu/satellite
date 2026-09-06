<template>
  <div class="portal-container">
      <!-- Cesium 3D 地球动态背景 -->
      <div ref="earthBg" class="earth-bg"></div>
      <!-- 闪烁星空 + 流星粒子层 -->
      <canvas ref="starCanvas" class="star-canvas"></canvas>
      <!-- 科技感扫描线 + 周期扫光 -->
      <div class="scanlines"></div>
      <!-- HUD 四角框线 + 遥测读数 -->
      <i class="hud-corner hud-tl"></i>
      <i class="hud-corner hud-tr"></i>
      <i class="hud-corner hud-bl"></i>
      <i class="hud-corner hud-br"></i>
      <div class="hud-telemetry"><span class="tele-dot"></span>ORBIT LINK · ACTIVE</div>
      <div class="hud-coords">LAT 08.00 · LON 105.00 · ALT 35,786 KM</div>
      <!-- 背景装饰光斑 -->
      <div class="glow-orb orb-1"></div>
      <div class="glow-orb orb-2"></div>

      <!-- 顶部导航 -->
      <header class="portal-nav">
          <div class="nav-brand">
              <div class="brand-logo">
                  <svg viewBox="0 0 24 24" fill="none" width="22" height="22">
                      <path d="M12 2L14.5 9.5L22 12L14.5 14.5L12 22L9.5 14.5L2 12L9.5 9.5L12 2Z"
                            fill="url(#navLogoGrad)"/>
                      <defs>
                          <linearGradient id="navLogoGrad" x1="2" y1="2" x2="22" y2="22">
                              <stop stop-color="#4fc3f7"/>
                              <stop offset="1" stop-color="#7c4dff"/>
                          </linearGradient>
                      </defs>
                  </svg>
              </div>
              <span class="nav-title">智能星簇协同运行验证系统</span>
          </div>
          <el-button class="nav-enter-btn" @click="enterSystem">进入系统</el-button>
      </header>

      <!-- Hero 区 -->
      <section class="portal-hero">
          <div class="hero-badge">{{ badgeText }}</div>
          <h1 class="hero-title">
              智能星簇<br/>
              <span class="hero-title-grad">协同运行验证系统</span>
          </h1>
          <p class="hero-desc">
              面向卫星星簇的三维组网可视化、任务协同规划与运行效能评估一体化验证平台，
              为星簇系统设计、推演与验证提供全流程支撑。
          </p>
          <div class="hero-actions">
              <el-button class="hero-btn-primary" @click="enterSystem">
                  进入系统
                  <svg viewBox="0 0 24 24" width="16" height="16" fill="none" style="margin-left:6px">
                      <path d="M5 12h14M13 6l6 6-6 6" stroke="currentColor" stroke-width="2"
                            stroke-linecap="round" stroke-linejoin="round"/>
                  </svg>
              </el-button>
          </div>

          <!-- 数据看板 -->
          <div class="hero-stats">
              <div class="stat-item" v-for="stat in stats" :key="stat.label">
                  <div class="stat-value">
                      <span class="stat-num">{{ stat.display }}</span><span class="stat-unit">{{ stat.unit }}</span>
                  </div>
                  <div class="stat-label">{{ stat.label }}</div>
              </div>
          </div>
      </section>

      <footer class="portal-footer">
          © 2026 智能星簇协同运行验证系统 · Satellite Cluster Collaborative Platform
      </footer>

      <!-- 弹层式登录 -->
      <transition name="login-pop">
          <div v-if="showLogin" class="login-overlay" @click.self="showLogin = false">
              <div class="login-dialog">
                  <div class="dialog-close" @click="showLogin = false">✕</div>
                  <LoginCard />
              </div>
          </div>
      </transition>
  </div>
</template>

<script>
import * as Cesium from "cesium";
import LoginCard from "@/views/login/LoginCard.vue";

export default {
  name: "portal",
  components: { LoginCard },
  data() {
      return {
          showLogin: false,
          badgeText: '',
          // 真实统计数据（来自后端 /statistics 接口）
          stats: [
              { label: '在轨卫星', value: 0, unit: ' 颗', decimals: 0, display: '0' },
              { label: '今日任务', value: 0, unit: ' 次', decimals: 0, display: '0' },
              { label: '待执行任务', value: 0, unit: ' 次', decimals: 0, display: '0' },
              { label: '在线客户端', value: 0, unit: ' 个', decimals: 0, display: '0' }
          ],
      };
  },
  methods: {
      onEscClose(e) {
          if (e.key === 'Escape') this.showLogin = false;
      },
      // 初始化 Cesium 3D 地球动态背景
      initEarth() {
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
          // 高德卫星影像图层
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
          // 开启动态大气光照，给背光面补充环境光，避免夜半球漆黑一团
          viewer.scene.globe.dynamicAtmosphereLighting = true;
          // 地球大气蓝晕
          if (viewer.scene.skyAtmosphere) {
              viewer.scene.skyAtmosphere.show = true;
          }
          // 泛光后期处理：轨道环与发光卫星产生辉光，增强科技感
          const bloom = viewer.scene.postProcessStages.bloom;
          bloom.enabled = true;
          bloom.uniforms.glowOnly = false;
          bloom.uniforms.contrast = 128;
          bloom.uniforms.brightness = -0.35;
          bloom.uniforms.delta = 1.2;
          bloom.uniforms.sigma = 3.0;
          bloom.uniforms.stepSize = 2.0;
          // 固定到亚洲昼半球时刻，展示明亮的日照面
          viewer.clock.currentTime = Cesium.JulianDate.fromDate(new Date(Date.UTC(2026, 7, 29, 3, 0, 0)));
          // 初始视角：地球目标直径 = min(55% 屏高, 40% 屏宽)，按视口宽高自适应换算相机距离，
          // 保证任何屏幕（含超宽/矮屏）下地球占比一致、不触边不压迫文字
          const h = Math.max(window.innerHeight, 700);
          const target = Math.min(h * 0.55, window.innerWidth * 0.4);
          this.camDist = 27700000 * h / target;
          viewer.camera.setView({
              destination: Cesium.Cartesian3.fromDegrees(105, 8, this.camDist)
          });
          // 视角在初始位置附近小幅往复摆动（±20°、周期约 45s），
          // 既有缓慢动感，又保证始终展示明亮的昼半球，不会转到漆黑的背光面
          this._swingStart = Date.now();
          this._swingPrev = 0;
          viewer.clock.onTick.addEventListener(() => {
              const t = (Date.now() - this._swingStart) / 1000;
              const angle = 0.35 * Math.sin(t * 2 * Math.PI / 45);
              viewer.scene.camera.rotate(Cesium.Cartesian3.UNIT_Z, angle - this._swingPrev);
              this._swingPrev = angle;
          });
          // 添加绕轨飞行的发光卫星（装饰性）
          this.addOrbitSats(viewer);
          // 地面站 + 星地链路光束
          this.addGroundStations(viewer);
          this.viewer = viewer;
      },
      // 在地球周围添加装饰性绕轨卫星：发光点 + 轨道环
      addOrbitSats(viewer) {
          const startTime = Cesium.JulianDate.clone(viewer.clock.currentTime);
          const satParms = [
              { alt: 1400000, inc: 0.5,  phase: 0.0, speed: 0.0010, color: '#4fc3f7' },
              { alt: 1800000, inc: -0.9, phase: 2.1, speed: 0.0008, color: '#8a7cff' },
              { alt: 2200000, inc: 1.1,  phase: 4.0, speed: 0.0006, color: '#4fd8c7' },
              { alt: 1600000, inc: -0.4, phase: 1.2, speed: 0.0009, color: '#6fa8ff' },
              { alt: 2500000, inc: 0.2,  phase: 5.3, speed: 0.0005, color: '#b47cff' }
          ];
          // 卫星位置计算函数（供星地链路光束复用）
          this._satPosFns = satParms.map(s => {
              const r = 6371000 + s.alt;
              return (time) => {
                  const t = Cesium.JulianDate.secondsDifference(time, startTime);
                  const u = s.phase + t * s.speed;
                  return new Cesium.Cartesian3(
                      r * Math.cos(u),
                      r * Math.sin(u) * Math.cos(s.inc),
                      r * Math.sin(u) * Math.sin(s.inc)
                  );
              };
          });
          satParms.forEach((s, i) => {
              const r = 6371000 + s.alt;
              const color = Cesium.Color.fromCssColorString(s.color);
              // 静态轨道环（一次性算好整圈折线，避免 Path 与 CallbackProperty 的兼容问题）
              const ringPositions = [];
              for (let i = 0; i <= 128; i++) {
                  const u = i / 128 * 2 * Math.PI;
                  ringPositions.push(new Cesium.Cartesian3(
                      r * Math.cos(u),
                      r * Math.sin(u) * Math.cos(s.inc),
                      r * Math.sin(u) * Math.sin(s.inc)
                  ));
              }
              viewer.entities.add({
                  polyline: {
                      positions: ringPositions,
                      width: 1.5,
                      material: new Cesium.PolylineGlowMaterialProperty({
                          glowPower: 0.12,
                          color: color.withAlpha(0.4)
                      })
                  }
              });
              // 发光卫星点（沿轨道运动，大小呼吸脉动）
              viewer.entities.add({
                  position: new Cesium.CallbackProperty((time) => this._satPosFns[i](time), false),
                  point: {
                      pixelSize: new Cesium.CallbackProperty(
                          () => 5.5 + 2 * Math.sin(Date.now() / 400 + s.phase), false),
                      color: color,
                      outlineColor: color.withAlpha(0.3),
                      outlineWidth: 6
                  }
              });
          });
          // 外圈两条虚线轨道环，营造星座网格 / 雷达扫描感
          [
              { alt: 3100000, inc: 0.85, dash: 16 },
              { alt: 3600000, inc: -0.55, dash: 10 }
          ].forEach(s => {
              const r = 6371000 + s.alt;
              const ringPositions = [];
              for (let i = 0; i <= 160; i++) {
                  const u = i / 160 * 2 * Math.PI;
                  ringPositions.push(new Cesium.Cartesian3(
                      r * Math.cos(u),
                      r * Math.sin(u) * Math.cos(s.inc),
                      r * Math.sin(u) * Math.sin(s.inc)
                  ));
              }
              viewer.entities.add({
                  polyline: {
                      positions: ringPositions,
                      width: 1.2,
                      material: new Cesium.PolylineDashMaterialProperty({
                          color: Cesium.Color.fromCssColorString('#5fb8ff').withAlpha(0.28),
                          dashLength: s.dash
                      })
                  }
              });
          });
      },
      // 地面站：呼吸光点 + 地面扩散波纹 + 到卫星的发光链路光束
      addGroundStations(viewer) {
          const stations = [
              { lon: 116.4, lat: 39.9 },   // 北京
              { lon: 76.0,  lat: 39.5 },   // 喀什
              { lon: 109.5, lat: 18.2 }    // 三亚
          ];
          const linkColor = Cesium.Color.fromCssColorString('#4fd8c7');
          const startTime = Cesium.JulianDate.clone(viewer.clock.currentTime);
          // 波纹进度：两个轴的回调用同一个 time 入参计算，保证 major === minor
          const rippleFrac = (time, phase) =>
              ((Cesium.JulianDate.secondsDifference(time, startTime) + phase) % 3) / 3;
          stations.forEach((st, idx) => {
              const pos = Cesium.Cartesian3.fromDegrees(st.lon, st.lat, 0);
              // 站点呼吸光点
              viewer.entities.add({
                  position: pos,
                  point: {
                      pixelSize: new Cesium.CallbackProperty(
                          () => 5 + 2 * Math.sin(Date.now() / 500 + idx * 2), false),
                      color: linkColor,
                      outlineColor: linkColor.withAlpha(0.35),
                      outlineWidth: 5
                  }
              });
              // 地面扩散波纹（半径 0 → 400km 循环，透明度随扩散衰减）
              const phase = idx * 0.9;
              viewer.entities.add({
                  position: pos,
                  ellipse: {
                      semiMajorAxis: new Cesium.CallbackProperty(
                          (time) => Math.max(rippleFrac(time, phase) * 400000, 1000), false),
                      semiMinorAxis: new Cesium.CallbackProperty(
                          (time) => Math.max(rippleFrac(time, phase) * 400000, 1000), false),
                      material: new Cesium.ColorMaterialProperty(new Cesium.CallbackProperty(
                          (time) => linkColor.withAlpha(0.3 * (1 - rippleFrac(time, phase))), false))
                  }
              });
              // 星地链路光束：实时连接对应装饰卫星，亮度脉动；
              // 卫星不在本站可见天空时（低于地平线/视角过斜）光束淡出，避免穿透地球的长线
              if (this._satPosFns && this._satPosFns[idx]) {
                  const up = Cesium.Cartesian3.normalize(pos, new Cesium.Cartesian3());
                  const toSat = new Cesium.Cartesian3();
                  viewer.entities.add({
                      polyline: {
                          positions: new Cesium.CallbackProperty(
                              (time) => [pos, this._satPosFns[idx](time)], false),
                          width: 1.6,
                          material: new Cesium.PolylineGlowMaterialProperty({
                              glowPower: 0.18,
                              color: new Cesium.CallbackProperty((time) => {
                                  const sat = this._satPosFns[idx](time);
                                  Cesium.Cartesian3.subtract(sat, pos, toSat);
                                  Cesium.Cartesian3.normalize(toSat, toSat);
                                  const cos = Cesium.Cartesian3.dot(up, toSat);
                                  if (cos < 0.35) return linkColor.withAlpha(0);
                                  const vis = (cos - 0.35) / 0.65;
                                  const pulse = 0.6 + 0.4 * Math.sin(Date.now() / 600 + idx);
                                  return linkColor.withAlpha(0.5 * vis * pulse);
                              }, false)
                          })
                      }
                  });
              }
          });
      },
      // 点击“进入系统”：相机先向地球推进，再弹出登录卡片
      enterSystem() {
          if (this.viewer) {
              const h = Math.max(window.innerHeight, 700);
              const flyTarget = Math.min(h * 0.75, window.innerWidth * 0.55);
              const flyDist = 27700000 * h / flyTarget;
              this.viewer.camera.flyTo({
                  destination: Cesium.Cartesian3.fromDegrees(105, 8, flyDist),
                  duration: 1.4
              });
              this._loginTimer = setTimeout(() => { this.showLogin = true; }, 800);
          } else {
              this.showLogin = true;
          }
      },
      // 徽章解码动效：从随机字符逐步“解码”为目标文字
      runBadgeDecode() {
          const target = 'SATELLITE CLUSTER COLLABORATIVE PLATFORM';
          const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
          let frame = 0;
          const total = 40;
          const tick = () => {
              frame++;
              const solved = Math.floor(frame / total * target.length);
              this.badgeText = target.split('').map((c, i) => {
                  if (c === ' ') return ' ';
                  return i < solved ? c : chars[Math.floor(Math.random() * chars.length)];
              }).join('');
              if (frame < total) {
                  this._badgeTimer = setTimeout(tick, 35);
              } else {
                  this.badgeText = target;
              }
          };
          tick();
      },
      // 闪烁星空 + 流星粒子层
      initStars() {
          const canvas = this.$refs.starCanvas;
          const ctx = canvas.getContext('2d');
          let stars = [];
          let meteors = [];
          let nextMeteor = performance.now() + 2500;
          const resize = () => {
              canvas.width = window.innerWidth;
              canvas.height = window.innerHeight;
              // 根据屏幕面积生成星星
              const count = Math.min(220, Math.floor(canvas.width * canvas.height / 9000));
              stars = Array.from({ length: count }, () => ({
                  x: Math.random() * canvas.width,
                  y: Math.random() * canvas.height,
                  r: Math.random() * 1.3 + 0.3,
                  baseAlpha: Math.random() * 0.5 + 0.3,
                  twinkleSpeed: Math.random() * 1.5 + 0.5,
                  phase: Math.random() * Math.PI * 2
              }));
          };
          resize();
          window.addEventListener('resize', resize);
          this._starResize = resize;
          const draw = (now) => {
              ctx.clearRect(0, 0, canvas.width, canvas.height);
              // 星星闪烁
              for (const s of stars) {
                  const alpha = s.baseAlpha * (0.6 + 0.4 * Math.sin(now / 1000 * s.twinkleSpeed + s.phase));
                  ctx.beginPath();
                  ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
                  ctx.fillStyle = `rgba(200, 225, 255, ${alpha})`;
                  ctx.fill();
              }
              // 偶发流星
              if (now > nextMeteor) {
                  nextMeteor = now + 4000 + Math.random() * 6000;
                  const fromLeft = Math.random() > 0.5;
                  meteors.push({
                      x: fromLeft ? Math.random() * canvas.width * 0.4 : canvas.width * (0.6 + Math.random() * 0.4),
                      y: Math.random() * canvas.height * 0.3,
                      vx: fromLeft ? 7 + Math.random() * 3 : -(7 + Math.random() * 3),
                      vy: 3.5 + Math.random() * 1.5,
                      life: 1
                  });
              }
              meteors = meteors.filter(m => m.life > 0);
              for (const m of meteors) {
                  m.x += m.vx;
                  m.y += m.vy;
                  m.life -= 0.016;
                  const grad = ctx.createLinearGradient(m.x, m.y, m.x - m.vx * 12, m.y - m.vy * 12);
                  grad.addColorStop(0, `rgba(180, 225, 255, ${0.9 * m.life})`);
                  grad.addColorStop(1, 'rgba(180, 225, 255, 0)');
                  ctx.beginPath();
                  ctx.moveTo(m.x, m.y);
                  ctx.lineTo(m.x - m.vx * 12, m.y - m.vy * 12);
                  ctx.strokeStyle = grad;
                  ctx.lineWidth = 1.6;
                  ctx.stroke();
              }
              this._starRaf = requestAnimationFrame(draw);
          };
          this._starRaf = requestAnimationFrame(draw);
      },
      // 鼠标视差：地球与前景内容反向轻微移动，营造纵深感
      onMouseMove(e) {
          if (this._parallaxRaf) return;
          this._parallaxRaf = requestAnimationFrame(() => {
              this._parallaxRaf = null;
              const dx = e.clientX / window.innerWidth - 0.5;
              const dy = e.clientY / window.innerHeight - 0.5;
              if (this.$refs.earthBg) {
                  this.$refs.earthBg.style.transform =
                      `scale(1.06) translate3d(${dx * -18}px, ${dy * -12}px, 0)`;
              }
              const hero = this.$el.querySelector('.portal-hero');
              if (hero) {
                  hero.style.transform = `translate3d(${dx * 8}px, ${dy * 6}px, 0)`;
              }
          });
      },
      // 从后端获取真实统计数据
      async fetchStats() {
          try {
              const res = await this.$request.get('/statistics');
              const d = res.data.data;
              this.stats[0].value = d.satellite_count;
              this.stats[1].value = d.today_task_count;
              this.stats[2].value = d.pending_task_count;
              this.stats[3].value = d.online_clients;
          } catch (e) {
              // 后端不可达时保持 0，不影响页面展示
          }
          this.runCountUp();
      },
      // 数字滚动动画
      runCountUp() {
          const duration = 1600;
          const start = performance.now();
          const tick = (now) => {
              const p = Math.min((now - start) / duration, 1);
              const eased = 1 - Math.pow(1 - p, 3);
              this.stats.forEach(s => {
                  s.display = (s.value * eased).toFixed(s.decimals);
              });
              if (p < 1) this._countRaf = requestAnimationFrame(tick);
          };
          this._countRaf = requestAnimationFrame(tick);
      }
  },
  watch: {
      // 登录弹层关闭时相机飞回原位，并恢复鼠标视差
      showLogin(v) {
          if (!v && this.viewer) {
              // 飞回绝对机位后重置摆动相位，防止摆动增量叠加导致视角跳变
              this._swingStart = Date.now();
              this._swingPrev = 0;
              this.viewer.camera.flyTo({
                  destination: Cesium.Cartesian3.fromDegrees(105, 8, this.camDist),
                  duration: 1.2
              });
              window.addEventListener('mousemove', this.onMouseMove);
          }
      }
  },
  mounted() {
      window.addEventListener('keydown', this.onEscClose);
      window.addEventListener('mousemove', this.onMouseMove);
      this.fetchStats();
      this.runBadgeDecode();
      this.initEarth();
      this.initStars();
  },
  beforeUnmount() {
      window.removeEventListener('keydown', this.onEscClose);
      window.removeEventListener('mousemove', this.onMouseMove);
      if (this._starResize) window.removeEventListener('resize', this._starResize);
      if (this._badgeTimer) clearTimeout(this._badgeTimer);
      if (this._loginTimer) clearTimeout(this._loginTimer); // “进入系统”延迟弹登录层的定时器
      if (this._starRaf) cancelAnimationFrame(this._starRaf);
      if (this._parallaxRaf) cancelAnimationFrame(this._parallaxRaf);
      if (this._countRaf) cancelAnimationFrame(this._countRaf); // 统计数字滚动动画
      if (this.viewer) {
          this.viewer.destroy();
          this.viewer = null;
      }
  }
}
</script>

<style scoped>
.portal-container {
  background: #050b1a; /* Cesium 地球背景加载前的底色 */
  min-height: 100vh;
  width: 100%;
  position: relative;
  overflow-x: hidden;
  display: flex;
  flex-direction: column;
}

/* Cesium 3D 地球背景层：画布加宽右偏，使地球居于画面右侧（左文右球构图） */
.earth-bg {
  position: fixed;
  top: 0;
  bottom: 0;
  left: -10vw;
  width: 160vw;
  z-index: 0;
  transform: scale(1.06);
  transition: transform 0.3s ease-out;
}

/* 闪烁星空 + 流星粒子层 */
.star-canvas {
  position: fixed;
  inset: 0;
  z-index: 1;
  pointer-events: none;
}

/* 科技感扫描线纹理 */
.scanlines {
  position: fixed;
  inset: 0;
  z-index: 3;
  pointer-events: none;
  background: repeating-linear-gradient(
    180deg,
    rgba(140, 200, 255, 0.028) 0 1px,
    transparent 1px 4px
  );
}

/* HUD 四角框线 */
.hud-corner {
  position: fixed;
  width: 26px;
  height: 26px;
  z-index: 3;
  pointer-events: none;
  opacity: 0.45;
}

.hud-tl { top: 14px; left: 14px; border-top: 1.5px solid rgba(95, 184, 255, 0.6); border-left: 1.5px solid rgba(95, 184, 255, 0.6); }
.hud-tr { top: 14px; right: 14px; border-top: 1.5px solid rgba(95, 184, 255, 0.6); border-right: 1.5px solid rgba(95, 184, 255, 0.6); }
.hud-bl { bottom: 14px; left: 14px; border-bottom: 1.5px solid rgba(95, 184, 255, 0.6); border-left: 1.5px solid rgba(95, 184, 255, 0.6); }
.hud-br { bottom: 14px; right: 14px; border-bottom: 1.5px solid rgba(95, 184, 255, 0.6); border-right: 1.5px solid rgba(95, 184, 255, 0.6); }

/* 遥测状态读数 */
.hud-telemetry,
.hud-coords {
  position: fixed;
  bottom: 22px;
  z-index: 3;
  pointer-events: none;
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: 'Courier New', monospace;
  font-size: 11px;
  letter-spacing: 2px;
  color: rgba(140, 180, 230, 0.55);
}

.hud-telemetry { left: 52px; }
.hud-coords { right: 52px; }

.tele-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #3ef2a8;
  box-shadow: 0 0 8px #3ef2a8;
  animation: tele-blink 1.6s ease-in-out infinite;
}

@keyframes tele-blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.25; }
}

/* Hero 区随鼠标轻微视差 */
.portal-hero {
  transition: transform 0.3s ease-out;
}

/* 深色渐变蒙层：上下加深保证文字可读，中部通透展示地球 */
.portal-container::before {
  content: '';
  position: fixed;
  inset: 0;
  background:
    linear-gradient(100deg, rgba(3, 8, 24, 0.9) 0%, rgba(3, 8, 24, 0.55) 42%, rgba(3, 8, 24, 0.12) 68%, rgba(3, 8, 24, 0) 100%),
    linear-gradient(180deg, rgba(3, 8, 24, 0.5) 0%, transparent 30%, transparent 62%, rgba(3, 8, 24, 0.82) 100%);
  z-index: 1;
  pointer-events: none;
}

.portal-container::after {
  content: '';
  position: fixed;
  inset: 0;
  background-image:
    linear-gradient(rgba(79, 195, 247, 0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(79, 195, 247, 0.05) 1px, transparent 1px);
  background-size: 56px 56px;
  mask-image: radial-gradient(ellipse at center, rgba(0,0,0,0.7) 0%, transparent 75%);
  -webkit-mask-image: radial-gradient(ellipse at center, rgba(0,0,0,0.7) 0%, transparent 75%);
  z-index: 1;
  pointer-events: none;
}

/* 装饰光斑 */
.glow-orb {
  position: fixed;
  border-radius: 50%;
  filter: blur(90px);
  opacity: 0.5;
  z-index: 0;
  animation: float 10s ease-in-out infinite;
}

.orb-1 {
  width: 480px;
  height: 480px;
  background: radial-gradient(circle, rgba(64, 158, 255, 0.5), transparent 70%);
  top: -140px;
  left: -120px;
}

.orb-2 {
  width: 420px;
  height: 420px;
  background: radial-gradient(circle, rgba(124, 77, 255, 0.45), transparent 70%);
  bottom: 0;
  right: -100px;
  animation-delay: -5s;
}

@keyframes float {
  0%, 100% { transform: translate(0, 0); }
  50% { transform: translate(30px, -30px); }
}

@keyframes fade-up {
  from { opacity: 0; transform: translateY(24px); }
  to { opacity: 1; transform: translateY(0); }
}

/* 顶部导航 */
.portal-nav {
  position: relative;
  z-index: 2;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 22px 48px;
  animation: fade-up 0.6s ease-out;
}

.nav-brand {
  display: flex;
  align-items: center;
  gap: 12px;
}

.brand-logo {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: rgba(64, 158, 255, 0.12);
  border: 1px solid rgba(120, 180, 255, 0.3);
  box-shadow: 0 0 16px rgba(64, 158, 255, 0.25);
}

.nav-title {
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 2px;
  color: #e8f1ff;
}

.nav-enter-btn {
  border-radius: 10px;
  border: 1px solid rgba(120, 180, 255, 0.4);
  background: rgba(64, 158, 255, 0.1);
  color: #bfe0ff;
  transition: all 0.25s ease;
}

.nav-enter-btn:hover {
  background: rgba(64, 158, 255, 0.25);
  color: #ffffff;
  border-color: rgba(120, 180, 255, 0.7);
  box-shadow: 0 0 16px rgba(64, 158, 255, 0.3);
}

/* Hero 区：左对齐分栏，右侧留给地球 */
.portal-hero {
  position: relative;
  z-index: 1;
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: flex-start;
  text-align: left;
  padding: 60px 24px 40px 9vw;
}

/* ===== 数据看板 ===== */
.hero-stats {
  position: relative;
  margin-top: 46px;
  display: flex;
  gap: 0;
  border: 1px solid rgba(120, 180, 255, 0.22);
  border-radius: 14px;
  background: rgba(8, 15, 34, 0.72);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  animation: fade-up 1s ease-out;
  overflow: hidden;
}

/* 看板上沿流动高光线 */
.hero-stats::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(111, 216, 255, 0.85), transparent);
  background-size: 40% 100%;
  background-repeat: no-repeat;
  animation: stats-scan 3.5s linear infinite;
}

@keyframes stats-scan {
  from { background-position: -40% 0; }
  to { background-position: 140% 0; }
}

.stat-item {
  padding: 16px 36px;
  text-align: center;
  position: relative;
}

.stat-item + .stat-item::before {
  content: '';
  position: absolute;
  left: 0;
  top: 25%;
  height: 50%;
  width: 1px;
  background: linear-gradient(180deg, transparent, rgba(120, 180, 255, 0.35), transparent);
}

.stat-value {
  font-size: 26px;
  font-weight: 700;
  color: #6fd8ff;
  text-shadow: 0 0 14px rgba(79, 195, 247, 0.55);
  font-variant-numeric: tabular-nums;
}

.stat-unit {
  font-size: 13px;
  font-weight: 400;
  color: rgba(160, 190, 235, 0.6);
}

.stat-label {
  margin-top: 4px;
  font-size: 12px;
  letter-spacing: 2px;
  color: rgba(160, 190, 235, 0.65);
}

/* 标题辉光 */
.hero-title {
  text-shadow: 0 0 30px rgba(79, 195, 247, 0.25);
}

.hero-badge {
  display: inline-block;
  position: relative;
  overflow: hidden;
  padding: 6px 18px;
  border-radius: 999px;
  border: 1px solid rgba(120, 180, 255, 0.35);
  background: rgba(64, 158, 255, 0.08);
  font-size: 11px;
  letter-spacing: 4px;
  color: rgba(160, 200, 250, 0.85);
  animation: fade-up 0.6s ease-out;
}

/* 徽章周期流光扫过 */
.hero-badge::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(100deg, transparent 25%, rgba(170, 215, 255, 0.35) 50%, transparent 75%);
  transform: translateX(-110%);
  animation: badge-shine 4.5s ease-in-out infinite;
}

@keyframes badge-shine {
  0% { transform: translateX(-110%); }
  55%, 100% { transform: translateX(110%); }
}

.hero-title {
  margin: 28px 0 0;
  font-size: 56px;
  line-height: 1.25;
  font-weight: 700;
  letter-spacing: 6px;
  color: #e8f1ff;
  animation: fade-up 0.7s ease-out;
}

.hero-title-grad {
  background: linear-gradient(90deg, #4fc3f7, #7c9eff, #b47cff, #4fc3f7);
  background-size: 200% auto;
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  animation: title-shine 4s linear infinite;
}

/* 标题流光扫过 */
@keyframes title-shine {
  from { background-position: 0% center; }
  to { background-position: 200% center; }
}

.hero-desc {
  margin: 24px 0 0;
  max-width: 520px;
  font-size: 16px;
  line-height: 1.9;
  color: rgba(190, 210, 245, 0.75);
  animation: fade-up 0.8s ease-out;
}

.hero-actions {
  margin-top: 40px;
  display: flex;
  gap: 18px;
  animation: fade-up 0.9s ease-out;
}

.hero-btn-primary {
  position: relative;
  display: inline-flex;
  align-items: center;
  height: 48px;
  padding: 0 34px;
  font-size: 16px;
  letter-spacing: 2px;
  color: #fff;
  border: none;
  border-radius: 12px;
  background: linear-gradient(90deg, #3a9cfd, #6a5cff);
  box-shadow: 0 8px 26px rgba(74, 124, 255, 0.4);
  transition: transform 0.2s ease, box-shadow 0.2s ease, filter 0.2s ease;
}

.hero-btn-primary:hover {
  transform: translateY(-2px);
  filter: brightness(1.1);
  box-shadow: 0 12px 32px rgba(74, 124, 255, 0.55);
  color: #fff;
}

/* 按钮能量脉冲环：周期扩散引导点击 */
.hero-btn-primary::after {
  content: '';
  position: absolute;
  inset: -1px;
  border-radius: 12px;
  border: 1.5px solid rgba(110, 150, 255, 0.7);
  pointer-events: none;
  animation: btn-pulse 2.2s ease-out infinite;
}

@keyframes btn-pulse {
  0% { transform: scale(1); opacity: 0.8; }
  100% { transform: scale(1.28, 1.65); opacity: 0; }
}

/* 页脚 */
.portal-footer {
  position: relative;
  z-index: 1;
  text-align: center;
  padding: 18px;
  font-size: 12px;
  letter-spacing: 1px;
  color: rgba(150, 175, 220, 0.4);
}

@media (max-width: 1100px) {
  .portal-hero { align-items: center; text-align: center; padding: 60px 20px 40px; }
  .earth-bg { left: -30vw; } /* 窄屏时地球回到画面中部 */
}

/* 低高度屏幕紧凑化 */
@media (max-height: 860px) {
  .portal-hero { padding-top: 24px; padding-bottom: 20px; }
  .hero-title { font-size: 42px; }
  .hero-desc { margin-top: 16px; font-size: 15px; }
  .hero-actions { margin-top: 28px; }
  .hero-stats { margin-top: 30px; }
}

@media (max-width: 768px) {
  .portal-nav { padding: 18px 20px; }
  .hero-title { font-size: 34px; letter-spacing: 3px; }
}

/* 弹层式登录 */
.login-overlay {
  position: fixed;
  inset: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(3, 8, 24, 0.55);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
}

.login-dialog {
  position: relative;
}

.dialog-close {
  position: absolute;
  top: 14px;
  right: 18px;
  z-index: 2;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  font-size: 13px;
  color: rgba(190, 215, 250, 0.6);
  cursor: pointer;
  transition: all 0.2s ease;
}

.dialog-close:hover {
  color: #ffffff;
  background: rgba(120, 180, 255, 0.15);
}

/* 弹层进出动画：背景淡入淡出，卡片缩放弹入 */
.login-pop-enter-active,
.login-pop-leave-active {
  transition: opacity 0.3s ease;
}

.login-pop-enter-active .login-dialog {
  animation: dialog-in 0.35s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.login-pop-enter-from,
.login-pop-leave-to {
  opacity: 0;
}

@keyframes dialog-in {
  from { opacity: 0; transform: scale(0.92) translateY(20px); }
  to { opacity: 1; transform: scale(1) translateY(0); }
}
</style>
