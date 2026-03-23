<template>
  <div class="cluster-manage">
    <!-- 搜索工具栏 -->
    <el-card shadow="never" class="search-card">
      <div class="search-bar">
        <div class="search-left">
          <el-input
            v-model="search.keyword"
            placeholder="请输入星簇名称搜索"
            clearable
            style="width: 280px"
            @keyup.enter="handleSearch"
            @clear="handleSearch"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
          <el-button type="primary" :icon="Search" @click="handleSearch">搜索</el-button>
          <el-button :icon="Refresh" @click="resetSearch">重置</el-button>
        </div>
        <div class="search-right">
          <el-button type="success" :icon="Plus" @click="showAddDialog">新增星簇</el-button>
          <el-button type="primary" :icon="Download" @click="exportAll">导出全部</el-button>
          <el-button :icon="Refresh" circle title="刷新" @click="refreshList" :loading="loading" />
        </div>
      </div>
    </el-card>

    <!-- 表格区域 -->
    <el-card shadow="never" class="table-card">
      <el-table 
        :data="tableData" 
        stripe 
        v-loading="loading"
      >
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="name" label="星簇名称" width="150" />
        <el-table-column prop="orbit" label="包含轨道" min-width="200" show-overflow-tooltip />
        <el-table-column prop="satellite_count" label="卫星数量" width="100" />
        <el-table-column prop="payload_resolution" label="载荷及分辨率" min-width="200" show-overflow-tooltip />
        <el-table-column label="状态" width="90">
          <template #default="scope">
            <el-switch
              v-model="scope.row.status"
              inline-prompt
              active-text="启用"
              inactive-text="禁用"
              @change="(val) => handleStatusChange(scope.row, val)"
            />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="scope">
            <el-button link type="primary" :icon="View" @click="showDetail(scope.row)">详情</el-button>
            <el-button link type="primary" :icon="Edit" @click="editCluster(scope.row)">编辑</el-button>
            <el-button link type="primary" :icon="RefreshRight" @click="showReplanDialog(scope.row)">重规划</el-button>
            <el-popconfirm title="确定要删除该星簇吗?" @confirm="deleteCluster(scope.row.id)">
              <template #reference>
                <el-button link type="danger" :icon="Delete">删除</el-button>
              </template>
            </el-popconfirm>
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

    <!-- 新增/编辑星簇弹窗 -->
    <el-dialog 
      v-model="dialogVisible" 
      :title="isEdit ? '编辑星簇' : '新增星簇'" 
      width="700px"
      destroy-on-close
    >
      <el-form :model="clusterForm" label-width="120px" :rules="formRules" ref="formRef">
        <el-form-item label="星簇名称" prop="name">
          <el-input v-model="clusterForm.name" placeholder="请输入星簇名称" />
        </el-form-item>
        
        <el-form-item label="选择轨道" prop="orbits">
          <el-select 
            v-model="clusterForm.orbits" 
            multiple 
            placeholder="请选择轨道"
            style="width: 100%"
            @change="onOrbitChange"
          >
            <el-option 
              v-for="orbit in orbitList" 
              :key="Object.keys(orbit)[0]" 
              :label="Object.values(orbit)[0]" 
              :value="parseInt(Object.keys(orbit)[0])"
            />
          </el-select>
          <div class="form-hint">选择包含该星簇的轨道</div>
        </el-form-item>

        <el-form-item label="载荷配置">
          <div class="payload-config">
            <div v-for="(payload, key) in payloadOptions" :key="key" class="payload-item">
              <el-checkbox v-model="payload.selected" @change="onPayloadChange">
                {{ payload.label }}
              </el-checkbox>
              <el-select 
                v-if="payload.selected" 
                v-model="payload.resolutions" 
                multiple 
                placeholder="选择分辨率"
                size="small"
                style="width: 200px; margin-left: 10px;"
              >
                <el-option 
                  v-for="res in payload.availableResolutions" 
                  :key="res" 
                  :label="res + ' m'" 
                  :value="res"
                />
              </el-select>
            </div>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="saveCluster" :loading="saving">保存</el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 重规划弹窗 -->
    <el-dialog 
      v-model="replanVisible" 
      title="任务重规划" 
      width="500px"
    >
      <div class="replan-content">
        <p>将星簇 <strong>{{ replanForm.oldCluster }}</strong> 的任务迁移至：</p>
        <el-select v-model="replanForm.newCluster" placeholder="选择目标星簇" style="width: 100%; margin-top: 16px;">
          <el-option 
            v-for="cluster in availableClusters" 
            :key="cluster.id" 
            :label="cluster.name" 
            :value="cluster.name"
          />
        </el-select>
      </div>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="replanVisible = false">取消</el-button>
          <el-button type="primary" @click="doReplan" :loading="replanning">确认迁移</el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 详情弹窗 -->
    <el-dialog 
      v-model="detailVisible" 
      title="星簇详情" 
      width="600px"
    >
      <el-descriptions :column="1" border v-if="currentCluster">
        <el-descriptions-item label="星簇ID">{{ currentCluster.id }}</el-descriptions-item>
        <el-descriptions-item label="星簇名称">{{ currentCluster.name }}</el-descriptions-item>
        <el-descriptions-item label="包含轨道">{{ currentCluster.orbit }}</el-descriptions-item>
        <el-descriptions-item label="卫星数量">{{ currentCluster.satellite_count }}</el-descriptions-item>
        <el-descriptions-item label="载荷及分辨率">{{ currentCluster.payload_resolution }}</el-descriptions-item>
        <el-descriptions-item label="包含卫星">
          <el-tag v-for="name in currentCluster.satellite_names" :key="name" size="small" style="margin-right: 8px; margin-bottom: 4px;">
            {{ name }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="currentCluster.status ? 'success' : 'danger'">
            {{ currentCluster.status ? '启用' : '禁用' }}
          </el-tag>
        </el-descriptions-item>
      </el-descriptions>
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ElMessage, ElMessageBox } from 'element-plus';
import { 
  Search, Refresh, Plus, Download, View, Edit, Delete, 
  RefreshRight
} from '@element-plus/icons-vue';

export default {
  name: 'ClusterManage',
  components: {
    Search, Refresh, Plus, Download, View, Edit, Delete, RefreshRight
  },
  data() {
    return {
      loading: false,
      tableData: [],
      totalNum: 0,
      search: {
        pageNum: 1,
        pageSize: 10,
        keyword: ''
      },
      
      // 弹窗相关
      dialogVisible: false,
      isEdit: false,
      saving: false,
      formRef: null,
      
      // 表单数据
      clusterForm: {
        id: null,
        name: '',
        orbits: [],
        payload_resolution: {}
      },
      
      // 轨道列表
      orbitList: [],
      
      // 载荷选项
      payloadOptions: {
        SAR: { label: 'SAR', selected: false, resolutions: [], availableResolutions: [0.5, 1, 2, 5] },
        optical: { label: '光学', selected: false, resolutions: [], availableResolutions: [0.5, 1, 2, 5, 10] },
        infrared: { label: '红外', selected: false, resolutions: [], availableResolutions: [5, 10, 20] }
      },
      
      // 表单验证规则
      formRules: {
        name: [{ required: true, message: '请输入星簇名称', trigger: 'blur' }],
        orbits: [{ required: true, message: '请至少选择一个轨道', trigger: 'change', type: 'array', min: 1 }]
      },
      
      // 重规划相关
      replanVisible: false,
      replanning: false,
      replanForm: {
        oldCluster: '',
        newCluster: ''
      },
      availableClusters: [],
      
      // 详情相关
      detailVisible: false,
      currentCluster: null
    };
  },
  created() {
    this.getList();
    this.loadOrbits();
  },
  methods: {
    // 获取星簇列表
    async getList() {
      this.loading = true;
      try {
        const res = await this.$request.post('/clusters/getClustersByPage', {
          page: this.search.pageNum,
          per_page: this.search.pageSize,
          cluster_name: this.search.keyword
        });
        if (res.data.status === 'success') {
          this.tableData = res.data.data.items;
          this.totalNum = res.data.data.total;
        }
      } catch (err) {
        console.error('获取星簇列表失败:', err);
        if (err.response?.status === 503) {
          ElMessage.warning('系统尚未初始化完成');
        } else {
          ElMessage.error('获取星簇列表失败: ' + (err.message || '未知错误'));
        }
        this.tableData = [];
        this.totalNum = 0;
      } finally {
        this.loading = false;
      }
    },
    
    // 加载轨道列表
    async loadOrbits() {
      try {
        const res = await this.$request.get('/clusters/getOrbits');
        if (res.data.status === 'success') {
          this.orbitList = res.data.orbits;
        }
      } catch (err) {
        console.error('加载轨道列表失败:', err);
      }
    },
    
    // 轨道变化时加载对应的分辨率选项
    async onOrbitChange(orbits) {
      if (orbits.length === 0) return;
      try {
        const res = await this.$request.post('/clusters/getInfoByOrbits', { orbits });
        if (res.data.status === 'success') {
          const resolutionMap = res.data.resolution_map;
          // 更新可用的分辨率选项
          for (const [payload, resolutions] of Object.entries(resolutionMap)) {
            if (this.payloadOptions[payload]) {
              this.payloadOptions[payload].availableResolutions = resolutions;
            }
          }
        }
      } catch (err) {
        console.error('获取载荷信息失败:', err);
      }
    },
    
    // 搜索
    handleSearch() {
      this.search.pageNum = 1;
      this.getList();
    },
    
    // 重置搜索
    resetSearch() {
      this.search = {
        pageNum: 1,
        pageSize: 10,
        keyword: ''
      };
      this.getList();
    },
    
    // 刷新
    refreshList() {
      this.getList();
    },
    
    // 分页
    handleSizeChange(val) {
      this.search.pageSize = val;
      this.search.pageNum = 1;
      this.getList();
    },
    handleCurrentChange(val) {
      this.search.pageNum = val;
      this.getList();
    },
    
    // 显示新增弹窗
    showAddDialog() {
      this.isEdit = false;
      this.clusterForm = {
        id: null,
        name: '',
        orbits: [],
        payload_resolution: {}
      };
      // 重置载荷选项
      for (const key in this.payloadOptions) {
        this.payloadOptions[key].selected = false;
        this.payloadOptions[key].resolutions = [];
      }
      this.dialogVisible = true;
    },
    
    // 编辑星簇
    editCluster(row) {
      this.isEdit = true;
      this.clusterForm = {
        id: row.id,
        name: row.name,
        orbits: [],  // 需要从row.orbit解析
        payload_resolution: {}
      };
      
      // 解析轨道
      if (row.orbit) {
        // 轨道格式是 "轨道1&&轨道2"，需要根据orbit_info反查轨道ID
        const orbitNames = row.orbit.split('&&');
        this.clusterForm.orbits = this.orbitList
          .filter(o => orbitNames.includes(Object.values(o)[0]))
          .map(o => parseInt(Object.keys(o)[0]));
      }
      
      // 解析载荷和分辨率
      if (row.payload_resolution) {
        const parts = row.payload_resolution.split('|');
        for (const part of parts) {
          if (part.includes(':')) {
            const [payload, resStr] = part.split(':');
            if (this.payloadOptions[payload]) {
              this.payloadOptions[payload].selected = true;
              this.payloadOptions[payload].resolutions = resStr.split(',').map(r => parseFloat(r));
            }
          } else {
            if (this.payloadOptions[part]) {
              this.payloadOptions[part].selected = true;
            }
          }
        }
      }
      
      this.dialogVisible = true;
    },
    
    // 保存星簇
    async saveCluster() {
      const valid = await this.$refs.formRef.validate().catch(() => false);
      if (!valid) return;
      
      // 构建载荷分辨率映射
      const payloadResolution = {};
      for (const [key, payload] of Object.entries(this.payloadOptions)) {
        if (payload.selected) {
          payloadResolution[key] = payload.resolutions;
        }
      }
      
      const data = {
        cluster_name: this.clusterForm.name,
        orbits: this.clusterForm.orbits,
        payload_resolution: payloadResolution
      };
      
      this.saving = true;
      try {
        if (this.isEdit) {
          await this.$request.post(`/clusters/updateCluster/${this.clusterForm.id}`, data);
          ElMessage.success('星簇更新成功');
        } else {
          await this.$request.post('/clusters/addCluster', data);
          ElMessage.success('星簇添加成功');
        }
        this.dialogVisible = false;
        this.getList();
      } catch (err) {
        ElMessage.error('保存失败: ' + (err.message || '未知错误'));
      } finally {
        this.saving = false;
      }
    },
    
    // 删除星簇
    async deleteCluster(id) {
      try {
        await this.$request.delete(`/clusters/deleteClusterById/${id}`);
        ElMessage.success('星簇删除成功');
        this.getList();
      } catch (err) {
        ElMessage.error('删除失败: ' + (err.message || '未知错误'));
      }
    },
    
    // 状态切换
    async handleStatusChange(row, val) {
      try {
        const url = val 
          ? `/clusters/setAvailableCluster/${row.id}`
          : `/clusters/setUnavailableCluster/${row.id}`;
        await this.$request.post(url);
        ElMessage.success(`${row.name} 已${val ? '启用' : '禁用'}`);
      } catch (err) {
        row.status = !val; // 回滚
        ElMessage.error('操作失败: ' + (err.message || '未知错误'));
      }
    },
    
    // 显示重规划弹窗
    showReplanDialog(row) {
      this.replanForm.oldCluster = row.name;
      this.replanForm.newCluster = '';
      // 加载其他可用的星簇
      this.availableClusters = this.tableData.filter(c => c.id !== row.id && c.status);
      this.replanVisible = true;
    },
    
    // 执行重规划
    async doReplan() {
      if (!this.replanForm.newCluster) {
        ElMessage.warning('请选择目标星簇');
        return;
      }
      
      this.replanning = true;
      try {
        await this.$request.post('/clusters/replan', {
          oldCluster: this.replanForm.oldCluster,
          newCluster: this.replanForm.newCluster
        });
        ElMessage.success('任务重规划完成');
        this.replanVisible = false;
      } catch (err) {
        ElMessage.error('重规划失败: ' + (err.message || '未知错误'));
      } finally {
        this.replanning = false;
      }
    },
    
    // 显示详情
    showDetail(row) {
      this.currentCluster = row;
      this.detailVisible = true;
    },
    
    // 导出全部
    async exportAll() {
      try {
        const res = await this.$request.get('/clusters/exportAllClusters', {
          responseType: 'blob'
        });
        const url = window.URL.createObjectURL(new Blob([res.data]));
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', '星簇信息.xlsx');
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
        ElMessage.success('导出成功');
      } catch (err) {
        ElMessage.error('导出失败');
      }
    },
    
    onPayloadChange() {
      // 载荷选择变化时的处理
    }
  }
};
</script>

<style scoped>
.cluster-manage {
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

/* 表格 */
.table-card {
  margin-bottom: 16px;
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  padding-top: 16px;
  border-top: 1px solid #ebeef5;
  margin-top: 16px;
}

/* 载荷配置 */
.payload-config {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.payload-item {
  display: flex;
  align-items: center;
}

.form-hint {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

/* 重规划 */
.replan-content {
  padding: 10px 0;
}

.replan-content p {
  color: #606266;
  margin: 0;
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
  .search-left .el-button,
  .search-right .el-button {
    width: 100%;
    margin: 0;
  }
}
</style>
