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
          <el-button type="warning" :icon="UploadFilled" @click="showImportDialog">批量导入</el-button>
          <el-button type="primary" :icon="Download" @click="exportAll">导出全部</el-button>
          <el-button :icon="Refresh" circle title="刷新" @click="refreshList" :loading="loading" />
        </div>
      </div>
    </el-card>

    <!-- 表格区域 -->
    <el-card shadow="never" class="table-card">
      <!-- 加载中显示骨架屏 -->
      <div v-if="loading" class="table-skeleton">
        <el-skeleton :rows="6" animated />
      </div>
      <el-table
        v-else
        :data="tableData"
        stripe
      >
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="name" label="星簇名称" width="150" />
        <el-table-column prop="orbit" label="包含轨道" min-width="200" show-overflow-tooltip />
        <el-table-column prop="satellite_count" label="卫星数量" width="100" />
        <el-table-column label="包含卫星" min-width="220">
          <template #default="scope">
            <template v-if="scope.row.satellite_names && scope.row.satellite_names.length">
              <el-tag 
                v-for="name in scope.row.satellite_names.slice(0, 3)" 
                :key="name" 
                size="small" 
                style="margin-right: 4px;"
              >
                {{ name }}
              </el-tag>
              <el-tooltip 
                v-if="scope.row.satellite_names.length > 3" 
                :content="scope.row.satellite_names.join('、')" 
                placement="top"
              >
                <el-tag size="small" type="info">+{{ scope.row.satellite_names.length - 3 }}</el-tag>
              </el-tooltip>
            </template>
            <span v-else style="color: #909399;">-</span>
          </template>
        </el-table-column>
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
        <el-form label-width="80px">
          <el-form-item label="原星簇">
            <el-select v-model="replanForm.oldCluster" placeholder="选择原星簇" style="width: 100%;">
              <el-option 
                v-for="cluster in allClusters" 
                :key="cluster.id" 
                :label="cluster.name" 
                :value="cluster.name"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="新星簇">
            <el-select v-model="replanForm.newCluster" placeholder="选择目标星簇" style="width: 100%;">
              <el-option 
                v-for="cluster in availableClusters" 
                :key="cluster.id" 
                :label="cluster.name" 
                :value="cluster.name"
              />
            </el-select>
            <div class="form-hint">仅显示可用且与原星簇轨道/载荷适配的星簇</div>
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="replanVisible = false">取消</el-button>
          <el-button type="primary" @click="doReplan" :loading="replanning">确认迁移</el-button>
        </div>
      </template>
    </el-dialog>

    <!-- Excel 批量导入弹窗 -->
    <el-dialog 
      v-model="importVisible" 
      title="Excel 批量导入星簇" 
      width="500px"
      destroy-on-close
    >
      <div class="upload-zone-wrapper">
        <el-upload
          ref="importUploadRef"
          class="import-uploader"
          drag
          action="#"
          :auto-upload="false"
          :show-file-list="true"
          :limit="1"
          :on-change="handleImportFileChange"
          :on-remove="onImportRemove"
          accept=".xlsx"
        >
          <el-icon class="upload-zone-icon" :size="40"><UploadFilled /></el-icon>
          <div class="upload-zone-text">
            <span class="primary">拖拽文件到此处</span>
            <span class="secondary">或 <em>点击选择文件</em></span>
          </div>
        </el-upload>
        <div class="format-tags">
          <el-tag size="small" effect="plain" type="info">XLSX</el-tag>
        </div>
        <div class="form-hint" style="margin-top: 8px;">上传星簇属性 Excel 模板，将批量初始化所有星簇（覆盖现有星簇）</div>
      </div>
      <template #footer>
        <div class="dialog-footer">
          <el-button :icon="Delete" @click="clearImportFile" :disabled="!importFileReady">清空</el-button>
          <el-button @click="importVisible = false">取消</el-button>
          <el-button type="primary" @click="submitImportFile" :loading="importing" :disabled="!importFileReady">上传文件</el-button>
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
  RefreshRight, UploadFilled
} from '@element-plus/icons-vue';

export default {
  name: 'ClusterManage',
  components: {
    Search, Refresh, Plus, Download, View, Edit, Delete, RefreshRight, UploadFilled
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
      allClusters: [],
      
      // Excel 批量导入相关
      importVisible: false,
      importFile: null,
      importFileReady: false,
      importing: false,
      
      // 详情相关
      detailVisible: false,
      currentCluster: null
    };
  },
  computed: {
    // 新星簇下拉选项：排除原星簇与不可用星簇，且要求与原星簇轨道或载荷类型适配（避免非法任务迁移）
    availableClusters() {
      const oldName = this.replanForm.oldCluster;
      const old = this.allClusters.find(c => c.name === oldName);
      // 载荷类型集合（格式 "SAR:0.5,1|optical:0.5" → ['SAR','optical']）
      const payloadTypes = (c) => String(c.payload_resolution || '').split('|').map(p => p.split(':')[0]).filter(Boolean);
      // 轨道ID集合（格式 "1,2"）
      const orbitIds = (c) => String(c.orbits || '').split(',').filter(Boolean);
      return this.allClusters.filter(c => {
        if (c.name === oldName) return false;   // 排除原星簇
        if (c.status === false) return false;   // 排除不可用星簇
        if (!old) return true;
        // 与原星簇有共同轨道或共同载荷类型才允许作为迁移目标
        return orbitIds(c).some(o => orbitIds(old).includes(o)) ||
               payloadTypes(c).some(p => payloadTypes(old).includes(p));
      });
    }
  },
  created() {
    this.getList();
    this.loadOrbits();
    this.loadAllClusters();
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
      // 重置载荷选项，避免上一次编辑/新增残留的勾选状态污染表单
      for (const key in this.payloadOptions) {
        this.payloadOptions[key].selected = false;
        this.payloadOptions[key].resolutions = [];
      }
      this.clusterForm = {
        id: row.id,
        name: row.name,
        orbits: [],  // 需要从row.orbit解析
        payload_resolution: {}
      };
      
      // 解析轨道：优先使用后端返回的纯轨道ID列表，兼容旧的文本解析
      if (Array.isArray(row.orbit_ids) && row.orbit_ids.length > 0) {
        this.clusterForm.orbits = [...row.orbit_ids];
      } else if (row.orbit) {
        // 后端返回的轨道格式如 "1,2,3" 或 "[1, 2, 3]"，提取数字作为轨道ID
        const orbitStr = String(row.orbit).replace(/[\[\]\{\}]/g, '').trim();
        this.clusterForm.orbits = orbitStr.split(',')
          .map(s => parseInt(s.trim()))
          .filter(n => !isNaN(n));
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
      
      // 编辑回填后主动加载所选轨道对应的分辨率选项（原仅在手动改选轨道时触发）
      if (this.clusterForm.orbits.length > 0) {
        this.onOrbitChange(this.clusterForm.orbits);
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
    
    // 加载全量星簇列表（用于重规划下拉框）
    async loadAllClusters() {
      try {
        const res = await this.$request.get('/clusters/getAllClustersNames');
        this.allClusters = Array.isArray(res.data) ? res.data : [];
      } catch (err) {
        console.error('加载星簇列表失败:', err);
        this.allClusters = [];
      }
    },
    
    // 显示重规划弹窗
    showReplanDialog(row) {
      this.replanForm.oldCluster = row.name;
      this.replanForm.newCluster = '';
      // 实时从后端同步全量星簇列表
      this.loadAllClusters();
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
        ElMessage.error('重规划失败: ' + ((err.response && err.response.data && err.response.data.message) || err.message || '未知错误'));
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
    
    // 显示 Excel 批量导入弹窗
    showImportDialog() {
      this.importFile = null;
      this.importFileReady = false;
      this.importVisible = true;
    },
    
    // 选择导入文件
    handleImportFileChange(file, fileList) {
      const fileName = file.name.toLowerCase();
      if (!fileName.endsWith('.xlsx')) {
        ElMessage.error('文件格式不支持，请上传 XLSX 格式的 Excel 模板');
        this.$refs.importUploadRef.clearFiles();
        this.importFile = null;
        this.importFileReady = false;
        return;
      }
      
      const maxSize = 10 * 1024 * 1024;
      if (file.size > maxSize) {
        ElMessage.error('文件大小不能超过 10MB');
        this.$refs.importUploadRef.clearFiles();
        this.importFile = null;
        this.importFileReady = false;
        return;
      }
      
      if (fileList.length > 1) {
        fileList.splice(0, 1);
      }
      
      this.importFile = file.raw;
      this.importFileReady = true;
      ElMessage.success(`已选择文件: ${file.name}`);
    },
    
    // 移除导入文件
    onImportRemove() {
      this.importFile = null;
      this.importFileReady = false;
    },
    
    // 清空导入文件
    clearImportFile() {
      this.$refs.importUploadRef.clearFiles();
      this.importFile = null;
      this.importFileReady = false;
    },
    
    // 上传星簇 Excel 文件
    async submitImportFile() {
      if (!this.importFile) {
        ElMessage.warning('请先选择文件');
        return;
      }
      
      const formData = new FormData();
      formData.append('file', this.importFile);
      
      this.importing = true;
      try {
        await this.$request.post('/clusters/submitClusterFile', formData, {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        });
        ElMessage.success('星簇 Excel 批量导入成功');
        this.importVisible = false;
        this.importFile = null;
        this.importFileReady = false;
        this.getList();
        this.loadAllClusters();
      } catch (err) {
        const errorMsg = err.response?.data?.error || err.response?.data?.message || err.message || '未知错误';
        ElMessage.error('批量导入失败: ' + errorMsg);
      } finally {
        this.importing = false;
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

/* Excel 批量导入 */
.upload-zone-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 24px 0;
  background: #fafafa;
  border-radius: 8px;
  border: 1px dashed #d9d9d9;
}

.import-uploader {
  width: 100%;
}

:deep(.import-uploader .el-upload) {
  width: 100%;
}

:deep(.import-uploader .el-upload-dragger) {
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
