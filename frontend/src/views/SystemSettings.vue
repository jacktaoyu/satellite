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
                <el-icon :size="16" color="#67C23A"><Clock /></el-icon>
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
                <el-icon :size="16" color="#E6A23C"><Switch /></el-icon>
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
                <el-icon :size="16" color="#409EFF"><Upload /></el-icon>
                <span class="card-title">TLE 轨道数据</span>
                <el-tag size="small" type="danger" effect="light">必需</el-tag>
              </div>
            </template>

            <div class="card-body compact">
              <p class="upload-text">上传 TLE 格式的卫星轨道数据文件</p>
              <el-upload
                class="simple-uploader"
                :action="uploadTleUrl"
                :show-file-list="true"
                :limit="1"
                :before-upload="beforeTleUpload"
                :on-success="onTleSuccess"
                :on-error="onTleError"
                accept=".txt,.tle"
              >
                <el-button type="primary" :icon="Upload" size="small">选择文件</el-button>
              </el-upload>
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
            <el-icon :size="16" color="#909399"><Document /></el-icon>
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
    </div>
  </div>
</template>

<script>
import { ElMessage } from 'element-plus';
import { 
  Setting, Clock, Switch, Check, Close, RefreshRight,
  Upload, UploadFilled, InfoFilled, Document, Delete
} from '@element-plus/icons-vue';

export default {
  name: 'SystemSettings',
  components: {
    Setting, Clock, Switch, Check, Close, RefreshRight,
    Upload, UploadFilled, InfoFilled, Document, Delete
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
      ]
    }
  },
  computed: {
    uploadTleUrl() {
      return `${this.baseUrl}/initTLE`;
    },
    uploadSatUrl() {
      return `${this.baseUrl}/initFiles`;
    }
  },
  created() {
    const host = window.location.hostname || '127.0.0.1'
    this.baseUrl = `http://${host}:5001`;
  },
  methods: {
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
        const res = await this.$request.post('/simulateParameters', payload);
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
      const mode = val ? 'auto' : 'manual';
      this.$request.post('/changeModel', { mode: mode }).then(() => {
        ElMessage.success(`已切换为${val ? '自动' : '手动'}模式`);
      }).catch((err) => {
        console.error('模式切换错误:', err);
        ElMessage.error('模式切换失败: ' + (err.response?.data?.message || err.message || '未知错误'));
      });
    },
    beforeTleUpload(file) {
      ElMessage.info(`正在上传 ${file.name}...`);
      return true;
    },
    onTleSuccess(res, file) {
      ElMessage.success('TLE 文件上传成功');
    },
    onTleError(err) {
      ElMessage.error('TLE 上传失败');
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
        const res = await this.$request.post('/initFiles', formData, {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        });
        loadingMessage.close();
        ElMessage.success('卫星参数文件上传成功，系统正在初始化...');
        this.$refs.satUploadRef.clearFiles();
        this.satFile = null;
        this.satFileReady = false;
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
  align-items: start;
}

.left-panel,
.right-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
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
  margin: 0 0 12px 0;
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
  padding: 24px 0;
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
  height: 140px;
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
</style>
