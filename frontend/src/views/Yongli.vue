<template>
  <div class="case-demo">
    <!-- 页面标题 -->
    <el-card shadow="never" class="header-card">
      <div class="header-content">
        <div class="header-title">
          <el-icon :size="24" color="#00dcff"><Document /></el-icon>
          <div>
            <h2 class="title">示范用例</h2>
            <p class="subtitle">执行典型任务场景，验证系统能力</p>
          </div>
        </div>
        <el-button type="primary" :icon="Refresh" @click="refreshAll" :loading="loading">刷新状态</el-button>
      </div>
    </el-card>

    <!-- 用例卡片列表 -->
    <el-row :gutter="16" class="case-row">
      <!-- 点目标案例 -->
      <el-col :xs="24" :md="8">
        <el-card shadow="hover" class="case-card">
          <div class="case-header">
            <div class="case-icon point">
              <el-icon :size="32" color="#fff"><MapLocation /></el-icon>
            </div>
            <div class="case-info">
              <h3 class="case-name">点目标案例</h3>
              <p class="case-desc">生成一批点目标观测任务，测试单点观测能力</p>
            </div>
          </div>
          <div class="case-content">
            <div class="case-features">
              <el-tag size="small" effect="plain">单点观测</el-tag>
              <el-tag size="small" effect="plain">高分辨率</el-tag>
              <el-tag size="small" effect="plain">快速响应</el-tag>
            </div>
            <div class="case-actions">
              <el-button 
                type="primary" 
                :icon="VideoPlay" 
                @click="executeCase('point')"
                :loading="caseLoading.point"
              >
                执行用例
              </el-button>
              <el-button :icon="View" @click="showCaseDetail('point')">查看详情</el-button>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 区域目标案例 -->
      <el-col :xs="24" :md="8">
        <el-card shadow="hover" class="case-card">
          <div class="case-header">
            <div class="case-icon area">
              <el-icon :size="32" color="#fff"><FullScreen /></el-icon>
            </div>
            <div class="case-info">
              <h3 class="case-name">区域目标案例</h3>
              <p class="case-desc">生成区域目标观测任务，测试大范围覆盖能力</p>
            </div>
          </div>
          <div class="case-content">
            <div class="case-features">
              <el-tag size="small" effect="plain">区域覆盖</el-tag>
              <el-tag size="small" effect="plain">条带拼接</el-tag>
              <el-tag size="small" effect="plain">协同观测</el-tag>
            </div>
            <div class="case-actions">
              <el-button 
                type="success" 
                :icon="VideoPlay" 
                @click="executeCase('area')"
                :loading="caseLoading.area"
              >
                执行用例
              </el-button>
              <el-button :icon="View" @click="showCaseDetail('area')">查看详情</el-button>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 海洋搜救案例 -->
      <el-col :xs="24" :md="8">
        <el-card shadow="hover" class="case-card">
          <div class="case-header">
            <div class="case-icon ocean">
              <el-icon :size="32" color="#fff"><Ship /></el-icon>
            </div>
            <div class="case-info">
              <h3 class="case-name">海洋搜救案例</h3>
              <p class="case-desc">生成海洋移动目标搜救任务，测试动态跟踪能力</p>
            </div>
          </div>
          <div class="case-content">
            <div class="case-features">
              <el-tag size="small" effect="plain">移动目标</el-tag>
              <el-tag size="small" effect="plain">动态跟踪</el-tag>
              <el-tag size="small" effect="plain">紧急响应</el-tag>
            </div>
            <div class="case-actions">
              <el-button 
                type="warning" 
                :icon="VideoPlay" 
                @click="executeCase('ocean')"
                :loading="caseLoading.ocean"
              >
                执行用例
              </el-button>
              <el-button :icon="View" @click="showCaseDetail('ocean')">查看详情</el-button>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 执行结果 -->
    <el-card shadow="never" class="result-card" v-if="executionResult">
      <template #header>
        <div class="result-header">
          <div class="result-title">
            <el-icon :size="18" color="#8ee06a"><CircleCheckFilled /></el-icon>
            <span>用例执行结果</span>
          </div>
          <el-button link :icon="Close" @click="executionResult = null">关闭</el-button>
        </div>
      </template>
      <el-descriptions :column="3" border>
        <el-descriptions-item label="用例类型">{{ executionResult.caseName }}</el-descriptions-item>
        <el-descriptions-item label="生成任务数">{{ executionResult.taskCount }} 个</el-descriptions-item>
        <el-descriptions-item label="执行状态">
          <el-tag :type="executionResult.success ? 'success' : 'danger'">
            {{ executionResult.success ? '成功' : '失败' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="执行时间">{{ executionResult.executeTime }}</el-descriptions-item>
        <el-descriptions-item label="描述" :span="2">{{ executionResult.message }}</el-descriptions-item>
      </el-descriptions>
      <div class="result-actions" v-if="executionResult.success">
        <el-button type="primary" :icon="List" @click="goToTasks">查看任务列表</el-button>
        <el-button :icon="View" @click="showResultDetail">查看详细结果</el-button>
      </div>
    </el-card>

    <!-- 用例详情弹窗 -->
    <el-dialog v-model="detailVisible" title="用例详情" width="600px" @closed="destroyCaseMap">
      <div v-if="currentCase" class="case-detail">
        <div class="detail-section">
          <h4 class="section-title">用例说明</h4>
          <p class="section-content">{{ currentCase.description }}</p>
        </div>
        <div class="detail-section" v-if="presetInfo">
          <h4 class="section-title">案例参数（预置文件真实数据）</h4>
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item label="优先级">{{ presetInfo.priority ?? '-' }}</el-descriptions-item>
            <el-descriptions-item label="是否紧急">{{ presetInfo.isEmergency || '-' }}</el-descriptions-item>
            <el-descriptions-item label="载荷类型">{{ presetInfo.sensorType || '-' }}</el-descriptions-item>
            <el-descriptions-item label="分辨率">{{ presetInfo.resolution ? presetInfo.resolution + ' m' : '-' }}</el-descriptions-item>
            <el-descriptions-item label="所属星簇">{{ presetInfo.clusterName || 'All_Sat' }}</el-descriptions-item>
            <el-descriptions-item label="云层厚度">{{ presetInfo.cloudThickness ?? 0 }} m</el-descriptions-item>
            <el-descriptions-item label="时间范围" :span="2">{{ presetInfo.timeRange || '-' }}</el-descriptions-item>
            <el-descriptions-item label="坐标点" :span="2">
              <span v-for="(p, i) in presetInfo.points" :key="i" class="point-tag">[{{ p[0] }}, {{ p[1] }}]</span>
            </el-descriptions-item>
          </el-descriptions>
        </div>
        <div class="detail-section" v-if="caseResult">
          <h4 class="section-title">最近执行结果（归档数据）</h4>
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item label="案例名称">{{ caseResult.taskName || '-' }}</el-descriptions-item>
            <el-descriptions-item label="案例状态">
              <el-tag size="small" :type="caseResult.status === 'Success' ? 'success' : 'danger'">
                {{ caseResult.status === 'Success' ? '成功' : (caseResult.status || '-') }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="开始时间">{{ caseResult.startTime || '-' }}</el-descriptions-item>
            <el-descriptions-item label="结束时间">{{ caseResult.endTime || '-' }}</el-descriptions-item>
            <el-descriptions-item label="优先级">{{ caseResult.priority ?? '-' }}</el-descriptions-item>
            <el-descriptions-item label="是否紧急">{{ caseResult.isEmergency ? '是' : '否' }}</el-descriptions-item>
            <el-descriptions-item label="载荷">{{ caseResult.sensorType || '-' }}</el-descriptions-item>
            <el-descriptions-item label="分辨率">{{ caseResult.resolution ? caseResult.resolution + ' m' : '-' }}</el-descriptions-item>
            <el-descriptions-item label="是否拍照">{{ caseResult.isPhoto ? '是' : '否' }}</el-descriptions-item>
            <el-descriptions-item label="所属卫星">{{ caseResult.assignedSatelliteName || '-' }}</el-descriptions-item>
            <el-descriptions-item label="图片路径" :span="2">{{ caseResult.path || '-' }}</el-descriptions-item>
            <el-descriptions-item label="位置（纬度，经度）" :span="2">{{ caseResult.targetLocation || '-' }}</el-descriptions-item>
          </el-descriptions>
        </div>
        <div class="detail-section" v-if="hasCaseMapData">
          <h4 class="section-title">案例区域示意</h4>
          <div ref="caseMap" class="case-map"></div>
        </div>
        <div class="detail-section">
          <h4 class="section-title">任务特点</h4>
          <ul class="feature-list">
            <li v-for="(feature, index) in currentCase.features" :key="index">{{ feature }}</li>
          </ul>
        </div>
        <div class="detail-section">
          <h4 class="section-title">执行流程</h4>
          <el-steps :active="3" simple>
            <el-step title="生成任务" :icon="Document" />
            <el-step title="任务规划" :icon="SetUp" />
            <el-step title="卫星执行" :icon="Compass" />
            <el-step title="结果反馈" :icon="CircleCheck" />
          </el-steps>
        </div>
      </div>
    </el-dialog>

    <!-- 历史记录 -->
    <el-card shadow="never" class="history-card">
      <template #header>
        <div class="history-header">
          <div class="history-title">
            <el-icon :size="18" color="#9fc6e8"><Timer /></el-icon>
            <span>执行历史</span>
          </div>
          <el-button link type="danger" :icon="Delete" @click="clearHistory">清空历史</el-button>
        </div>
      </template>
      <el-empty v-if="historyList.length === 0" description="暂无执行记录" />
      <el-timeline v-else>
        <el-timeline-item
          v-for="item in historyList"
          :key="item.id"
          :type="item.success ? 'success' : 'danger'"
          :icon="item.success ? CircleCheckFilled : CircleCloseFilled"
          :timestamp="item.time"
        >
          <div class="timeline-content">
            <span class="timeline-title">{{ item.caseName }}</span>
            <el-tag size="small" :type="item.success ? 'success' : 'danger'">
              {{ item.success ? '成功' : '失败' }}
            </el-tag>
            <span class="timeline-detail">生成 {{ item.taskCount }} 个任务</span>
          </div>
        </el-timeline-item>
      </el-timeline>
    </el-card>
  </div>
</template>

<script>
import { ElMessage, ElMessageBox } from 'element-plus';
import * as Cesium from 'cesium';
import {
  Document, Refresh, VideoPlay, View, MapLocation, FullScreen, Ship,
  CircleCheckFilled, Close, List, SetUp, Compass, CircleCheck,
  Timer, Delete, CircleCloseFilled
} from '@element-plus/icons-vue';

export default {
  name: 'CaseDemo',
  components: {
    Document, Refresh, VideoPlay, View, MapLocation, FullScreen, Ship,
    CircleCheckFilled, Close, List, SetUp, Compass, CircleCheck,
    Timer, Delete, CircleCloseFilled
  },
  data() {
    return {
      loading: false,
      caseLoading: {
        point: false,
        area: false,
        ocean: false
      },
      executionResult: null,
      detailVisible: false,
      currentCase: null,
      presetInfo: null,  // 预置案例文件中的真实案例参数（/tasks/presetCaseInfo）
      caseResult: null,  // 最近一次已归档的用例执行结果（/tasks/caseResult）
      historyList: [],
      caseDetails: {
        point: {
          name: '点目标案例',
          description: '点目标观测是卫星对地观测的基本任务类型。本用例将生成多个点目标观测任务，分布在不同地理区域，测试卫星对定点目标的快速响应和观测能力。',
          features: [
            '任务分布范围广，覆盖多个地理区域',
            '任务优先级各异，测试调度算法',
            '不同载荷类型需求（光学/SAR/红外）',
            '测试卫星姿态机动能力'
          ]
        },
        area: {
          name: '区域目标案例',
          description: '区域目标观测需要对大范围区域进行覆盖成像，通常需要多颗卫星协同完成。本用例将生成区域覆盖任务，测试多星协同观测能力。',
          features: [
            '大范围区域覆盖需求',
            '多星协同条带拼接',
            '测试负载均衡能力',
            '验证任务分解与合并策略'
          ]
        },
        ocean: {
          name: '海洋搜救案例',
          description: '海洋搜救任务通常具有紧急性和时效性要求，需要对移动目标进行持续跟踪。本用例模拟海上搜救场景，测试应急任务响应能力。',
          features: [
            '紧急任务优先级处理',
            '移动目标动态跟踪',
            '多星接力观测',
            '实时任务重规划能力'
          ]
        }
      }
    };
  },
  computed: {
    // 是否有可绘制到示意图上的数据（预置坐标点或归档执行结果位置）
    hasCaseMapData() {
      const presetPts = this.presetInfo && this.presetInfo.points;
      if (presetPts && presetPts.length) return true;
      return this.parsePoints(this.caseResult && this.caseResult.targetLocation).length > 0;
    }
  },
  created() {
    this.loadHistory();
  },
  beforeUnmount() {
    this.destroyCaseMap();
  },
  methods: {
    // 执行用例
    async executeCase(type) {
      const urlMap = {
        point: '/tasks/pointTargetCase',
        area: '/tasks/areaTargetCase',
        ocean: '/tasks/oceanTargetCase'
      };
      
      const nameMap = {
        point: '点目标案例',
        area: '区域目标案例',
        ocean: '海洋搜救案例'
      };

      this.caseLoading[type] = true;
      
      try {
        const res = await this.$request.get(urlMap[type]);
        
        const result = {
          caseType: type,
          caseName: nameMap[type],
          success: true,
          taskCount: res.data?.count || '若干',
          message: res.data?.message || `${nameMap[type]}执行成功，任务已生成并加入调度队列`,
          executeTime: new Date().toLocaleString()
        };
        
        this.executionResult = result;
        
        // 添加到历史记录
        this.addToHistory(result);
        
        ElMessage.success(`${nameMap[type]}执行成功`);
      } catch (err) {
        console.error('执行用例失败:', err);
        
        const result = {
          caseType: type,
          caseName: nameMap[type],
          success: false,
          taskCount: 0,
          message: err.response?.data?.error || err.message || '执行失败',
          executeTime: new Date().toLocaleString()
        };
        
        this.executionResult = result;
        this.addToHistory(result);
        
        ElMessage.error(`${nameMap[type]}执行失败: ${result.message}`);
      } finally {
        this.caseLoading[type] = false;
      }
    },

    // 显示用例详情（加载预置案例文件中的真实参数并渲染区域示意图）
    async showCaseDetail(type) {
      this.currentCase = {
        ...this.caseDetails[type],
        type
      };
      this.presetInfo = null;
      this.caseResult = null;
      this.detailVisible = true;
      try {
        const res = await this.$request.get(`/tasks/presetCaseInfo/${type}`);
        if (res.data?.status === 'success') {
          this.presetInfo = res.data.data;
        }
      } catch (e) {
        console.error('获取案例参数失败:', e);
      }
      // 查询最近一次执行归档结果（404 表示暂无归档，属正常情况）
      try {
        const res = await this.$request.get(`/tasks/caseResult/${type}`);
        if (res.data?.status === 'success') {
          this.caseResult = res.data.data;
        }
      } catch (e) {
        console.error('获取用例执行结果失败:', e);
      }
      // 等弹窗动画与 DOM 渲染完成后初始化地图
      this.$nextTick(() => { setTimeout(this.initCaseMap, 300); });
    },

    // 解析位置字符串为坐标点列表：支持 "[44.81, -98.44]" 与 "[[44.81,-98.44],[...]]" 两种格式
    parsePoints(str) {
      if (!str) return [];
      const matches = String(str).match(/-?\d+\.?\d*/g) || [];
      const pts = [];
      for (let i = 0; i + 1 < matches.length; i += 2) {
        pts.push([parseFloat(matches[i]), parseFloat(matches[i + 1])]);
      }
      return pts;
    },

    // 初始化案例区域示意图（2D 平面地图 + 坐标点/边界多边形）
    initCaseMap() {
      const pts = (this.presetInfo && this.presetInfo.points) || [];
      // 归档执行结果的位置点（红色标注，区分预置区域的青色）
      const resultPts = this.parsePoints(this.caseResult && this.caseResult.targetLocation);
      const el = this.$refs.caseMap;
      if (!el || (!pts.length && !resultPts.length)) return;
      this.destroyCaseMap();
      this._caseViewer = new Cesium.Viewer(el, {
        baseLayer: false,  // 禁用默认 Ion 底图，改用高德瓦片
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
        sceneMode: Cesium.SceneMode.SCENE2D  // 2D 平面示意更直观
      });
      this._caseViewer.imageryLayers.removeAll();
      // 底图：Esri 全球卫星影像（全球覆盖无占位图）+ 高德中文注记叠加层
      this._caseViewer.imageryLayers.addImageryProvider(new Cesium.UrlTemplateImageryProvider({
        url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        maximumLevel: 13
      }));
      this._caseViewer.imageryLayers.addImageryProvider(new Cesium.UrlTemplateImageryProvider({
        url: 'https://webst0{s}.is.autonavi.com/appmaptile?style=8&x={x}&y={y}&z={z}',
        subdomains: ['1', '2', '3', '4'],
        maximumLevel: 13
      }));
      this._caseViewer._cesiumWidget._creditContainer.style.display = 'none';
      const positions = [];
      pts.forEach((p, idx) => {
        const c = Cesium.Cartesian3.fromDegrees(p[1], p[0]);  // [纬度, 经度] → (lon, lat)
        positions.push(c);
        this._caseViewer.entities.add({
          position: c,
          point: {
            pixelSize: 10,
            color: Cesium.Color.fromCssColorString('#00f0ff'),
            outlineColor: Cesium.Color.WHITE,
            outlineWidth: 2
          },
          // 海洋搜救案例：边界点标注为“搜救目标N”（对齐图42 设计稿）
          label: this.currentCase && this.currentCase.type === 'ocean' ? {
            text: `搜救目标${idx + 1}`,
            font: '12px sans-serif',
            pixelOffset: new Cesium.Cartesian2(0, -16),
            fillColor: Cesium.Color.fromCssColorString('#00f0ff')
          } : undefined
        });
      });
      // 多坐标点（区域类案例）绘制边界多边形
      if (pts.length > 2) {
        this._caseViewer.entities.add({
          polygon: {
            hierarchy: new Cesium.PolygonHierarchy(positions),
            material: Cesium.Color.fromCssColorString('#00dcff').withAlpha(0.3),
            outline: true,
            outlineColor: Cesium.Color.fromCssColorString('#00f0ff')
          }
        });
      }
      // 海洋搜救案例：搜救目标点依次连成绿色虚线作为“目标轨迹”示意（对齐图42 设计稿；
      // 注意：后端无真实移动目标轨迹数据，此为示意图，非真实轨迹）
      if (this.currentCase && this.currentCase.type === 'ocean' && positions.length > 1) {
        this._caseViewer.entities.add({
          polyline: {
            positions: positions,
            width: 3,
            material: new Cesium.PolylineDashMaterialProperty({
              color: Cesium.Color.fromCssColorString('#7cffb2')
            })
          }
        });
        // 轨迹标签放在中间位置
        this._caseViewer.entities.add({
          position: positions[Math.floor(positions.length / 2)],
          label: {
            text: '目标轨迹',
            font: '12px sans-serif',
            pixelOffset: new Cesium.Cartesian2(0, 14),
            fillColor: Cesium.Color.fromCssColorString('#7cffb2')
          }
        });
      }
      // 归档执行结果位置：红色点 + 标签（单点标任务名，多点标 任务名-P1..N）
      const resultName = (this.caseResult && this.caseResult.taskName) || '';
      resultPts.forEach((p, idx) => {
        this._caseViewer.entities.add({
          position: Cesium.Cartesian3.fromDegrees(p[1], p[0]),
          point: {
            pixelSize: 12,
            color: Cesium.Color.fromCssColorString('#ff6b6b'),
            outlineColor: Cesium.Color.WHITE,
            outlineWidth: 2
          },
          // 多点结果与预置点位置重合时不再加文字标签（预置点的“搜救目标N”标签已标识），单点显示任务名
          label: resultPts.length > 1 ? undefined : {
            text: resultName,
            font: '12px sans-serif',
            pixelOffset: new Cesium.Cartesian2(0, -18),
            fillColor: Cesium.Color.fromCssColorString('#ff6b6b')
          }
        });
      });
      // 视野对准案例区域（四周留 0.5° 边距，让小区域特征更清晰）
      const allPts = pts.concat(resultPts);
      const lats = allPts.map(p => p[0]);
      const lons = allPts.map(p => p[1]);
      this._caseViewer.camera.setView({
        destination: Cesium.Rectangle.fromDegrees(
          Math.min(...lons) - 0.5, Math.min(...lats) - 0.5,
          Math.max(...lons) + 0.5, Math.max(...lats) + 0.5
        )
      });
    },

    // 销毁案例示意图 viewer，释放 WebGL 上下文
    destroyCaseMap() {
      if (this._caseViewer) {
        this._caseViewer.destroy();
        this._caseViewer = null;
      }
    },

    // 显示结果详情
    showResultDetail() {
      if (this.executionResult) {
        ElMessage.info('任务已生成，可在任务管理页面查看详情');
      }
    },

    // 跳转到任务列表
    goToTasks() {
      this.$router.push('/satellite/renwu/shuxing');
    },

    // 刷新所有：真实请求后端任务状态接口，成功后再提示
    async refreshAll() {
      this.loading = true;
      try {
        await this.$request.get('/tasks/getNewTasksByCondition');
        ElMessage.success('状态已刷新');
      } catch (err) {
        ElMessage.error('刷新失败：后端服务暂不可用');
      } finally {
        this.loading = false;
      }
    },

    // 添加到历史记录（后端持久化，后端不可用时降级为本地缓存）
    async addToHistory(result) {
      try {
        const res = await this.$request.post('/tasks/caseHistory', {
          caseType: result.caseType,
          caseName: result.caseName,
          success: result.success,
          taskCount: typeof result.taskCount === 'number' ? result.taskCount : null,
          message: result.message
        });
        if (res.data?.data) {
          this.historyList.unshift({ ...res.data.data, id: 'srv_' + res.data.data.id });
        }
      } catch (e) {
        console.error('保存后端历史记录失败，降级为本地缓存:', e);
        this.historyList.unshift({
          id: Date.now() + '_' + Math.random().toString(36).slice(2, 8),
          caseName: result.caseName,
          success: result.success,
          taskCount: result.taskCount,
          time: result.executeTime
        });
        this.saveHistory();
      }
      // 只保留最近10条
      if (this.historyList.length > 10) {
        this.historyList = this.historyList.slice(0, 10);
      }
    },

    // 保存历史记录到本地
    saveHistory() {
      localStorage.setItem('caseHistory', JSON.stringify(this.historyList));
    },

    // 加载历史记录（优先后端持久化数据，失败时回退本地缓存）
    async loadHistory() {
      try {
        const res = await this.$request.get('/tasks/caseHistory');
        if (Array.isArray(res.data)) {
          this.historyList = res.data.slice(0, 10).map(item => ({ ...item, id: 'srv_' + item.id }));
          return;
        }
      } catch (e) {
        console.error('加载后端历史记录失败，回退本地缓存:', e);
      }
      const history = localStorage.getItem('caseHistory');
      if (history) {
        try {
          // 兼容旧数据：没有 id 的历史记录按 时间+名称 补一个唯一 key
          this.historyList = JSON.parse(history).map((item, i) => ({
            ...item,
            id: item.id || `${item.time}_${item.caseName}_${i}`
          }));
        } catch (e) {
          console.error('加载历史记录失败:', e);
        }
      }
    },

    // 清空历史
    async clearHistory() {
      try {
        await ElMessageBox.confirm('确定要清空所有执行历史吗？', '提示', {
          type: 'warning'
        });
        this.historyList = [];
        try {
          await this.$request.delete('/tasks/caseHistory');
        } catch (e) {
          console.error('清空后端历史记录失败:', e);
        }
        localStorage.removeItem('caseHistory');
        ElMessage.success('历史记录已清空');
      } catch {
        // 取消
      }
    }
  }
};
</script>

<style scoped>
.case-demo {
  padding: 0;
}

/* 头部卡片 */
.header-card {
  margin-bottom: 20px;
  background: linear-gradient(135deg, #f5f7fa 0%, #e4e7ed 100%);
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
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

/* 用例卡片 */
.case-row {
  margin-bottom: 20px;
}

.case-card {
  height: 100%;
  transition: all 0.3s;
}

.case-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.case-header {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 20px;
}

.case-icon {
  width: 60px;
  height: 60px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.case-icon.point {
  background: linear-gradient(135deg, #409EFF 0%, #66b1ff 100%);
}

.case-icon.area {
  background: linear-gradient(135deg, #67C23A 0%, #85ce61 100%);
}

.case-icon.ocean {
  background: linear-gradient(135deg, #E6A23C 0%, #ebb563 100%);
}

.case-info {
  flex: 1;
}

.case-name {
  margin: 0 0 8px 0;
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.case-desc {
  margin: 0;
  font-size: 13px;
  color: #606266;
  line-height: 1.5;
}

.case-content {
  border-top: 1px solid #ebeef5;
  padding-top: 16px;
}

.case-features {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}

.case-actions {
  display: flex;
  gap: 12px;
}

/* 结果卡片 */
.result-card {
  margin-bottom: 20px;
  background: #f0f9ff;
  border: 1px solid #d9ecff;
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.result-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.result-actions {
  display: flex;
  gap: 12px;
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #d9ecff;
}

/* 用例详情 */
.case-detail {
  padding: 10px 0;
}

.detail-section {
  margin-bottom: 24px;
}

.detail-section:last-child {
  margin-bottom: 0;
}

/* 案例区域示意图 */
.case-map {
  height: 280px;
  width: 100%;
  border-radius: 4px;
  overflow: hidden;
}

/* 案例坐标点标签 */
.point-tag {
  display: inline-block;
  margin: 2px 6px 2px 0;
  padding: 1px 6px;
  background: rgba(64, 158, 255, 0.1);
  border-radius: 3px;
  font-family: 'Courier New', monospace;
  font-size: 12px;
}

.section-title {
  margin: 0 0 12px 0;
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

.section-content {
  margin: 0;
  font-size: 14px;
  color: #606266;
  line-height: 1.6;
}

.feature-list {
  margin: 0;
  padding-left: 20px;
  color: #606266;
}

.feature-list li {
  margin-bottom: 8px;
  line-height: 1.5;
}

.feature-list li:last-child {
  margin-bottom: 0;
}

/* 历史记录 */
.history-card {
  margin-top: 20px;
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.history-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.timeline-content {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.timeline-title {
  font-weight: 500;
  color: #303133;
}

.timeline-detail {
  font-size: 13px;
  color: #909399;
}

/* 响应式 */
@media (max-width: 768px) {
  .header-content {
    flex-direction: column;
    gap: 16px;
    align-items: flex-start;
  }

  .case-header {
    flex-direction: column;
    align-items: center;
    text-align: center;
  }

  .case-actions {
    flex-direction: column;
  }

  .case-actions .el-button {
    width: 100%;
  }

  .result-actions {
    flex-direction: column;
  }

  .timeline-content {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
}
</style>
