<template>
  <div class="settings-container">

    <!-- 第一部分：系统参数设置 -->
    <div class="section-wrapper">
      <div class="section-header">
        <div class="section-tag">01</div>
        <h2 class="section-title">系统参数设置</h2>
      </div>
      
      <div class="two-column-layout">
        <!-- 左侧：时间与参数 -->
        <div class="left-panel">
          <el-card shadow="never" class="setting-card">
            <template #header>
              <div class="card-header-inner">
                <el-icon :size="16" color="#8ee06a"><Clock /></el-icon>
                <span class="card-title">时间和参数设置</span>
              </div>
            </template>

            <div class="card-body">
              <div class="form-row">
                <label class="form-label">系统仿真时间</label>
                <div class="form-control">
                  <el-date-picker
                    v-model="form.dateRange"
                    type="datetimerange"
                    start-placeholder="开始时间"
                    end-placeholder="结束时间"
                    :default-time="defaultTime"
                    format="YYYY-MM-DD HH:mm:ss"
                    value-format="YYYY-MM-DD HH:mm:ss"
                    style="width: 100%"
                  />
                  <span class="input-hint">设置卫星网络仿真的起止时间范围</span>
                </div>
              </div>

              <div class="form-row">
                <label class="form-label">算法权重配置</label>
                <div class="form-control">
                  <div class="weight-inputs">
                    <div class="weight-box">
                      <span class="weight-name">任务完成率</span>
                      <el-input-number 
                        v-model="form.completed_gravity" 
                        :min="0" 
                        :max="10" 
                        :step="0.1"
                        :precision="1"
                        controls-position="right"
                        size="default"
                      />
                    </div>
                    <div class="weight-box">
                      <span class="weight-name">负载均衡</span>
                      <el-input-number 
                        v-model="form.balance_gravity" 
                        :min="0" 
                        :max="10" 
                        :step="0.1"
                        :precision="1"
                        controls-position="right"
                        size="default"
                      />
                    </div>
                    <div class="weight-box">
                      <span class="weight-name">优先级权重</span>
                      <el-input-number 
                        v-model="form.priority_gravity" 
                        :min="0" 
                        :max="10" 
                        :step="0.1"
                        :precision="1"
                        controls-position="right"
                        size="default"
                      />
                    </div>
                  </div>
                  <span class="input-hint">调整任务规划算法的优化目标权重</span>
                </div>
              </div>

              <div class="form-actions-row">
                <el-button type="primary" :icon="Check" @click="submitSimulate">保存并应用</el-button>
                <el-button :icon="RefreshRight" @click="resetForm">重置</el-button>
              </div>
            </div>
          </el-card>
        </div>

        <!-- 右侧：系统模式与上传 -->
        <div class="right-panel">
          <!-- 系统模式选择 -->
          <el-card shadow="never" class="setting-card mode-card">
            <template #header>
              <div class="card-header-inner">
                <el-icon :size="16" color="#f0b95c"><Switch /></el-icon>
                <span class="card-title">系统模式</span>
              </div>
            </template>

            <div class="card-body compact">
              <div class="mode-selector">
                <span class="mode-label" :class="{ inactive: form.auto_mode }">手动模式</span>
                <el-switch 
                  v-model="form.auto_mode" 
                  @change="changeMode"
                />
                <span class="mode-label" :class="{ inactive: !form.auto_mode }">自动模式</span>
              </div>
              
              <p class="mode-tip">
                <el-icon :size="12"><InfoFilled /></el-icon>
                {{ form.auto_mode ? '自动触发规划与调度' : '可自定义选择调度方案' }}
              </p>
              <p class="mode-desc">
                {{ form.auto_mode
                  ? '自动模式是三种方案加权输出（任务完成度最高方案、资源利用率最大方案、成像质量最高方案），系统将根据当前任务需求智能分配权重。'
                  : '手动模式可在下方指定调度方案，该方案将作为下一批次任务规划算法的执行目标。' }}
              </p>

              <div class="status-strip">
                <el-tag size="small" :type="submitStatus.tle ? 'success' : 'info'" effect="light">
                  TLE {{ submitStatus.tle ? '已上传' : '未上传' }}
                </el-tag>
                <el-tag size="small" :type="submitStatus.sat ? 'success' : 'info'" effect="light">
                  卫星参数 {{ submitStatus.sat ? '已上传' : '未上传' }}
                </el-tag>
                <el-tag size="small" :type="submitStatus.sys ? 'success' : 'warning'" effect="light">
                  系统参数 {{ submitStatus.sys ? '已提交' : '待提交' }}
                </el-tag>
              </div>

              <!-- 方案选择 -->
              <div v-show="!form.auto_mode" class="plan-box">
                <div class="plan-label">调度方案</div>
                <el-radio-group v-model="selectedPlan" @change="onPlanChange" size="small">
                  <el-radio-button label="completion">任务完成度最高</el-radio-button>
                  <el-radio-button label="utilization">资源利用率最大</el-radio-button>
                  <el-radio-button label="imaging">成像质量最高</el-radio-button>
                </el-radio-group>
              </div>
            </div>
          </el-card>

          <!-- TLE 文件上传 -->
          <el-card shadow="never" class="setting-card upload-mini-card">
            <template #header>
              <div class="card-header-inner">
                <el-icon :size="16" color="#00dcff"><Upload /></el-icon>
                <span class="card-title">TLE 轨道数据</span>
                <el-tag size="small" type="danger" effect="light">必需</el-tag>
              </div>
            </template>

            <div class="card-body compact">
              <p class="upload-text">上传 TLE 格式的卫星轨道数据文件</p>
              <el-upload
                class="simple-uploader"
                :action="uploadTleUrl"
                :headers="uploadHeaders"
                :show-file-list="true"
                :limit="1"
                :before-upload="beforeTleUpload"
                :on-success="onTleSuccess"
                :on-error="onTleError"
                accept=".txt,.tle"
              >
                <el-button type="primary" :icon="Upload" size="small">选择文件</el-button>
              </el-upload>
              <el-button type="success" :icon="Download" size="small" class="export-tle-btn" @click="exportTleFile">导出轨道数据</el-button>
            </div>
          </el-card>
        </div>
      </div>
    </div>

    <!-- 第二部分：卫星参数设置 -->
    <div class="section-wrapper">
      <div class="section-header">
        <div class="section-tag">02</div>
        <h2 class="section-title">卫星参数配置</h2>
      </div>

      <el-card shadow="never" class="setting-card sat-card">
        <template #header>
          <div class="card-header-inner">
            <el-icon :size="16" color="#9fc6e8"><Document /></el-icon>
            <span class="card-title">批量导入卫星参数</span>
            <el-tag size="small" type="danger" effect="light">必需</el-tag>
          </div>
        </template>

        <div class="sat-upload-container">
          <!-- 上传区域 -->
          <div class="upload-zone-wrapper">
            <el-upload
              ref="satUploadRef"
              class="sat-uploader"
              drag
              action="#"
              :auto-upload="false"
              :show-file-list="true"
              :on-change="handleSatFileChange"
              :on-remove="onSatRemove"
              accept=".json,.txt,.xls,.xlsx,.csv"
            >
              <el-icon class="upload-zone-icon" :size="40"><UploadFilled /></el-icon>
              <div class="upload-zone-text">
                <span class="primary">拖拽文件到此处</span>
                <span class="secondary">或 <em>点击选择文件</em></span>
              </div>
            </el-upload>

            <!-- 格式标签 -->
            <div class="format-tags">
              <el-tag v-for="fmt in ['JSON', 'TXT', 'XLS', 'XLSX', 'CSV']" :key="fmt" size="small" effect="plain" type="info">
                {{ fmt }}
              </el-tag>
            </div>
          </div>

          <!-- 操作按钮 -->
          <div class="upload-actions-bar" v-if="satFileReady">
            <el-button type="primary" :icon="Check" @click="submitSatUpload">确认上传</el-button>
            <el-button :icon="Delete" @click="clearSatFile">清空</el-button>
          </div>

        </div>
      </el-card>

      <!-- 方式二：单个卫星设置 -->
      <el-card shadow="never" class="setting-card sat-single-card">
        <template #header>
          <div class="card-header-inner">
            <el-icon :size="16" color="#8ee06a"><Edit /></el-icon>
            <span class="card-title">单个卫星参数设置</span>
            <el-button link type="primary" :icon="Setting" @click="$router.push('/satellite/network_parameters')">
              按载荷批量设置
            </el-button>
          </div>
        </template>

        <div class="sat-single-container">
          <!-- 卫星选择 -->
          <div class="sat-select-row">
            <label class="form-label">选择卫星</label>
            <div class="sat-select-wrapper">
              <el-select 
                v-model="selectedSatId" 
                placeholder="请选择要设置的卫星"
                @change="onSatelliteChange"
                filterable
                style="width: 100%"
              >
                <el-option 
                  v-for="sat in satelliteList" 
                  :key="sat.id" 
                  :label="`${sat.name} (${sat.orbit} - ${sat.loadType})`" 
                  :value="sat.id"
                />
              </el-select>
              <el-button :icon="Refresh" @click="loadSatelliteList" :loading="loadingSatList" circle size="small" title="刷新列表"></el-button>
            </div>
          </div>

          <!-- 参数表单 -->
          <el-collapse-transition>
            <div v-show="selectedSatId" class="satellite-form-wrapper">
              <el-divider content-position="left">基础参数</el-divider>
              
              <div class="param-grid">
                <div class="param-item">
                  <label>存储容量 (GB)</label>
                  <el-input-number v-model="satelliteForm.storage" :min="1" :max="10000" controls-position="right" />
                </div>
                <div class="param-item">
                  <label>电池容量 (Wh)</label>
                  <el-input-number v-model="satelliteForm.battery" :min="1" :max="20000" controls-position="right" />
                </div>
                <div class="param-item">
                  <label>下行速率 (GB/s)</label>
                  <el-input-number v-model="satelliteForm.downlink_rate" :min="0.1" :max="100" :step="0.1" controls-position="right" />
                </div>
              </div>

              <el-divider content-position="left">功率参数</el-divider>
              
              <div class="param-grid">
                <div class="param-item">
                  <label>空闲功率 (W)</label>
                  <el-input-number v-model="satelliteForm.eclipse_powers" :min="0" :max="1000" controls-position="right" />
                </div>
                <div class="param-item">
                  <label>太阳能功率 (W)</label>
                  <el-input-number v-model="satelliteForm.sunlight_powers" :min="0" :max="1000" controls-position="right" />
                </div>
                <div class="param-item">
                  <label>机动功率 (W)</label>
                  <el-input-number v-model="satelliteForm.maneuver_powers" :min="0" :max="5000" controls-position="right" />
                </div>
                <div class="param-item">
                  <label>成像功率 (W)</label>
                  <el-input-number v-model="satelliteForm.imaging_powers" :min="0" :max="5000" controls-position="right" />
                </div>
              </div>

              <el-divider content-position="left">载荷参数</el-divider>
              
              <div class="param-grid">
                <div class="param-item">
                  <label>载荷类型</label>
                  <el-select 
                    v-model="satelliteForm.loadType" 
                    placeholder="请选择载荷类型"
                    @change="onLoadTypeChange"
                    style="width: 100%"
                  >
                    <el-option 
                      v-for="opt in loadTypeOptions" 
                      :key="opt.value" 
                      :label="opt.label" 
                      :value="opt.value"
                    />
                  </el-select>
                </div>
                <div class="param-item">
                  <label>分辨率 (m)</label>
                  <el-input-number v-model="satelliteForm.resolution" :min="0.1" :max="100" :step="0.1" :precision="1" controls-position="right" />
                </div>
                <div class="param-item">
                  <label>幅宽最大值 (km)</label>
                  <el-input-number v-model="satelliteForm.width" :min="1" :max="500" controls-position="right" />
                </div>
                <div class="param-item">
                  <label>角度转动速度 (°/s)</label>
                  <el-input-number v-model="satelliteForm.angle_velocity" :min="0.1" :max="10" :step="0.1" controls-position="right" />
                </div>
                <div class="param-item">
                  <label>稳定时间 (s)</label>
                  <el-input-number v-model="satelliteForm.stable_time" :min="0" :max="60" controls-position="right" />
                </div>
                <div class="param-item">
                  <label>最大侧摆角度 (°)</label>
                  <el-input-number v-model="satelliteForm.side_swing_angle_Max" :min="0" :max="90" controls-position="right" />
                </div>
                <div class="param-item">
                  <label>最大俯仰角度 (°)</label>
                  <el-input-number v-model="satelliteForm.pitch_angle_Max" :min="0" :max="90" controls-position="right" />
                </div>
                <div class="param-item">
                  <label>云层厚度阈值 (m)</label>
                  <el-input-number v-model="satelliteForm.cloud_threshold" :min="0" :max="2000" controls-position="right" />
                </div>
              </div>

              <!-- 保存按钮 -->
              <div class="form-actions-row">
                <el-button type="primary" :icon="Check" @click="saveSatelliteProperty" :loading="savingSatellite">
                  保存设置
                </el-button>
                <el-button type="success" :icon="Plus" @click="addToBatchList">
                  添加到列表
                </el-button>
                <el-button :icon="RefreshRight" @click="resetSatelliteForm">重置</el-button>
              </div>
            </div>
          </el-collapse-transition>
        </div>
      </el-card>

      <!-- 方式三：批量提交列表（添加到列表后统一提交） -->
      <el-card shadow="never" class="setting-card sat-batch-card" v-if="satBatchList.length">
        <template #header>
          <div class="card-header-inner">
            <el-icon :size="16" color="#f0b95c"><Document /></el-icon>
            <span class="card-title">数据列表（{{ satBatchList.length }} 条记录）</span>
            <div class="batch-actions">
              <el-button size="small" :icon="Delete" @click="clearBatchList">清空</el-button>
              <el-button type="success" size="small" :icon="Check" @click="submitBatchList" :loading="submittingBatch">
                提交全部参数
              </el-button>
            </div>
          </div>
        </template>
        <el-table :data="satBatchList" size="small" class="batch-table">
          <el-table-column prop="name" label="卫星名称" min-width="120" fixed="left" />
          <el-table-column prop="loadType" label="载荷类型" width="100" />
          <el-table-column prop="storage" label="存储容量 (GB)" width="110" />
          <el-table-column prop="battery" label="电池容量 (Wh)" width="110" />
          <el-table-column prop="resolution" label="分辨率 (m)" width="100" />
          <el-table-column prop="width" label="幅宽 (km)" width="90" />
          <el-table-column prop="downlink_rate" label="下行速率 (GB/s)" width="120" />
          <el-table-column prop="eclipse_powers" label="空闲功率 (W)" width="100" />
          <el-table-column prop="sunlight_powers" label="太阳能功率 (W)" width="120" />
          <el-table-column prop="maneuver_powers" label="机动功率 (W)" width="100" />
          <el-table-column prop="imaging_powers" label="成像功率 (W)" width="100" />
          <el-table-column prop="angle_velocity" label="角速度 (°/s)" width="110" />
          <el-table-column prop="stable_time" label="稳定时间 (s)" width="100" />
          <el-table-column prop="side_swing_angle_Max" label="最大侧摆角 (°)" width="120" />
          <el-table-column prop="pitch_angle_Max" label="最大俯仰角 (°)" width="120" />
          <el-table-column prop="cloud_threshold" label="云层阈值 (m)" width="110" />
          <el-table-column label="操作" width="80" fixed="right">
            <template #default="{ $index }">
              <el-button link type="danger" @click="removeBatchRow($index)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </div>
  </div>
</template>

<script>
import { ElMessage } from 'element-plus';
import { API_BASE } from '@/utils/config.js';
import {
  Setting, Clock, Switch, Check, Close, RefreshRight,
  Upload, UploadFilled, InfoFilled, Document, Delete, Edit, Refresh, Download, Plus
} from '@element-plus/icons-vue';

export default {
  name: 'SystemSettings',
  components: {
    Setting, Clock, Switch, Check, Close, RefreshRight,
    Upload, UploadFilled, InfoFilled, Document, Delete, Edit, Refresh, Download, Plus
  },
  data() {
    const defaultTime = [
      new Date(2000, 0, 1, 0, 0, 0),
      new Date(2000, 0, 1, 23, 59, 59),
    ];
    return {
      form: {
        dateRange: [],
        completed_gravity: 1.0,
        balance_gravity: 1.0,
        priority_gravity: 1.0,
        auto_mode: true,
      },
      baseUrl: '',
      defaultTime: defaultTime,
      selectedPlan: 'completion',
      submitStatus: {
        tle: false,
        sat: false,
        sys: false
      },
      checkingStatus: false,
      planOptions: [
        { value: 'completion', label: '任务完成度最高' },
        { value: 'utilization', label: '资源利用率最大' },
        { value: 'imaging', label: '成像质量最高' }
      ],
      satFile: null,
      satFileReady: false,
      satFields: [
        'name', 'loadType', 'storage', 'battery', 'resolution',
        'pitchAngle', 'sideAngle', 'settlingTime', 'angularVelocity',
        'width', 'threshold', 'downlink_rate', 'sunlight_powers',
        'maneuver_powers', 'imaging_powers', 'eclipse_powers'
      ],
      // 载荷类型选项（取值与后端 star_payload 一致）
      loadTypeOptions: [
        { value: 'optical', label: '可见光' },
        { value: 'infrared', label: '红外' },
        { value: 'SAR', label: 'SAR' }
      ],
      // 不同载荷类型的参数模板（参考 NetworkParameters.vue）
      payloadTemplates: {
        optical: { resolution: 1, width: 100 },
        infrared: { resolution: 1.5, width: 110 },
        SAR: { resolution: 2, width: 120 }
      },
      // 单个卫星设置
      satelliteList: [],
      selectedSatId: null,
      loadingSatList: false,
      savingSatellite: false,
      // 批量提交列表（添加到列表后统一提交）
      satBatchList: [],
      submittingBatch: false,
      satelliteForm: {
        storage: 500,
        battery: 5000,
        downlink_rate: 4,
        eclipse_powers: 8,
        sunlight_powers: 300,
        maneuver_powers: 500,
        imaging_powers: 700,
        loadType: 'optical',
        resolution: 1,
        width: 100,
        angle_velocity: 1.0,
        stable_time: 10,
        side_swing_angle_Max: 45,
        pitch_angle_Max: 45,
        cloud_threshold: 800
      },
      satelliteFormDefault: {
        storage: 500,
        battery: 5000,
        downlink_rate: 4,
        eclipse_powers: 8,
        sunlight_powers: 300,
        maneuver_powers: 500,
        imaging_powers: 700,
        loadType: 'optical',
        resolution: 1,
        width: 100,
        angle_velocity: 1.0,
        stable_time: 10,
        side_swing_angle_Max: 45,
        pitch_angle_Max: 45,
        cloud_threshold: 800
      }
    }
  },
  computed: {
    uploadTleUrl() {
      return `${this.baseUrl}/initTLE`;
    },
    uploadSatUrl() {
      return `${this.baseUrl}/initFiles`;
    },
    // el-upload 原生上传不走 axios 拦截器，需手动携带 Ac-Token 鉴权头
    uploadHeaders() {
      return { 'Ac-Token': localStorage.getItem('token') || '' };
    }
  },
  created() {
    // 上传地址与全局 API_BASE 保持一致（支持 VITE_API_BASE 环境变量覆盖），
    // 原先按 window.location.hostname + 固定 5001 端口拼接，部署到其它端口或 https 时上传会失败
    this.baseUrl = API_BASE;
    this._retryTimers = [];  // 上传后重试刷新卫星列表的定时器（非响应式）
    this._satListUpdatedNotified = false;
    this.restorePreferences();
    this.initializePage();
  },
  beforeUnmount() {
    // 组件卸载时清理未执行的重试定时器，避免卸载后仍触发请求与提示
    this.clearRetryTimers();
  },
  methods: {
    async initializePage() {
      await this.fetchSubmitStatus();
      if (this.submitStatus.sat) {
        this.loadSatelliteList();
      }
    },
    restorePreferences() {
      const savedMode = localStorage.getItem('system_auto_mode');
      const savedPlan = localStorage.getItem('system_selected_plan');
      if (savedMode !== null) {
        this.form.auto_mode = savedMode === 'true';
      }
      if (savedPlan) {
        this.selectedPlan = savedPlan;
      }
    },
    async fetchSubmitStatus() {
      this.checkingStatus = true;
      try {
        const [tleRes, satRes, sysRes] = await Promise.all([
          this.$request.get('/isSubmitTle'),
          this.$request.get('/isSubmitSat'),
          this.$request.get('/isSubmitSys')
        ]);
        this.submitStatus.tle = Boolean(tleRes.data?.is_submit_tle);
        this.submitStatus.sat = Boolean(satRes.data?.is_submit_sat);
        this.submitStatus.sys = Boolean(sysRes.data?.is_submit_sys);
      } catch (err) {
        console.error('获取系统状态失败:', err);
      } finally {
        this.checkingStatus = false;
      }
    },
    resetForm() {
      this.form.dateRange = [];
      this.form.completed_gravity = 1.0;
      this.form.balance_gravity = 1.0;
      this.form.priority_gravity = 1.0;
      ElMessage.success('已重置为默认值');
    },
    async submitSimulate() {
      if (!this.form.dateRange || this.form.dateRange.length !== 2) {
        ElMessage.warning('请选择开始与结束时间');
        return;
      }

      const toStr = (v) => {
        if (!v) return null;
        if (typeof v === 'string') return v;
        return this.formatDate(v);
      };

      const payload = {
        date1: toStr(this.form.dateRange[0]),
        date2: toStr(this.form.dateRange[1]),
        completed_gravity: this.form.completed_gravity,
        balance_gravity: this.form.balance_gravity,
        priority_gravity: this.form.priority_gravity,
      };

      try {
        await this.$request.post('/simulateParameters', payload);
        this.submitStatus.sys = true;
        ElMessage.success('参数提交成功');
      } catch (e) {
        ElMessage.error('提交失败');
      }
    },
    formatDate(date) {
      const d = new Date(date);
      const pad = (n) => (n < 10 ? '0' + n : n);
      return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
    },
    changeMode(val) {
      localStorage.setItem('system_auto_mode', String(val));
      ElMessage.success(`已切换为${val ? '自动' : '手动'}模式`);
    },
    onPlanChange(plan) {
      localStorage.setItem('system_selected_plan', plan);
      const currentPlan = this.planOptions.find(item => item.value === plan);
      if (currentPlan) {
        ElMessage.success(`已切换调度方案: ${currentPlan.label}`);
      }
    },
    beforeTleUpload(file) {
      ElMessage.info(`正在上传 ${file.name}...`);
      return true;
    },
    onTleSuccess(res, file) {
      this.submitStatus.tle = true;
      ElMessage.success('TLE 文件上传成功');
      this.fetchSubmitStatus();
    },
    onTleError(err) {
      ElMessage.error('TLE 上传失败');
    },
    // 导出轨道数据（TLE 文件）
    async exportTleFile() {
      try {
        const res = await this.$request.get('/exportTleFile', {
          responseType: 'blob'
        });
        const url = window.URL.createObjectURL(new Blob([res.data]));
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', 'TLE.txt');
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
        ElMessage.success('轨道数据导出成功');
      } catch (err) {
        ElMessage.error('轨道数据导出失败');
      }
    },
    handleSatFileChange(file, fileList) {
      const validExtensions = ['.json', '.txt', '.xls', '.xlsx', '.csv'];
      const fileName = file.name.toLowerCase();
      const isValid = validExtensions.some(ext => fileName.endsWith(ext));

      if (!isValid) {
        ElMessage.error('文件格式不支持，请上传 JSON/TXT/XLS/XLSX/CSV 格式');
        this.$refs.satUploadRef.clearFiles();
        this.satFile = null;
        this.satFileReady = false;
        return;
      }

      const maxSize = 10 * 1024 * 1024;
      if (file.size > maxSize) {
        ElMessage.error('文件大小不能超过 10MB');
        this.$refs.satUploadRef.clearFiles();
        this.satFile = null;
        this.satFileReady = false;
        return;
      }

      if (fileList.length > 1) {
        fileList.splice(0, 1);
      }

      this.satFile = file.raw;
      this.satFileReady = true;
      ElMessage.success(`已选择文件: ${file.name}`);
    },
    async submitSatUpload() {
      if (!this.satFile) {
        ElMessage.warning('请先选择文件');
        return;
      }

      const formData = new FormData();
      formData.append('file', this.satFile);

      let loadingMessage = null;
      try {
        loadingMessage = ElMessage({
          type: 'loading',
          message: '正在上传卫星参数文件...',
          duration: 0
        });
        await this.$request.post('/initFiles', formData, {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        });
        loadingMessage.close();
        this.submitStatus.sat = true;
        ElMessage.success('卫星参数文件上传成功，系统正在初始化...');
        this.$refs.satUploadRef.clearFiles();
        this.satFile = null;
        this.satFileReady = false;

        this.fetchSubmitStatus();
        this.refreshSatelliteListAfterUpload();
      } catch (err) {
        if (loadingMessage) loadingMessage.close();
        const errorMsg = err.response?.data?.error || err.message || '未知错误';
        ElMessage.error('卫星参数上传失败: ' + errorMsg);
      }
    },
    clearSatFile() {
      this.$refs.satUploadRef.clearFiles();
      this.satFile = null;
      this.satFileReady = false;
      ElMessage.info('已清空文件选择');
    },
    onSatRemove(file) {
      this.satFile = null;
      this.satFileReady = false;
    },

    // ========== 单个卫星设置方法 ==========
    // 加载卫星列表
    async loadSatelliteList(options = {}) {
      const { silent = false } = options;
      this.loadingSatList = true;
      try {
        const res = await this.$request.post('/satellites/getAllSatellites', { sate_name: '' });
        if (res?.status && res.status >= 400) {
          throw new Error(res.data?.error || res.data?.message || '卫星列表暂不可用');
        }
        if (Array.isArray(res.data)) {
          this.satelliteList = res.data;
          return true;
        }
        return false;
      } catch (err) {
        console.error('加载卫星列表失败:', err);
        const errorMessage = err.response?.data?.error || err.response?.data?.message || err.message || '未知错误';
        if (!silent && !String(errorMessage).includes('未初始化')) {
          ElMessage.error('加载卫星列表失败: ' + errorMessage);
        }
        return false;
      } finally {
        this.loadingSatList = false;
      }
    },
    refreshSatelliteListAfterUpload() {
      // 先清掉上一轮未执行的重试定时器，防止重复弹成功提示
      this.clearRetryTimers();
      this._satListUpdatedNotified = false;
      const retryDelays = [1500, 3000, 5000];
      retryDelays.forEach((delay, index) => {
        const timer = window.setTimeout(async () => {
          const loaded = await this.loadSatelliteList({ silent: true });
          if (loaded && index > 0 && !this._satListUpdatedNotified) {
            this._satListUpdatedNotified = true;
            ElMessage.success('卫星参数已生效，卫星列表已更新');
          }
        }, delay);
        this._retryTimers.push(timer);
      });
    },
    clearRetryTimers() {
      if (this._retryTimers && this._retryTimers.length) {
        this._retryTimers.forEach(t => window.clearTimeout(t));
      }
      this._retryTimers = [];
    },

    mapSatelliteDetailToForm(sat = {}) {
      return {
        storage: sat.storage ?? this.satelliteFormDefault.storage,
        battery: sat.battery ?? this.satelliteFormDefault.battery,
        downlink_rate: sat.downlink_rate ?? this.satelliteFormDefault.downlink_rate,
        eclipse_powers: sat.eclipse_powers ?? this.satelliteFormDefault.eclipse_powers,
        sunlight_powers: sat.sunlight_powers ?? this.satelliteFormDefault.sunlight_powers,
        maneuver_powers: sat.maneuver_powers ?? this.satelliteFormDefault.maneuver_powers,
        imaging_powers: sat.imaging_powers ?? this.satelliteFormDefault.imaging_powers,
        loadType: sat.loadType ?? sat.star_payload ?? this.satelliteFormDefault.loadType,
        resolution: sat.resolution ?? this.satelliteFormDefault.resolution,
        width: sat.width ?? sat.width_of_cloth ?? this.satelliteFormDefault.width,
        angle_velocity: sat.angleVelocity ?? sat.angle_velocity ?? this.satelliteFormDefault.angle_velocity,
        stable_time: sat.settlingTime ?? sat.stable_time ?? this.satelliteFormDefault.stable_time,
        side_swing_angle_Max: sat.side_swing_angle_Max ?? this.satelliteFormDefault.side_swing_angle_Max,  // 能力上限，不可用当前姿态角 sideAngle 回填
        pitch_angle_Max: sat.pitch_angle_Max ?? this.satelliteFormDefault.pitch_angle_Max,
        cloud_threshold: sat.cloud_threshold ?? sat.threshold ?? this.satelliteFormDefault.cloud_threshold
      };
    },

    // 选择卫星变化
    async onSatelliteChange(satId) {
      if (!satId) {
        this.resetSatelliteForm();
        return;
      }
      try {
        const res = await this.$request.get(`/satellites/getSatelliteById/${satId}`);
        this.satelliteForm = this.mapSatelliteDetailToForm(res.data);
      } catch (err) {
        console.error('获取卫星详情失败:', err);
        const sat = this.satelliteList.find(s => s.id === satId);
        this.satelliteForm = this.mapSatelliteDetailToForm(sat);
        ElMessage.warning('未能获取完整卫星详情，已使用列表中的基础数据');
      }
    },

    // 载荷类型切换：按对应模板适配分辨率与幅宽
    onLoadTypeChange(loadType) {
      const template = this.payloadTemplates[loadType];
      if (template) {
        this.satelliteForm.resolution = template.resolution;
        this.satelliteForm.width = template.width;
      }
    },

    // 保存卫星参数
    async saveSatelliteProperty() {
      if (!this.selectedSatId) {
        ElMessage.warning('请先选择卫星');
        return;
      }

      this.savingSatellite = true;
      try {
        const res = await this.$request.post(
          `/satellites/setSatelliteProperty/${this.selectedSatId}`,
          this.satelliteForm
        );
        ElMessage.success('卫星参数保存成功');
      } catch (err) {
        console.error('保存卫星参数失败:', err);
        ElMessage.error('保存失败: ' + (err.response?.data?.message || err.message || '未知错误'));
      } finally {
        this.savingSatellite = false;
      }
    },

    // 重置卫星表单
    resetSatelliteForm() {
      this.satelliteForm = { ...this.satelliteFormDefault };
      ElMessage.info('已重置为默认值');
    },

    // 添加到批量提交列表（同名卫星覆盖旧记录）
    addToBatchList() {
      if (!this.selectedSatId) {
        ElMessage.warning('请先选择卫星');
        return;
      }
      const sat = this.satelliteList.find(s => s.id === this.selectedSatId);
      if (!sat) {
        ElMessage.warning('未找到所选卫星');
        return;
      }
      const item = { name: sat.name, ...this.satelliteForm };
      const idx = this.satBatchList.findIndex(i => i.name === item.name);
      if (idx >= 0) {
        this.satBatchList.splice(idx, 1, item);
        ElMessage.success(`已更新列表中的 ${item.name}`);
      } else {
        this.satBatchList.push(item);
        ElMessage.success(`已添加 ${item.name} 到批量列表`);
      }
      // 添加后自动滚动到数据列表，让用户立即看到记录
      this.$nextTick(() => {
        const el = document.querySelector('.sat-batch-card');
        if (el) el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      });
    },

    // 删除批量列表中的一行
    removeBatchRow(index) {
      this.satBatchList.splice(index, 1);
    },

    // 清空批量列表
    clearBatchList() {
      this.satBatchList = [];
    },

    // 提交全部参数（字段名映射为后端 /networkParametersList 要求的格式）
    async submitBatchList() {
      if (!this.satBatchList.length) {
        ElMessage.warning('批量列表为空，请先添加卫星参数');
        return;
      }
      this.submittingBatch = true;
      try {
        const list = this.satBatchList.map(i => ({
          name: i.name,
          loadType: i.loadType,
          storage: i.storage,
          battery: i.battery,
          resolution: i.resolution,
          pitchAngle: i.pitch_angle_Max,
          sideAngle: i.side_swing_angle_Max,
          settlingTime: i.stable_time,
          angularVelocity: i.angle_velocity,
          width: i.width,
          threshold: i.cloud_threshold,
          downlink_rate: i.downlink_rate,
          sunlight_powers: i.sunlight_powers,
          maneuver_powers: i.maneuver_powers,
          imaging_powers: i.imaging_powers,
          eclipse_powers: i.eclipse_powers
        }));
        await this.$request.post('/networkParametersList', { list });
        ElMessage.success('全部参数提交成功');
        this.satBatchList = [];
      } catch (err) {
        console.error('批量提交失败:', err);
        ElMessage.error('提交失败: ' + (err.response?.data?.message || err.message || '未知错误'));
      } finally {
        this.submittingBatch = false;
      }
    }
  }
}
</script>

<style scoped>
/* ===== 基础布局 ===== */
.settings-container {
  padding: 20px;
  background-color: #f0f2f5;
  min-height: 100vh;
  box-sizing: border-box;
}

/* ===== 页面标题 ===== */
.page-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 24px;
  padding: 16px 20px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
}

.header-icon {
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #ecf5ff;
  border-radius: 8px;
}

.page-title {
  font-size: 20px;
  font-weight: 600;
  color: #303133;
  margin: 0 0 4px 0;
  line-height: 1;
}

.page-subtitle {
  font-size: 13px;
  color: #909399;
  margin: 0;
}

/* ===== 分区标题 ===== */
.section-wrapper {
  margin-bottom: 20px;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
}

.section-tag {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #409EFF;
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  border-radius: 6px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin: 0;
}

/* ===== 双栏布局 ===== */
.two-column-layout {
  display: grid;
  grid-template-columns: 1.5fr 1fr;
  gap: 20px;
  align-items: stretch; /* 左右两列等高，消除左列底部大空白 */
}

.left-panel,
.right-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* 左列卡片撑满列高，内容纵向分布，操作按钮沉底 */
.left-panel .setting-card {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.left-panel .setting-card :deep(.el-card__body) {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.left-panel .card-body {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.left-panel .form-actions-row {
  margin-top: auto; /* 按钮沉底，消除内容下方空白 */
}

/* ===== 卡片基础样式 ===== */
.setting-card {
  border-radius: 8px;
  border: none;
  background: #fff;
}

:deep(.el-card__header) {
  padding: 14px 16px;
  border-bottom: 1px solid #ebeef5;
  background: #fafafa;
}

.card-header-inner {
  display: flex;
  align-items: center;
  gap: 8px;
}

.card-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  flex: 1;
}

.card-body {
  padding: 20px 16px;
}

.card-body.compact {
  padding: 16px;
}

/* ===== 表单样式 ===== */
.form-row {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 20px;
}

.form-row:last-of-type {
  margin-bottom: 0;
}

.form-label {
  font-size: 13px;
  font-weight: 500;
  color: #606266;
}

.form-control {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.input-hint {
  font-size: 12px;
  color: #909399;
}

/* 权重输入 */
.weight-inputs {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.weight-box {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.weight-name {
  font-size: 12px;
  color: #606266;
}

:deep(.weight-box .el-input-number) {
  width: 100%;
}

/* 操作按钮 */
.form-actions-row {
  display: flex;
  gap: 12px;
  padding-top: 8px;
  border-top: 1px solid #ebeef5;
  margin-top: 8px;
}

/* ===== 系统模式区域 ===== */
.mode-card {
  flex: 0 0 auto;
}

.mode-selector {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 12px 0;
}

.mode-label {
  font-size: 13px;
  color: #303133;
  font-weight: 500;
  transition: color 0.3s;
}

.mode-label.inactive {
  color: #c0c4cc;
}

.mode-tip {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  font-size: 12px;
  color: #909399;
  margin: 0 0 8px 0;
}

.mode-desc {
  font-size: 12px;
  line-height: 1.6;
  color: #909399;
  margin: 0 0 12px 0;
  padding: 8px 10px;
  background: rgba(64, 158, 255, 0.06);
  border-radius: 6px;
}

.status-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
  margin-bottom: 12px;
}

.plan-box {
  padding-top: 12px;
  border-top: 1px solid #ebeef5;
  margin-top: 12px;
}

.plan-label {
  font-size: 12px;
  font-weight: 500;
  color: #606266;
  margin-bottom: 10px;
}

:deep(.plan-box .el-radio-group) {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

:deep(.plan-box .el-radio-button__inner) {
  border-radius: 4px;
  border-left: 1px solid #dcdfe6;
  padding: 6px 12px;
  font-size: 12px;
}

:deep(.plan-box .el-radio-button:first-child .el-radio-button__inner) {
  border-left: 1px solid #dcdfe6;
  border-radius: 4px;
}

:deep(.plan-box .el-radio-button:last-child .el-radio-button__inner) {
  border-radius: 4px;
}

:deep(.plan-box .el-radio-button__original-radio:checked + .el-radio-button__inner) {
  border-left-color: #409eff;
}

/* ===== TLE 上传卡片 ===== */
.upload-mini-card {
  flex: 0 0 auto;
}

.upload-text {
  font-size: 12px;
  color: #606266;
  margin: 0 0 12px 0;
}

.export-tle-btn {
  margin-top: 10px;
}

.simple-uploader {
  display: flex;
  justify-content: flex-start;
}

/* ===== 卫星参数上传区域 ===== */
.sat-card {
  background: #fff;
}

.sat-upload-container {
  padding: 4px;
}

.upload-zone-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 14px 0; /* 压缩批量导入区高度，避免把单星设置挤出首屏 */
  background: #fafafa;
  border-radius: 8px;
  border: 1px dashed #d9d9d9;
}

.sat-uploader {
  width: 100%;
}

:deep(.sat-uploader .el-upload) {
  width: 100%;
}

:deep(.sat-uploader .el-upload-dragger) {
  width: 100%;
  height: 110px; /* 原 140px，压缩拖拽区高度 */
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
}

.upload-zone-icon {
  color: #c0c4cc;
  margin-bottom: 12px;
}

.upload-zone-text {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.upload-zone-text .primary {
  font-size: 14px;
  color: #606266;
}

.upload-zone-text .secondary {
  font-size: 12px;
  color: #909399;
}

.upload-zone-text .secondary em {
  color: #409EFF;
  font-style: normal;
}

.format-tags {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}

/* 操作按钮 */
.upload-actions-bar {
  display: flex;
  justify-content: center;
  gap: 12px;
  padding: 16px 0;
  margin-top: 16px;
  border-top: 1px solid #ebeef5;
}

/* 导入说明 */
.info-section {
  padding: 16px;
  background: #f5f7fa;
  border-radius: 6px;
  margin-top: 16px;
}

.info-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 500;
  color: #606266;
  margin-bottom: 12px;
}

.field-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 8px;
}

.field-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #606266;
  padding: 4px 8px;
  background: #fff;
  border-radius: 4px;
}

.field-dot {
  width: 6px;
  height: 6px;
  background: #c0c4cc;
  border-radius: 50%;
}

/* ===== 响应式 ===== */
@media (max-width: 992px) {
  .two-column-layout {
    grid-template-columns: 1fr;
  }
  
  .weight-inputs {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .settings-container {
    padding: 12px;
  }
  
  .page-header {
    flex-direction: column;
    text-align: center;
  }
  
  .form-actions-row {
    flex-direction: column;
  }
  
  :deep(.form-actions-row .el-button) {
    width: 100%;
    margin: 0;
  }
  
  .upload-actions-bar {
    flex-direction: column;
  }
  
  .upload-actions-bar .el-button {
    width: 100%;
    margin: 0;
  }
  
  .field-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

/* ===== 单个卫星设置区域 ===== */
.sat-single-card {
  margin-top: 20px;
  background: #fff;
}

.sat-batch-card {
  margin-top: 20px;
  background: #fff;
}

.sat-batch-card .card-header-inner {
  display: flex;
  align-items: center;
  width: 100%;
}

.sat-batch-card .batch-actions {
  margin-left: auto;
  display: flex;
  gap: 8px;
}

.sat-batch-card .batch-table {
  width: 100%;
}

.sat-single-container {
  padding: 4px;
}

.sat-select-row {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 20px;
}

.sat-select-wrapper {
  display: flex;
  align-items: center;
  gap: 12px;
}

.satellite-form-wrapper {
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.param-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}

.param-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.param-item label {
  font-size: 12px;
  color: #606266;
  font-weight: 500;
}

.param-item .el-input-number {
  width: 100%;
}

@media (max-width: 768px) {
  .param-grid {
    grid-template-columns: 1fr;
  }
  
  .sat-select-wrapper {
    flex-direction: column;
    align-items: stretch;
  }
  
  .sat-select-wrapper .el-button {
    align-self: flex-end;
  }
}
</style>
