<template>
  <div class="network-params-outer">
    <div class="network-params">
      <h2 class="params-title">网络参数配置</h2>
      
      <!-- 三个传感器类型卡片 -->
      <div class="sensors-container">
        <div 
          v-for="sensor in sensorTypes" 
          :key="sensor"
          class="sensor-card"
          :class="{ active: activeSensor === sensor }"
          @click="activeSensor = sensor"
        >
          <div class="sensor-icon">{{ getSensorIcon(sensor) }}</div>
          <div class="sensor-name">{{ getSensorLabel(sensor) }}</div>
        </div>
      </div>

      <!-- 参数编辑表单 -->
      <el-card class="params-form-card" shadow="hover">
        <template #header>
          <div class="card-header">
            <span class="header-dot">●</span>
            <span>{{ getSensorLabel(activeSensor) }}卫星参数</span>
          </div>
        </template>

        <el-form
          :model="params[activeSensor]"
          label-width="120px"
          class="params-form"
        >
          <!-- 第一列 -->
          <div class="form-columns">
            <div class="form-column">
              <el-form-item label="最大存储(MB)">
                <el-input-number
                  v-model="params[activeSensor].storage"
                  :min="0"
                  :step="100"
                />
              </el-form-item>

              <el-form-item label="最大电池(Wh)">
                <el-input-number
                  v-model="params[activeSensor].battery"
                  :min="0"
                  :step="500"
                />
              </el-form-item>

              <el-form-item label="分辨率(m)">
                <el-input-number
                  v-model="params[activeSensor].resolution"
                  :min="0.1"
                  :step="0.1"
                  :precision="2"
                />
              </el-form-item>

              <el-form-item label="俯仰角(°)">
                <el-input-number
                  v-model="params[activeSensor].pitchAngle"
                  :min="0"
                  :max="90"
                />
              </el-form-item>

              <el-form-item label="侧摇角(°)">
                <el-input-number
                  v-model="params[activeSensor].sideAngle"
                  :min="0"
                  :max="90"
                />
              </el-form-item>
            </div>

            <!-- 第二列 -->
            <div class="form-column">
              <el-form-item label="稳定时间(s)">
                <el-input-number
                  v-model="params[activeSensor].settlingTime"
                  :min="0"
                  :step="1"
                />
              </el-form-item>

              <el-form-item label="角速度(°/s)">
                <el-input-number
                  v-model="params[activeSensor].angularVelocity"
                  :min="0.1"
                  :step="0.1"
                  :precision="2"
                />
              </el-form-item>

              <el-form-item label="条带宽度(km)">
                <el-input-number
                  v-model="params[activeSensor].width"
                  :min="0"
                  :step="10"
                />
              </el-form-item>

              <el-form-item label="阈值">
                <el-input-number
                  v-model="params[activeSensor].threshold"
                  :min="0"
                  :step="100"
                />
              </el-form-item>

              <el-form-item label="下行速率(Mbps)">
                <el-input-number
                  v-model="params[activeSensor].downlink_rate"
                  :min="0"
                  :step="1"
                />
              </el-form-item>
            </div>

            <!-- 第三列 -->
            <div class="form-column">
              <el-form-item label="阳光功率(W)">
                <el-input-number
                  v-model="params[activeSensor].sunlight_powers"
                  :min="0"
                  :step="50"
                />
              </el-form-item>

              <el-form-item label="机动功率(W)">
                <el-input-number
                  v-model="params[activeSensor].maneuver_powers"
                  :min="0"
                  :step="50"
                />
              </el-form-item>

              <el-form-item label="成像功率(W)">
                <el-input-number
                  v-model="params[activeSensor].imaging_powers"
                  :min="0"
                  :step="50"
                />
              </el-form-item>

              <el-form-item label="日影功率(W)">
                <el-input-number
                  v-model="params[activeSensor].eclipse_powers"
                  :min="0"
                  :step="1"
                />
              </el-form-item>

              <div style="height: 40px;"></div>
            </div>
          </div>
        </el-form>
      </el-card>

      <!-- 操作按钮 -->
      <div class="action-buttons">
        <el-button @click="resetParams" class="btn-reset">重置</el-button>
        <el-button type="primary" @click="submitParams" class="btn-submit">提交配置</el-button>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, reactive, getCurrentInstance } from 'vue';
import { ElMessage } from 'element-plus';

export default {
  name: 'NetworkParameters',
  setup() {
    const { proxy } = getCurrentInstance();
    const activeSensor = ref('optical');
    const sensorTypes = ['optical', 'SAR', 'infrared'];

    // 初始化参数
    const initParams = () => ({
      optical: {
        storage: 500,
        battery: 5000,
        resolution: 1,
        pitchAngle: 45,
        sideAngle: 45,
        settlingTime: 10,
        angularVelocity: 1.0,
        width: 100,
        threshold: 800,
        downlink_rate: 4,
        sunlight_powers: 300,
        maneuver_powers: 500,
        imaging_powers: 700,
        eclipse_powers: 8
      },
      SAR: {
        storage: 600,
        battery: 5500,
        resolution: 2,
        pitchAngle: 50,
        sideAngle: 50,
        settlingTime: 12,
        angularVelocity: 0.8,
        width: 120,
        threshold: 850,
        downlink_rate: 5,
        sunlight_powers: 350,
        maneuver_powers: 550,
        imaging_powers: 800,
        eclipse_powers: 10
      },
      infrared: {
        storage: 550,
        battery: 5200,
        resolution: 1.5,
        pitchAngle: 48,
        sideAngle: 48,
        settlingTime: 11,
        angularVelocity: 0.9,
        width: 110,
        threshold: 820,
        downlink_rate: 4.5,
        sunlight_powers: 320,
        maneuver_powers: 520,
        imaging_powers: 750,
        eclipse_powers: 9
      }
    });

    const params = reactive(initParams());
    const paramsBackup = reactive(initParams());

    const getSensorLabel = (type) => {
      const labels = {
        optical: '光学',
        SAR: 'SAR',
        infrared: '红外'
      };
      return labels[type] || type;
    };

    const getSensorIcon = (type) => {
      const icons = {
        optical: '📸',
        SAR: '📡',
        infrared: '🌡️'
      };
      return icons[type] || '•';
    };

    const resetParams = () => {
      // 恢复所有参数
      Object.keys(params).forEach(key => {
        Object.assign(params[key], paramsBackup[key]);
      });
      ElMessage.success('参数已重置');
    };

    const submitParams = async () => {
      try {
        // 构建请求体：键为传感器类型，值为参数对象
        const payload = {
          optical: params.optical,
          SAR: params.SAR,
          infrared: params.infrared
        };

        await proxy.$request.post('/networkParameters', payload);

        ElMessage.success('网络参数配置成功');
      } catch (error) {
        const errorMessage = error.response?.data?.message || error.message || '未知错误';
        ElMessage.error('配置失败: ' + errorMessage);
        console.error('提交错误:', error);
      }
    };

    return {
      activeSensor,
      sensorTypes,
      params,
      getSensorLabel,
      getSensorIcon,
      resetParams,
      submitParams
    };
  }
};
</script>

<style scoped lang="scss">
.network-params-outer {
  padding: 20px;
  background: linear-gradient(135deg, #071428 0%, #0b2b44 100%);
  min-height: 100vh;
}

.network-params {
  max-width: 1200px;
  margin: 0 auto;
}

.params-title {
  color: #7cc3ff;
  font-size: 24px;
  margin-bottom: 30px;
  text-align: center;
  font-weight: 600;
}

.sensors-container {
  display: flex;
  justify-content: center;
  gap: 20px;
  margin-bottom: 30px;
  flex-wrap: wrap;
}

.sensor-card {
  width: 100px;
  padding: 15px;
  border: 2px solid #1e5a96;
  border-radius: 8px;
  background: rgba(30, 90, 150, 0.1);
  cursor: pointer;
  transition: all 0.3s ease;
  text-align: center;
  color: #7cc3ff;

  &:hover {
    border-color: #7cc3ff;
    background: rgba(124, 195, 255, 0.1);
  }

  &.active {
    border-color: #7cc3ff;
    background: rgba(124, 195, 255, 0.2);
    box-shadow: 0 0 15px rgba(124, 195, 255, 0.3);
  }

  .sensor-icon {
    font-size: 32px;
    margin-bottom: 8px;
  }

  .sensor-name {
    font-size: 14px;
    font-weight: 600;
  }
}

.params-form-card {
  background: rgba(11, 43, 68, 0.8) !important;
  border: 1px solid #1e5a96 !important;
  margin-bottom: 30px;

  .card-header {
    color: #7cc3ff;
    font-size: 16px;
    font-weight: 600;
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .header-dot {
    color: #7cc3ff;
    font-size: 14px;
  }
}

.params-form {
  :deep(.el-form-item) {
    margin-bottom: 20px;

    .el-form-item__label {
      color: #7cc3ff !important;
      font-size: 13px;
    }

    .el-input__wrapper {
      background-color: rgba(30, 90, 150, 0.3) !important;
      border: 1px solid #1e5a96 !important;
    }

    .el-input__inner {
      color: #fff;
    }

    input {
      background-color: transparent !important;
      color: #fff !important;

      &::placeholder {
        color: #7cc3ff;
        opacity: 0.5;
      }
    }
  }

  :deep(.el-input-number) {
    width: 100%;

    .el-input-number__decrease,
    .el-input-number__increase {
      background-color: rgba(124, 195, 255, 0.1) !important;
      color: #7cc3ff !important;
      border-color: #1e5a96 !important;

      &:hover {
        background-color: rgba(124, 195, 255, 0.2) !important;
      }
    }

    .el-input__wrapper {
      background-color: rgba(30, 90, 150, 0.3) !important;
      border-color: #1e5a96 !important;
    }

    input {
      color: #fff !important;
      background-color: transparent !important;
    }
  }
}

.form-columns {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
}

.form-column {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.action-buttons {
  display: flex;
  justify-content: center;
  gap: 20px;
  margin-top: 30px;
}

.btn-reset {
  width: 120px;
  height: 40px;
  background-color: rgba(30, 90, 150, 0.3) !important;
  border: 1px solid #1e5a96 !important;
  color: #7cc3ff !important;
  font-weight: 600;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.3s ease;

  &:hover {
    background-color: rgba(124, 195, 255, 0.1) !important;
    border-color: #7cc3ff !important;
  }
}

.btn-submit {
  width: 120px;
  height: 40px;
  background: linear-gradient(135deg, #1e5a96 0%, #7cc3ff 100%) !important;
  border: none !important;
  color: #fff !important;
  font-weight: 600;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.3s ease;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 5px 15px rgba(124, 195, 255, 0.3) !important;
  }
}

@media (max-width: 768px) {
  .form-columns {
    grid-template-columns: 1fr;
  }

  .params-title {
    font-size: 18px;
  }

  .sensors-container {
    gap: 10px;
  }

  .sensor-card {
    width: 80px;
    padding: 10px;
  }
}
</style>
