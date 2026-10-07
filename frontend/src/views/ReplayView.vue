<template>
  <div class="replay-page">
    <!-- 顶部控制条 -->
    <el-card shadow="never" class="control-card">
      <div class="control-bar">
        <div class="cb-title">
          <span class="cb-name">态势回放</span>
          <span class="cb-sub">STATE REPLAY</span>
        </div>
        <div class="cb-info" v-if="snapshots.length > 0">
          <span>共 {{ snapshots.length }} 帧</span>
          <span class="cb-range">{{ snapshots[0].time }} ~ {{ snapshots[snapshots.length - 1].time }}</span>
        </div>
        <div class="cb-actions">
          <el-button size="small" :icon="isPlaying ? VideoPause : VideoPlay" type="primary"
                     :disabled="snapshots.length === 0" @click="togglePlay">
            {{ isPlaying ? '暂停' : '播放' }}
          </el-button>
          <el-button size="small" :icon="Refresh" @click="loadSnapshots">刷新</el-button>
        </div>
      </div>
      <!-- 帧滑块 -->
      <div class="slider-row" v-if="snapshots.length > 0">
        <el-slider v-model="frameIndex" :min="0" :max="snapshots.length - 1"
                   :show-tooltip="false" @input="onSlider" />
        <div class="frame-time">{{ currentSnapshot ? currentSnapshot.time : '--' }}</div>
      </div>
      <el-empty v-else-if="loaded" description="暂无回放快照：后端运行后会每 5 秒记录一帧（最多保留 720 帧）" :image-size="80" />
    </el-card>

    <!-- 当前帧卫星状态表 -->
    <el-card shadow="never" class="table-card" v-if="snapshots.length > 0">
      <template #header>
        <div class="card-header">
          <span>卫星状态（{{ filteredRows.length }}/{{ tableRows.length }}）</span>
          <el-input v-model.trim="keyword" size="small" placeholder="搜索卫星名称…" clearable class="sat-kw" />
        </div>
      </template>
      <el-table :data="pagedRows" stripe size="small" max-height="520">
        <el-table-column type="index" label="#" width="55" :index="(i) => (page - 1) * pageSize + i + 1" />
        <el-table-column prop="name" label="卫星" min-width="120" sortable />
        <el-table-column label="电量 (Wh)" min-width="160" sortable :sort-by="(r) => r.battery">
          <template #default="scope">
            <div class="batt-cell">
              <el-progress :percentage="batteryPct(scope.row.battery)" :stroke-width="8"
                           :color="batteryColor(scope.row.battery)" :show-text="false" class="batt-bar" />
              <span class="batt-num">{{ scope.row.battery }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="storage" label="存储 (GB)" width="110" sortable />
        <el-table-column prop="lat" label="纬度 (°)" width="110">
          <template #default="scope">{{ fmtNum(scope.row.lat) }}</template>
        </el-table-column>
        <el-table-column prop="lng" label="经度 (°)" width="110">
          <template #default="scope">{{ fmtNum(scope.row.lng) }}</template>
        </el-table-column>
        <el-table-column prop="height" label="高度 (km)" width="110" sortable />
      </el-table>
      <div class="pager-row">
        <el-pagination background layout="total, prev, pager, next" :total="filteredRows.length"
                       :current-page="page" :page-size="pageSize" @current-change="(p) => page = p" />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { ElMessage } from 'element-plus';
import { VideoPlay, VideoPause, Refresh } from '@element-plus/icons-vue';
import { authFetch } from '@/utils/authFetch.js';

// 态势回放：读取后端 state_snapshots（每 5 秒一帧，最多 720 帧），滑块/播放回看历史卫星状态
const snapshots = ref([]);
const loaded = ref(false);
const frameIndex = ref(0);
const isPlaying = ref(false);
const keyword = ref('');
const page = ref(1);
const pageSize = 15;
let playTimer = null;

const currentSnapshot = computed(() =>
  snapshots.value.length > 0 ? snapshots.value[Math.min(frameIndex.value, snapshots.value.length - 1)] : null
);

// 当前帧的卫星状态表行
const tableRows = computed(() => {
  const snap = currentSnapshot.value;
  if (!snap || !snap.sats) return [];
  return Object.entries(snap.sats).map(([name, s]) => ({
    name,
    battery: s.battery ?? 0,
    storage: s.storage ?? 0,
    lat: s.lat,
    lng: s.lng,
    height: s.height ?? '-'
  }));
});

const filteredRows = computed(() => {
  const kw = keyword.value.toLowerCase();
  if (!kw) return tableRows.value;
  return tableRows.value.filter((r) => r.name.toLowerCase().includes(kw));
});

const pagedRows = computed(() =>
  filteredRows.value.slice((page.value - 1) * pageSize, page.value * pageSize)
);

// 电量进度条按初始电量 3000Wh 估算百分比，仅作可视化参考
function batteryPct(b) {
  return Math.max(0, Math.min(100, Math.round((b / 3000) * 100)));
}
function batteryColor(b) {
  if (b < 20) return '#ff6b6b';
  if (b < 50) return '#ffd657';
  return '#52ffa8';
}
function fmtNum(v) {
  return typeof v === 'number' ? v.toFixed(2) : '-';
}

// 手动拖动滑块时暂停播放，避免跳帧冲突
function onSlider() {
  if (isPlaying.value) togglePlay();
}

function togglePlay() {
  if (isPlaying.value) {
    clearInterval(playTimer);
    playTimer = null;
    isPlaying.value = false;
  } else {
    isPlaying.value = true;
    playTimer = setInterval(() => {
      if (frameIndex.value >= snapshots.value.length - 1) {
        togglePlay();  // 播到末帧自动停止
      } else {
        frameIndex.value += 1;
      }
    }, 500);  // 2 帧/秒回放
  }
}

async function loadSnapshots() {
  try {
    const r = await authFetch('/satellites/replay/snapshots?index=-1');
    const d = await r.json();
    snapshots.value = Array.isArray(d.snapshots) ? d.snapshots : [];
    loaded.value = true;
    if (snapshots.value.length > 0) {
      frameIndex.value = snapshots.value.length - 1;  // 默认定位到最新帧
      page.value = 1;
    }
  } catch (e) {
    ElMessage.warning('回放快照加载失败，请确认后端服务已启动');
  }
}

onMounted(loadSnapshots);
onUnmounted(() => { if (playTimer) clearInterval(playTimer); });
</script>

<style scoped>
.replay-page { padding: 16px; }
.control-card { margin-bottom: 14px; }
.control-bar { display: flex; align-items: center; gap: 18px; flex-wrap: wrap; }
.cb-title { display: flex; align-items: baseline; gap: 8px; }
.cb-name { font-size: 16px; font-weight: 700; color: #00dcff; letter-spacing: 2px; }
.cb-sub { font-size: 10px; letter-spacing: 2px; color: #4d7a9a; font-family: 'Courier New', monospace; }
.cb-info { display: flex; gap: 14px; font-size: 12px; color: #9fc6e8; font-family: 'Courier New', monospace; }
.cb-actions { margin-left: auto; display: flex; gap: 8px; }
.slider-row { display: flex; align-items: center; gap: 16px; margin-top: 12px; }
.slider-row :deep(.el-slider) { flex: 1; }
.frame-time {
  font-family: 'Courier New', monospace;
  font-size: 13px;
  color: #00f0ff;
  min-width: 150px;
  text-align: right;
}
.card-header { display: flex; justify-content: space-between; align-items: center; }
.sat-kw { width: 200px; }
.batt-cell { display: flex; align-items: center; gap: 8px; }
.batt-bar { flex: 1; }
.batt-num { font-family: 'Courier New', monospace; font-size: 12px; min-width: 48px; text-align: right; }
.pager-row { display: flex; justify-content: flex-end; margin-top: 10px; }
</style>
