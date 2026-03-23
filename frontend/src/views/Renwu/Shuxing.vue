<template>
  <div class="task-manage">
    <!-- 搜索工具栏 -->
    <el-card shadow="never" class="search-card">
      <div class="search-bar">
        <div class="search-left">
          <el-input
            v-model="search.keyword"
            placeholder="请输入任务名称搜索"
            clearable
            style="width: 200px"
            @keyup.enter="handleSearch"
            @clear="handleSearch"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
          <el-select v-model="search.taskType" placeholder="任务类型" clearable style="width: 140px" @change="handleSearch">
            <el-option label="点目标" value="点目标" />
            <el-option label="区域目标" value="区域目标" />
            <el-option label="移动目标" value="移动目标" />
          </el-select>
          <el-select v-model="search.sensorType" placeholder="载荷类型" clearable style="width: 120px" @change="handleSearch">
            <el-option label="SAR" value="SAR" />
            <el-option label="光学" value="optical" />
            <el-option label="红外" value="infrared" />
          </el-select>
          <el-select v-model="search.status" placeholder="任务状态" clearable style="width: 120px" @change="handleSearch">
            <el-option label="等待执行" value="等待执行" />
            <el-option label="执行中" value="执行中" />
            <el-option label="暂停" value="暂停" />
            <el-option label="已完成" value="已完成" />
          </el-select>
          <el-button type="primary" @click.stop="handleSearch">
            <el-icon style="margin-right: 4px"><Search /></el-icon>搜索
          </el-button>
          <el-button @click="resetSearch">
            <el-icon style="margin-right: 4px"><Refresh /></el-icon>重置
          </el-button>
        </div>
        <div class="search-right">
          <el-button type="success" :icon="Plus" @click="showAddDialog">新增任务</el-button>
          <el-button :icon="Refresh" circle title="刷新" @click="refreshList" :loading="loading" />
        </div>
      </div>
    </el-card>

    <!-- 批量操作工具栏 -->
    <el-card shadow="never" class="toolbar-card" v-if="selectedTasks.length > 0">
      <div class="batch-toolbar">
        <span class="batch-text">已选择 <strong>{{ selectedTasks.length }}</strong> 个任务</span>
        <el-button-group>
          <el-button type="success" size="small" :icon="VideoPlay" @click="batchStart">批量启动</el-button>
          <el-button type="warning" size="small" :icon="VideoPause" @click="batchPause">批量暂停</el-button>
          <el-button type="danger" size="small" :icon="CircleClose" @click="batchEnd">批量结束</el-button>
        </el-button-group>
        <el-button link type="danger" size="small" :icon="Close" @click="clearSelection">清空选择</el-button>
      </div>
    </el-card>

    <!-- 统计卡片 -->
    <el-row :gutter="16" class="stats-row">
      <el-col :xs="12" :sm="6">
        <el-card shadow="never" class="stat-card">
          <div class="stat-value">{{ stats.total }}</div>
          <div class="stat-label">总任务数</div>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="6">
        <el-card shadow="never" class="stat-card stat-waiting">
          <div class="stat-value">{{ stats.waiting }}</div>
          <div class="stat-label">等待执行</div>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="6">
        <el-card shadow="never" class="stat-card stat-running">
          <div class="stat-value">{{ stats.running }}</div>
          <div class="stat-label">执行中</div>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="6">
        <el-card shadow="never" class="stat-card stat-completed">
          <div class="stat-value">{{ stats.completed }}</div>
          <div class="stat-label">已完成</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 任务表格 -->
    <el-card shadow="never" class="table-card">
      <el-tabs v-model="activeTab" @tab-change="handleTabChange">
        <el-tab-pane label="待执行任务" name="new">
          <el-table 
            ref="taskTable"
            :data="tableData" 
            stripe 
            v-loading="loading" 
            height="500"
            @selection-change="handleSelectionChange"
            row-key="id"
          >
            <el-table-column type="selection" width="55" reserve-selection />
            <el-table-column prop="id" label="ID" width="60" />
            <el-table-column prop="task_name" label="任务名称" width="150" show-overflow-tooltip />
            <el-table-column prop="type" label="任务类型" width="100">
              <template #default="scope">
                <el-tag size="small" :type="getTaskTypeType(scope.row.type)">
                  {{ scope.row.type }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="priority" label="优先级" width="80" sortable />
            <el-table-column prop="isEmergency" label="紧急" width="70">
              <template #default="scope">
                <el-tag v-if="scope.row.isEmergency" size="small" type="danger">是</el-tag>
                <span v-else>-</span>
              </template>
            </el-table-column>
            <el-table-column prop="sensorType" label="载荷" width="90" />
            <el-table-column prop="resolution" label="分辨率(m)" width="100" />
            <el-table-column prop="assignedSatelliteName" label="分配卫星" width="120" />
            <el-table-column prop="clusterName" label="指定星簇" width="120" />
            <el-table-column prop="status" label="状态" width="100">
              <template #default="scope">
                <el-tag size="small" :type="getStatusType(scope.row.status)">
                  {{ scope.row.status === 'Success' ? '成功' : scope.row.status }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="startTime" label="开始时间" width="160" />
            <el-table-column label="操作" width="280" fixed="right">
              <template #default="scope">
                <el-button link type="primary" :icon="View" @click="showDetail(scope.row)">详情</el-button>
                <!-- 启动/暂停按钮 -->
                <el-button 
                  v-if="scope.row.status === '暂停'" 
                  link 
                  type="success" 
                  :icon="VideoPlay" 
                  @click="startTask(scope.row)"
                >启动</el-button>
                <el-button 
                  v-if="scope.row.status === '执行中' || scope.row.status === '运行中'" 
                  link 
                  type="warning" 
                  :icon="VideoPause" 
                  @click="pauseTask(scope.row)"
                >暂停</el-button>
                <el-button 
                  v-if="scope.row.status !== '已完成' && scope.row.status !== '失败'"
                  link 
                  type="danger" 
                  :icon="CircleClose" 
                  @click="endTask(scope.row)"
                >结束</el-button>
                <el-popconfirm title="确定要删除该任务吗?" @confirm="deleteTask(scope.row.id)">
                  <template #reference>
                    <el-button link type="danger" :icon="Delete">删除</el-button>
                  </template>
                </el-popconfirm>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="历史任务" name="old">
          <el-table :data="oldTaskData" stripe v-loading="loading" height="500">
            <el-table-column prop="id" label="ID" width="60" />
            <el-table-column prop="task_name" label="任务名称" width="150" show-overflow-tooltip />
            <el-table-column prop="type" label="任务类型" width="100">
              <template #default="scope">
                <el-tag size="small" :type="getTaskTypeType(scope.row.type)">
                  {{ scope.row.type }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="priority" label="优先级" width="80" />
            <el-table-column prop="satellite_name" label="执行卫星" width="120" />
            <el-table-column prop="status" label="执行结果" width="100">
              <template #default="scope">
                <el-tag size="small" :type="scope.row.status === 'Success' ? 'success' : 'danger'">
                  {{ scope.row.status === 'Success' ? '成功' : '失败' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="startTime" label="开始时间" width="160" />
            <el-table-column prop="endTime" label="结束时间" width="160" />
            <el-table-column label="操作" width="150" fixed="right">
              <template #default="scope">
                <el-button link type="primary" :icon="View" @click="showOldDetail(scope.row)">详情</el-button>
                <el-button link type="success" :icon="Download" @click="exportTask(scope.row)">导出</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>

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

    <!-- 新增任务弹窗 -->
    <el-dialog v-model="addDialogVisible" title="新增任务" width="600px" destroy-on-close>
      <el-form :model="taskForm" label-width="120px" :rules="taskRules" ref="taskFormRef">
        <el-form-item label="任务名称" prop="taskName">
          <el-input v-model="taskForm.taskName" placeholder="请输入任务名称" />
        </el-form-item>
        <el-form-item label="任务类型" prop="taskType">
          <el-select v-model="taskForm.taskType" placeholder="请选择任务类型" style="width: 100%">
            <el-option label="点目标" value="点目标" />
            <el-option label="区域目标" value="区域目标" />
            <el-option label="移动目标" value="移动目标" />
          </el-select>
        </el-form-item>
        <el-form-item label="优先级" prop="priority">
          <el-input-number v-model="taskForm.priority" :min="1" :max="10" style="width: 100%" />
        </el-form-item>
        <el-form-item label="是否紧急">
          <el-switch v-model="taskForm.isEmergency" active-text="是" inactive-text="否" />
        </el-form-item>
        <el-form-item label="载荷类型" prop="sensorType">
          <el-select v-model="taskForm.sensorType" placeholder="请选择载荷类型" style="width: 100%">
            <el-option label="SAR" value="SAR" />
            <el-option label="光学" value="optical" />
            <el-option label="红外" value="infrared" />
          </el-select>
        </el-form-item>
        <el-form-item label="分辨率要求">
          <el-input-number v-model="taskForm.resolution" :min="0.1" :max="100" :step="0.1" style="width: 100%" />
        </el-form-item>
        <el-form-item label="目标位置" prop="targetLocation">
          <el-input v-model="taskForm.targetLocation" placeholder="格式: [纬度, 经度]" />
        </el-form-item>
        <el-form-item label="指定星簇">
          <el-select v-model="taskForm.clusterName" placeholder="请选择星簇（可选）" clearable style="width: 100%">
            <el-option v-for="cluster in clusterList" :key="cluster.id" :label="cluster.name" :value="cluster.name" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitTask" :loading="submitting">提交</el-button>
      </template>
    </el-dialog>

    <!-- 任务详情弹窗 -->
    <el-dialog v-model="detailVisible" title="任务详情" width="700px">
      <el-descriptions :column="2" border v-if="currentTask">
        <el-descriptions-item label="任务ID">{{ currentTask.id }}</el-descriptions-item>
        <el-descriptions-item label="任务名称">{{ currentTask.task_name }}</el-descriptions-item>
        <el-descriptions-item label="任务类型">{{ currentTask.type }}</el-descriptions-item>
        <el-descriptions-item label="优先级">{{ currentTask.priority }}</el-descriptions-item>
        <el-descriptions-item label="是否紧急">{{ currentTask.is_urgent ? '是' : '否' }}</el-descriptions-item>
        <el-descriptions-item label="载荷类型">{{ currentTask.payload }}</el-descriptions-item>
        <el-descriptions-item label="分辨率">{{ currentTask.resolution }} m</el-descriptions-item>
        <el-descriptions-item label="目标位置">{{ currentTask.targetLocation }}</el-descriptions-item>
        <el-descriptions-item label="分配卫星">{{ currentTask.satellite_name || '未分配' }}</el-descriptions-item>
        <el-descriptions-item label="指定星簇">{{ currentTask.cluster_name || '无' }}</el-descriptions-item>
        <el-descriptions-item label="任务状态">
          <el-tag :type="getStatusType(currentTask.status)">{{ currentTask.status }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="开始时间">{{ currentTask.startTime }}</el-descriptions-item>
        <el-descriptions-item label="结束时间">{{ currentTask.endTime || '-' }}</el-descriptions-item>
        <el-descriptions-item label="云层厚度">{{ currentTask.cloudThickness || '-' }}</el-descriptions-item>
        <el-descriptions-item label="备注" :span="2">{{ currentTask.comment || '无' }}</el-descriptions-item>
      </el-descriptions>
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
        <el-button type="primary" :icon="Download" @click="exportCurrentTask">导出</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ElMessage, ElMessageBox } from 'element-plus';
import { 
  Search, Refresh, Plus, View, Delete, VideoPlay, VideoPause, Download, CircleClose, Close
} from '@element-plus/icons-vue';

export default {
  name: 'TaskManage',
  components: {
    Search, Refresh, Plus, View, Delete, VideoPlay, VideoPause, Download, CircleClose, Close
  },
  data() {
    return {
      loading: false,
      activeTab: 'new',
      tableData: [],
      oldTaskData: [],
      totalNum: 0,
      search: {
        pageNum: 1,
        pageSize: 10,
        keyword: '',
        taskType: '',
        sensorType: '',
        status: ''
      },
      stats: {
        total: 0,
        waiting: 0,
        running: 0,
        completed: 0
      },
      // 批量选择
      selectedTasks: [],
      // 新增任务
      addDialogVisible: false,
      submitting: false,
      taskFormRef: null,
      taskForm: {
        taskName: '',
        taskType: '点目标',
        priority: 5,
        isEmergency: false,
        sensorType: '',
        resolution: 1.0,
        targetLocation: '',
        clusterName: ''
      },
      taskRules: {
        taskName: [{ required: true, message: '请输入任务名称', trigger: 'blur' }],
        taskType: [{ required: true, message: '请选择任务类型', trigger: 'change' }],
        priority: [{ required: true, message: '请设置优先级', trigger: 'change' }],
        sensorType: [{ required: true, message: '请选择载荷类型', trigger: 'change' }],
        targetLocation: [{ required: true, message: '请输入目标位置', trigger: 'blur' }]
      },
      clusterList: [],
      // 详情
      detailVisible: false,
      currentTask: null
    };
  },
  created() {
    this.getList();
    this.getStats();
    this.loadClusters();
  },
  methods: {
    // 获取新任务列表
    async getList() {
      this.loading = true;
      try {
        const params = {
          page: this.search.pageNum,
          page_size: this.search.pageSize
        };
        // 只传递有值的搜索参数（后端期望数组格式）
        if (this.search.keyword) params.task_name = this.search.keyword;
        if (this.search.taskType) params.type = [this.search.taskType];
        if (this.search.sensorType) params.payload = [this.search.sensorType];
        if (this.search.status) params.status = [this.search.status];
        console.log('搜索参数:', params);
        const res = await this.$request.post('/tasks/getNewTasks', params);
        // 处理后端返回的数据结构 { status: 'success', data: { items: [...], total: ... } }
        const responseData = res.data.data || res.data;
        if (responseData) {
          const items = responseData.items || responseData || [];
          // 添加 isRunning 属性用于开关绑定
          this.tableData = items.map(item => ({
            ...item,
            isRunning: item.status === '执行中' || item.status === '运行中'
          }));
          this.totalNum = responseData.total || responseData.length || 0;
        }
      } catch (err) {
        console.error('获取任务列表失败:', err);
        if (err.response?.status !== 503) {
          ElMessage.error('获取任务列表失败: ' + (err.message || '未知错误'));
        }
        this.tableData = [];
        this.totalNum = 0;
      } finally {
        this.loading = false;
      }
    },

    // 获取历史任务
    async getOldTasks() {
      this.loading = true;
      try {
        const params = {
          page: this.search.pageNum,
          page_size: this.search.pageSize
        };
        // 只传递有值的搜索参数（后端期望数组格式）
        if (this.search.keyword) params.task_name = this.search.keyword;
        if (this.search.taskType) params.type = [this.search.taskType];
        if (this.search.sensorType) params.payload = [this.search.sensorType];
        if (this.search.status) params.status = [this.search.status];
        const res = await this.$request.post('/tasks/getOldTasks', params);
        // 处理后端返回的数据结构
        const responseData = res.data.data || res.data;
        if (responseData) {
          this.oldTaskData = responseData.items || responseData || [];
          this.totalNum = responseData.total || responseData.length || 0;
        }
      } catch (err) {
        console.error('获取历史任务失败:', err);
        this.oldTaskData = [];
        this.totalNum = 0;
      } finally {
        this.loading = false;
      }
    },

    // 获取统计数据
    async getStats() {
      try {
        const res = await this.$request.get('/tasks/getNewTasksByCondition');
        // 处理后端返回的数据结构
        const tasks = res.data.data || res.data || [];
        if (Array.isArray(tasks)) {
          this.stats.total = tasks.length;
          this.stats.waiting = tasks.filter(t => t.status === '等待执行' || t.status === '等待规划').length;
          this.stats.running = tasks.filter(t => t.status === '执行中' || t.status === '运行中').length;
          this.stats.completed = tasks.filter(t => t.status === '已完成' || t.status === '失败' || t.status === 'Success').length;
        }
      } catch (err) {
        console.error('获取统计数据失败:', err);
      }
    },

    // 加载星簇列表
    async loadClusters() {
      try {
        const res = await this.$request.get('/clusters/getAllClustersNames');
        // 处理后端返回的数据结构
        this.clusterList = res.data.data || res.data || [];
      } catch (err) {
        console.error('加载星簇列表失败:', err);
      }
    },

    // Tab切换
    handleTabChange(tab) {
      this.search.pageNum = 1;
      if (tab === 'new') {
        this.getList();
      } else {
        this.getOldTasks();
      }
    },

    // 搜索（重置页码）
    handleSearch(e) {
      if (e) e.preventDefault();
      console.log('搜索关键词:', this.search.keyword, '事件触发');
      this.search.pageNum = 1;
      this.doSearch();
    },

    // 执行搜索（不重置页码，用于分页）
    doSearch() {
      if (this.activeTab === 'new') {
        this.getList();
      } else {
        this.getOldTasks();
      }
    },

    // 重置搜索
    resetSearch() {
      this.search = {
        pageNum: 1,
        pageSize: 10,
        keyword: '',
        taskType: '',
        sensorType: '',
        status: ''
      };
      this.handleSearch();
    },

    // 刷新
    refreshList() {
      this.getList();
      this.getStats();
    },

    // 分页
    handleSizeChange(val) {
      this.search.pageSize = val;
      this.search.pageNum = 1;
      this.doSearch();
    },
    handleCurrentChange(val) {
      this.search.pageNum = val;
      this.doSearch();
    },

    // 选择变化
    handleSelectionChange(selection) {
      this.selectedTasks = selection;
    },

    // 清空选择
    clearSelection() {
      this.selectedTasks = [];
      this.$refs.taskTable?.clearSelection();
    },

    // 批量启动
    async batchStart() {
      if (this.selectedTasks.length === 0) return;
      const waitingTasks = this.selectedTasks.filter(t => t.status === '暂停');
      if (waitingTasks.length === 0) {
        ElMessage.warning('没有可启动的任务（只有暂停状态的任务才能启动）');
        return;
      }
      try {
        await ElMessageBox.confirm(`确定要启动选中的 ${waitingTasks.length} 个任务吗？`, '提示');
        let successCount = 0;
        for (const task of waitingTasks) {
          try {
            await this.$request.get(`/tasks/startTask/${task.id}`);
            successCount++;
          } catch (err) {
            console.error(`启动任务 ${task.id} 失败:`, err);
          }
        }
        ElMessage.success(`成功启动 ${successCount} 个任务`);
        this.clearSelection();
        this.getList();
        this.getStats();
      } catch (err) {
        if (err !== 'cancel') {
          ElMessage.error('批量启动失败');
        }
      }
    },

    // 批量暂停
    async batchPause() {
      if (this.selectedTasks.length === 0) return;
      const runningTasks = this.selectedTasks.filter(t => t.status === '执行中' || t.status === '运行中');
      if (runningTasks.length === 0) {
        ElMessage.warning('没有可暂停的任务（请选择执行中或运行中的任务）');
        return;
      }
      try {
        await ElMessageBox.confirm(`确定要暂停选中的 ${runningTasks.length} 个任务吗？`, '提示');
        let successCount = 0;
        for (const task of runningTasks) {
          try {
            await this.$request.get(`/tasks/pauseTask/${task.id}`);
            successCount++;
          } catch (err) {
            console.error(`暂停任务 ${task.id} 失败:`, err);
          }
        }
        ElMessage.success(`成功暂停 ${successCount} 个任务`);
        this.clearSelection();
        this.getList();
        this.getStats();
      } catch (err) {
        if (err !== 'cancel') {
          ElMessage.error('批量暂停失败');
        }
      }
    },

    // 批量结束
    async batchEnd() {
      if (this.selectedTasks.length === 0) return;
      const activeTasks = this.selectedTasks.filter(t => t.status !== '已完成' && t.status !== '失败');
      if (activeTasks.length === 0) {
        ElMessage.warning('没有可结束的任务');
        return;
      }
      try {
        await ElMessageBox.confirm(`确定要结束选中的 ${activeTasks.length} 个任务吗？`, '提示', { type: 'warning' });
        let successCount = 0;
        for (const task of activeTasks) {
          try {
            await this.$request.get(`/tasks/manualEndTask/${task.id}`);
            successCount++;
          } catch (err) {
            console.error(`结束任务 ${task.id} 失败:`, err);
          }
        }
        ElMessage.success(`成功结束 ${successCount} 个任务`);
        this.clearSelection();
        this.getList();
        this.getStats();
      } catch (err) {
        if (err !== 'cancel') {
          ElMessage.error('批量结束失败');
        }
      }
    },

    // 结束单个任务
    async endTask(row) {
      try {
        await ElMessageBox.confirm(`确定要结束任务 "${row.task_name || row.id}" 吗？`, '提示', { type: 'warning' });
        const res = await this.$request.get(`/tasks/manualEndTask/${row.id}`);
        if (res.data && res.data.result === 'ok') {
          ElMessage.success('任务已结束');
          this.getList();
          this.getStats();
        } else {
          ElMessage.error('结束任务失败: ' + (res.data?.message || '未知错误'));
        }
      } catch (err) {
        if (err !== 'cancel') {
          console.error('结束任务失败:', err);
          ElMessage.error('结束任务失败: ' + (err.response?.data?.message || err.message || '服务器内部错误'));
        }
      }
    },

    // 显示新增弹窗
    showAddDialog() {
      this.taskForm = {
        taskName: '',
        taskType: '点目标',
        priority: 5,
        isEmergency: false,
        sensorType: '',
        resolution: 1.0,
        targetLocation: '',
        clusterName: ''
      };
      this.addDialogVisible = true;
    },

    // 提交任务
    async submitTask() {
      const valid = await this.$refs.taskFormRef.validate().catch(() => false);
      if (!valid) return;

      this.submitting = true;
      try {
        await this.$request.post('/tasks/addSingleTask', this.taskForm);
        ElMessage.success('任务添加成功');
        this.addDialogVisible = false;
        this.getList();
        this.getStats();
      } catch (err) {
        ElMessage.error('添加失败: ' + (err.message || '未知错误'));
      } finally {
        this.submitting = false;
      }
    },

    // 处理状态开关变化
    async handleTaskStatusChange(row, val) {
      const originalStatus = row.status;
      try {
        if (val) {
          // 切换到运行状态
          await this.$request.get(`/tasks/startTask/${row.id}`);
          row.status = '执行中';
          ElMessage.success('任务已启动');
        } else {
          // 切换到暂停状态
          await this.$request.get(`/tasks/pauseTask/${row.id}`);
          row.status = '暂停';
          ElMessage.success('任务已暂停');
        }
        this.getStats();
      } catch (err) {
        // 恢复状态
        row.isRunning = !val;
        row.status = originalStatus;
        ElMessage.error('操作失败: ' + (err.message || '未知错误'));
      }
    },

    // 开始任务（按钮方式）
    async startTask(row) {
      try {
        const res = await this.$request.get(`/tasks/startTask/${row.id}`);
        // 处理不同的响应格式
        const responseData = res.data;
        if (responseData && (responseData.result === 'ok' || responseData.result === 'success')) {
          row.status = '执行中';
          row.isRunning = true;
          ElMessage.success('任务已启动');
          this.getStats();
        } else if (responseData && responseData.error) {
          ElMessage.error('启动失败: ' + responseData.error);
        } else {
          ElMessage.error('启动失败: 未知错误');
        }
      } catch (err) {
        console.error('启动任务失败:', err);
        const errorMsg = err.response?.data?.error || err.response?.data?.message || err.message || '服务器内部错误';
        ElMessage.error('启动失败: ' + errorMsg);
      }
    },

    // 暂停任务（按钮方式）
    async pauseTask(row) {
      try {
        const res = await this.$request.get(`/tasks/pauseTask/${row.id}`);
        // 处理不同的响应格式
        const responseData = res.data;
        if (responseData && (responseData.result === 'ok' || responseData.result === 'success')) {
          row.status = '暂停';
          row.isRunning = false;
          ElMessage.success('任务已暂停');
          this.getStats();
        } else if (responseData && responseData.error) {
          ElMessage.error('暂停失败: ' + responseData.error);
        } else {
          ElMessage.error('暂停失败: 未知错误');
        }
      } catch (err) {
        console.error('暂停任务失败:', err);
        const errorMsg = err.response?.data?.error || err.response?.data?.message || err.message || '服务器内部错误';
        ElMessage.error('暂停失败: ' + errorMsg);
      }
    },

    // 删除任务
    async deleteTask(id) {
      try {
        await this.$request.delete(`/tasks/deleteTaskById/${id}`);
        ElMessage.success('任务删除成功');
        this.getList();
        this.getStats();
      } catch (err) {
        ElMessage.error('删除失败');
      }
    },

    // 显示详情
    showDetail(row) {
      this.currentTask = row;
      this.detailVisible = true;
    },

    // 显示历史任务详情
    showOldDetail(row) {
      this.currentTask = row;
      this.detailVisible = true;
    },

    // 导出任务
    async exportTask(row) {
      try {
        const url = this.activeTab === 'new' 
          ? `/tasks/exportTask/${row.id}`
          : `/tasks/exportOldTask/${row.id}`;
        const res = await this.$request.get(url, { responseType: 'blob' });
        this.downloadBlob(res.data, `${row.task_name || 'task'}_${row.id}.xlsx`);
        ElMessage.success('导出成功');
      } catch (err) {
        ElMessage.error('导出失败');
      }
    },

    // 导出当前任务
    async exportCurrentTask() {
      if (this.currentTask) {
        await this.exportTask(this.currentTask);
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

    // 获取任务类型样式
    getTaskTypeType(type) {
      const map = {
        '点目标': 'primary',
        '区域目标': 'success',
        '移动目标': 'warning'
      };
      return map[type] || 'info';
    },

    // 获取状态样式
    getStatusType(status) {
      const map = {
        '等待规划': 'info',
        '等待执行': 'info',
        '执行中': 'primary',
        '运行中': 'primary',
        '暂停': 'warning',
        '已完成': 'success',
        '失败': 'danger',
        'Success': 'success'
      };
      return map[status] || 'info';
    }
  }
};
</script>

<style scoped>
.task-manage {
  padding: 0;
}

/* 搜索栏 */
.search-card {
  margin-bottom: 16px;
}

.search-card :deep(.el-card__body) {
  padding: 12px 16px;
}

.search-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

.search-left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  min-width: 0;
  overflow-x: auto;
}

.search-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

/* 统计卡片 */
.stats-row {
  margin-bottom: 16px;
}

.stat-card {
  text-align: center;
  padding: 10px 0;
}

.stat-value {
  font-size: 28px;
  font-weight: 600;
  color: #409EFF;
  margin-bottom: 4px;
}

.stat-label {
  font-size: 13px;
  color: #909399;
}

.stat-waiting .stat-value {
  color: #E6A23C;
}

.stat-running .stat-value {
  color: #409EFF;
}

.stat-completed .stat-value {
  color: #67C23A;
}

/* 批量操作工具栏 */
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
    margin: 0;
  }
}
</style>
