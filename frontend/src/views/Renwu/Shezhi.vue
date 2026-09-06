<template>
  <div class="task-settings">
    <el-row :gutter="16">
      <!-- 左侧：任务批量导入 -->
      <el-col :xs="24" :lg="12">
        <el-card shadow="never" class="upload-card">
          <template #header>
            <div class="card-header">
              <el-icon :size="18" color="#00dcff"><Upload /></el-icon>
              <span>批量导入任务</span>
            </div>
          </template>
          
          <el-upload
            ref="taskUploadRef"
            class="task-uploader"
            drag
            action="#"
            :auto-upload="false"
            :show-file-list="true"
            :on-change="handleFileChange"
            :on-remove="handleFileRemove"
            accept=".xlsx,.xls,.csv,.json"
          >
            <el-icon class="upload-icon" :size="48"><UploadFilled /></el-icon>
            <div class="upload-text">
              <span class="primary">拖拽任务文件到此处</span>
              <span class="secondary">或 <em>点击选择文件</em></span>
            </div>
            <template #tip>
              <div class="format-tags">
                <el-tag size="small" effect="plain">XLSX</el-tag>
                <el-tag size="small" effect="plain">XLS</el-tag>
                <el-tag size="small" effect="plain">CSV</el-tag>
                <el-tag size="small" effect="plain">JSON</el-tag>
              </div>
            </template>
          </el-upload>

          <div class="upload-actions" v-if="fileReady">
            <el-button type="primary" :icon="Check" @click="submitUpload">确认上传</el-button>
            <el-button :icon="Delete" @click="clearFile">清空</el-button>
          </div>

          <div class="quick-actions">
            <el-button link type="primary" @click="goToTaskManage">前往任务管理查看列表</el-button>
          </div>

          <el-alert
            title="导入说明"
            type="info"
            :closable="false"
            class="upload-info"
          >
            <template #default>
              <p>导入文件应包含以下字段：</p>
              <p class="field-list">
                taskName（任务名称）、taskType（任务类型）、priority（优先级）、
                isEmergency（是否紧急）、sensorType（载荷类型）、resolution（分辨率）、
                targetLocation（目标位置）、clusterName（指定星簇，可选）
              </p>
            </template>
          </el-alert>
        </el-card>
      </el-col>

      <!-- 右侧：任务用例 -->
      <el-col :xs="24" :lg="12">
        <el-card shadow="never" class="case-card">
          <template #header>
            <div class="card-header">
              <el-icon :size="18" color="#8ee06a"><Document /></el-icon>
              <span>快速生成用例</span>
            </div>
          </template>

          <div class="case-list">
            <div class="case-item" v-for="(item, index) in caseList" :key="index">
              <div class="case-info">
                <div class="case-name">{{ item.name }}</div>
                <div class="case-desc">{{ item.description }}</div>
              </div>
              <el-button type="success" size="small" :icon="Plus" @click="generateCase(item.type)">
                生成
              </el-button>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 用例生成结果 -->
    <el-card shadow="never" class="result-card" v-if="caseResult">
      <template #header>
        <div class="card-header">
          <el-icon :size="18" color="#f0b95c"><Check /></el-icon>
          <span>用例生成结果</span>
        </div>
      </template>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="用例类型">{{ caseResult.caseType }}</el-descriptions-item>
        <el-descriptions-item label="任务ID">{{ caseResult.id || '-' }}</el-descriptions-item>
        <el-descriptions-item label="任务数量">{{ caseResult.taskCount }}</el-descriptions-item>
        <el-descriptions-item label="生成时间">{{ caseResult.generateTime }}</el-descriptions-item>
        <el-descriptions-item label="任务状态">{{ caseResult.status || '-' }}</el-descriptions-item>
        <el-descriptions-item label="载荷类型">{{ caseResult.sensorType || '-' }}</el-descriptions-item>
        <el-descriptions-item label="任务类型">{{ caseResult.taskType || '-' }}</el-descriptions-item>
        <el-descriptions-item label="执行卫星">{{ caseResult.assignedSatelliteName || '未分配' }}</el-descriptions-item>
        <el-descriptions-item label="目标位置" :span="2">{{ caseResult.targetLocation || '-' }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag type="success">生成成功</el-tag>
        </el-descriptions-item>
      </el-descriptions>
      <div class="result-actions">
        <el-button type="primary" @click="goToTaskManage">前往任务管理</el-button>
      </div>
    </el-card>
  </div>
</template>

<script>
import { ElMessage } from 'element-plus';
import { Upload, UploadFilled, Document, Plus, Check, Delete } from '@element-plus/icons-vue';

export default {
  name: 'TaskSettings',
  components: {
    Upload, UploadFilled, Document, Plus, Check, Delete
  },
  data() {
    return {
      taskFile: null,
      fileReady: false,
      caseResult: null,
      caseList: [
        { name: '点目标案例', description: '生成一批点目标观测任务', type: 'point' },
        { name: '区域目标案例', description: '生成一批区域目标观测任务', type: 'area' },
        { name: '海洋搜救案例', description: '生成海洋移动目标搜救任务', type: 'ocean' }
      ]
    };
  },
  methods: {
    goToTaskManage() {
      this.$router.push('/satellite/renwu/shuxing');
    },
    // 文件变化
    handleFileChange(file, fileList) {
      const validTypes = ['.xlsx', '.xls', '.csv', '.json'];
      const fileName = file.name.toLowerCase();
      const isValid = validTypes.some(ext => fileName.endsWith(ext));
      
      if (!isValid) {
        ElMessage.error('文件格式不支持，请上传 XLSX/XLS/CSV/JSON 格式');
        this.$refs.taskUploadRef.clearFiles();
        this.taskFile = null;
        this.fileReady = false;
        return;
      }
      
      if (fileList.length > 1) {
        fileList.splice(0, 1);
      }
      
      this.taskFile = file.raw;
      this.fileReady = true;
      ElMessage.success(`已选择文件: ${file.name}`);
    },

    // 移除文件
    handleFileRemove() {
      this.taskFile = null;
      this.fileReady = false;
    },

    // 清空文件
    clearFile() {
      this.$refs.taskUploadRef.clearFiles();
      this.taskFile = null;
      this.fileReady = false;
      ElMessage.info('已清空文件选择');
    },

    // 提交上传
    async submitUpload() {
      if (!this.taskFile) {
        ElMessage.warning('请先选择文件');
        return;
      }

      const formData = new FormData();
      formData.append('file', this.taskFile);

      let loadingMessage = null;
      try {
        loadingMessage = ElMessage({
          type: 'loading',
          message: '正在上传任务文件...',
          duration: 0
        });
        
        await this.$request.post('/tasks/addTasks', formData, {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        });
        
        loadingMessage.close();
        ElMessage.success('任务批量导入成功');
        this.$refs.taskUploadRef.clearFiles();
        this.taskFile = null;
        this.fileReady = false;
      } catch (err) {
        if (loadingMessage) loadingMessage.close();
        const errorMessage = err.response?.data?.error || err.response?.data?.message || err.message || '未知错误';
        ElMessage.error('上传失败: ' + errorMessage);
      }
    },

    // 生成用例
    async generateCase(type) {
      const urlMap = {
        point: '/tasks/pointTargetCase',
        area: '/tasks/areaTargetCase',
        ocean: '/tasks/oceanTargetCase'
      };
      
      try {
        const res = await this.$request.get(urlMap[type]);
        if (res.data) {
          const caseNames = {
            point: '点目标案例',
            area: '区域目标案例',
            ocean: '海洋搜救案例'
          };
          this.caseResult = {
            caseType: caseNames[type],
            id: res.data.id || '-',
            taskCount: res.data.count || 1,
            generateTime: new Date().toLocaleString(),
            status: res.data.status || 'Success',
            sensorType: res.data.sensorType || '-',
            taskType: res.data.taskType || caseNames[type],
            assignedSatelliteName: res.data.assignedSatelliteName || '',
            targetLocation: res.data.targetLocation || res.data.locations || '-'
          };
          ElMessage.success(`${caseNames[type]}生成成功`);
        }
      } catch (err) {
        const errorMessage = err.response?.data?.msg || err.response?.data?.error || err.response?.data?.message || err.message || '未知错误';
        ElMessage.error('用例生成失败: ' + errorMessage);
      }
    }
  }
};
</script>

<style scoped>
.task-settings {
  padding: 0;
}

/* 卡片头部 */
.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

/* 上传卡片 */
.upload-card {
  margin-bottom: 16px;
}

.quick-actions {
  margin-top: 12px;
  text-align: right;
}

.task-uploader {
  width: 100%;
}

.result-actions {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

:deep(.task-uploader .el-upload) {
  width: 100%;
}

:deep(.task-uploader .el-upload-dragger) {
  width: 100%;
  height: 180px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: #fafafa;
  border: 2px dashed #dcdfe6;
  border-radius: 8px;
  transition: all 0.3s;
}

:deep(.task-uploader .el-upload-dragger:hover) {
  border-color: #409EFF;
  background: #f0f9ff;
}

.upload-icon {
  color: #c0c4cc;
  margin-bottom: 16px;
}

.upload-text {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.upload-text .primary {
  font-size: 15px;
  color: #606266;
}

.upload-text .secondary {
  font-size: 13px;
  color: #909399;
}

.upload-text .secondary em {
  color: #409EFF;
  font-style: normal;
}

.format-tags {
  display: flex;
  justify-content: center;
  gap: 8px;
  margin-top: 12px;
}

.upload-actions {
  display: flex;
  justify-content: center;
  gap: 12px;
  margin-top: 16px;
}

.upload-info {
  margin-top: 16px;
}

.field-list {
  margin: 8px 0 0 0;
  font-size: 12px;
  color: #606266;
  line-height: 1.6;
}

/* 用例卡片 */
.case-card {
  margin-bottom: 16px;
}

.case-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.case-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  background: #f5f7fa;
  border-radius: 8px;
  transition: all 0.3s;
}

.case-item:hover {
  background: #ecf5ff;
}

.case-info {
  flex: 1;
}

.case-name {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 4px;
}

.case-desc {
  font-size: 12px;
  color: #909399;
}

/* 结果卡片 */
.result-card {
  margin-top: 16px;
}

/* 响应式 */
@media (max-width: 768px) {
  .case-item {
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
  }
  
  .case-item .el-button {
    width: 100%;
  }
}
</style>
