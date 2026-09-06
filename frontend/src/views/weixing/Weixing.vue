<template>
  <div class="satellite-manage">
    <!-- 搜索工具栏 -->
    <el-card shadow="never" class="search-card">
      <div class="search-bar">
        <div class="search-left">
          <el-input
            v-model="search.keyword"
            placeholder="请输入卫星名称搜索"
            clearable
            style="width: 280px"
            @keyup.enter="handleSearch"
            @clear="handleSearch"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
          <el-select 
            v-model="search.loadType" 
            placeholder="载荷类型" 
            clearable 
            style="width: 140px"
            @change="handleSearch"
          >
            <el-option label="SAR" value="SAR" />
            <el-option label="光学" value="optical" />
            <el-option label="红外" value="infrared" />
          </el-select>
          <el-select 
            v-model="search.status" 
            placeholder="状态" 
            clearable 
            style="width: 120px"
            @change="handleSearch"
          >
            <el-option label="可用" :value="true" />
            <el-option label="不可用" :value="false" />
          </el-select>
          <el-button type="primary" :icon="Search" @click="handleSearch">搜索</el-button>
          <el-button :icon="Refresh" @click="resetSearch">重置</el-button>
        </div>
        <div class="search-right">
          <el-button type="success" :icon="Download" @click="exportAll">导出全部</el-button>
          <el-button :icon="Refresh" circle title="刷新" @click="refreshList" :loading="loading" />
        </div>
      </div>
    </el-card>

    <!-- 批量操作工具栏 -->
    <el-card shadow="never" class="toolbar-card" v-if="selectedSatellites.length > 0">
      <div class="batch-toolbar">
        <span class="batch-text">已选择 <strong>{{ selectedSatellites.length }}</strong> 颗卫星</span>
        <el-button-group>
          <el-button type="success" size="small" :icon="CircleCheck" @click="batchEnable">批量启用</el-button>
          <el-button type="warning" size="small" :icon="CircleClose" @click="batchDisable">批量禁用</el-button>
          <el-button type="primary" size="small" :icon="Download" @click="batchExport">批量导出</el-button>
        </el-button-group>
        <el-button link type="danger" size="small" :icon="Close" @click="clearSelection">清空选择</el-button>
      </div>
    </el-card>

    <!-- 表格区域 -->
    <el-card shadow="never" class="table-card">
      <el-table 
        ref="table"
        :data="tableData" 
        stripe 
        v-loading="loading"
        @selection-change="handleSelectionChange"
        row-key="id"
      >
        <el-table-column type="selection" width="55" reserve-selection />
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="name" label="卫星名称" width="120" />
        <el-table-column prop="orbit" label="轨道" show-overflow-tooltip min-width="120" />
        <el-table-column prop="loadType" label="载荷" width="100">
          <template #default="scope">
            <el-tag size="small" :type="getLoadTypeType(scope.row.loadType)">
              {{ scope.row.loadType || '未知' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="battery" label="电池(Wh)" width="100" sortable />
        <el-table-column prop="storage" label="存储(GB)" width="100" sortable />
        <el-table-column prop="resolution" label="分辨率(m)" width="110" />
        <!-- <el-table-column label="状态" width="90">
          <template #default="scope">
            <el-switch
              v-model="scope.row.is_available"
              inline-prompt
              active-text="可用"
              inactive-text="禁用"
              @change="(val) => handleStatusChange(scope.row, val)"
            />
          </template>
        </el-table-column> -->
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="scope">
            <el-button link type="primary" :icon="View" @click="showDetail(scope.row)">详情</el-button>
            <el-button link type="primary" :icon="Edit" @click="editItem(scope.row)">编辑</el-button>
            <el-button link type="primary" :icon="Download" @click="exportSatellite(scope.row)">导出</el-button>
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
          :total="totalNum" 
          :current-page="search.pageNum"
          :page-size="search.pageSize"
          :page-sizes="[10, 20, 50, 100]"
        />
      </div>
    </el-card>

    <!-- 编辑弹窗 -->
    <el-dialog 
      v-model="editDialogVisible" 
      title="编辑卫星参数" 
      width="600px"
      destroy-on-close
    >
      <el-form :model="editForm" label-width="140px" class="edit-form">
        <el-divider content-position="left">基础参数</el-divider>
        <el-form-item label="卫星名称">
          <el-input v-model="editForm.name" disabled />
        </el-form-item>
        <el-form-item label="存储容量 (GB)">
          <el-input-number v-model="editForm.storage" :min="1" :max="10000" controls-position="right" />
        </el-form-item>
        <el-form-item label="电池容量 (Wh)">
          <el-input-number v-model="editForm.battery" :min="1" :max="20000" controls-position="right" />
        </el-form-item>
        <el-form-item label="下行速率 (GB/s)">
          <el-input-number v-model="editForm.downlink_rate" :min="0.1" :max="100" :step="0.1" controls-position="right" />
        </el-form-item>
        
        <el-divider content-position="left">功率参数</el-divider>
        <el-form-item label="空闲功率 (W)">
          <el-input-number v-model="editForm.eclipse_powers" :min="0" :max="1000" controls-position="right" />
        </el-form-item>
        <el-form-item label="太阳能功率 (W)">
          <el-input-number v-model="editForm.sunlight_powers" :min="0" :max="1000" controls-position="right" />
        </el-form-item>
        <el-form-item label="机动功率 (W)">
          <el-input-number v-model="editForm.maneuver_powers" :min="0" :max="5000" controls-position="right" />
        </el-form-item>
        <el-form-item label="成像功率 (W)">
          <el-input-number v-model="editForm.imaging_powers" :min="0" :max="5000" controls-position="right" />
        </el-form-item>
        
        <el-divider content-position="left">载荷参数</el-divider>
        <el-form-item label="角度转动速度 (°/s)">
          <el-input-number v-model="editForm.angle_velocity" :min="0.1" :max="10" :step="0.1" controls-position="right" />
        </el-form-item>
        <el-form-item label="稳定时间 (s)">
          <el-input-number v-model="editForm.stable_time" :min="0" :max="60" controls-position="right" />
        </el-form-item>
        <el-form-item label="最大侧摆角度 (°)">
          <el-input-number v-model="editForm.side_swing_angle_Max" :min="0" :max="90" controls-position="right" />
        </el-form-item>
        <el-form-item label="最大俯仰角度 (°)">
          <el-input-number v-model="editForm.pitch_angle_Max" :min="0" :max="90" controls-position="right" />
        </el-form-item>
        <el-form-item label="云层厚度阈值 (m)">
          <el-input-number v-model="editForm.cloud_threshold" :min="0" :max="2000" controls-position="right" />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="editDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="saveEdit" :loading="saving">保存</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ElMessage, ElMessageBox } from 'element-plus';
import { 
  Search, Refresh, Download, View, Edit, CircleCheck, CircleClose, Close,
  ArrowDown, OfficeBuilding
} from '@element-plus/icons-vue';

export default {
  components: {
    Search, Refresh, Download, View, Edit, CircleCheck, CircleClose, Close,
    ArrowDown, OfficeBuilding
  },
  data() {
    return {
      loading: false,
      allSatellites: [], // 全部数据
      tableData: [], // 当前页数据
      totalNum: 0,
      search: {
        pageNum: 1,
        pageSize: 10,
        keyword: '',
        loadType: '',
        status: null
      },
      selectedSatellites: [],
      editDialogVisible: false,
      saving: false,
      editForm: {
        id: null,
        name: '',
        storage: 500,
        battery: 5000,
        downlink_rate: 4,
        eclipse_powers: 8,
        sunlight_powers: 300,
        maneuver_powers: 500,
        imaging_powers: 700,
        angle_velocity: 1.0,
        stable_time: 10,
        side_swing_angle_Max: 45,
        pitch_angle_Max: 45,
        cloud_threshold: 800
      }
    };
  },
  created() {
    this.getList();
    this.isAdmin = localStorage.getItem("isAdmin");
  },
  methods: {
    // 获取卫星列表
    async getList() {
      this.loading = true;
      try {
        const res = await this.$request.post(
          "/satellites/getAllSatellites",
          { sate_name: "" }
        );
        if (Array.isArray(res.data)) {
          this.allSatellites = res.data;
          this.filterAndPaginate();
        }
      } catch (err) {
        console.error('获取卫星列表失败:', err);
        // const errorMessage = err.response?.data?.error || err.response?.data?.message || err.message || '';
        // if (err.response?.status === 503 || String(errorMessage).includes('未初始化')) {
        //   // ElMessage.warning('系统尚未初始化完成，请先上传 TLE 文件和卫星参数文件');
        //   ElMessage.error('获取卫星列表失败: ' + errorMessage);
        // } else {
        //   ElMessage.error('获取卫星列表失败: ' + errorMessage);
        // }
        this.allSatellites = [];
        this.tableData = [];
        this.totalNum = 0;
      } finally {
        this.loading = false;
      }
    },

    // 筛选和分页
    filterAndPaginate() {
      let data = [...this.allSatellites];

      // 关键词搜索
      if (this.search.keyword) {
        const keyword = this.search.keyword.toLowerCase();
        data = data.filter(sat => 
          sat.name?.toLowerCase().includes(keyword) ||
          sat.orbit?.toLowerCase().includes(keyword)
        );
      }

      // 载荷类型筛选
      if (this.search.loadType) {
        data = data.filter(sat => sat.loadType === this.search.loadType);
      }

      // 状态筛选
      if (this.search.status !== null && this.search.status !== '') {
        data = data.filter(sat => sat.is_available === this.search.status);
      }

      this.totalNum = data.length;

      // 分页
      const start = (this.search.pageNum - 1) * this.search.pageSize;
      const end = start + this.search.pageSize;
      this.tableData = data.slice(start, end);
    },

    // 搜索
    handleSearch() {
      this.search.pageNum = 1;
      this.filterAndPaginate();
    },

    // 重置搜索
    resetSearch() {
      this.search = {
        pageNum: 1,
        pageSize: 10,
        keyword: '',
        loadType: '',
        status: null
      };
      this.filterAndPaginate();
    },

    // 刷新
    refreshList() {
      this.getList();
    },

    // 分页
    handleSizeChange(val) {
      this.search.pageSize = val;
      this.search.pageNum = 1;
      this.filterAndPaginate();
    },
    handleCurrentChange(val) {
      this.search.pageNum = val;
      this.filterAndPaginate();
    },

    // 选择变化
    handleSelectionChange(selection) {
      this.selectedSatellites = selection;
    },

    // 清空选择
    clearSelection() {
      this.selectedSatellites = [];
      this.$refs.table?.clearSelection();
    },

    // 获取载荷类型样式
    getLoadTypeType(loadType) {
      const map = {
        'SAR': 'success',
        'optical': 'primary',
        'infrared': 'warning'
      };
      return map[loadType] || 'info';
    },

    // 状态切换
    async handleStatusChange(row, val) {
      try {
        const url = val 
          ? `/satellites/setSatelliteAvailable/${row.id}`
          : `/satellites/setSatelliteUnavailable/${row.id}`;
        await this.$request.post(url);
        ElMessage.success(`${row.name} 已${val ? '启用' : '禁用'}`);
      } catch (err) {
        row.is_available = !val; // 回滚
        ElMessage.error('操作失败: ' + (err.message || '未知错误'));
      }
    },

    // 切换状态（更多菜单）
    async toggleStatus(row) {
      const newStatus = !row.is_available;
      try {
        await ElMessageBox.confirm(
          `确定要${newStatus ? '启用' : '禁用'}卫星 ${row.name} 吗？`,
          '提示',
          { type: 'warning' }
        );
        await this.handleStatusChange(row, newStatus);
      } catch {
        // 取消
      }
    },

    // 批量启用
    async batchEnable() {
      try {
        await ElMessageBox.confirm(`确定要启用选中的 ${this.selectedSatellites.length} 颗卫星吗？`, '提示');
        for (const sat of this.selectedSatellites) {
          await this.$request.post(`/satellites/setSatelliteAvailable/${sat.id}`);
          sat.is_available = true;
        }
        ElMessage.success('批量启用成功');
        this.clearSelection();
      } catch (err) {
        if (err !== 'cancel') {
          ElMessage.error('批量启用失败');
        }
      }
    },

    // 批量禁用
    async batchDisable() {
      try {
        await ElMessageBox.confirm(`确定要禁用选中的 ${this.selectedSatellites.length} 颗卫星吗？`, '提示');
        for (const sat of this.selectedSatellites) {
          await this.$request.post(`/satellites/setSatelliteUnavailable/${sat.id}`);
          sat.is_available = false;
        }
        ElMessage.success('批量禁用成功');
        this.clearSelection();
      } catch (err) {
        if (err !== 'cancel') {
          ElMessage.error('批量禁用失败');
        }
      }
    },

    // 导出单个卫星
    async exportSatellite(row) {
      try {
        const res = await this.$request.get(
          `/satellites/exportSatelliteInfo/${row.id}`,
          { responseType: 'blob' }
        );
        this.downloadBlob(res.data, `${row.name}_info.xlsx`);
        ElMessage.success('导出成功');
      } catch (err) {
        ElMessage.error('导出失败');
      }
    },

    // 批量导出
    async batchExport() {
      try {
        ElMessage.info('正在导出，请稍候...');
        for (const sat of this.selectedSatellites) {
          await this.exportSatellite(sat);
        }
        ElMessage.success('批量导出完成');
      } catch (err) {
        ElMessage.error('导出失败');
      }
    },

    // 导出全部
    async exportAll() {
      try {
        const res = await this.$request.get(
          '/satellites/exportAllSatelliteInfo',
          { responseType: 'blob' }
        );
        this.downloadBlob(res.data, 'all_satellites_info.xlsx');
        ElMessage.success('导出成功');
      } catch (err) {
        ElMessage.error('导出失败');
      }
    },

    // 下载blob
    downloadBlob(blob, filename) {
      const url = window.URL.createObjectURL(new Blob([blob]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    },

    // 编辑
    editItem(row) {
      this.editForm = {
        id: row.id,
        name: row.name,
        storage: row.storage || 500,
        battery: row.battery || 5000,
        downlink_rate: row.downlink_rate || 4,
        eclipse_powers: 8,
        sunlight_powers: 300,
        maneuver_powers: 500,
        imaging_powers: 700,
        angle_velocity: 1.0,
        stable_time: 10,
        side_swing_angle_Max: 45,
        pitch_angle_Max: 45,
        cloud_threshold: 800
      };
      // 获取详细信息填充表单
      this.$request.get(`/satellites/getSatelliteById/${row.id}`).then(res => {
        if (res.data) {
          this.editForm = { ...this.editForm, ...res.data };
        }
      }).catch(() => {
        ElMessage.error('获取卫星详情失败');
      });
      this.editDialogVisible = true;
    },

    // 保存编辑
    async saveEdit() {
      this.saving = true;
      try {
        await this.$request.post(
          `/satellites/setSatelliteProperty/${this.editForm.id}`,
          this.editForm
        );
        ElMessage.success('保存成功');
        this.editDialogVisible = false;
        this.refreshList();
      } catch (err) {
        ElMessage.error('保存失败: ' + (err.message || '未知错误'));
      } finally {
        this.saving = false;
      }
    },

    // 详情
    showDetail(row) {
      this.$router.push(`/satellite/Weixing/info/${row.name}`);
    }
  }
};
</script>

<style scoped>
.satellite-manage {
  padding: 0;
}

/* 搜索栏 */
.search-card {
  margin-bottom: 16px;
}

.search-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}

.search-left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.search-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 批量工具栏 */
.toolbar-card {
  margin-bottom: 16px;
  background: #f0f9ff;
}

.batch-toolbar {
  display: flex;
  align-items: center;
  gap: 16px;
}

.batch-text {
  font-size: 14px;
  color: #606266;
}

.batch-text strong {
  color: #409EFF;
  font-size: 16px;
}

/* 表格卡片 */
.table-card {
  margin-bottom: 16px;
}

.satellite-name {
  display: flex;
  align-items: center;
  gap: 6px;
}

/* 分页 */
.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  padding-top: 16px;
  border-top: 1px solid #ebeef5;
  margin-top: 16px;
}

/* 编辑表单 */
.edit-form {
  max-height: 60vh;
  overflow-y: auto;
  padding-right: 10px;
}

.edit-form .el-input-number {
  width: 100%;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

/* 响应式 */
@media (max-width: 768px) {
  .search-bar {
    flex-direction: column;
    align-items: stretch;
  }
  
  .search-left,
  .search-right {
    flex-direction: column;
    width: 100%;
  }
  
  .search-left .el-input,
  .search-left .el-select,
  .search-left .el-button {
    width: 100%;
  }
  
  .batch-toolbar {
    flex-direction: column;
    align-items: stretch;
  }
  
  .batch-toolbar .el-button-group {
    display: flex;
    flex-direction: column;
  }
}
</style>
