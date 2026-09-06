<template>
  <div class="performance-analysis">
    <!-- 页面头部 -->
    <el-card shadow="never" class="header-card">
      <div class="header-content">
        <div class="header-title">
          <el-icon :size="24" color="#00dcff"><TrendCharts /></el-icon>
          <div>
            <h2 class="title">性能分析</h2>
            <p class="subtitle">任务规划算法评估与系统性能监控</p>
          </div>
        </div>
        <div class="header-actions">
          <el-button :icon="Refresh" @click="refreshData" :loading="loading">刷新数据</el-button>
        </div>
      </div>
    </el-card>

    <el-tabs v-model="activeTab" class="perf-tabs" @tab-change="onTabChange">
      <!-- 算法性能分析 -->
      <el-tab-pane label="算法性能分析" name="algorithm">
        <el-card shadow="never" class="cluster-card">
          <template #header>
            <div class="card-header">
              <div class="sys-meta">
                <span class="meta-item">当前系统模式：<b>{{ modeText }}</b></span>
                <span class="meta-item">当前系统时间：<b>{{ simTime }}</b></span>
              </div>
              <el-select v-model="selectedCluster" placeholder="选择星簇" size="small" @change="onClusterChange" style="width: 220px;">
                <el-option v-for="cluster in clusterOptions" :key="cluster.value" :label="cluster.label" :value="cluster.value" />
              </el-select>
            </div>
          </template>
          <el-empty v-if="clusterLoaded && clusterData.length === 0" description="暂无数据，请先执行任务规划" />
          <el-row :gutter="16" v-show="clusterData.length > 0">
            <el-col :xs="24" :lg="12">
              <div class="grid-chart-title">任务数量</div>
              <div ref="clusterTasksChart" class="grid-chart-container"></div>
            </el-col>
            <el-col :xs="24" :lg="12">
              <div class="grid-chart-title">电量消耗量(Wh)</div>
              <div ref="clusterBatteryChart" class="grid-chart-container"></div>
            </el-col>
            <el-col :xs="24" :lg="12">
              <div class="grid-chart-title">固存使用量(GB)</div>
              <div ref="clusterStorageChart" class="grid-chart-container"></div>
            </el-col>
            <el-col :xs="24" :lg="12">
              <div class="grid-chart-title">固存资源利用率(%)</div>
              <div ref="clusterStorageUtilChart" class="grid-chart-container"></div>
            </el-col>
          </el-row>
        </el-card>
      </el-tab-pane>

      <!-- 系统性能分析 -->
      <el-tab-pane label="系统性能分析" name="system">
        <!-- 算法数据导出 -->
        <el-card shadow="never" class="export-card">
          <div class="export-bar">
            <el-button type="primary" :icon="Download" @click="doExport('greedy')"
              :loading="exportingType === 'greedy'" :disabled="!hasSchedule">导出贪心算法数据</el-button>
            <el-button type="primary" :icon="Download" @click="doExport('ant')"
              :loading="exportingType === 'ant'" :disabled="!hasSchedule">导出蚁群算法数据</el-button>
            <el-button type="primary" :icon="Download" @click="doExport('genetic')"
              :loading="exportingType === 'genetic'" :disabled="!hasSchedule">导出遗传算法数据</el-button>
            <el-button type="primary" :icon="Download" @click="doExport('schedule')"
              :loading="exportingType === 'schedule'" :disabled="!hasSchedule">导出当前方案数据</el-button>
          </div>
        </el-card>

        <!-- 统计概览 -->
        <el-row :gutter="16" class="stats-row">
          <el-col :xs="12" :sm="6">
            <el-card shadow="hover" class="stat-card">
              <div class="stat-icon" style="background: rgba(0,220,255,0.12); color: #00dcff; border: 1px solid rgba(0,220,255,0.35);">
                <el-icon :size="24"><CircleCheck /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ stats.completionRate }}%</div>
                <div class="stat-label">任务完成率</div>
              </div>
            </el-card>
          </el-col>
          <el-col :xs="12" :sm="6">
            <el-card shadow="hover" class="stat-card">
              <div class="stat-icon" style="background: rgba(103,194,58,0.12); color: #8ee06a; border: 1px solid rgba(103,194,58,0.4);">
                <el-icon :size="24"><Cpu /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ stats.resourceUtilization }}%</div>
                <div class="stat-label">资源利用率</div>
              </div>
            </el-card>
          </el-col>
          <el-col :xs="12" :sm="6">
            <el-card shadow="hover" class="stat-card">
              <div class="stat-icon" style="background: rgba(230,162,60,0.12); color: #f0b95c; border: 1px solid rgba(230,162,60,0.4);">
                <el-icon :size="24"><Timer /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ stats.avgResponseTime }}</div>
                <div class="stat-label">平均规划耗时</div>
              </div>
            </el-card>
          </el-col>
          <el-col :xs="12" :sm="6">
            <el-card shadow="hover" class="stat-card">
              <div class="stat-icon" style="background: rgba(140,170,200,0.12); color: #9fc6e8; border: 1px solid rgba(140,170,200,0.35);">
                <el-icon :size="24"><DataAnalysis /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ stats.planningCount }}</div>
                <div class="stat-label">规划次数</div>
              </div>
            </el-card>
          </el-col>
        </el-row>

        <!-- 多算法指标对比折线图 -->
        <el-card shadow="never" class="compare-card">
          <template #header>
            <div class="card-header">
              <div class="header-title">
                <el-icon :size="18" color="#00dcff"><TrendCharts /></el-icon>
                <span>多算法性能对比</span>
              </div>
            </div>
          </template>
          <el-empty v-if="evaluationRaw.length === 0" description="暂无数据，请先执行任务规划" />
          <el-row :gutter="16" v-show="evaluationRaw.length > 0">
            <el-col :xs="24" :lg="12">
              <div class="grid-chart-title">任务完成率(%)</div>
              <div ref="cmpCompletionChart" class="grid-chart-container"></div>
            </el-col>
            <el-col :xs="24" :lg="12">
              <div class="grid-chart-title">电量消耗量(Wh)</div>
              <div ref="cmpBatteryChart" class="grid-chart-container"></div>
            </el-col>
            <el-col :xs="24" :lg="12">
              <div class="grid-chart-title">固存使用量(GB)</div>
              <div ref="cmpStorageChart" class="grid-chart-container"></div>
            </el-col>
            <el-col :xs="24" :lg="12">
              <div class="grid-chart-title">规划耗时(s)</div>
              <div ref="cmpDurationChart" class="grid-chart-container"></div>
            </el-col>
          </el-row>
        </el-card>

        <!-- 规划算法评估 -->
        <el-row :gutter="16" class="chart-row">
          <el-col :xs="24" :lg="12">
            <el-card shadow="never" class="chart-card">
              <template #header>
                <div class="chart-header">
                  <div class="chart-title">
                    <el-icon :size="18" color="#00dcff"><PieChart /></el-icon>
                    <span>算法评估指标</span>
                  </div>
                  <el-radio-group v-model="selectedAlgorithm" size="small" @change="onAlgorithmChange">
                    <el-radio-button label="greedy">贪心</el-radio-button>
                    <el-radio-button label="ant">蚁群</el-radio-button>
                    <el-radio-button label="genetic">遗传</el-radio-button>
                  </el-radio-group>
                </div>
              </template>
              <div ref="radarChart" class="chart-container"></div>
            </el-card>
          </el-col>
          <el-col :xs="24" :lg="12">
            <el-card shadow="never" class="chart-card">
              <template #header>
                <div class="chart-header">
                  <div class="chart-title">
                    <el-icon :size="18" color="#8ee06a"><Histogram /></el-icon>
                    <span>任务执行统计</span>
                  </div>
                </div>
              </template>
              <div ref="barChart" class="chart-container"></div>
            </el-card>
          </el-col>
        </el-row>

        <!-- 详细评估数据 -->
        <el-card shadow="never" class="detail-card">
          <template #header>
            <div class="card-header">
              <div class="header-title">
                <el-icon :size="18" color="#9fc6e8"><Document /></el-icon>
                <span>详细评估数据</span>
              </div>
              <el-button link :icon="Refresh" @click="loadEvaluationData">刷新</el-button>
            </div>
          </template>
          <el-table :data="evaluationData" stripe v-loading="tableLoading">
            <el-table-column prop="algorithm" label="算法" width="120">
              <template #default="scope">
                <el-tag :type="getAlgorithmType(scope.row.algorithm)">{{ scope.row.algorithm }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="completionRate" label="完成率" width="100">
              <template #default="scope">
                <span :class="getRateClass(scope.row.completionRate)">{{ scope.row.completionRate }}%</span>
              </template>
            </el-table-column>
            <el-table-column prop="resourceUtilization" label="资源利用率" width="110">
              <template #default="scope">
                <el-progress :percentage="scope.row.resourceUtilization" :color="getProgressColor" />
              </template>
            </el-table-column>
            <el-table-column prop="imagingQuality" label="成像质量" width="110">
              <template #default="scope">
                <span>{{ scope.row.imagingQuality }}%</span>
              </template>
            </el-table-column>
            <el-table-column prop="batteryCost" label="电量消耗(Wh)" width="120" />
            <el-table-column prop="storageCost" label="存储消耗(GB)" width="120" />
            <el-table-column prop="executionTime" label="规划耗时(s)" width="130" />
            <el-table-column prop="timestamp" label="评估时间" min-width="160" />
            <el-table-column label="操作" width="120" fixed="right">
              <template #default="scope">
                <el-button link type="primary" @click="viewDetail(scope.row)">详情</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script>
import { ElMessage } from 'element-plus';
import * as echarts from 'echarts';
import {
  TrendCharts, Refresh, Download, CircleCheck, Cpu, Timer, DataAnalysis,
  PieChart, Histogram, Document
} from '@element-plus/icons-vue';

// ECharts 实例放模块级变量，避免放进 data() 被 Vue 深度响应式化（会导致图表内部状态被代理、性能下降）
const chartInsts = {};

export default {
  name: 'PerformanceAnalysis',
  components: {
    TrendCharts, Refresh, Download, CircleCheck, Cpu, Timer, DataAnalysis,
    PieChart, Histogram, Document
  },
  data() {
    return {
      activeTab: 'algorithm',
      loading: false,
      tableLoading: false,
      hasSchedule: false,
      systemMode: 0,
      simTime: '--',
      simTimer: null,
      stats: {
        completionRate: 0,
        resourceUtilization: 0,
        avgResponseTime: '0ms',
        planningCount: 0
      },
      selectedAlgorithm: 'greedy',
      clusterOptions: [],
      selectedCluster: '',
      evaluationData: [],
      evaluationRaw: [],
      clusterData: [],
      clusterLoaded: false,
      exportingType: ''
    };
  },
  computed: {
    getProgressColor() {
      return [
        { color: '#f56c6c', percentage: 20 },
        { color: '#e6a23c', percentage: 40 },
        { color: '#5cb87a', percentage: 60 },
        { color: '#1989fa', percentage: 80 },
        { color: '#6f7ad3', percentage: 100 }
      ];
    },
    // 当前系统模式文案（0=自动/综合最优 1=任务完成度最高 2=资源利用率最大 3=成像质量最高）
    modeText() {
      const map = {
        0: '自动（综合最优方案）',
        1: '任务完成度最高方案',
        2: '资源利用率最大方案',
        3: '成像质量最高方案'
      };
      return map[this.systemMode] || '自动（综合最优方案）';
    }
  },
  mounted() {
    this.loadData();
    this.loadClusterOptions();
    // 轮询仿真时间，保持与卫星网络页一致的时间锚点
    this.simTimer = setInterval(this.loadSimTime, 5000);
    window.addEventListener('resize', this.handleResize);
  },
  beforeUnmount() {
    window.removeEventListener('resize', this.handleResize);
    if (this.simTimer) {
      clearInterval(this.simTimer);
      this.simTimer = null;
    }
    this.disposeCharts();
  },
  methods: {
    // 惰性获取图表实例：隐藏 tab 中的图表在首次可见时才初始化，避免 0 尺寸问题
    getChartInst(refName) {
      if (!chartInsts[refName] && this.$refs[refName]) {
        chartInsts[refName] = echarts.init(this.$refs[refName]);
      }
      return chartInsts[refName] || null;
    },

    // 销毁图表
    disposeCharts() {
      Object.keys(chartInsts).forEach(key => {
        chartInsts[key].dispose();
        delete chartInsts[key];
      });
    },

    // 窗口大小变化处理
    handleResize() {
      Object.values(chartInsts).forEach(inst => inst.resize());
    },

    // tab 切换：图表容器从隐藏变为可见后需要 resize 并重绘
    onTabChange(name) {
      this.$nextTick(() => {
        if (name === 'algorithm') {
          this.updateClusterCharts();
        } else {
          this.updateCharts();
          this.updateCompareCharts();
        }
        this.handleResize();
      });
    },

    // 加载所有数据
    async loadData() {
      this.loading = true;
      try {
        await Promise.all([
          this.loadEvaluationData(),
          this.checkScheduleStatus(),
          this.loadStats(),
          this.loadSystemInfo()
        ]);
      } finally {
        this.loading = false;
      }
    },

    // 刷新数据
    async refreshData() {
      await this.loadData();
      if (this.selectedCluster) {
        await this.loadClusterData();
      }
      ElMessage.success('数据已刷新');
    },

    // 加载当前系统模式与仿真时间
    async loadSystemInfo() {
      try {
        const res = await this.$request.get('/getModel');
        this.systemMode = res.data?.mode ?? 0;
      } catch (err) {
        this.systemMode = 0;
      }
      await this.loadSimTime();
    },

    // 加载当前系统（仿真）时间
    async loadSimTime() {
      try {
        const res = await this.$request.get('/getCurrentTime');
        const t = res.data?.current_time;
        this.simTime = t ? String(t).slice(0, 19) : '--';
      } catch (err) {
        /* 后端未就绪时静默 */
      }
    },

    // 加载统计数据
    async loadStats() {
      try {
        const res = await this.$request.get('/getPlanningEvaluation');
        const evaluation = res.data?.evaluation;
        if (evaluation && evaluation.length > 0) {
          const latest = evaluation[evaluation.length - 1];
          // 资源利用率取三种算法的平均值（后端仅按算法存储该指标）
          const algos = [latest.genetic, latest.greedy, latest.ant_colony].filter(Boolean);
          const avgUtil = algos.length > 0
            ? algos.reduce((sum, a) => sum + (a.resource_utilization || 0), 0) / algos.length
            : 0;
          const avgDuration = evaluation.reduce((sum, e) => sum + (e.duration || 0), 0) / evaluation.length;
          this.stats = {
            completionRate: Math.round((latest.task_satisfaction || 0) * 100),
            resourceUtilization: Math.round(avgUtil * 100),
            avgResponseTime: `${avgDuration.toFixed(2)}s`,
            planningCount: evaluation.length
          };
        }
      } catch (err) {
        console.error('加载统计数据失败:', err);
        ElMessage.warning('统计数据加载失败，请确认后端服务已启动');
      }
    },

    // 检查方案状态
    async checkScheduleStatus() {
      try {
        const res = await this.$request.get('/exportScheduleStatus');
        this.hasSchedule = res.data?.status || false;
      } catch (err) {
        this.hasSchedule = false;
      }
    },

    // 加载评估数据
    async loadEvaluationData() {
      this.tableLoading = true;
      try {
        const res = await this.$request.get('/getPlanningEvaluation');
        const evaluation = res.data?.evaluation || [];
        this.evaluationRaw = evaluation;

        // 取最近一次规划周期的数据，按算法拆成三行展示
        const latest = evaluation.length > 0 ? evaluation[evaluation.length - 1] : null;
        const algoMap = [
          { key: 'greedy', name: '贪心算法' },
          { key: 'ant_colony', name: '蚁群算法' },
          { key: 'genetic', name: '遗传算法' }
        ];
        this.evaluationData = latest ? algoMap.map((algo, index) => {
          const metrics = latest[algo.key] || {};
          return {
            id: index,
            algorithm: algo.name,
            completionRate: Math.round((metrics.task_satisfaction || 0) * 100),
            resourceUtilization: Math.round((metrics.resource_utilization || 0) * 100),
            imagingQuality: Math.round((metrics.imaging_quality || 0) * 100),
            batteryCost: (metrics.overall_battery_cost || 0).toFixed(2),
            storageCost: (metrics.overall_storage_cost || 0).toFixed(2),
            executionTime: (latest.duration || 0).toFixed(2),
            timestamp: latest.time || '-'
          };
        }) : [];

        // 更新图表
        this.updateCharts();
        this.updateCompareCharts();
      } catch (err) {
        console.error('加载评估数据失败:', err);
        this.evaluationData = [];
        this.evaluationRaw = [];
        this.updateCharts();
        this.updateCompareCharts();
        ElMessage.warning('评估数据加载失败，请确认系统已初始化并完成过任务规划');
      } finally {
        this.tableLoading = false;
      }
    },

    // 加载星簇选项
    async loadClusterOptions() {
      try {
        const res = await this.$request.get('/clusters/getAllClustersNames');
        const clusters = res.data?.data || res.data || [];
        this.clusterOptions = clusters.map(c => ({
          label: c.name || c,
          value: c.name || c
        }));
        if (this.clusterOptions.length > 0) {
          this.selectedCluster = this.clusterOptions[0].value;
          this.loadClusterData();
        }
      } catch (err) {
        console.error('加载星簇选项失败:', err);
      }
    },

    // 加载星簇数据
    async loadClusterData() {
      if (!this.selectedCluster) return;
      try {
        const res = await this.$request.get(`/getClusterData/${this.selectedCluster}`);
        this.clusterData = res.data?.data || [];
        this.clusterLoaded = true;
        this.$nextTick(() => this.updateClusterCharts());
      } catch (err) {
        console.error('加载星簇数据失败:', err);
        this.clusterData = [];
        this.clusterLoaded = true;
        this.updateClusterCharts();
      }
    },

    // 通用折线图渲染（深色 HUD 配色）
    setLineChart(refName, { times, series, percent = false }) {
      const inst = this.getChartInst(refName);
      if (!inst) return;
      const option = {
        color: series.map(s => s.color),
        tooltip: {
          trigger: 'axis',
          backgroundColor: 'rgba(6, 18, 42, 0.95)',
          borderColor: 'rgba(0, 220, 255, 0.35)',
          textStyle: { color: '#cfe8ff' },
          valueFormatter: percent ? (v) => `${v}%` : undefined
        },
        legend: series.length > 1 ? {
          textStyle: { color: '#9fc6e8' },
          top: 0
        } : undefined,
        grid: { left: 55, right: 20, top: 35, bottom: 28 },
        xAxis: {
          type: 'category',
          data: times.map(t => t.slice(5, 16)),
          axisLabel: { color: '#9fc6e8' },
          axisLine: { lineStyle: { color: 'rgba(0, 220, 255, 0.25)' } }
        },
        yAxis: {
          type: 'value',
          axisLabel: { color: '#9fc6e8', formatter: percent ? '{value}%' : '{value}' },
          splitLine: { lineStyle: { color: 'rgba(0, 220, 255, 0.12)' } }
        },
        series: series.map(s => ({
          name: s.name,
          type: 'line',
          smooth: true,
          data: s.data,
          // 发光线条 + 节点光晕，统一 HUD 质感
          lineStyle: { color: s.color, width: 2, shadowColor: s.color, shadowBlur: 8 },
          itemStyle: { color: s.color, shadowColor: s.color, shadowBlur: 5 },
          // 面积纵向渐变：上实下虚
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: s.color + '3d' },
              { offset: 1, color: s.color + '05' }
            ])
          }
        }))
      };
      inst.setOption(option, true);
    },

    // 更新星簇四指标折线图（任务数量/电量消耗量/固存使用量/固存资源利用率）
    updateClusterCharts() {
      const times = this.clusterData.map(item => String(item.time || '').slice(0, 19));
      // 后端每个时间点元素为 { time, status: { cluster_tasks_count, ... } }，status 可能为 null
      const getVal = (item, key) => {
        const s = item.status && typeof item.status === 'object' ? item.status : item;
        return Number(s[key] || 0);
      };
      this.setLineChart('clusterTasksChart', {
        times,
        series: [{ name: '任务数量', color: '#00dcff', data: this.clusterData.map(i => getVal(i, 'cluster_tasks_count')) }]
      });
      this.setLineChart('clusterBatteryChart', {
        times,
        series: [{ name: '电量消耗量', color: '#8ee06a', data: this.clusterData.map(i => Number(getVal(i, 'cluster_battery_cost').toFixed(2))) }]
      });
      this.setLineChart('clusterStorageChart', {
        times,
        series: [{ name: '固存使用量', color: '#ffd657', data: this.clusterData.map(i => Number(getVal(i, 'cluster_storage_cost').toFixed(2))) }]
      });
      this.setLineChart('clusterStorageUtilChart', {
        times,
        percent: true,
        series: [{ name: '固存资源利用率', color: '#ff7a7a', data: this.clusterData.map(i => Number((getVal(i, 'cluster_storage_utilization') * 100).toFixed(2))) }]
      });
    },

    // 更新多算法对比折线图（任务完成率/电量消耗量/固存使用量/规划耗时）
    updateCompareCharts() {
      const evals = this.evaluationRaw;
      const times = evals.map(e => String(e.time || '').slice(0, 19));
      const round2 = (v) => Number((v || 0).toFixed(2));
      // 蚁群/遗传/贪心 + 当前方案 四类曲线
      const buildSeries = (field, scale = 1) => [
        { name: '蚁群算法', color: '#8ee06a', data: evals.map(e => round2(((e.ant_colony || {})[field] || 0) * scale)) },
        { name: '遗传算法', color: '#ffd657', data: evals.map(e => round2(((e.genetic || {})[field] || 0) * scale)) },
        { name: '贪心算法', color: '#00dcff', data: evals.map(e => round2(((e.greedy || {})[field] || 0) * scale)) },
        { name: '当前方案', color: '#ff7a7a', data: evals.map(e => round2((e[field] || 0) * scale)) }
      ];
      this.setLineChart('cmpCompletionChart', {
        times, percent: true, series: buildSeries('task_satisfaction', 100)
      });
      this.setLineChart('cmpBatteryChart', {
        times, series: buildSeries('overall_battery_cost')
      });
      this.setLineChart('cmpStorageChart', {
        times, series: buildSeries('overall_storage_cost')
      });
      // 规划耗时仅展示当前方案
      this.setLineChart('cmpDurationChart', {
        times,
        series: [{ name: '当前方案', color: '#ff7a7a', data: evals.map(e => round2(e.duration)) }]
      });
    },

    // 更新图表
    updateCharts() {
      const radarChartInst = this.getChartInst('radarChart');
      const barChartInst = this.getChartInst('barChart');

      // 雷达图配置（深色 HUD 配色：浅色文字 + 青色网格线）
      if (radarChartInst) {
        const radarOption = {
          color: ['#00dcff', '#8ee06a', '#ffd657'],
          tooltip: {
            backgroundColor: 'rgba(6, 18, 42, 0.95)',
            borderColor: 'rgba(0, 220, 255, 0.35)',
            textStyle: { color: '#cfe8ff' }
          },
          legend: {
            textStyle: { color: '#9fc6e8' }
          },
          radar: {
            indicator: [
              { name: '完成率', max: 100 },
              { name: '资源利用率', max: 100 },
              { name: '成像质量', max: 100 },
              { name: '响应速度', max: 100 }
            ],
            radius: '65%',
            axisName: { color: '#9fc6e8' },
            splitLine: { lineStyle: { color: 'rgba(0, 220, 255, 0.2)' } },
            splitArea: { areaStyle: { color: ['rgba(0,220,255,0.03)', 'rgba(0,220,255,0.06)'] } },
            axisLine: { lineStyle: { color: 'rgba(0, 220, 255, 0.2)' } }
          },
          series: [{
            type: 'radar',
            // 雷达填充渐变发光：算法色半透明填充 + 描边发光
            data: this.evaluationData.map((item, idx) => {
              const c = ['#00dcff', '#8ee06a', '#ffd657'][idx % 3];
              return {
                // 响应速度：规划耗时按 0~60s 线性映射为 100~0 分（耗时越短得分越高，超 60s 计 0 分）
                value: [
                  item.completionRate,
                  item.resourceUtilization,
                  item.imagingQuality,
                  Math.max(0, Math.min(100, Math.round(100 - Number(item.executionTime) / 60 * 100)))
                ],
                name: item.algorithm,
                lineStyle: { color: c, width: 2, shadowColor: c, shadowBlur: 6 },
                itemStyle: { color: c },
                areaStyle: { color: c + '26' }
              };
            })
          }]
        };
        radarChartInst.setOption(radarOption, true);
      }

      // 柱状图配置（深色 HUD 配色）
      if (barChartInst) {
        const barOption = {
          tooltip: {
            trigger: 'axis',
            backgroundColor: 'rgba(6, 18, 42, 0.95)',
            borderColor: 'rgba(0, 220, 255, 0.35)',
            textStyle: { color: '#cfe8ff' }
          },
          xAxis: {
            type: 'category',
            data: this.evaluationData.map(item => item.algorithm),
            axisLabel: { color: '#9fc6e8' },
            axisLine: { lineStyle: { color: 'rgba(0, 220, 255, 0.25)' } }
          },
          yAxis: {
            type: 'value',
            max: 100,
            axisLabel: { color: '#9fc6e8' },
            splitLine: { lineStyle: { color: 'rgba(0, 220, 255, 0.12)' } }
          },
          series: [{
            data: this.evaluationData.map(item => {
              const c = item.algorithm === '贪心算法' ? '#00c8f0' :
                        item.algorithm === '蚁群算法' ? '#67C23A' : '#E6A23C';
              return {
                value: item.completionRate,
                // 柱体纵向渐变 + 发光
                itemStyle: {
                  color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                    { offset: 0, color: c },
                    { offset: 1, color: c + '3d' }
                  ]),
                  borderRadius: [3, 3, 0, 0],
                  shadowColor: c + '88',
                  shadowBlur: 8
                }
              };
            }),
            type: 'bar',
            barWidth: '40%'
          }]
        };
        barChartInst.setOption(barOption, true);
      }
    },

    // 算法切换
    onAlgorithmChange(val) {
      // 可以在这里更新图表高亮等
    },

    // 星簇切换
    onClusterChange() {
      this.loadClusterData();
    },

    // 获取算法标签类型
    getAlgorithmType(algorithm) {
      const map = {
        '贪心算法': 'primary',
        '蚁群算法': 'success',
        '遗传算法': 'warning'
      };
      return map[algorithm] || 'info';
    },

    // 获取完成率样式
    getRateClass(rate) {
      if (rate >= 90) return 'rate-excellent';
      if (rate >= 75) return 'rate-good';
      return 'rate-normal';
    },

    // 查看详情
    viewDetail(row) {
      ElMessage.info(`查看 ${row.algorithm} 的详细评估数据`);
    },

    // 执行导出
    async doExport(type) {
      this.exportingType = type;
      try {
        const res = await this.$request.post(
          `/exportSchedule/${type}`,
          { number: null },
          { responseType: 'blob' }
        );

        const url = window.URL.createObjectURL(new Blob([res.data]));
        const link = document.createElement('a');
        link.href = url;

        const fileNames = {
          greedy: '贪心算法方案.txt',
          ant: '蚁群算法方案.txt',
          genetic: '遗传算法方案.txt',
          schedule: '所选方案.txt'
        };
        link.setAttribute('download', fileNames[type]);

        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);

        ElMessage.success('导出成功');
      } catch (err) {
        ElMessage.error('导出失败: ' + (err.message || '未知错误'));
      } finally {
        this.exportingType = '';
      }
    }
  }
};
</script>

<style scoped>
.performance-analysis {
  padding: 0;
}

/* 头部卡片 */
.header-card {
  margin-bottom: 20px;
  /* 深色 HUD 渐变由 dark-tech.css 的 .header-card 规则统一覆盖 */
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 16px;
}

.title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #303133;
}

.subtitle {
  margin: 4px 0 0 0;
  font-size: 13px;
  color: #909399;
}

.header-actions {
  display: flex;
  gap: 12px;
}

/* tab 页签 */
.perf-tabs {
  margin-bottom: 4px;
}

/* 系统模式/时间信息栏 */
.sys-meta {
  display: flex;
  align-items: center;
  gap: 32px;
  flex-wrap: wrap;
}

.meta-item {
  font-size: 14px;
  color: #9fc6e8;
}

.meta-item b {
  color: #00dcff;
  font-weight: 600;
}

/* 导出按钮栏 */
.export-card {
  margin-bottom: 20px;
}

.export-bar {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

/* 统计卡片 */
.stats-row {
  margin-bottom: 20px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 24px;
  font-weight: 600;
  color: #303133;
  line-height: 1.2;
}

.stat-label {
  font-size: 13px;
  color: #909399;
  margin-top: 4px;
}

/* 图表行 */
.chart-row {
  margin-bottom: 20px;
}

.chart-card {
  height: 400px;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}

.chart-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

.chart-container {
  height: 320px;
  width: 100%;
}

/* 星簇卡片 / 对比图卡片 */
.cluster-card {
  margin-bottom: 20px;
}

.compare-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}

.grid-chart-title {
  font-size: 13px;
  color: #9fc6e8;
  margin: 8px 0 4px 4px;
}

.grid-chart-container {
  height: 260px;
  width: 100%;
}

/* 详细数据卡片 */
.detail-card {
  margin-bottom: 20px;
}

/* 完成率样式 */
.rate-excellent {
  color: #67C23A;
  font-weight: 600;
}

.rate-good {
  color: #409EFF;
  font-weight: 600;
}

.rate-normal {
  color: #E6A23C;
}

/* 响应式 */
@media (max-width: 768px) {
  .header-content {
    flex-direction: column;
    align-items: flex-start;
  }

  .header-actions {
    width: 100%;
  }

  .header-actions .el-button {
    flex: 1;
  }

  .chart-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .card-header {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
