<template>
  <div class="situation-page">
    <!-- 星空粒子背景（Cesium 地球之下，填补深空区域） -->
    <Starfield :density="0.9" :opacity="0.8" />
    <div id="cesiumContainer"></div>

    <!-- 轨道数据加载提示：首次需后端解算全部卫星轨道，耗时较长时给出明确反馈 -->
    <transition name="fade">
      <div v-if="czmlLoading" class="czml-loading">
        <div class="czml-loading-ring"></div>
        <div class="czml-loading-text">正在解算卫星轨道数据…</div>
        <div class="czml-loading-sub">ORBIT DATA COMPUTING</div>
      </div>
    </transition>

    <!-- 中央态势装饰环（纯装饰，不遮挡交互） -->
    <div class="center-hud">
      <div class="radar-ring ring-a"></div>
      <div class="radar-ring ring-b"></div>
      <div class="crosshair crosshair-h"></div>
      <div class="crosshair crosshair-v"></div>
    </div>

    <!-- 顶部标题栏（左侧内嵌紧凑指标，避免悬浮卡片遮挡地球） -->
    <div class="hud top-header">
      <div class="header-stats">
        <div class="hs-item"><b><CountUp :value="satList.length" /></b><span>在线卫星</span></div>
        <div class="hs-item"><b><CountUp :value="runningTaskCount" /></b><span>正在执行</span></div>
        <div class="hs-item"><b><CountUp :value="satisfaction" suffix="%" /></b><span>任务满足率</span></div>
        <div class="hs-item"><b><CountUp :value="planDuration" :decimals="1" suffix="s" /></b><span>规划耗时</span></div>
      </div>
      <div class="sys-title">
        卫星网络态势监控
        <span class="sub-title">SATELLITE NETWORK SITUATION</span>
      </div>
      <div class="header-right">
        <div class="sim-time">仿真时间&nbsp;{{ simTime }}</div>
        <button class="fullscreen-btn" :title="isFullscreen ? '退出全屏' : '全屏展示'" @click="toggleFullscreen">
          <svg v-if="!isFullscreen" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5"/></svg>
          <svg v-else viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M9 4v5H4M15 4v5h5M9 20v-5H4M15 20v-5h5"/></svg>
        </button>
      </div>
    </div>

    <!-- 左侧卫星列表 -->
    <div class="hud left-panel">
      <i class="pc pc-tr"></i><i class="pc pc-bl"></i>
      <div class="panel-title">实时卫星列表（{{ filteredSats.length }}/{{ satList.length }}）</div>
      <div class="sat-search">
        <input v-model.trim="satSearch" class="sat-search-input" type="text" placeholder="搜索卫星名称 / 载荷类型…" />
        <span v-if="satSearch" class="sat-search-clear" @click="satSearch = ''">×</span>
      </div>
      <div class="sat-list">
        <div v-for="sat in filteredSats" :key="sat.id" class="sat-item" @click="focusSat(sat)">
          <input type="checkbox" class="sat-check" :checked="isSatChecked(sat.name)"
                 @click.stop @change="toggleSatVisible(sat.name, $event.target.checked)" />
          <span class="sat-name">{{ sat.name }}</span>
          <span class="sat-payload">{{ sat.loadType }}</span>
          <span class="sat-battery" :class="satDotClass(sat)">{{ sat.battery }}Wh</span>
        </div>
        <div v-if="filteredSats.length === 0" class="empty-tip">{{ satList.length === 0 ? '暂无卫星数据，请先完成系统初始化' : '未找到匹配的卫星' }}</div>
      </div>
      <div class="panel-title">任务执行进度（{{ taskList.length }}）</div>
      <div class="task-list">
        <div v-for="task in taskList" :key="task.task_name" class="task-item">
          <div class="task-head">
            <span class="task-name">{{ task.task_name }}</span>
            <span class="task-pct">{{ taskProgress(task) }}%</span>
          </div>
          <div class="progress-track">
            <div class="progress-fill" :class="{ urgent: task.is_urgent }" :style="{ width: taskProgress(task) + '%' }"></div>
          </div>
        </div>
        <div v-if="taskList.length === 0" class="empty-tip">暂无任务数据</div>
      </div>
      <div class="panel-title">载荷类型分布</div>
      <div ref="payloadChart" class="payload-chart"></div>
      <div class="panel-title">常用功能</div>
      <div class="quick-actions">
        <div class="detail-row"><span>全部轨迹</span>
          <label class="hud-switch"><input type="checkbox" :checked="globalPathShow" @change="toggleAllPaths($event.target.checked)"><i></i></label>
        </div>
        <div class="detail-row"><span>全部视锥体</span>
          <label class="hud-switch"><input type="checkbox" :checked="globalFrustumShow" @change="toggleAllFrustums($event.target.checked)"><i></i></label>
        </div>
        <div class="detail-row"><span>实时事件栏</span>
          <label class="hud-switch"><input type="checkbox" :checked="showEventBar" @change="showEventBar = $event.target.checked"><i></i></label>
        </div>
        <div class="detail-row"><span>通信链路</span>
          <label class="hud-switch"><input type="checkbox" :checked="globalLinkShow" @change="toggleAllLinks($event.target.checked)"><i></i></label>
        </div>
        <div class="detail-row"><span>地球自转展示</span>
          <label class="hud-switch"><input type="checkbox" :checked="autoRotate" @change="toggleAutoRotate($event.target.checked)"><i></i></label>
        </div>
      </div>
    </div>

    <!-- 右侧面板：卫星详情 + 态势图表 -->
    <div class="hud right-panel">
      <i class="pc pc-tr"></i><i class="pc pc-bl"></i>
      <div class="panel-title">
        卫星详情
        <span class="close-btn" v-show="selectedSat" @click="closeDetail">×</span>
      </div>
      <template v-if="selectedSat">
        <div class="detail-name">{{ selectedSat.name }}</div>
        <div class="detail-row"><span>纬度</span><b>{{ selectedSat.lat }}°</b></div>
        <div class="detail-row"><span>经度</span><b>{{ selectedSat.lng }}°</b></div>
        <div class="detail-row"><span>高度</span><b>{{ selectedSat.height }} km</b></div>
        <template v-if="selectedSat.info">
          <div class="detail-row"><span>载荷类型</span><b>{{ selectedSat.info.loadType }}</b></div>
          <div class="detail-row"><span>分辨率</span><b>{{ selectedSat.info.resolution }} m</b></div>
          <div class="detail-row"><span>电量</span><b>{{ selectedSat.info.battery }} Wh</b></div>
          <div class="detail-row"><span>存储</span><b>{{ selectedSat.info.storage }} GB</b></div>
        </template>
        <div class="detail-row"><span>周期</span><b>{{ selectedExtra ? satPeriod(selectedExtra.tle2) : '-' }}</b></div>
        <div class="detail-row"><span>时间</span><b>{{ simTime }}</b></div>
        <div class="detail-row"><span>俯仰角</span><b>{{ selectedExtra ? selectedExtra.pitchAngle + '°' : '-' }}</b></div>
        <div class="detail-row"><span>侧摆角</span><b>{{ selectedExtra ? selectedExtra.rollAngle + '°' : '-' }}</b></div>
        <div class="detail-row"><span>相连地面站</span><b>{{ selectedExtra ? fmtConn(selectedExtra.connecting_ground_station) : '无' }}</b></div>
        <div class="detail-row"><span>相连高轨卫星</span><b>{{ selectedExtra ? fmtConn(selectedExtra.connecting_geo) : '无' }}</b></div>
        <div class="detail-row"><span>是否显示路径</span>
          <label class="hud-switch"><input type="checkbox" :checked="getSatSwitch(selectedSat.name).path" @change="togglePathShow(selectedSat.name, $event.target.checked)"><i></i></label>
        </div>
        <div class="detail-row"><span>是否显示视锥体</span>
          <label class="hud-switch"><input type="checkbox" :checked="isFrustumShown(selectedSat.name)" @change="toggleFrustumShow(selectedSat.name, $event.target.checked)"><i></i></label>
        </div>
        <button class="hide-detail-btn" @click="closeDetail">隐藏</button>
        <!-- 星下点轨迹小地图（仅选中卫星时显示） -->
        <div class="panel-title subtrack-title">星下点轨迹</div>
        <SubTrackMap :entity="selectedEntity" :viewer="viewerRef" :period-min="selectedPeriodMin" />
      </template>
      <div v-else class="chart-empty detail-empty-static">点击卫星或左侧列表查看详情</div>
      <div class="panel-title">任务状态统计</div>
      <div ref="taskStatusChart" class="right-chart"></div>
      <div class="panel-title">任务满足率趋势</div>
      <div class="right-chart chart-wrap">
        <div ref="satisfactionChart" class="chart-inner"></div>
        <div v-if="!hasSatisfaction" class="chart-empty">暂无规划数据<br/>运行任务规划后展示趋势</div>
      </div>
    </div>

    <!-- 底部告警/事件滚动栏 -->
    <div class="hud bottom-bar" v-show="showEventBar">
      <span class="bottom-label"><i class="dot"></i>实时事件</span>
      <div class="event-scroll">
        <div class="event-track">
          <span v-for="(ev, i) in eventList" :key="i" class="event-item" :class="ev.level">{{ ev.text }}</span>
          <span v-if="eventList.length === 0" class="event-item">系统运行正常，暂无告警事件</span>
        </div>
      </div>
    </div>
  </div>
</template>
  
<script setup>
  import { onMounted, onUnmounted, ref, reactive, computed } from "vue";
  import * as Cesium from "cesium";
  import echarts from "@/utils/echarts.js";
  import { authFetch } from "@/utils/authFetch.js";
  import Starfield from "@/components/Starfield.vue";
  import CountUp from "@/components/CountUp.vue";
  import SubTrackMap from "@/components/SubTrackMap.vue";

  // 提亮加青色光晕的卫星图标（替换 CZML 内置的暗色 16px 图标）
  const SAT_ICON_URI = "data:image/png;base64,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";

  // ===== 大屏 HUD 数据状态 =====
  const simTime = ref('--');
  const czmlLoading = ref(true);  // 轨道数据加载中（首次生成需解算全部卫星轨道，耗时较长）
  const satList = ref([]);
  const runningTaskCount = ref(0);
  const satisfaction = ref('--');
  const planDuration = ref('--');
  const hasSatisfaction = ref(false);  // 是否已有规划评估数据（控制趋势图空态）
  const selectedSat = ref(null);
  const taskList = ref([]);       // 任务列表（左侧任务执行进度面板）
  const eventList = ref([]);      // 底部实时事件滚动队列
  let viewerRef = null;        // Cesium viewer 引用
  let satDataSource = null;    // 卫星 CZML 数据源引用
  const satDsReady = ref(0);   // satDataSource 赋值完成的响应式标志（computed 依赖用）
  let satEntities = [];        // 所有卫星 CZML 实体（供全局显隐开关遍历）
  let satGlowPoints = null;    // 卫星轨道拖尾光点 Map（key: 实体 id）
  let frustumPrims = null;     // 卫星视锥填充体 Map（key: 实体 id）
  let outlinePrims = null;     // 卫星视锥轮廓 Map
  let linkDataSource = null;   // 通信链路数据源（星间链路 + 星地数传链路）
  const linkTargetMap = {};    // 卫星链路连接表（key: satName → {gs, geo}），供链路 CallbackProperty 实时读取
  const hiddenFrustumId = ref(null);  // 当前被隐藏视锥的卫星实体 id（选中自动隐藏）
  const focusMode = ref(false);       // 跟踪视角：隐藏全部视锥，避免近距离巨锥糊满屏幕
  const satCheckedMap = reactive({});  // 卫星勾选状态记忆（key: 卫星名，默认勾选）
  const satSwitchMap = reactive({});   // 每颗卫星的路径/视锥体开关记忆（key: 卫星名）
  const globalPathShow = ref(false);   // 常用功能：全部轨迹开关（默认关：200 条拖尾全开会糊满屏幕）
  const globalFrustumShow = ref(false); // 常用功能：全部视锥体开关（默认关：视锥全开遮挡地球）
  const globalLinkShow = ref(false);   // 常用功能：通信链路开关（默认关：链路全开交织成网）
  const showEventBar = ref(true);      // 常用功能：实时事件栏开关
  const satInfoMap = ref({});          // getAllSatelliteInfo 结果（key: satName）
  let hudTimer = null;
  const prevTaskStatus = {};        // 任务状态快照，用于比对生成事件
  const lowBatteryWarned = new Set(); // 已报过低电量告警的卫星
  let lastSatisfaction = null;      // 上一次满足率，用于生成规划完成事件
  const satSearch = ref('');        // 卫星列表搜索关键字（名称 / 载荷类型）
  const isFullscreen = ref(false);  // 全屏展示状态
  const autoRotate = ref(false);    // 地球自转展示开关（跟踪卫星时自动暂停）
  let rotateHandler = null;         // Cesium postRender 自转回调引用

  // 按关键字过滤卫星列表（匹配名称或载荷类型，不区分大小写）
  const filteredSats = computed(() => {
    const kw = satSearch.value.toLowerCase();
    if (!kw) return satList.value;
    return satList.value.filter(s =>
      String(s.name).toLowerCase().includes(kw) ||
      String(s.loadType || '').toLowerCase().includes(kw));
  });

  // 全屏展示切换（演示模式：浏览器级全屏）
  function toggleFullscreen() {
    if (document.fullscreenElement) {
      document.exitFullscreen();
    } else {
      document.documentElement.requestFullscreen().catch(() => {});
    }
  }
  function onFullscreenChange() {
    isFullscreen.value = !!document.fullscreenElement;
  }

  // 地球自转展示：相机绕地轴缓慢旋转；用户选中卫星进入跟踪时自动暂停
  function toggleAutoRotate(on) {
    autoRotate.value = on;
    if (!viewerRef) return;
    if (on) {
      rotateHandler = viewerRef.scene.postRender.addEventListener(() => {
        // 跟踪视角下暂停自转，避免视角漂移
        if (!focusMode.value) {
          viewerRef.scene.camera.rotate(Cesium.Cartesian3.UNIT_Z, -Cesium.Math.toRadians(0.02));
        }
      });
    } else if (rotateHandler) {
      rotateHandler();
      rotateHandler = null;
    }
  }

  // Esc 快捷关闭详情面板并退出跟踪视角
  function onKeydown(e) {
    if (e.key === 'Escape' && selectedSat.value) closeDetail();
  }
  // 页面回到前台时补刷一次 HUD，避免数据滞后
  function onVisibility() {
    if (!document.hidden) refreshHud();
  }

  // 面板数据轮询
  async function refreshHud() {
    try {
      const r = await authFetch('/getCurrentTime');
      const d = await r.json();
      simTime.value = (d.current_time || '--').slice(0, 19);
    } catch (e) { /* 后端未就绪时静默 */ }
    try {
      const r = await authFetch('/satellites/getAllSatellites', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}'
      });
      const d = await r.json();
      satList.value = Array.isArray(d) ? d : [];
      updatePayloadChart();
      checkLowBattery(satList.value);
    } catch (e) { }
    try {
      const r = await authFetch('/satellites/getAllSatelliteInfo', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}'
      });
      const d = await r.json();
      if (Array.isArray(d)) {
        const m = {};
        d.forEach(s => { m[s.satName] = s; });
        satInfoMap.value = m;
        // 同步刷新链路连接表（星间链路/星地链路 CallbackProperty 实时读取）
        d.forEach(s => {
          linkTargetMap[s.satName] = { gs: s.connecting_ground_station, geo: s.connecting_geo };
        });
      }
    } catch (e) { }
    try {
      const r = await authFetch('/tasks/getNewTasksByCondition');
      const d = await r.json();
      const tasks = Array.isArray(d) ? d : [];
      taskList.value = tasks;
      runningTaskCount.value = tasks.filter(t => t.status === '正在执行').length;
      diffTaskEvents(tasks);
      updateTaskStatusChart();
    } catch (e) { }
    try {
      const r = await authFetch('/getPlanningEvaluation');
      const d = await r.json();
      const ev = d.evaluation;
      if (ev && ev.length > 0) {
        hasSatisfaction.value = true;
        const latest = ev[ev.length - 1];
        const sat = Math.round((latest.task_satisfaction || 0) * 100);
        if (lastSatisfaction !== null && lastSatisfaction !== sat) {
          pushEvent(`任务规划完成，满足率 ${sat}%`);
        }
        lastSatisfaction = sat;
        satisfaction.value = sat;
        planDuration.value = (latest.duration || 0).toFixed(1);
        updateSatisfactionChart(ev.slice(-10));
      }
    } catch (e) { }
  }

  // 载荷类型分布环形图
  const payloadChart = ref(null);
  let payloadChartInst = null;
  function updatePayloadChart() {
    if (!payloadChart.value) return;
    if (!payloadChartInst) payloadChartInst = echarts.init(payloadChart.value);
    const counts = {};
    satList.value.forEach(s => { counts[s.loadType] = (counts[s.loadType] || 0) + 1; });
    const colors = { optical: '#00dcff', infrared: '#ffd657', SAR: '#7cffb2' };
    payloadChartInst.setOption({
      tooltip: { trigger: 'item' },
      legend: { bottom: 0, textStyle: { color: '#9fc6e8', fontSize: 11 }, itemWidth: 12, itemHeight: 8 },
      series: [{
        type: 'pie',
        radius: ['45%', '70%'],
        center: ['50%', '42%'],
        label: { show: false },
        data: Object.keys(counts).map(k => ({
          name: k, value: counts[k],
          itemStyle: { color: colors[k] || '#5b8ff9' }
        }))
      }]
    });
  }

  // ===== 任务进度 / 事件聚合 / 右侧图表 =====
  // 任务执行进度百分比：按仿真时间在 [start_time, end_time] 中的位置估算
  function taskProgress(task) {
    if (task.status === '已完成') return 100;
    if (task.status === '等待规划') return 0;
    const start = new Date(String(task.start_time).replace(' ', 'T'));
    const end = new Date(String(task.end_time).replace(' ', 'T'));
    const now = new Date(simTime.value.replace(' ', 'T'));
    if (isNaN(start) || isNaN(end) || isNaN(now) || end <= start) {
      return task.status === '正在执行' ? 50 : 0;
    }
    return Math.min(100, Math.max(0, Math.round((now - start) / (end - start) * 100)));
  }

  // 底部事件队列：追加一条事件，最多保留 30 条
  function pushEvent(text, level = 'info') {
    const time = simTime.value.length >= 19 ? simTime.value.slice(11, 19) : '';
    eventList.value.push({ text: `${time} ${text}`, level });
    if (eventList.value.length > 30) eventList.value.splice(0, eventList.value.length - 30);
  }

  // 对比任务状态快照，生成“新任务 / 状态变更”事件
  function diffTaskEvents(tasks) {
    const hasSnapshot = Object.keys(prevTaskStatus).length > 0;
    tasks.forEach(t => {
      const prev = prevTaskStatus[t.task_name];
      if (prev === undefined) {
        if (hasSnapshot) pushEvent(`发现新任务 ${t.task_name}`);
      } else if (prev !== t.status) {
        pushEvent(`任务 ${t.task_name} 状态变更：${prev} → ${t.status}`, t.status === '正在执行' ? 'warn' : 'info');
      }
      prevTaskStatus[t.task_name] = t.status;
    });
  }

  // 卫星低电量告警（每颗卫星只报一次）
  function checkLowBattery(sats) {
    sats.forEach(s => {
      if (typeof s.battery === 'number' && s.battery < 20 && !lowBatteryWarned.has(s.name)) {
        lowBatteryWarned.add(s.name);
        pushEvent(`卫星 ${s.name} 电量过低（${s.battery}Wh），请注意`, 'alarm');
      }
    });
  }

  // 右侧：任务状态统计柱状图
  const taskStatusChart = ref(null);
  let taskStatusChartInst = null;
  function updateTaskStatusChart() {
    if (!taskStatusChart.value) return;
    if (!taskStatusChartInst) taskStatusChartInst = echarts.init(taskStatusChart.value);
    const counts = {};
    taskList.value.forEach(t => { counts[t.status] = (counts[t.status] || 0) + 1; });
    const names = Object.keys(counts);
    const palette = { '等待规划': '#7fd4ff', '正在执行': '#ffd657', '已完成': '#7cffb2' };
    taskStatusChartInst.setOption({
      grid: { top: 12, left: 36, right: 10, bottom: 22 },
      xAxis: {
        type: 'category', data: names,
        axisLabel: { color: '#9fc6e8', fontSize: 10 },
        axisLine: { lineStyle: { color: 'rgba(0,220,255,0.3)' } }
      },
      yAxis: {
        type: 'value', minInterval: 1,
        axisLabel: { color: '#9fc6e8', fontSize: 10 },
        splitLine: { lineStyle: { color: 'rgba(0,220,255,0.1)' } }
      },
      series: [{
        type: 'bar', barWidth: 16,
        data: names.map(n => {
          const c = palette[n] || '#00dcff';
          return {
            value: counts[n],
            // 柱体纵向渐变 + 顶部发光，贴合 HUD 质感
            itemStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: c },
                { offset: 1, color: c + '33' }
              ]),
              borderRadius: [2, 2, 0, 0],
              shadowColor: c + '88',
              shadowBlur: 6
            }
          };
        })
      }]
    });
  }

  // 右侧：任务满足率趋势折线图（取最近 10 次规划评估）
  const satisfactionChart = ref(null);
  let satisfactionChartInst = null;
  function updateSatisfactionChart(evList) {
    if (!satisfactionChart.value) return;
    if (!satisfactionChartInst) satisfactionChartInst = echarts.init(satisfactionChart.value);
    const data = evList.map(e => Math.round((e.task_satisfaction || 0) * 100));
    satisfactionChartInst.setOption({
      grid: { top: 12, left: 36, right: 10, bottom: 22 },
      xAxis: {
        type: 'category', data: data.map((_, i) => i + 1),
        axisLabel: { color: '#9fc6e8', fontSize: 10 },
        axisLine: { lineStyle: { color: 'rgba(0,220,255,0.3)' } }
      },
      yAxis: {
        type: 'value', min: 0, max: 100,
        axisLabel: { color: '#9fc6e8', fontSize: 10, formatter: '{value}%' },
        splitLine: { lineStyle: { color: 'rgba(0,220,255,0.1)' } }
      },
      series: [{
        type: 'line', data, smooth: true,
        symbol: 'circle', symbolSize: 5,
        lineStyle: { color: '#00f0ff', width: 2, shadowColor: 'rgba(0,240,255,0.6)', shadowBlur: 8 },
        itemStyle: { color: '#00f0ff' },
        areaStyle: { color: 'rgba(0, 220, 255, 0.15)' }
      }]
    });
  }

  // 当前选中卫星的扩展信息（getAllSatelliteInfo 返回，按 satName 匹配）
  const selectedExtra = computed(() =>
    selectedSat.value ? (satInfoMap.value[selectedSat.value.name] || null) : null
  );

  // 当前选中卫星的 Cesium 实体（星下点小地图数据源）
  const selectedEntity = computed(() => {
    // 依赖 satDsReady：CZML 异步加载完成后触发重算
    void satDsReady.value;
    if (!selectedSat.value || !satDataSource) return null;
    return satDataSource.entities.getById(`Satellite/${selectedSat.value.name}`) || null;
  });
  // 当前选中卫星的轨道周期（分钟，数值型；供小地图回溯采样）
  const selectedPeriodMin = computed(() => {
    const tle2 = selectedExtra.value && selectedExtra.value.tle2;
    if (!tle2 || tle2.length < 63) return 95;
    const mm = parseFloat(tle2.substring(52, 63));
    return (isNaN(mm) || mm <= 0) ? 95 : 1440 / mm;
  });

  // 由 TLE 第二行计算轨道周期（分钟）：周期 = 1440 / 平均运动（第 53-63 列，rev/day），解析失败显示 '-'
  function satPeriod(tle2) {
    if (!tle2 || tle2.length < 63) return '-';
    const mm = parseFloat(tle2.substring(52, 63));
    if (isNaN(mm) || mm <= 0) return '-';
    return (1440 / mm).toFixed(2) + ' min';
  }

  // 连接对象显示格式化：无连接显示“无”
  function fmtConn(v) {
    if (v === null || v === undefined || v === '') return '无';
    return Array.isArray(v) ? (v.length ? v.join('、') : '无') : String(v);
  }

  // 卫星列表状态呼吸灯：电量 <20 红色告警，<50 黄色关注，否则绿色在线
  function satDotClass(sat) {
    if (typeof sat.battery === 'number') {
      if (sat.battery < 20) return 'dot-alarm';
      if (sat.battery < 50) return 'dot-warn';
    }
    return 'dot-ok';
  }

  // 卫星勾选状态（默认勾选），轮询刷新列表时不重置
  function isSatChecked(name) {
    return satCheckedMap[name] !== false;
  }

  // 每颗卫星的路径/视锥体开关状态（默认均开）
  function getSatSwitch(name) {
    if (!satSwitchMap[name]) satSwitchMap[name] = { path: true, frustum: true };
    return satSwitchMap[name];
  }

  // 显示/隐藏指定卫星的视锥（填充体 + 轮廓）
  function setFrustumVisible(id, show) {
    const fp = frustumPrims && frustumPrims.get(id);
    const op = outlinePrims && outlinePrims.get(id);
    if (fp) fp.show = show;
    if (op) op.show = show;
  }

  // 按当前全部状态（勾选、全局开关、单星开关、选中自动隐藏）刷新一颗卫星的场景显隐
  function applySatVisibility(name) {
    if (!satDataSource) return;
    const id = `Satellite/${name}`;
    const checked = isSatChecked(name);
    const sw = getSatSwitch(name);
    const entity = satDataSource.entities.getById(id);
    if (entity) {
      entity.show = checked;  // 标签/billboard/轨迹整体隐显
      if (entity.path) entity.path.show = checked && globalPathShow.value && sw.path;
    }
    const glow = satGlowPoints && satGlowPoints.get(id);
    if (glow) glow.show = checked;
    setFrustumVisible(id, checked && globalFrustumShow.value && sw.frustum && hiddenFrustumId.value !== id && !focusMode.value);
  }

  // 刷新所有卫星的场景显隐（全局开关切换 / CZML 加载完成后调用）
  function applyAllVisibility() {
    satEntities.forEach(e => applySatVisibility(e.name || String(e.id).split('/')[1]));
  }

  // 左侧列表勾选框：控制卫星在 3D 场景中的显示/隐藏
  function toggleSatVisible(name, checked) {
    satCheckedMap[name] = checked;
    applySatVisibility(name);
  }

  // 详情面板开关：当前选中卫星的轨迹显隐
  function togglePathShow(name, show) {
    getSatSwitch(name).path = show;
    applySatVisibility(name);
  }

  // 详情面板开关：当前选中卫星的视锥显隐
  function toggleFrustumShow(name, show) {
    getSatSwitch(name).frustum = show;
    // 用户手动打开时解除“选中自动隐藏”与跟踪隐藏，让开关立即生效
    const id = `Satellite/${name}`;
    if (show && hiddenFrustumId.value === id) hiddenFrustumId.value = null;
    if (show && focusMode.value) { focusMode.value = false; applyAllVisibility(); return; }
    applySatVisibility(name);
  }
  // 常用功能：全部轨迹显示/隐藏
  function toggleAllPaths(show) {
    globalPathShow.value = show;
    applyAllVisibility();
  }

  // 常用功能：全部视锥体显示/隐藏
  function toggleAllFrustums(show) {
    globalFrustumShow.value = show;
    applyAllVisibility();
  }

  // 常用功能：通信链路显示/隐藏（星间链路 + 星地数传链路）
  function toggleAllLinks(show) {
    globalLinkShow.value = show;
    if (linkDataSource) linkDataSource.show = show;
  }

  // 视锥开关显示值：开关状态 && 未被选中自动隐藏
  function isFrustumShown(name) {
    return getSatSwitch(name).frustum && hiddenFrustumId.value !== `Satellite/${name}`;
  }

  // 选中卫星时进入跟踪视角：隐藏所有视锥（含其他卫星），避免巨锥糊满屏幕
  function onSelectSat(name) {
    focusMode.value = true;
    if (hiddenFrustumId.value) {
      hiddenFrustumId.value = null;
    }
    hiddenFrustumId.value = `Satellite/${name}`;
    applyAllVisibility();  // 跟踪隐藏影响所有卫星的视锥，需整体刷新
  }
  // 关闭详情：退出跟踪视角、恢复视锥显示，相机飞回全球视角（页面无 homeButton，需手动复位）
  function closeDetail() {
    focusMode.value = false;
    if (hiddenFrustumId.value) {
      hiddenFrustumId.value = null;
    }
    selectedSat.value = null;
    applyAllVisibility();
    // 飞回全球俯瞰视角（flyHome 已被上面的初始 setView 覆盖为全球视角）
    if (viewerRef) viewerRef.camera.flyHome(2);
  }

  // 点击左侧列表项：飞向对应卫星
  function focusSat(sat) {
    if (!viewerRef || !satDataSource) return;
    const entity = satDataSource.entities.getById(`Satellite/${sat.name}`);
    if (entity) viewerRef.flyTo(entity, { duration: 2 });
    onSelectSat(sat.name);
    // 与 3D 场景点击一致：计算卫星当前真实经纬度/高度，取不到时保持 '--'
    let lat = '--', lng = '--', height = '--';
    if (entity) {
      const pos = entity.position.getValue(viewerRef.clock.currentTime);
      if (pos) {
        const carto = Cesium.Cartographic.fromCartesian(pos);
        lat = Cesium.Math.toDegrees(carto.latitude).toFixed(2);
        lng = Cesium.Math.toDegrees(carto.longitude).toFixed(2);
        height = (carto.height / 1000).toFixed(1);
      }
    }
    selectedSat.value = { name: sat.name, lat, lng, height, info: sat };
  }

  // 窗口大小变化时重排三个 ECharts 图表
  function handleResize() {
    if (payloadChartInst) payloadChartInst.resize();
    if (taskStatusChartInst) taskStatusChartInst.resize();
    if (satisfactionChartInst) satisfactionChartInst.resize();
  }

  onUnmounted(() => {
    if (hudTimer) { clearInterval(hudTimer); hudTimer = null; }
    window.removeEventListener('resize', handleResize);
    window.removeEventListener('keydown', onKeydown);
    document.removeEventListener('fullscreenchange', onFullscreenChange);
    document.removeEventListener('visibilitychange', onVisibility);
    if (rotateHandler) { rotateHandler(); rotateHandler = null; }
    if (payloadChartInst) { payloadChartInst.dispose(); payloadChartInst = null; }
    if (taskStatusChartInst) { taskStatusChartInst.dispose(); taskStatusChartInst = null; }
    if (satisfactionChartInst) { satisfactionChartInst.dispose(); satisfactionChartInst = null; }
    // 销毁 Cesium viewer，释放 WebGL 上下文（反复进出页面时防泄漏）；
    // viewer.destroy() 会一并清理 dataSources、onTick 监听器与 screenSpaceEventHandler
    if (viewerRef) {
      viewerRef.destroy();
      viewerRef = null;
    }
    satDataSource = null;
    satEntities = [];
    satGlowPoints = null;
    frustumPrims = null;
    outlinePrims = null;
    linkDataSource = null;
    hiddenFrustumId.value = null;
  });
  // ===== HUD 结束 =====
 
  
  onMounted(() => {
    // ArcGIS影像图层 对浏览器会有压力
    // const esri = new Cesium.ArcGisMapServerImageryProvider({
    //   url:"https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer",
    //   enablePickFeatures:false
    // })
    // 底图：Esri 全球卫星影像。高德 style=6 瓦片在海洋/偏远区域 z8 起即返回
    // “此区域无卫星图”占位图；Esri 全球覆盖至 z13，设 maximumLevel 后更高层级
    // 自动拉伸低级瓦片，任何区域都不会出现占位文字。
    const esri = new Cesium.UrlTemplateImageryProvider({
      url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
      maximumLevel: 13
    });
    // 叠加高德中文路网/地名注记层（透明 PNG，仅标注，不遮挡影像）
    const amapLabel = new Cesium.UrlTemplateImageryProvider({
      url: 'https://webst0{s}.is.autonavi.com/appmaptile?style=8&x={x}&y={y}&z={z}',
      subdomains: ['1', '2', '3', '4'],
      maximumLevel: 13
    });
    // 创建 Cesium 视图
    let viewer = new Cesium.Viewer("cesiumContainer", {
      baseLayer:false, // 禁用默认 Ion 底图（token 已失效会报 401），底图改用下方高德瓦片
      animation:false, // 动画控件（隐藏，保持 HUD 大屏整洁）
      timeline:true, // 时间轴控件（底部显示，可拖动查看轨迹时刻）
      geocoder:false, // 地理编码搜索控件
      homeButton:false, // 主页控件
      sceneModePicker:false, // 投影方式控件
      baseLayerPicker:false, // 图层选择控件
      navigationHelpButton:false, // 帮助控件
      fullscreenButton:false, // 全屏控件
      selectionIndicator:false, // 选取指示器组件
      infoBox: false, // 信息框，If set to false, the InfoBox widget will not be created.点击的详情弹窗entity的description可以描述html显示在弹窗中,也可以通过viewer.infoBox.frame来接入访问
      contextOptions: {
          webgl:{
            alpha: true,
            depth:true,
            stencil:true,
            antialias:true,
            premultipliedAlpha:true,
            //通过canvas.toDataURL()实现截图需要将该项设置为true
            preserveDrawingBuffer:true,
            failIfMajorPerformanceCaveat:true
          }
        }
      // terrainProvider:Cesium.createWorldTerrain({
      //   requestWaterMask:true, // 水面特效 对浏览器会有压力
      // }),
    });
    //去掉版权信息
    viewer.clock.shouldAnimate = true;
    viewer._cesiumWidget._creditContainer.style.display = "none"
    viewerRef = viewer;  // 供 HUD 面板使用
    // 初始与"回家"视角：全球俯瞰（CZML 加载后默认会缩放到数据可用区间起点、
    // 高度贴地导致底图瓦片加载不出显示灰块，这里显式设为全球视角并覆盖默认 HOME）
    const HOME_DEST = Cesium.Cartesian3.fromDegrees(105, 12, 2.6e7);
    viewer.camera.setView({ destination: HOME_DEST });
    viewer.camera.flyHome(0);
    viewer.scene.screenSpaceCameraController.enableCollisionDetection = false;
    window.addEventListener('keydown', onKeydown);
    document.addEventListener('fullscreenchange', onFullscreenChange);
    // 添加底图（构造函数传 imageryProvider 会加载失败显示蓝色球体，需在创建后通过 imageryLayers 添加）
    viewer.imageryLayers.removeAll();
    viewer.imageryLayers.addImageryProvider(esri);
    const amapLabelLayer = viewer.imageryLayers.addImageryProvider(amapLabel);
    // 注记层按相机高度分级显隐：全球视角（>1200万米）下中文地名密成一团且浪费瓦片请求，
    // 仅在拉近到区域/城市级别时显示
    const updateLabelVisibility = () => {
      amapLabelLayer.show = viewer.camera.positionCartographic.height < 1.2e7;
    };
    viewer.camera.changed.addEventListener(updateLabelVisibility);
    viewer.camera.percentageChanged = 0.01;  // 默认 0.5 节流阈值太大，小范围移动不触发
    updateLabelVisibility();
    // // 把cesium的动画开关打开
    // viewer.clock.shouldAnimate = true;
    // window.viewer = viewer;
    // localStorage.setItem("viewer", viewer);
    // 加载 CZML 数据：优先使用后端根据当前 TLE 动态生成的数据，失败时回退本地静态文件
    // 首次生成需解算全部卫星轨道，耗时较长，期间展示加载提示
    async function loadCzmlDataSource() {
      czmlLoading.value = true;
      try {
        const res = await authFetch('/getCzml');
        if (res.ok) {
          const data = await res.json();
          if (Array.isArray(data) && data.length > 1) {
            return Cesium.CzmlDataSource.load(data);
          }
        }
        console.warn("后端 CZML 数据不可用，回退到本地静态文件");
      } catch (e) {
        console.warn("后端 CZML 获取失败，回退到本地静态文件:", e);
      }
      // 回退本地静态文件（放在 public/ 下，生产构建后路径仍有效）
      return Cesium.CzmlDataSource.load("/wx.czml");
    }
    const czmldata = loadCzmlDataSource();
    viewer.dataSources.add(czmldata);
  
    // 别忘记把 Cesium 的动画开关打开
    viewer.clock.shouldAnimate = true;
  
    // 在 CZML 数据加载完成后，为特定卫星添加扫描圆锥并绑定点击事件
    czmldata.then((dataSource) => {
      czmlLoading.value = false;   // 轨道数据就绪，关闭加载提示
      satDataSource = dataSource;  // 供 HUD 面板使用
      satDsReady.value++;          // 通知响应式依赖（selectedEntity 等）数据源就绪
      satGlowPoints = new Map();   // 轨道拖尾光点（key: 卫星实体 id）
  
      // 找到 ID 为 'Sat_1_1' 的卫星
      const satellite1 = dataSource.entities.getById("Satellite/Sat_1_1");
      const satellite2 = dataSource.entities.getById("Satellite/Sat_2_1");
      const satellite3 = dataSource.entities.getById("Satellite/Sat_3_1");
      // 找到所有 ID 以 "Sat_" 开头的卫星实体
      const satelliteEntities = [];
      dataSource.entities.values.forEach(entity => {
          if (entity.id.includes("Sat_")) {
              satelliteEntities.push(entity);
          }
      });
      satEntities = satelliteEntities;  // 供全局显隐开关使用

      // 通信链路：为每颗卫星创建星间链路（→高轨中继星，橙色虚线）与星地数传链路（→地面站，亮青实线）
      // 连接目标由 linkTargetMap 提供（refreshHud 轮询刷新），CallbackProperty 跟随卫星实时位置
      satelliteEntities.forEach(entity => {
          const satName = String(entity.id).split('/')[1];
          const getSatPos = (time) => entity.position.getValue(time) || entity.position.getValue(viewer.clock.currentTime);
          // 星间链路：卫星 → 相连高轨卫星（低透明虚线，构成全网拓扑）
          linkDataSource.entities.add({
              polyline: {
                  // 200 条星间虚线近距离会糊满背景，仅当相机拉远（距地心 >3.5e7m，可看到 GEO 拓扑）时显示
                  show: new Cesium.CallbackProperty(() => {
                      const t = linkTargetMap[satName];
                      if (!isSatChecked(satName) || !(t && t.geo && GEO_POSITIONS[t.geo])) return false;
                      return Cesium.Cartesian3.magnitude(viewer.camera.position) > 3.5e7;
                  }, false),
                  positions: new Cesium.CallbackProperty((time) => {
                      const pos = getSatPos(time);
                      const t = linkTargetMap[satName];
                      if (!pos || !t || !GEO_POSITIONS[t.geo]) return [Cesium.Cartesian3.ZERO, Cesium.Cartesian3.ZERO];
                      return [pos, GEO_POSITIONS[t.geo]];
                  }, false),
                  width: 1,
                  arcType: Cesium.ArcType.NONE,  // 空间直线，不贴地
                  material: new Cesium.PolylineDashMaterialProperty({
                      color: Cesium.Color.fromCssColorString('#ffd657').withAlpha(0.28),
                      dashLength: 12
                  })
              }
          });
          // 星地链路：数传窗口内卫星 → 相连地面站
          linkDataSource.entities.add({
              polyline: {
                  show: new Cesium.CallbackProperty(() => {
                      const t = linkTargetMap[satName];
                      return isSatChecked(satName) && !!(t && t.gs && gsPosition(gsFrontName(t.gs)));
                  }, false),
                  positions: new Cesium.CallbackProperty((time) => {
                      const pos = getSatPos(time);
                      const t = linkTargetMap[satName];
                      const gsPos = t ? gsPosition(gsFrontName(t.gs)) : null;
                      if (!pos || !gsPos) return [Cesium.Cartesian3.ZERO, Cesium.Cartesian3.ZERO];
                      return [pos, gsPos];
                  }, false),
                  width: 1.5,
                  arcType: Cesium.ArcType.NONE,
                  // 短虚线 + 青色发光，区分星间长虚线，避免整屏实心线糊满
                  material: new Cesium.PolylineDashMaterialProperty({
                      color: Cesium.Color.fromCssColorString('#00f0ff').withAlpha(0.75),
                      dashLength: 10
                  })
              }
          });
      });
      // const satelliteEntities = dataSource.entities.values.filter(entity => 
      // entity.id.startsWith("Sat_"));
      // 显示效果优化：标签仅在相机拉近时显示，轨道线改为青色发光材质（参考态势大屏风格）
      satelliteEntities.forEach(entity => {
          if (entity.label) {
              entity.label.distanceDisplayCondition = new Cesium.DistanceDisplayCondition(0, 1.0e7);
          }
          // 卫星图标：换用提亮加青色光晕的版本（原版 16px 暗色图标在深色太空背景下几乎不可见），
          // 远处适度缩小并配合拖尾光点，既清晰又不遮挡地球
          if (entity.billboard) {
              entity.billboard.image = SAT_ICON_URI;
              entity.billboard.scale = 0.7;
              entity.billboard.scaleByDistance = new Cesium.NearFarScalar(1.5e7, 1.0, 8.0e7, 0.7);
          }
          if (entity.path) {
              entity.path.width = 2;
              entity.path.material = new Cesium.PolylineGlowMaterialProperty({
                  glowPower: 0.15,
                  color: Cesium.Color.fromCssColorString('#00dcff').withAlpha(0.55)
              });
              // 200 颗卫星的拖尾线在全球视角下交织成乱麻，仅在相机拉近（<2e7m）时显示
              entity.path.distanceDisplayCondition = new Cesium.DistanceDisplayCondition(0, 2.0e7);
          }
      });
      // 轨道流光特效：为每颗卫星添加一个沿轨道流动的拖尾光点
      // 取过去时刻的位置（CZML 采样区间内必有值），多颗卫星错开相位形成流动感
      satelliteEntities.forEach((entity, idx) => {
          const offset = 20 + (idx % 5) * 25;  // 拖尾时间差 20~120 秒
          const scratchTime = new Cesium.JulianDate();
          const glowEntity = viewer.entities.add({
              position: new Cesium.CallbackProperty(() => {
                  Cesium.JulianDate.addSeconds(viewer.clock.currentTime, -offset, scratchTime);
                  const pos = entity.position.getValue(scratchTime);
                  return pos || entity.position.getValue(viewer.clock.currentTime);
              }, false),
              point: {
                  pixelSize: 5,
                  color: Cesium.Color.fromCssColorString('#00f0ff'),
                  outlineColor: Cesium.Color.WHITE.withAlpha(0.8),
                  outlineWidth: 1,
                  // 拖尾光点仅在相机拉近时显示（全球视角下 200 个光点会糊成杂乱光斑）
                  distanceDisplayCondition: new Cesium.DistanceDisplayCondition(0, 1.2e7)
              }
          });
          satGlowPoints.set(entity.id, glowEntity);
      });
      if (!satellite1) {
        console.error("未找到 ID 为 'Sat_1_1' 的卫星");
        return;
      }
  

      // 创建视锥体
      // orientation - 相机镜头对准的方法.
      //   heading - 代表镜头左右方向, 正值为右, 负值为左, 360度和0度是一样的
      // pitch - 代表镜头上下方向, 正值为上, 负值为下.
      //   roll - 代表镜头左右倾斜.正值, 向右倾斜, 负值向左倾斜
      // 默认hpr都为0，是正向朝北，沿着Y轴，按照东北上参考坐标系
      // 在全局作用域声明存储所有视锥体的Map
      const frustumPrimitives = new Map();
      const outlinePrimitives = new Map();
      frustumPrims = frustumPrimitives;  // 暴露给外层，供选中隐藏/关闭恢复
      outlinePrims = outlinePrimitives;
      const length = 1000000;
      const frustumShape = new Cesium.PerspectiveFrustum({
        fov: Cesium.Math.toRadians(50),
        aspectRatio: 1,
        near: 1,
        far: length,
      });
      // 本地坐标系中的姿态（roll=180°，即绕X轴翻转）
      const localOrientation = Cesium.Transforms.headingPitchRollQuaternion(
        Cesium.Cartesian3.ZERO,
        new Cesium.HeadingPitchRoll(0, 0, Math.PI)
      );

      function initFrustum(satellite) {
        // 创建填充视锥体（本地原点，通过modelMatrix变换到卫星位置）
        const fillGeometry = new Cesium.FrustumGeometry({
          frustum: frustumShape,
          origin: Cesium.Cartesian3.ZERO,
          orientation: localOrientation,
          vertexFormat: Cesium.VertexFormat.POSITION_ONLY,
        });
        const fillInstance = new Cesium.GeometryInstance({
          geometry: fillGeometry,
          attributes: {
            color: Cesium.ColorGeometryInstanceAttribute.fromColor(
              new Cesium.Color(0.0, 0.8627, 1.0, 0.32)  // 视锥填充降透明，减少遮挡压迫感
            ),
            // 远距离隐藏视锥体，减少视觉杂乱和离屏渲染
            distanceDisplayCondition: new Cesium.DistanceDisplayConditionGeometryInstanceAttribute(0, 1.5e7),
          },
        });
        const fillPrimitive = new Cesium.Primitive({
          geometryInstances: fillInstance,
          appearance: new Cesium.PerInstanceColorAppearance({
            closed: true,
            flat: true,
          }),
        });
        viewer.scene.primitives.add(fillPrimitive);
        frustumPrimitives.set(satellite.id, fillPrimitive);

        // 创建轮廓线
        const outlineGeometry = new Cesium.FrustumOutlineGeometry({
          frustum: frustumShape,
          origin: Cesium.Cartesian3.ZERO,
          orientation: localOrientation,
          vertexFormat: Cesium.VertexFormat.POSITION_ONLY,
        });
        const outlineInstance = new Cesium.GeometryInstance({
          geometry: outlineGeometry,
          attributes: {
            color: Cesium.ColorGeometryInstanceAttribute.fromColor(
              new Cesium.Color(1.0, 1.0, 1.0, 1.0)
            ),
            distanceDisplayCondition: new Cesium.DistanceDisplayConditionGeometryInstanceAttribute(0, 1.5e7),
          },
        });
        const outlinePrimitive = new Cesium.Primitive({
          geometryInstances: outlineInstance,
          appearance: new Cesium.PerInstanceColorAppearance({
            closed: true,
            flat: true,
          }),
        });
        viewer.scene.primitives.add(outlinePrimitive);
        outlinePrimitives.set(satellite.id, outlinePrimitive);
      }

      function updateFrustumModelMatrix(satellite) {
        const position = satellite.position.getValue(viewer.clock.currentTime);
        if (!position) return;
        const modelMatrix = Cesium.Transforms.headingPitchRollToFixedFrame(
          position,
          new Cesium.HeadingPitchRoll(0, 0, 0),
          Cesium.Ellipsoid.WGS84
        );
        const fp = frustumPrimitives.get(satellite.id);
        const op = outlinePrimitives.get(satellite.id);
        if (fp) fp.modelMatrix = modelMatrix;
        if (op) op.modelMatrix = modelMatrix;
      }

      // 一次性初始化所有视锥体
      satelliteEntities.forEach(satellite => {
        initFrustum(satellite);
      });
      applyAllVisibility();  // 按当前勾选/开关状态统一刷新显隐（默认全部显示）
      viewer.scene.globe.depthTestAgainstTerrain = true;

      // 每帧仅更新modelMatrix
      viewer.clock.onTick.addEventListener(function () {
        satelliteEntities.forEach(satellite => {
          updateFrustumModelMatrix(satellite);
        });
      });

      // 为卫星实体绑定点击事件
      viewer.screenSpaceEventHandler.setInputAction((event) => {
        const pickedEntity = viewer.scene.pick(event.position);
        if (Cesium.defined(pickedEntity)) {
          const entity = pickedEntity.id; // 获取点击的实体
          if (entity) {
            // 获取卫星的详细信息
            const name = entity.name || "未知卫星";
            const posValue = entity.position && entity.position.getValue(viewer.clock.currentTime);
            if (!posValue) return; // 位置不可用（非卫星实体或超出仿真时段）时不更新面板
            onSelectSat(name);
            const position = Cesium.Cartographic.fromCartesian(posValue);
            const lat = Cesium.Math.toDegrees(position.latitude);
            const lng = Cesium.Math.toDegrees(position.longitude);
            const height = position.height;
  
            // 在右侧详情面板中显示
            const info = satList.value.find(s => s.name === name) || null;
            selectedSat.value = {
              name,
              lat: lat.toFixed(2),
              lng: lng.toFixed(2),
              height: (height / 1000).toFixed(1),
              info
            };
          }
        }
      }, Cesium.ScreenSpaceEventType.LEFT_CLICK);
    }).catch((error) => {
      czmlLoading.value = false;  // 失败同样关闭加载提示，避免永久转圈
      console.error("加载 CZML 数据失败：", error);
    });

    //卫星地面站网络构建
    const Positions_of_GroundStations = {
    '重庆站':  { id: '重庆站',     lon: 105.11,  lat: 28.10, radius: 300000 },
    '雄安站':  { id: '雄安站',     lon: 115.38,  lat: 38.10, radius: 300000 },
    '喀什站':  { id: '喀什站',     lon: 79.57,   lat: 40.18, radius: 300000 },
    '文昌站':  { id: '文昌站',     lon: 110.28,  lat: 19.21, radius: 300000 },
    '佳木斯站':{ id: '佳木斯站',    lon: 129.29,  lat: 45.56, radius: 300000 }};
    const Networking_Dicts = {'重庆站': {'dst1':'雄安站','dst2':'喀什站', 'dst3':'文昌站'},'喀什站': {'dst1':'雄安站'},'佳木斯站': {'dst1':'雄安站'}, '文昌站': {'dst1':'雄安站'}};

    // 卫星地面站建立
    const GroundStations = new Cesium.CustomDataSource("GroundStations");
    viewer.dataSources.add(GroundStations);
    const groundStationStates = new Map();
    Object.keys(Positions_of_GroundStations).forEach(i => {Create_for_GroundStations(Positions_of_GroundStations[i].id, Positions_of_GroundStations[i].lon, Positions_of_GroundStations[i].lat, Positions_of_GroundStations[i].radius)});
    // 合并为一个onTick监听器更新所有地面站
    viewer.clock.onTick.addEventListener(() => {
      groundStationStates.forEach(state => {
        state.heading += 5.0;
        state.positionArr = calcPoints(state.lon, state.lat, state.radius, state.heading);
      });
    });
    function Create_for_GroundStations(id, lon, lat, radius) {
      const state = { heading: 0, positionArr: calcPoints(lon, lat, radius, 0), lon, lat, radius };
      groundStationStates.set(id, state);
      GroundStations.entities.add({
         name: id,
         label: {
              text: `${id}`,
              heightReference:Cesium.HeightReference.CLAMP_TO_GROUND,
              font: "12pt sans-serif",
              verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
              pixelOffset: new Cesium.Cartesian2(0.0, -12),
              // 远距缩小字号、超远直接隐藏，避免多站标签在全球视角下重叠成一团
              scaleByDistance: new Cesium.NearFarScalar(1.0e6, 1.0, 2.0e7, 0.4),
              distanceDisplayCondition: new Cesium.DistanceDisplayCondition(0, 1.5e7),
              fillColor: Cesium.Color.WHITE,
         },
         position: Cesium.Cartesian3.fromDegrees(lon,lat),
         wall: {
           positions: new Cesium.CallbackProperty(() => {
             return Cesium.Cartesian3.fromDegreesArrayHeights(groundStationStates.get(id).positionArr);
           }, false),
           material: Cesium.Color.fromCssColorString("#00dcff82"),
         },
         ellipsoid: {
           radii: new Cesium.Cartesian3(radius, radius, radius),
           maximumCone: Cesium.Math.toRadians(90),
           material: Cesium.Color.fromCssColorString("#00dcff82"),  //Cesium.Color.RED.withAlpha(0.8):颜色和透明度；
           outline: true,
           outlineColor: Cesium.Color.fromCssColorString("#00dcff82"),
           outlineWidth: 1,
         },
      });
    }
    function calcPoints(x1, y1, radius, heading){
      var m = Cesium.Transforms.eastNorthUpToFixedFrame(Cesium.Cartesian3.fromDegrees(x1, y1));
      var rx = radius * Math.cos(heading * Math.PI / 180.0);
      var ry = radius * Math.sin(heading * Math.PI / 180.0);
      var translation = Cesium.Cartesian3.fromElements(rx, ry, 0);
      var d = Cesium.Matrix4.multiplyByPoint(m, translation, new Cesium.Cartesian3());
      var c = Cesium.Cartographic.fromCartesian(d);
      var x2 = Cesium.Math.toDegrees(c.longitude);
      var y2 = Cesium.Math.toDegrees(c.latitude);
      return computeCirclularFlight(x1, y1, x2, y2, 0, 90);
    }
    function computeCirclularFlight(x1, y1, x2, y2, fx, angle) {
      let positionArr = [];
      positionArr.push(x1);
      positionArr.push(y1);
      positionArr.push(0);
      var radius = Cesium.Cartesian3.distance(Cesium.Cartesian3.fromDegrees(x1, y1), Cesium.Cartesian3.fromDegrees(x2, y2));
      for (let i = fx; i <= fx + angle; i++) {
        let h = radius * Math.sin(i * Math.PI / 180.0);
        let r = Math.cos(i * Math.PI / 180.0);
        let x = (x2 - x1) * r + x1;
        let y = (y2 - y1) * r + y1;
        positionArr.push(x);
        positionArr.push(y);
        positionArr.push(h);
      }
      return positionArr;
    }

    // 高轨中继卫星固定轨位（与后端 SatelliteService 中定义一致：东经120°/西经120°/0°，GEO 高度35786km）
    const GEO_POSITIONS = {
      '高轨卫星1': Cesium.Cartesian3.fromDegrees(120, 0, 35786000),
      '高轨卫星2': Cesium.Cartesian3.fromDegrees(-120, 0, 35786000),
      '高轨卫星3': Cesium.Cartesian3.fromDegrees(0, 0, 35786000),
    };
    // 后端地面站名（config.py）→ 前端 3D 场景站名 映射
    const gsNameMap = { '新疆喀什': '喀什站', '重庆': '重庆站', '雄安': '雄安站', '海南文昌': '文昌站', '黑龙江佳木斯': '佳木斯站' };
    function gsFrontName(backendName) {
      if (!backendName) return null;
      return gsNameMap[backendName] || (Positions_of_GroundStations[backendName] ? backendName : `${backendName}站`);
    }
    function gsPosition(frontName) {
      const st = frontName && Positions_of_GroundStations[frontName];
      return st ? Cesium.Cartesian3.fromDegrees(st.lon, st.lat) : null;
    }
    // 通信链路数据源：星间链路（卫星↔高轨卫星）与星地数传链路（卫星↔地面站）
    linkDataSource = new Cesium.CustomDataSource('CommLinks');
    viewer.dataSources.add(linkDataSource);
    // 高轨中继卫星节点（点 + 标签）
    Object.keys(GEO_POSITIONS).forEach(name => {
      linkDataSource.entities.add({
        name,
        position: GEO_POSITIONS[name],
        point: {
          pixelSize: 8,
          color: Cesium.Color.fromCssColorString('#ffd657'),
          outlineColor: Cesium.Color.WHITE.withAlpha(0.8),
          outlineWidth: 1,
        },
        label: {
          text: name,
          font: '12pt sans-serif',
          verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
          pixelOffset: new Cesium.Cartesian2(0.0, -12),
          fillColor: Cesium.Color.fromCssColorString('#ffd657'),
          scaleByDistance: new Cesium.NearFarScalar(1.0e7, 1.0, 1.0e8, 0.5),
          distanceDisplayCondition: new Cesium.DistanceDisplayCondition(0, 1.2e8),
        },
      });
    });

    //卫星地面站网络建立
    const Networking_for_GroundStation = new Cesium.CustomDataSource("Networking_for_GroundStation");
    viewer.dataSources.add(Networking_for_GroundStation);
    Object.keys(Networking_Dicts).forEach(key => {Creat_Networks_for_GroundSations(key, Networking_Dicts[key])});

    // 启动 HUD 数据轮询（5秒刷新一次）；页面在后台标签时暂停，回前台立即补刷一次
    refreshHud();
    hudTimer = setInterval(() => { if (!document.hidden) refreshHud(); }, 5000);
    document.addEventListener('visibilitychange', onVisibility);
    // 窗口尺寸变化时重排 HUD 图表
    window.addEventListener('resize', handleResize);
    function Creat_Networks_for_GroundSations(src, dst_dicts){
      Object.keys(dst_dicts).forEach(key =>{
        Networking_for_GroundStation.entities.add({
          polyline: {
              positions: Cesium.Cartesian3.fromDegreesArray([Positions_of_GroundStations[src].lon, Positions_of_GroundStations[src].lat,
                Positions_of_GroundStations[dst_dicts[key]].lon, Positions_of_GroundStations[dst_dicts[key]].lat,
                  ]),
              width: 2, // 线宽
              material: Cesium.Color.fromCssColorString('#ffd657').withAlpha(0.55) // 地面站骨干网，黄色低透明，与星间链路色系统一
          }
        });
      });
    }

  });
</script>

<style scoped>
    .situation-page {
        position: relative;
        width: 100%;
        height: 100%;
        overflow: hidden;
        background: #050a1e;
    }
    #cesiumContainer{
        width: 100%;
        height: 100%;
        overflow: hidden;
    }

    /* ===== 中央态势装饰环 ===== */
    .center-hud {
        position: absolute;
        left: 50%;
        top: 50%;
        transform: translate(-50%, -50%);
        width: min(72vh, 60vw);
        height: min(72vh, 60vw);
        pointer-events: none;
        z-index: 5;
    }
    .radar-ring {
        position: absolute;
        border-radius: 50%;
    }
    .ring-a {
        inset: 0;
        border: 1px dashed rgba(0, 220, 255, 0.35);
        box-shadow: 0 0 20px rgba(0, 220, 255, 0.08);
        animation: hud-spin 60s linear infinite;
    }
    .ring-b {
        inset: 6%;
        border: 1px solid rgba(0, 220, 255, 0.18);
        border-top-color: rgba(0, 240, 255, 0.7);
        animation: hud-spin 18s linear infinite reverse;
    }
    /* 轨道数据加载提示层 */
    .czml-loading {
        position: absolute;
        left: 50%;
        top: 50%;
        transform: translate(-50%, -50%);
        z-index: 30;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 12px;
        padding: 26px 34px;
        background: rgba(4, 14, 32, 0.82);
        border: 1px solid rgba(0, 220, 255, 0.35);
        border-radius: 10px;
        box-shadow: 0 0 30px rgba(0, 220, 255, 0.15);
        backdrop-filter: blur(8px);
    }
    .czml-loading-ring {
        width: 38px;
        height: 38px;
        border-radius: 50%;
        border: 2px solid rgba(0, 220, 255, 0.2);
        border-top-color: #00f0ff;
        animation: hud-spin 1s linear infinite;
    }
    .czml-loading-text {
        font-size: 13px;
        letter-spacing: 2px;
        color: #cfeeff;
    }
    .czml-loading-sub {
        font-size: 10px;
        letter-spacing: 3px;
        color: #4d7a9a;
        font-family: 'Courier New', monospace;
    }
    .fade-enter-active, .fade-leave-active { transition: opacity 0.3s ease; }
    .fade-enter-from, .fade-leave-to { opacity: 0; }
    @keyframes hud-spin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }
    .crosshair {
        position: absolute;
        background: linear-gradient(90deg, transparent, rgba(0, 220, 255, 0.25), transparent);
    }
    .crosshair-h { left: -8%; right: -8%; top: 50%; height: 1px; }
    .crosshair-v {
        top: -8%; bottom: -8%; left: 50%; width: 1px;
        background: linear-gradient(180deg, transparent, rgba(0, 220, 255, 0.25), transparent);
    }

    /* 左右面板补充右上/左下角标，构成四角 HUD 边框 */
    .pc {
        position: absolute;
        width: 12px;
        height: 12px;
        z-index: 1;
    }
    .pc-tr {
        top: -1px; right: -1px;
        border-top: 2px solid #00f0ff;
        border-right: 2px solid #00f0ff;
    }
    .pc-bl {
        bottom: -1px; left: -1px;
        border-bottom: 2px solid #00f0ff;
        border-left: 2px solid #00f0ff;
    }

    /* ===== HUD 通用面板样式：深色半透明 + 青色发光描边 ===== */
    .hud {
        position: absolute;
        background: rgba(8, 20, 46, 0.78);
        border: 1px solid rgba(0, 220, 255, 0.35);
        border-radius: 4px;
        box-shadow: 0 0 12px rgba(0, 220, 255, 0.15), inset 0 0 20px rgba(0, 100, 200, 0.1);
        backdrop-filter: blur(4px);
        color: #cfe8ff;
        z-index: 10;
    }
    .panel-title {
        position: relative;
        overflow: hidden;
        font-size: 13px;
        font-weight: 600;
        color: #00dcff;
        padding: 8px 12px;
        border-bottom: 1px solid rgba(0, 220, 255, 0.25);
        letter-spacing: 1px;
        display: flex;
        justify-content: flex-start;
        align-items: center;
        background: linear-gradient(90deg, rgba(0, 220, 255, 0.12), transparent);
    }
    /* 面板标题流光扫过动画 */
    .panel-title::after {
        content: '';
        position: absolute;
        top: 0;
        left: -40%;
        width: 30%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(0, 240, 255, 0.12), transparent);
        animation: title-sheen 3.5s ease-in-out infinite;
        pointer-events: none;
    }
    @keyframes title-sheen {
        0% { left: -40%; }
        60%, 100% { left: 110%; }
    }
    .panel-title::before {
        content: '';
        display: inline-block;
        width: 3px;
        height: 12px;
        background: #00f0ff;
        box-shadow: 0 0 6px rgba(0, 240, 255, 0.8);
        margin-right: 8px;
        flex-shrink: 0;
    }
    .panel-title .close-btn { margin-left: auto; }

    /* 顶部标题栏 */
    .top-header {
        top: 0; left: 0; right: 0;
        height: 56px;
        border-radius: 0;
        border-left: none; border-right: none; border-top: none;
        display: flex;
        justify-content: center;
        align-items: center;
        padding: 0 16px;
        background: linear-gradient(180deg, rgba(6, 18, 42, 0.95), rgba(6, 18, 42, 0.55));
    }
    /* 标题两侧装饰渐变线（左侧线让位给内嵌指标，仅保留右侧） */
    .top-header::before, .top-header::after {
        content: '';
        position: absolute;
        top: 50%;
        width: 20%;
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(0, 220, 255, 0.6));
    }
    .top-header::before { display: none; }
    .top-header::after { right: 130px; transform: scaleX(-1); }

    /* 顶栏左侧内嵌紧凑指标 */
    .header-stats {
        position: absolute;
        left: 16px;
        top: 50%;
        transform: translateY(-50%);
        display: flex;
        gap: 20px;
    }
    .hs-item { display: flex; align-items: baseline; gap: 6px; white-space: nowrap; }
    .hs-item b {
        font-size: 16px;
        font-weight: 700;
        color: #00f0ff;
        text-shadow: 0 0 8px rgba(0, 240, 255, 0.7);
        font-family: 'Courier New', monospace;
    }
    .hs-item .hs-unit { font-size: 10px; font-style: normal; margin-left: 1px; }
    .hs-item span { font-size: 11px; color: #9fc6e8; }

    /* 窄屏时顶栏指标紧凑化，避免与居中标题拥挤 */
    @media (max-width: 1500px) {
        .header-stats { gap: 12px; left: 12px; }
        .hs-item b { font-size: 14px; }
        .hs-item span { font-size: 10px; }
    }
    .sys-title {
        font-size: 21px;
        font-weight: 700;
        letter-spacing: 3px;
        background: linear-gradient(180deg, #ffffff, #7fd4ff);
        -webkit-background-clip: text;
        background-clip: text;
        -webkit-text-fill-color: transparent;
        filter: drop-shadow(0 0 8px rgba(0, 220, 255, 0.5));
        /* 标题光泽缓慢扫过 */
        background-size: 200% 100%;
        animation: title-sheen-move 5s ease-in-out infinite;
    }
    @keyframes title-sheen-move {
        0%, 100% { background-position: 0% 0; }
        50% { background-position: 100% 0; }
    }
    .sub-title {
        margin-left: 12px;
        font-size: 10px;
        font-weight: 400;
        letter-spacing: 2px;
        color: rgba(0, 220, 255, 0.5);
    }
    .sim-time {
        font-size: 13px;
        color: #7fd4ff;
        font-family: 'Courier New', monospace;
    }
    .header-right {
        position: absolute;
        right: 16px;
        top: 50%;
        transform: translateY(-50%);
        display: flex;
        align-items: center;
        gap: 10px;
    }
    /* 全屏展示按钮（演示模式） */
    .fullscreen-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 26px; height: 26px;
        background: rgba(0, 220, 255, 0.08);
        border: 1px solid rgba(0, 220, 255, 0.35);
        border-radius: 4px;
        color: #00dcff;
        cursor: pointer;
        transition: all 0.25s;
    }
    .fullscreen-btn:hover {
        background: rgba(0, 220, 255, 0.2);
        box-shadow: 0 0 10px rgba(0, 220, 255, 0.4);
    }
    /* 卫星列表搜索框 */
    .sat-search {
        position: relative;
        margin: 0 10px 6px;
    }
    .sat-search-input {
        width: 100%;
        height: 26px;
        padding: 0 22px 0 10px;
        background: rgba(0, 220, 255, 0.05);
        border: 1px solid rgba(0, 220, 255, 0.25);
        border-radius: 4px;
        color: #cfe8ff;
        font-size: 11px;
        outline: none;
        transition: border-color 0.25s, box-shadow 0.25s;
        box-sizing: border-box;
    }
    .sat-search-input::placeholder { color: rgba(159, 198, 232, 0.45); }
    .sat-search-input:focus {
        border-color: rgba(0, 220, 255, 0.6);
        box-shadow: 0 0 8px rgba(0, 220, 255, 0.25);
    }
    .sat-search-clear {
        position: absolute;
        right: 7px;
        top: 50%;
        transform: translateY(-50%);
        color: rgba(159, 198, 232, 0.6);
        cursor: pointer;
        font-size: 13px;
        line-height: 1;
    }
    .sat-search-clear:hover { color: #00dcff; }

    /* 顶部指标（已内嵌进标题栏，原悬浮卡片样式移除） */
    .stat-value {
        font-size: 22px;
        font-weight: 700;
        color: #00f0ff;
        text-shadow: 0 0 8px rgba(0, 240, 255, 0.7);
        font-family: 'Courier New', monospace;
    }
    .stat-value .unit { font-size: 12px; margin-left: 2px; }
    .stat-label { font-size: 12px; color: #9fc6e8; margin-top: 2px; }

    /* 左侧卫星列表 */
    .left-panel {
        top: 64px; left: 10px; bottom: 46px;
        width: 230px;
        display: flex;
        flex-direction: column;
    }
    /* 左右面板科技感四角边框 */
    .left-panel::before, .right-panel::before {
        content: '';
        position: absolute;
        top: -1px; left: -1px;
        width: 12px; height: 12px;
        border-top: 2px solid #00f0ff;
        border-left: 2px solid #00f0ff;
    }
    .left-panel::after, .right-panel::after {
        content: '';
        position: absolute;
        bottom: -1px; right: -1px;
        width: 12px; height: 12px;
        border-bottom: 2px solid #00f0ff;
        border-right: 2px solid #00f0ff;
    }
    .sat-list { flex: 1; overflow-y: auto; padding: 4px 0; }
    .sat-list::-webkit-scrollbar { width: 4px; }
    .sat-list::-webkit-scrollbar-thumb { background: rgba(0, 220, 255, 0.3); border-radius: 2px; }
    .sat-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 5px 12px;
        font-size: 12px;
        cursor: pointer;
        border-left: 2px solid transparent;
    }
    .sat-item:hover {
        background: rgba(0, 220, 255, 0.12);
        border-left-color: #00dcff;
    }
    .sat-name { color: #e8f6ff; font-family: 'Courier New', monospace; flex: 1; min-width: 0; }
    .sat-payload {
        color: #ffd657; font-size: 10px;
        padding: 0 5px; margin-right: 6px; flex-shrink: 0;
        border: 1px solid rgba(255, 214, 87, 0.35); border-radius: 3px;
        background: rgba(255, 214, 87, 0.08);
    }
    .sat-battery { display: inline-flex; align-items: center; gap: 4px; font-size: 11px; font-family: 'Courier New', monospace; flex-shrink: 0; }
    .sat-batt-dot { width: 5px; height: 5px; border-radius: 50%; background: currentColor; box-shadow: 0 0 5px currentColor; }
    .sat-battery.dot-ok { color: #52ffa8; }
    .sat-battery.dot-warn { color: #ffd657; }
    .sat-battery.dot-alarm { color: #ff6b6b; }
    .empty-tip { padding: 20px 12px; font-size: 12px; color: #68809a; text-align: center; }
    .payload-chart { height: 150px; flex-shrink: 0; }

    /* 卫星列表勾选框 */
    .sat-check { accent-color: #00dcff; margin-right: 6px; flex-shrink: 0; cursor: pointer; }

    /* 卫星状态呼吸灯：绿=在线，黄=低电量关注，红=告警 */
    .sat-status-dot {
        width: 6px; height: 6px; border-radius: 50%;
        margin-right: 7px; flex-shrink: 0;
        animation: sat-dot-breathe 2.4s ease-in-out infinite;
    }
    .sat-status-dot.dot-ok { background: #52ffa8; box-shadow: 0 0 6px rgba(82, 255, 168, 0.8); }
    .sat-status-dot.dot-warn { background: #ffd657; box-shadow: 0 0 6px rgba(255, 214, 87, 0.8); }
    .sat-status-dot.dot-alarm { background: #ff6b6b; box-shadow: 0 0 8px rgba(255, 107, 107, 0.9); animation-duration: 1.1s; }
    @keyframes sat-dot-breathe {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.35; }
    }

    /* HUD 开关（详情面板/常用功能通用） */
    .hud-switch { position: relative; display: inline-block; width: 30px; height: 16px; flex-shrink: 0; }
    .hud-switch input { display: none; }
    .hud-switch i {
        position: absolute; inset: 0;
        border-radius: 8px;
        background: rgba(0, 220, 255, 0.12);
        border: 1px solid rgba(0, 220, 255, 0.4);
        transition: 0.2s;
        cursor: pointer;
    }
    .hud-switch i::after {
        content: '';
        position: absolute; top: 2px; left: 2px;
        width: 10px; height: 10px;
        border-radius: 50%;
        background: #68809a;
        transition: 0.2s;
    }
    .hud-switch input:checked + i {
        background: rgba(0, 240, 255, 0.3);
        box-shadow: 0 0 6px rgba(0, 240, 255, 0.5);
    }
    .hud-switch input:checked + i::after { left: 16px; background: #00f0ff; }

    /* 详情面板“隐藏”按钮 */
    .hide-detail-btn {
        display: block;
        margin: 8px 12px 10px;
        width: calc(100% - 24px);
        padding: 5px 0;
        font-size: 12px;
        letter-spacing: 2px;
        color: #00dcff;
        background: rgba(0, 220, 255, 0.1);
        border: 1px solid rgba(0, 220, 255, 0.4);
        border-radius: 3px;
        cursor: pointer;
    }
    .hide-detail-btn:hover { background: rgba(0, 220, 255, 0.22); box-shadow: 0 0 8px rgba(0, 240, 255, 0.4); }

    /* 常用功能区 */
    .quick-actions { padding: 2px 0 4px; flex-shrink: 0; }

    /* 任务执行进度列表 */
    .task-list { max-height: 180px; overflow-y: auto; padding: 4px 0; flex-shrink: 0; }
    .task-list::-webkit-scrollbar { width: 4px; }
    .task-list::-webkit-scrollbar-thumb { background: rgba(0, 220, 255, 0.3); border-radius: 2px; }
    .task-item { padding: 5px 12px; font-size: 12px; }
    .task-head { display: flex; justify-content: space-between; margin-bottom: 3px; }
    .task-name {
        color: #e8f6ff;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        max-width: 150px;
    }
    .task-pct { color: #7fd4ff; font-family: 'Courier New', monospace; }
    .progress-track {
        height: 4px;
        background: rgba(0, 220, 255, 0.12);
        border-radius: 2px;
        overflow: hidden;
    }
    .progress-fill {
        height: 100%;
        background: linear-gradient(90deg, #0090c0, #00f0ff);
        box-shadow: 0 0 6px rgba(0, 240, 255, 0.6);
        border-radius: 2px;
        transition: width 0.5s;
    }
    .progress-fill.urgent {
        background: linear-gradient(90deg, #c09000, #ffd657);
        box-shadow: 0 0 6px rgba(255, 214, 87, 0.6);
    }

    /* 右侧面板：卫星详情 + 态势图表（收窄与左面板对齐） */
    .right-panel {
        top: 64px; right: 10px; bottom: 46px;
        width: 230px;
        display: flex;
        flex-direction: column;
        overflow-y: auto;
    }
    .right-chart { height: 130px; flex-shrink: 0; }
    .chart-wrap { position: relative; }
    .chart-inner { height: 100%; }
    /* 趋势图空态占位 */
    .chart-empty {
        position: absolute;
        inset: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        text-align: center;
        font-size: 12px;
        line-height: 1.9;
        color: #68809a;
        border: 1px dashed rgba(0, 220, 255, 0.18);
        margin: 6px 10px;
        flex-direction: column;
        gap: 6px;
    }
    .chart-empty::before {
        content: '';
        width: 26px; height: 26px;
        border: 1.5px solid rgba(0, 220, 255, 0.35); border-radius: 50%;
        border-top-color: transparent; border-bottom-color: transparent;
        box-shadow: 0 0 10px rgba(0, 220, 255, 0.2);
    }
    /* 卫星详情空态：flex 容器内静态布局（规则放在 .chart-empty 之后以覆盖 inset） */
    .chart-empty.detail-empty-static {
        position: relative;
        inset: auto;
        height: 120px;
        flex-shrink: 0;
    }
    .close-btn { cursor: pointer; color: #68809a; font-size: 16px; }
    .close-btn:hover { color: #00dcff; }
    /* 星下点小地图标题与上方内容拉开 */
    .subtrack-title { margin-top: 6px; border-top: 1px solid rgba(0, 220, 255, 0.12); }
    .detail-name {
        padding: 10px 12px 4px;
        font-size: 15px;
        font-weight: 600;
        color: #00f0ff;
        font-family: 'Courier New', monospace;
    }
    .detail-row {
        display: flex;
        justify-content: space-between;
        padding: 5px 12px;
        font-size: 12px;
    }
    .detail-row span { color: #9fc6e8; }
    .detail-row b { color: #e8f6ff; font-family: 'Courier New', monospace; font-weight: 600; }

    /* 底部告警/事件滚动栏 */
    .bottom-bar {
        bottom: 0; left: 0; right: 0;
        height: 36px;
        border-radius: 0;
        border-left: none; border-right: none; border-bottom: none;
        display: flex;
        align-items: center;
        padding: 0 12px;
        background: linear-gradient(0deg, rgba(6, 18, 42, 0.92), rgba(6, 18, 42, 0.6));
    }
    /* Cesium 时间轴：抬到实时事件栏（36px）上方，左右内嵌避开两侧 HUD 面板（宽 230px + 边距 10px），加深色半透明底与主题融合 */
    /* 注意：Cesium Viewer 会给 timelineContainer 写入内联 left:0;right:0，必须用 !important 覆盖 */
    :deep(.cesium-viewer-timelineContainer) {
        bottom: 36px;
        left: 245px !important;
        right: 245px !important;
        background: rgba(6, 18, 42, 0.85);
        border-top: 1px solid rgba(0, 220, 255, 0.25);
    }
    .bottom-label {
        font-size: 12px;
        color: #00dcff;
        font-weight: 600;
        letter-spacing: 1px;
        flex-shrink: 0;
        padding-right: 12px;
        border-right: 1px solid rgba(0, 220, 255, 0.25);
        display: flex;
        align-items: center;
    }
    .bottom-label .dot {
        display: inline-block;
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: #00f0ff;
        box-shadow: 0 0 6px #00f0ff;
        margin-right: 6px;
        animation: blink 1.2s ease-in-out infinite;
    }
    @keyframes blink {
        50% { opacity: 0.25; }
    }
    .event-scroll { flex: 1; overflow: hidden; margin-left: 12px; }
    .event-track {
        display: inline-block;
        white-space: nowrap;
        animation: marquee 30s linear infinite;
    }
    .event-scroll:hover .event-track { animation-play-state: paused; }
    .event-item {
        font-size: 12px;
        color: #9fc6e8;
        margin-right: 40px;
        font-family: 'Courier New', monospace;
    }
    /* 事件级别前置小图标 */
    .event-item::before {
        content: '●';
        margin-right: 5px;
        font-size: 9px;
        color: #00dcff;
    }
    .event-item.warn { color: #ffd657; }
    .event-item.warn::before { content: '▲'; color: #ffd657; }
    .event-item.alarm { color: #ff7a7a; }
    .event-item.alarm::before { content: '✖'; color: #ff7a7a; animation: blink 1s ease-in-out infinite; }
    @keyframes marquee {
        0% { transform: translateX(100%); }
        100% { transform: translateX(-100%); }
    }
</style>

  
  
  