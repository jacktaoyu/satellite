<template>
  <div class="satellite-detail">
    <!-- 头部信息 -->
    <el-card shadow="never" class="header-card">
      <div class="header-content">
        <div class="header-left">
          <div class="satellite-icon">
            <el-icon :size="40" color="#409EFF"><OfficeBuilding /></el-icon>
          </div>
          <div class="header-info">
            <h2 class="satellite-name">{{ satelliteInfo.name || '未知卫星' }}</h2>
            <div class="header-tags">
              <el-tag size="small" :type="getLoadTypeType(satelliteInfo.loadType)">
                {{ satelliteInfo.loadType || '未知载荷' }}
              </el-tag>
              <el-tag size="small" :type="satelliteInfo.is_available ? 'success' : 'danger'">
                {{ satelliteInfo.is_available ? '可用' : '不可用' }}
              </el-tag>
              <el-tag size="small" type="info">{{ satelliteInfo.orbit || '未知轨道' }}</el-tag>
            </div>
          </div>
        </div>
        <div class="header-actions">
          <el-button :icon="ArrowLeft" @click="$router.back()">返回</el-button>
          <el-button type="primary" :icon="Edit" @click="editSatellite">编辑</el-button>
          <el-button type="success" :icon="Download" @click="exportSatellite">导出</el-button>
        </div>
      </div>
    </el-card>

    <!-- 基本信息 -->
    <el-row :gutter="16">
      <el-col :xs="24" :lg="12">
        <el-card shadow="never" class="info-card">
          <template #header>
            <div class="card-header">
              <el-icon :size="18" color="#67C23A"><InfoFilled /></el-icon>
              <span>基础信息</span>
            </div>
          </template>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="卫星ID">{{ satelliteInfo.id || '-' }}</el-descriptions-item>
            <el-descriptions-item label="卫星名称">{{ satelliteInfo.name || '-' }}</el-descriptions-item>
            <el-descriptions-item label="轨道">{{ satelliteInfo.orbit || '-' }}</el-descriptions-item>
            <el-descriptions-item label="载荷类型">{{ satelliteInfo.loadType || '-' }}</el-descriptions-item>
            <el-descriptions-item label="分辨率">{{ satelliteInfo.resolution ? satelliteInfo.resolution + ' m' : '-' }}</el-descriptions-item>
            <el-descriptions-item label="幅宽">{{ satelliteInfo.width ? satelliteInfo.width + ' km' : '-' }}</el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-switch
                v-model="satelliteInfo.is_available"
                inline-prompt
                active-text="可用"
                inactive-text="禁用"
                @change="handleStatusChange"
              />
            </el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="12">
        <el-card shadow="never" class="info-card">
          <template #header>
            <div class="card-header">
              <el-icon :size="18" color="#E6A23C"><Location /></el-icon>
              <span>实时状态</span>
            </div>
          </template>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="卫星位置">{{ satelliteInfo.position || '-' }}</el-descriptions-item>
            <el-descriptions-item label="速度">{{ satelliteInfo.speed || '-' }}</el-descriptions-item>
            <el-descriptions-item label="星下点">{{ satelliteInfo.sub_point || '-' }}</el-descriptions-item>
            <el-descriptions-item label="飞行圈数">{{ satelliteInfo.turns || '-' }}</el-descriptions-item>
            <el-descriptions-item label="连接的高轨卫星">{{ satelliteInfo.connecting_geo || '无' }}</el-descriptions-item>
            <el-descriptions-item label="执行中的任务">{{ satelliteInfo.running_task || '无' }}</el-descriptions-item>
            <el-descriptions-item label="任务总数">{{ satelliteInfo.task_num || '0' }}</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
    </el-row>

    <!-- 资源与功率 -->
    <el-row :gutter="16" style="margin-top: 16px;">
      <el-col :xs="24" :lg="12">
        <el-card shadow="never" class="info-card">
          <template #header>
            <div class="card-header">
              <el-icon :size="18" color="#409EFF"><Box /></el-icon>
              <span>资源信息</span>
            </div>
          </template>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="存储容量">{{ satelliteInfo.storage ? satelliteInfo.storage + ' GB' : '-' }}</el-descriptions-item>
            <el-descriptions-item label="电池容量">{{ satelliteInfo.battery ? satelliteInfo.battery + ' Wh' : '-' }}</el-descriptions-item>
            <el-descriptions-item label="下行速率">{{ satelliteInfo.downlink_rate ? satelliteInfo.downlink_rate + ' GB/s' : '-' }}</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="12">
        <el-card shadow="never" class="info-card">
          <template #header>
            <div class="card-header">
              <el-icon :size="18" color="#F56C6C"><Lightning /></el-icon>
              <span>功率参数</span>
            </div>
          </template>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="空闲功率">{{ satelliteInfo.eclipse_powers ? satelliteInfo.eclipse_powers + ' W' : '-' }}</el-descriptions-item>
            <el-descriptions-item label="太阳能功率">{{ satelliteInfo.sunlight_powers ? satelliteInfo.sunlight_powers + ' W' : '-' }}</el-descriptions-item>
            <el-descriptions-item label="机动功率">{{ satelliteInfo.maneuver_powers ? satelliteInfo.maneuver_powers + ' W' : '-' }}</el-descriptions-item>
            <el-descriptions-item label="成像功率">{{ satelliteInfo.imaging_powers ? satelliteInfo.imaging_powers + ' W' : '-' }}</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
    </el-row>

    <!-- 载荷参数 -->
    <el-card shadow="never" class="info-card" style="margin-top: 16px;">
      <template #header>
        <div class="card-header">
          <el-icon :size="18" color="#909399"><Tools /></el-icon>
          <span>载荷参数</span>
        </div>
      </template>
      <el-row :gutter="16">
        <el-col :xs="24" :sm="12" :md="8" v-for="(item, index) in payloadParams" :key="index">
          <div class="param-item">
            <div class="param-label">{{ item.label }}</div>
            <div class="param-value">{{ item.value || '-' }}</div>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <!-- 编辑弹窗 -->
    <el-dialog v-model="editDialogVisible" title="编辑卫星参数" width="600px" destroy-on-close>
      <el-form :model="editForm" label-width="150px">
        <el-divider content-position="left">基础参数</el-divider>
        <el-form-item label="存储容量 (GB)">
          <el-input-number v-model="editForm.storage" :min="1" :max="10000" controls-position="right" style="width: 100%" />
        </el-form-item>
        <el-form-item label="电池容量 (Wh)">
          <el-input-number v-model="editForm.battery" :min="1" :max="20000" controls-position="right" style="width: 100%" />
        </el-form-item>
        <el-divider content-position="left">功率参数</el-divider>
        <el-form-item label="空闲功率 (W)">
          <el-input-number v-model="editForm.eclipse_powers" :min="0" :max="1000" controls-position="right" style="width: 100%" />
        </el-form-item>
        <el-form-item label="太阳能功率 (W)">
          <el-input-number v-model="editForm.sunlight_powers" :min="0" :max="1000" controls-position="right" style="width: 100%" />
        </el-form-item>
        <el-form-item label="机动功率 (W)">
          <el-input-number v-model="editForm.maneuver_powers" :min="0" :max="5000" controls-position="right" style="width: 100%" />
        </el-form-item>
        <el-form-item label="成像功率 (W)">
          <el-input-number v-model="editForm.imaging_powers" :min="0" :max="5000" controls-position="right" style="width: 100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveEdit" :loading="saving">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ElMessage } from 'element-plus';
import { 
  ArrowLeft, Edit, Download, OfficeBuilding, InfoFilled, Location, 
  Box, Lightning, Tools 
} from '@element-plus/icons-vue';

export default {
  name: "WeixingInfo",
  components: {
    ArrowLeft, Edit, Download, OfficeBuilding, InfoFilled, Location,
    Box, Lightning, Tools
  },
  data() {
    return {
      satelliteInfo: {},
      editDialogVisible: false,
      saving: false,
      editForm: {
        storage: 0,
        battery: 0,
        eclipse_powers: 0,
        sunlight_powers: 0,
        maneuver_powers: 0,
        imaging_powers: 0
      }
    };
  },
  computed: {
    payloadParams() {
      return [
        { label: '侧摆角', value: this.satelliteInfo.sideAngle ? this.satelliteInfo.sideAngle + '°' : null },
        { label: '俯仰角', value: this.satelliteInfo.pitchAngle ? this.satelliteInfo.pitchAngle + '°' : null },
        { label: '载荷转动角速度', value: this.satelliteInfo.angleVelocity ? this.satelliteInfo.angleVelocity + '°/s' : null },
        { label: '稳定时间', value: this.satelliteInfo.settlingTime ? this.satelliteInfo.settlingTime + 's' : null },
        { label: '云层遮挡阈值', value: this.satelliteInfo.threshold ? this.satelliteInfo.threshold + 'm' : null },
        { label: '最大侧摆角度', value: this.satelliteInfo.side_swing_angle_Max ? this.satelliteInfo.side_swing_angle_Max + '°' : null },
        { label: '最大俯仰角度', value: this.satelliteInfo.pitch_angle_Max ? this.satelliteInfo.pitch_angle_Max + '°' : null },
        { label: '角度转动速度', value: this.satelliteInfo.angle_velocity ? this.satelliteInfo.angle_velocity + '°/s' : null }
      ];
    }
  },
  created() {
    this.loadSatelliteInfo();
  },
  methods: {
    loadSatelliteInfo() {
      const name = this.$route.params.name;
      this.$request.get(`/satellites/getSatelliteByName/${name}`).then(res => {
        if (res.data) {
          this.satelliteInfo = res.data;
        }
      }).catch(() => {
        ElMessage.error('获取卫星信息失败');
      });
    },
    
    getLoadTypeType(loadType) {
      const map = {
        'SAR': 'success',
        'optical': 'primary',
        'infrared': 'warning'
      };
      return map[loadType] || 'info';
    },

    async handleStatusChange(val) {
      try {
        const url = val 
          ? `/satellites/setSatelliteAvailable/${this.satelliteInfo.id}`
          : `/satellites/setSatelliteUnavailable/${this.satelliteInfo.id}`;
        await this.$request.post(url);
        ElMessage.success(`已${val ? '启用' : '禁用'}`);
      } catch (err) {
        this.satelliteInfo.is_available = !val;
        ElMessage.error('操作失败');
      }
    },

    editSatellite() {
      this.editForm = {
        storage: this.satelliteInfo.storage || 500,
        battery: this.satelliteInfo.battery || 5000,
        eclipse_powers: this.satelliteInfo.eclipse_powers || 8,
        sunlight_powers: this.satelliteInfo.sunlight_powers || 300,
        maneuver_powers: this.satelliteInfo.maneuver_powers || 500,
        imaging_powers: this.satelliteInfo.imaging_powers || 700
      };
      this.editDialogVisible = true;
    },

    async saveEdit() {
      this.saving = true;
      try {
        await this.$request.post(
          `/satellites/setSatelliteProperty/${this.satelliteInfo.id}`,
          this.editForm
        );
        ElMessage.success('保存成功');
        this.editDialogVisible = false;
        this.loadSatelliteInfo();
      } catch (err) {
        ElMessage.error('保存失败');
      } finally {
        this.saving = false;
      }
    },

    async exportSatellite() {
      try {
        const res = await this.$request.get(
          `/satellites/exportSatelliteInfo/${this.satelliteInfo.id}`,
          { responseType: 'blob' }
        );
        const url = window.URL.createObjectURL(new Blob([res.data]));
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', `${this.satelliteInfo.name}_info.xlsx`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
        ElMessage.success('导出成功');
      } catch (err) {
        ElMessage.error('导出失败');
      }
    }
  }
};
</script>

<style scoped>
.satellite-detail {
  padding: 0;
}

/* 头部卡片 */
.header-card {
  margin-bottom: 16px;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.satellite-icon {
  width: 60px;
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #ecf5ff 0%, #d9ecff 100%);
  border-radius: 12px;
}

.satellite-name {
  margin: 0 0 8px 0;
  font-size: 22px;
  font-weight: 600;
  color: #303133;
}

.header-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.header-actions {
  display: flex;
  gap: 10px;
}

/* 信息卡片 */
.info-card {
  height: 100%;
}

:deep(.info-card .el-card__header) {
  padding: 12px 16px;
  background: #fafafa;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

/* 参数项 */
.param-item {
  padding: 16px;
  background: #f5f7fa;
  border-radius: 8px;
  margin-bottom: 12px;
  text-align: center;
}

.param-label {
  font-size: 12px;
  color: #909399;
  margin-bottom: 6px;
}

.param-value {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

/* 响应式 */
@media (max-width: 768px) {
  .header-content {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .header-actions {
    width: 100%;
    flex-direction: column;
  }
  
  .header-actions .el-button {
    width: 100%;
    margin: 0;
  }
}
</style>
