<template>
  <div class="alert-center">
    <el-card shadow="never" class="header-card">
      <div class="header-content">
        <div class="header-title">
          <el-icon :size="24" color="#ff7a7a"><BellFilled /></el-icon>
          <div>
            <h2 class="title">告警中心</h2>
            <p class="subtitle">系统运行告警与事件的集中管理</p>
          </div>
        </div>
        <div class="header-actions">
          <el-button :icon="Refresh" @click="load" :loading="loading">刷新</el-button>
          <el-button type="primary" plain :icon="Check" @click="ackAll" :disabled="!hasUnacked">全部确认</el-button>
        </div>
      </div>
    </el-card>

    <!-- 统计概览 -->
    <el-row :gutter="16" class="stats-row">
      <el-col :xs="8" :sm="8">
        <el-card shadow="never" class="stat-card">
          <div class="stat-value" style="color:#ff7a7a">{{ countBy('alarm') }}</div>
          <div class="stat-label">严重告警</div>
        </el-card>
      </el-col>
      <el-col :xs="8" :sm="8">
        <el-card shadow="never" class="stat-card">
          <div class="stat-value" style="color:#ffd657">{{ countBy('warn') }}</div>
          <div class="stat-label">警告</div>
        </el-card>
      </el-col>
      <el-col :xs="8" :sm="8">
        <el-card shadow="never" class="stat-card">
          <div class="stat-value" style="color:#7fd4ff">{{ countBy('info') }}</div>
          <div class="stat-label">提示</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 筛选 + 列表 -->
    <el-card shadow="never" class="table-card">
      <div class="filter-bar">
        <el-radio-group v-model="filterLevel" size="small">
          <el-radio-button value="">全部级别</el-radio-button>
          <el-radio-button value="alarm">严重</el-radio-button>
          <el-radio-button value="warn">警告</el-radio-button>
          <el-radio-button value="info">提示</el-radio-button>
        </el-radio-group>
        <el-radio-group v-model="filterCategory" size="small">
          <el-radio-button value="">全部类型</el-radio-button>
          <el-radio-button value="任务">任务</el-radio-button>
          <el-radio-button value="卫星">卫星</el-radio-button>
          <el-radio-button value="系统">系统</el-radio-button>
        </el-radio-group>
        <el-checkbox v-model="onlyUnacked" size="small">仅看未确认</el-checkbox>
      </div>

      <div v-if="loading" class="table-skeleton"><el-skeleton :rows="8" animated /></div>
      <el-table v-else :data="filtered" stripe max-height="560" :default-sort="{ prop: 'time', order: 'descending' }">
        <el-table-column label="级别" width="90">
          <template #default="scope">
            <el-tag size="small" :type="levelTagType(scope.row.level)" effect="dark">
              {{ levelText(scope.row.level) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="category" label="类型" width="90" />
        <el-table-column prop="message" label="告警内容" min-width="320" show-overflow-tooltip />
        <el-table-column prop="time" label="时间" width="170" sortable />
        <el-table-column label="状态" width="90">
          <template #default="scope">
            <span :class="scope.row.acknowledged ? 'ack-yes' : 'ack-no'">
              {{ scope.row.acknowledged ? '已确认' : '未确认' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="scope">
            <el-button v-if="!scope.row.acknowledged" link type="primary" @click="ackOne(scope.row)">确认</el-button>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无告警，系统运行正常" />
        </template>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { BellFilled, Refresh, Check } from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';
import { authFetch } from '@/utils/authFetch.js';
import { useAlertStoreMutable, fetchAlerts, ackAlert, startAlertPoll, stopAlertPoll } from '@/utils/alertStore.js';

const store = useAlertStoreMutable();
const loading = ref(false);
const filterLevel = ref('');
const filterCategory = ref('');
const onlyUnacked = ref(false);

const filtered = computed(() => {
  return store.alerts.filter(a => {
    if (filterLevel.value && a.level !== filterLevel.value) return false;
    if (filterCategory.value && a.category !== filterCategory.value) return false;
    if (onlyUnacked.value && a.acknowledged) return false;
    return true;
  });
});
const hasUnacked = computed(() => store.alerts.some(a => !a.acknowledged));

function countBy(level) { return store.alerts.filter(a => a.level === level).length; }
function levelTagType(l) { return l === 'alarm' ? 'danger' : l === 'warn' ? 'warning' : 'info'; }
function levelText(l) { return l === 'alarm' ? '严重' : l === 'warn' ? '警告' : '提示'; }

async function load() {
  loading.value = true;
  await fetchAlerts(authFetch);
  loading.value = false;
}

async function ackOne(row) {
  if (row._local) { row.acknowledged = true; return; }
  // 后端下标 = 在 store.alerts（非 _local）中的顺序需要映射回后端顺序（后端按时间正序存）
  const remoteList = store.alerts.filter(a => !a._local);
  const idxInRemote = remoteList.indexOf(row); // 倒序数组中的位置
  if (idxInRemote < 0) return;
  const backendIdx = remoteList.length - 1 - idxInRemote; // 还原为正序下标
  await ackAlert(authFetch, backendIdx);
  row.acknowledged = true;
}

async function ackAll() {
  await ackAlert(authFetch, -1);
  ElMessage.success('全部告警已确认');
}

onMounted(() => { load(); startAlertPoll(authFetch); });
onUnmounted(() => { stopAlertPoll(); });
</script>

<style scoped>
.alert-center { padding: 0; }
.header-card { margin-bottom: 20px; }
.header-content { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 16px; }
.header-title { display: flex; align-items: center; gap: 16px; }
.title { margin: 0; font-size: 20px; font-weight: 600; color: #e8f6ff; }
.subtitle { margin: 4px 0 0 0; font-size: 13px; color: #9fc6e8; }
.header-actions { display: flex; gap: 12px; }
.stats-row { margin-bottom: 20px; }
.stat-card { text-align: center; padding: 16px 0; }
.stat-value { font-size: 26px; font-weight: 700; font-family: 'Courier New', monospace; }
.stat-label { font-size: 13px; color: #9fc6e8; margin-top: 4px; }
.filter-bar { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; margin-bottom: 14px; }
.table-skeleton { padding: 12px 0; }
.ack-yes { color: #68809a; font-size: 12px; }
.ack-no { color: #ffd657; font-size: 12px; font-weight: 600; }
@media (max-width: 768px) {
  .header-content { flex-direction: column; align-items: flex-start; }
}
</style>
