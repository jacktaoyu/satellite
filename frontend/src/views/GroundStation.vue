<template>
  <div class="gs-page">
    <!-- 顶部标题卡片 -->
    <div class="hud title-panel">
      <div class="panel-title">地面站管理</div>
      <div class="title-body">
        <div class="title-left">
          <span class="sys-title">地面站管理</span>
          <span class="sub-title">GROUND STATION MANAGEMENT</span>
        </div>
        <div class="title-stats">
          <div class="hs-item"><b>{{ stations.length }}</b><span>地面站总数</span></div>
          <div class="hs-item"><b>{{ totalLinks }}</b><span>当前链路数</span></div>
          <el-button :icon="Refresh" size="small" @click="loadData" :loading="loading">刷新</el-button>
        </div>
      </div>
    </div>

    <!-- 地面站表格 -->
    <div class="hud table-panel">
      <div class="panel-title">地面站列表</div>
      <div class="table-body">
        <el-table
          :data="pagedStations"
          v-loading="loading"
          stripe
          :empty-text="emptyText"
        >
          <el-table-column type="expand">
            <template #default="scope">
              <div class="expand-content">
                <span class="expand-label">连接卫星：</span>
                <template v-if="scope.row.connecting_satellite && scope.row.connecting_satellite.length">
                  <el-tag
                    v-for="sat in scope.row.connecting_satellite"
                    :key="sat"
                    size="small"
                    class="sat-tag"
                  >{{ sat }}</el-tag>
                </template>
                <span v-else class="expand-empty">当前无连接卫星</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="name" label="站名" min-width="140">
            <template #default="scope">
              <span class="station-name">
                <el-icon><Position /></el-icon>{{ scope.row.name }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="经度 (°)" width="130">
            <template #default="scope">
              <span class="num">{{ fmtCoord(scope.row.location, 1) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="纬度 (°)" width="130">
            <template #default="scope">
              <span class="num">{{ fmtCoord(scope.row.location, 0) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="覆盖 / 链路状态" width="140">
            <template #default="scope">
              <el-tag
                size="small"
                :type="scope.row.connecting_satellite && scope.row.connecting_satellite.length ? 'success' : 'info'"
              >
                {{ scope.row.connecting_satellite && scope.row.connecting_satellite.length ? '链路已建立' : '空闲待命' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="当前连接卫星数" width="140">
            <template #default="scope">
              <span class="num">{{ (scope.row.connecting_satellite || []).length }}</span>
            </template>
          </el-table-column>
          <el-table-column label="连接卫星列表" min-width="200">
            <template #default="scope">
              <template v-if="scope.row.connecting_satellite && scope.row.connecting_satellite.length">
                <el-tag
                  v-for="sat in scope.row.connecting_satellite"
                  :key="sat"
                  size="small"
                  class="sat-tag"
                >{{ sat }}</el-tag>
              </template>
              <span v-else class="cell-empty">-</span>
            </template>
          </el-table-column>
        </el-table>

        <!-- 分页 -->
        <div class="pagination-wrapper">
          <el-pagination
            background
            @size-change="handleSizeChange"
            @current-change="handleCurrentChange"
            layout="total, sizes, prev, pager, next, jumper"
            :total="stations.length"
            :current-page="currentPage"
            :page-size="pageSize"
            :page-sizes="[10, 20, 50, 100]"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { Refresh, Position } from '@element-plus/icons-vue';

export default {
  name: 'GroundStation',
  components: { Refresh, Position },
  data() {
    return {
      loading: false,
      stations: [],
      loadError: false,
      currentPage: 1,
      pageSize: 10
    };
  },
  computed: {
    totalLinks() {
      return this.stations.reduce((sum, s) => sum + ((s.connecting_satellite || []).length), 0);
    },
    emptyText() {
      return this.loadError ? '卫星网络未初始化' : '暂无地面站数据';
    },
    // 数据前端一次性拉取，分页在前端切片
    pagedStations() {
      const start = (this.currentPage - 1) * this.pageSize;
      return this.stations.slice(start, start + this.pageSize);
    }
  },
  created() {
    this.loadData();
  },
  methods: {
    async loadData() {
      this.loading = true;
      this.loadError = false;
      try {
        const res = await this.$request.get('/satellites/groundStationInfo');
        this.stations = Array.isArray(res.data) ? res.data : [];
      } catch (err) {
        console.error('获取地面站信息失败:', err);
        this.stations = [];
        this.loadError = true;
      } finally {
        this.loading = false;
      }
    },
    handleSizeChange(val) {
      this.pageSize = val;
      this.currentPage = 1;
    },
    handleCurrentChange(val) {
      this.currentPage = val;
    },
    // 后端 location 为 [纬度, 经度] 数组，兼容字符串格式
    fmtCoord(location, index) {
      if (Array.isArray(location) && location.length >= 2) {
        const v = Number(location[index]);
        return Number.isFinite(v) ? v.toFixed(2) : '-';
      }
      return '-';
    }
  }
};
</script>

<style scoped>
.gs-page {
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* ===== HUD 通用面板样式：深色半透明 + 青色发光描边（与卫星网络页一致） ===== */
.hud {
  background: rgba(8, 20, 46, 0.78);
  border: 1px solid rgba(0, 220, 255, 0.35);
  border-radius: 4px;
  box-shadow: 0 0 12px rgba(0, 220, 255, 0.15), inset 0 0 20px rgba(0, 100, 200, 0.1);
  backdrop-filter: blur(4px);
  color: #cfe8ff;
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
  align-items: center;
  background: linear-gradient(90deg, rgba(0, 220, 255, 0.12), transparent);
}
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

/* ===== 顶部标题卡片 ===== */
.title-body {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  padding: 14px 16px;
}
.title-left {
  display: flex;
  align-items: baseline;
}
.sys-title {
  font-size: 20px;
  font-weight: 700;
  letter-spacing: 3px;
  background: linear-gradient(180deg, #ffffff, #7fd4ff);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  filter: drop-shadow(0 0 8px rgba(0, 220, 255, 0.5));
}
.sub-title {
  margin-left: 12px;
  font-size: 12px;
  letter-spacing: 1px;
  background: linear-gradient(180deg, #bfefff, #00dcff);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}
.title-stats {
  display: flex;
  align-items: center;
  gap: 20px;
}
.hs-item {
  display: flex;
  align-items: baseline;
  gap: 6px;
  white-space: nowrap;
}
.hs-item b {
  font-size: 16px;
  font-weight: 700;
  color: #00f0ff;
  text-shadow: 0 0 8px rgba(0, 240, 255, 0.7);
  font-family: 'Courier New', monospace;
}
.hs-item span {
  font-size: 11px;
  color: #9fc6e8;
}

/* ===== 表格 ===== */
.table-body {
  padding: 12px 16px 16px;
}
.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  padding-top: 16px;
  border-top: 1px solid rgba(0, 220, 255, 0.15);
  margin-top: 16px;
}
.station-name {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #e8f6ff;
}
.station-name .el-icon {
  color: #00dcff;
}
.num {
  font-family: 'Courier New', monospace;
  color: #00f0ff;
  text-shadow: 0 0 8px rgba(0, 240, 255, 0.5);
}
.cell-empty {
  color: #68809a;
}
.sat-tag {
  margin-right: 6px;
  margin-bottom: 4px;
}
.expand-content {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
  padding: 4px 32px;
}
.expand-label {
  color: #9fc6e8;
  margin-right: 8px;
}
.expand-empty {
  color: #68809a;
}

@media (max-width: 768px) {
  .title-body {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
