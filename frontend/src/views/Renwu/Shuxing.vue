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
            <el-option label="广域目标" value="广域目标" />
            <el-option label="移动目标" value="移动目标" />
            <el-option label="静态观测" value="静态观测" />
            <el-option label="周期观测" value="周期观测" />
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
          <el-button type="primary" plain :icon="Download" @click="exportAllTasks">导出当前列表</el-button>
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
          <!-- 加载中显示骨架屏，比转圈更贴近表格结构、减少视觉跳变 -->
          <div v-if="loading" class="table-skeleton">
            <el-skeleton :rows="8" animated />
          </div>
          <el-table
            v-else
            ref="taskTable"
            :data="tableData"
            stripe
            max-height="500"
            @selection-change="handleSelectionChange"
            row-key="id"
          >
            <el-table-column type="selection" width="55" reserve-selection />
            <el-table-column prop="id" label="ID" width="60" />
            <el-table-column prop="task_name" label="任务名称" width="140" show-overflow-tooltip />
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
            <el-table-column prop="sensorType" label="载荷" width="80" />
            <el-table-column prop="resolution" label="分辨率(m)" width="90" />
            <el-table-column prop="assignedSatelliteName" label="分配卫星" width="110" />
            <el-table-column prop="clusterName" label="指定星簇" width="100" />
            <el-table-column label="合并任务ID" width="100">
              <template #default="scope">
                <span>{{ scope.row.friendTask && scope.row.friendTask !== 'None' ? scope.row.friendTask : '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="90">
              <template #default="scope">
                <el-tag size="small" :type="getStatusType(scope.row.status)">
                  {{ scope.row.status === 'Success' ? '成功' : scope.row.status }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="startTime" label="开始时间" width="160" />
            <el-table-column prop="endTime" label="结束时间" width="160" />
            <el-table-column label="定时时间" width="160">
              <template #default="scope">
                <span>{{ scope.row.appointTime && scope.row.appointTime !== 'None' ? scope.row.appointTime : '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="targetLocation" label="区域信息" width="180" show-overflow-tooltip />
            <el-table-column label="操作" width="380" fixed="right">
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
                  v-if="scope.row.status === '执行中' || scope.row.status === '运行中' || scope.row.status === '正在执行'" 
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
                <el-button link type="primary" :icon="Edit" @click="showEditDialog(scope.row)">编辑</el-button>
                <el-button link type="success" :icon="Download" @click="exportTask(scope.row)">导出</el-button>
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
          <el-table :data="oldTaskData" stripe v-loading="loading" max-height="500">
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

    <!-- 新增/编辑任务弹窗 -->
    <el-dialog v-model="addDialogVisible" :title="editingTaskId ? '编辑任务' : '新增任务'" width="600px" destroy-on-close @closed="handleDialogClosed">
      <el-form :model="taskForm" label-width="120px" :rules="taskRules" ref="taskFormRef">
        <el-form-item label="任务名称" prop="taskName">
          <el-input v-model="taskForm.taskName" placeholder="请输入任务名称" />
        </el-form-item>
        <el-form-item label="任务类型" prop="taskType">
          <el-select v-model="taskForm.taskType" placeholder="请选择任务类型" style="width: 100%" @change="handleTaskTypeChange">
            <el-option label="点目标" value="点目标" />
            <el-option label="区域目标" value="区域目标" />
            <el-option label="广域目标" value="广域目标" />
            <el-option label="移动目标" value="移动目标" />
            <el-option label="静态观测" value="静态观测" />
            <el-option label="周期观测" value="周期观测" />
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
            <el-option v-for="opt in filteredSensorOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="分辨率要求">
          <el-select v-if="resolutionOptions.length" v-model="taskForm.resolution" placeholder="请选择分辨率" style="width: 100%">
            <el-option v-for="r in resolutionOptions" :key="r" :label="r + ' m'" :value="Number(r)" />
          </el-select>
          <el-input-number v-else v-model="taskForm.resolution" :min="0.1" :max="100" :step="0.1" style="width: 100%" />
        </el-form-item>
        <el-form-item label="时间范围">
          <el-date-picker
            v-model="taskForm.dateRange"
            type="datetimerange"
            start-placeholder="开始时间"
            end-placeholder="结束时间"
            value-format="YYYY-MM-DD HH:mm:ss"
            format="YYYY-MM-DD HH:mm:ss"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item v-if="!isAreaTaskType" label="目标位置">
          <el-input v-model="taskForm.targetLocation" placeholder="格式: [纬度, 经度]" />
        </el-form-item>
        <el-form-item v-else label="区域坐标点">
          <div class="area-points">
            <div v-for="(point, index) in taskForm.areaPoints" :key="index" class="area-point-row">
              <el-input v-model="taskForm.areaPoints[index]" placeholder="格式: 纬度, 经度" />
              <el-button link type="danger" :icon="Delete" :disabled="taskForm.areaPoints.length <= 1" @click="removeAreaPoint(index)" />
            </div>
            <el-button link type="primary" :icon="Plus" @click="addAreaPoint">新增坐标点</el-button>
          </div>
        </el-form-item>
        <el-form-item label="指定星簇">
          <el-select v-model="taskForm.clusterName" placeholder="请选择星簇（可选）" clearable style="width: 100%" @change="handleClusterChange">
            <el-option v-for="cluster in clusterList" :key="cluster.id" :label="cluster.name" :value="cluster.name" />
          </el-select>
        </el-form-item>
        <el-form-item label="预约时间">
          <el-date-picker
            v-model="taskForm.appointTime"
            type="datetime"
            placeholder="可选"
            value-format="YYYY-MM-DD HH:mm:ss"
            format="YYYY-MM-DD HH:mm:ss"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="周期(分钟)">
          <el-input-number v-model="taskForm.cycle" :min="1" :max="1440" style="width: 100%" />
        </el-form-item>
        <el-form-item label="云层厚度">
          <el-input-number v-model="taskForm.cloudThickness" :min="0" :max="5000" :step="0.1" style="width: 100%" />
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
  Search, Refresh, Plus, View, Delete, Edit, VideoPlay, VideoPause, Download, CircleClose, Close
} from '@element-plus/icons-vue';

export default {
  name: 'TaskManage',
  components: {
    Search, Refresh, Plus, View, Delete, Edit, VideoPlay, VideoPause, Download, CircleClose, Close
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
      // 新增/编辑任务
      addDialogVisible: false,
      editingTaskId: null,
      clusterDetails: null,
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
        areaPoints: [''],
        clusterName: '',
        dateRange: [],
        appointTime: '',
        cycle: 60,
        cloudThickness: 0
      },
      taskRules: {
        taskName: [{ required: true, message: '请输入任务名称', trigger: 'blur' }],
        taskType: [{ required: true, message: '请选择任务类型', trigger: 'change' }],
        priority: [{ required: true, message: '请设置优先级', trigger: 'change' }],
        sensorType: [{ required: true, message: '请选择载荷类型', trigger: 'change' }]
      },
      clusterList: [],
      // 详情
      detailVisible: false,
      currentTask: null
    };
  },
  computed: {
    // 多坐标点任务类型（区域目标/广域目标显示多坐标点录入，其余显示单坐标）
    isAreaTaskType() {
      return ['区域目标', '广域目标'].includes(this.taskForm.taskType);
    },
    // 载荷类型选项：选择星簇后过滤为该星簇支持的载荷
    filteredSensorOptions() {
      const all = [
        { label: 'SAR', value: 'SAR' },
        { label: '光学', value: 'optical' },
        { label: '红外', value: 'infrared' }
      ];
      const supported = this.clusterDetails?.sensor_type;
      if (this.taskForm.clusterName && Array.isArray(supported) && supported.length) {
        return all.filter(opt => supported.includes(opt.value));
      }
      return all;
    },
    // 分辨率选项：星簇返回了该载荷对应的分辨率列表时下拉选择，否则手动输入
    resolutionOptions() {
      const map = this.clusterDetails?.payload_resolution;
      if (this.taskForm.clusterName && map && this.taskForm.sensorType && Array.isArray(map[this.taskForm.sensorType])) {
        return map[this.taskForm.sensorType];
      }
      return [];
    }
  },
  created() {
    this.getList();
    this.getStats();
    this.loadClusters();
    // 任务列表 5 秒轮询，状态变更即时反馈（文档 3.7.10：表格与后端任务库实时联动）；
    // 弹窗打开时暂停避免干扰编辑；页面在后台标签时同样暂停，回前台立即补刷一次
    this._pollTimer = setInterval(() => {
      if (document.hidden) return;
      if (!this.addDialogVisible && !this.detailVisible) this.getList();
    }, 5000);
    this._onVisibility = () => {
      if (!document.hidden && !this.addDialogVisible && !this.detailVisible) this.getList();
    };
    document.addEventListener('visibilitychange', this._onVisibility);
  },
  beforeUnmount() {
    if (this._pollTimer) { clearInterval(this._pollTimer); this._pollTimer = null; }
    if (this._onVisibility) { document.removeEventListener('visibilitychange', this._onVisibility); this._onVisibility = null; }
  },
  methods: {
    normalizeTask(task = {}, source = 'new') {
      return {
        id: task.id,
        task_name: task.task_name || task.taskName || '',
        type: task.type || task.taskType || '',
        priority: task.priority ?? '',
        is_urgent: task.is_urgent ?? task.isEmergency ?? false,
        isEmergency: task.is_urgent ?? task.isEmergency ?? false,
        payload: task.payload || task.sensorType || '',
        sensorType: task.payload || task.sensorType || '',
        resolution: task.resolution ?? '',
        assignedSatelliteName: task.satellite_name || task.assignedSatelliteName || '',
        satellite_name: task.satellite_name || task.assignedSatelliteName || '',
        clusterName: task.cluster_name || task.clusterName || '',
        cluster_name: task.cluster_name || task.clusterName || '',
        friendTask: task.friend_task ?? task.friendTask ?? '',  // 合并任务ID（合并的友任务id）
        status: task.status || '',
        startTime: task.start_time || task.startTime || '',
        endTime: task.end_time || task.endTime || '',
        appointTime: task.appoint_time || task.appointTime || '',
        targetLocation: task.coordinates || task.targetLocation || '',
        cloudThickness: task.cloud_thickness ?? task.cloudThickness ?? '',
        comment: task.comment || '',
        source,
      };
    },
    // TODO: 后端 /tasks/getNewTasks、/tasks/getOldTasks 暂不支持关键字查询参数，
    // 目前关键字为页内过滤，仅作用于当前页数据，与服务端分页存在矛盾；后端支持后应改为传参查询
    applyKeywordFilter(items) {
      if (!this.search.keyword) return items;
      const keyword = this.search.keyword.trim().toLowerCase();
      return items.filter((item) =>
        [
          item.task_name,
          item.type,
          item.sensorType,
          item.assignedSatelliteName,
          item.clusterName,
          item.status,
          item.targetLocation,
        ].some((field) => String(field || '').toLowerCase().includes(keyword))
      );
    },
    resetTaskForm() {
      this.taskForm = {
        taskName: '',
        taskType: '点目标',
        priority: 5,
        isEmergency: false,
        sensorType: '',
        resolution: 1.0,
        targetLocation: '',
        areaPoints: [''],
        clusterName: '',
        dateRange: [],
        appointTime: '',
        cycle: 60,
        cloudThickness: 0
      };
    },
    // 获取新任务列表
    async getList() {
      this.loading = true;
      try {
        const params = {
          page: this.search.pageNum,
          page_size: this.search.pageSize
        };
        if (this.search.taskType) params.type = [this.search.taskType];
        if (this.search.sensorType) params.payload = [this.search.sensorType];
        if (this.search.status) params.status = [this.search.status];
        const res = await this.$request.post('/tasks/getNewTasks', params);
        const responseData = res.data.data || res.data;
        if (responseData) {
          const items = (responseData.items || responseData || []).map((item) => this.normalizeTask(item, 'new'));
          const filteredItems = this.applyKeywordFilter(items);
          this.tableData = filteredItems.map(item => ({
            ...item,
            isRunning: item.status === '执行中' || item.status === '运行中'
          }));
          this.totalNum = this.search.keyword ? filteredItems.length : (responseData.total || filteredItems.length || 0);
        }
      } catch (err) {
        console.error('获取任务列表失败:', err);
        const errorMessage = err.response?.data?.error || err.response?.data?.message || err.message || '未知错误';
        if (String(errorMessage).includes('未初始化')) {
          ElMessage.warning('系统尚未初始化完成，请先上传 TLE 和卫星参数');
        } else {
          ElMessage.error('获取任务列表失败: ' + errorMessage);
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
        if (this.search.taskType) params.type = [this.search.taskType];
        if (this.search.sensorType) params.payload = [this.search.sensorType];
        if (this.search.status) params.status = [this.search.status];
        const res = await this.$request.post('/tasks/getOldTasks', params);
        const responseData = res.data.data || res.data;
        if (responseData) {
          const items = (responseData.items || responseData || []).map((item) => this.normalizeTask(item, 'old'));
          const filteredItems = this.applyKeywordFilter(items);
          this.oldTaskData = filteredItems;
          this.totalNum = this.search.keyword ? filteredItems.length : (responseData.total || filteredItems.length || 0);
        }
      } catch (err) {
        console.error('获取历史任务失败:', err);
        const errorMessage = err.response?.data?.error || err.response?.data?.message || err.message || '未知错误';
        ElMessage.error('获取历史任务失败: ' + errorMessage);
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
        const tasks = (res.data.data || res.data || []).map((task) => this.normalizeTask(task, 'new'));
        if (Array.isArray(tasks)) {
          this.stats.total = tasks.length;
          this.stats.waiting = tasks.filter(t => t.status === '等待执行' || t.status === '等待规划').length;
          this.stats.running = tasks.filter(t => t.status === '执行中' || t.status === '运行中' || t.status === '正在执行').length;
          this.stats.completed = tasks.filter(t => t.status === '已完成' || t.status === '失败' || t.status === 'Success' || t.status === 'Failed').length;
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
      this.search.pageNum = 1;
      // 后端不支持关键字参数，关键字仅过滤当前页，明确提示用户
      if (this.search.keyword && this.search.keyword.trim()) {
        ElMessage.info('关键字搜索仅过滤当前页数据');
      }
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
      this.doSearch();
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
            await this.$request.post(`/tasks/startTask/${task.id}`);
            successCount++;
          } catch (err) {
            console.error(`启动任务 ${task.id} 失败:`, err);
          }
        }
        ElMessage.success(`成功启动 ${successCount} 个任务`);
        this.clearSelection();
        this.refreshList();
      } catch (err) {
        if (err !== 'cancel') {
          ElMessage.error('批量启动失败');
        }
      }
    },

    // 批量暂停
    async batchPause() {
      if (this.selectedTasks.length === 0) return;
      const runningTasks = this.selectedTasks.filter(t => t.status === '执行中' || t.status === '运行中' || t.status === '正在执行');
      if (runningTasks.length === 0) {
        ElMessage.warning('没有可暂停的任务（请选择执行中或运行中的任务）');
        return;
      }
      try {
        await ElMessageBox.confirm(`确定要暂停选中的 ${runningTasks.length} 个任务吗？`, '提示');
        let successCount = 0;
        for (const task of runningTasks) {
          try {
            await this.$request.post(`/tasks/pauseTask/${task.id}`);
            successCount++;
          } catch (err) {
            console.error(`暂停任务 ${task.id} 失败:`, err);
          }
        }
        ElMessage.success(`成功暂停 ${successCount} 个任务`);
        this.clearSelection();
        this.refreshList();
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
            await this.$request.post(`/tasks/manualEndTask/${task.id}`);
            successCount++;
          } catch (err) {
            console.error(`结束任务 ${task.id} 失败:`, err);
          }
        }
        ElMessage.success(`成功结束 ${successCount} 个任务`);
        this.clearSelection();
        this.refreshList();
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
        const res = await this.$request.post(`/tasks/manualEndTask/${row.id}`);
        if (res.data === 'ok' || res.data?.result === 'ok') {
          ElMessage.success('任务已结束');
          this.refreshList();
        } else {
          ElMessage.error('结束任务失败: ' + (res.data?.error || res.data?.message || '未知错误'));
        }
      } catch (err) {
        if (err !== 'cancel') {
          console.error('结束任务失败:', err);
          ElMessage.error('结束任务失败: ' + (err.response?.data?.error || err.response?.data?.message || err.message || '服务器内部错误'));
        }
      }
    },

    // 显示新增弹窗
    showAddDialog() {
      this.editingTaskId = null;
      this.clusterDetails = null;
      this.resetTaskForm();
      this.addDialogVisible = true;
    },

    // 显示编辑弹窗（回填该行任务数据）
    async showEditDialog(row) {
      this.editingTaskId = row.id;
      this.clusterDetails = null;
      const points = this.parseCoordinates(row.targetLocation);
      const startLocal = this.utcStrToLocal(row.startTime);
      const endLocal = this.utcStrToLocal(row.endTime);
      this.taskForm = {
        taskName: row.task_name || '',
        taskType: row.type || '点目标',
        priority: Number(row.priority) || 5,
        isEmergency: !!row.is_urgent,
        sensorType: '',
        resolution: Number(row.resolution) || 1.0,
        targetLocation: row.type === '区域目标' ? '' : (points[0] || ''),
        areaPoints: row.type === '区域目标' ? (points.length ? points : ['']) : [''],
        clusterName: row.cluster_name || '',
        dateRange: startLocal && endLocal ? [startLocal, endLocal] : [],
        appointTime: this.utcStrToLocal(row.appointTime),
        cycle: 60,
        cloudThickness: Number(row.cloudThickness) || 0
      };
      this.addDialogVisible = true;
      // 先加载星簇载荷信息，再回填载荷类型，避免被联动清空
      if (this.taskForm.clusterName) {
        await this.handleClusterChange(this.taskForm.clusterName);
      }
      this.taskForm.sensorType = row.sensorType || row.payload || '';
    },

    // 弹窗关闭后重置编辑状态
    handleDialogClosed() {
      this.editingTaskId = null;
      this.clusterDetails = null;
    },

    // 任务类型切换：单坐标与多坐标点互相迁移（区域目标/广域目标为多坐标点类型）
    handleTaskTypeChange(type) {
      const isArea = ['区域目标', '广域目标'].includes(type);
      if (isArea && this.taskForm.targetLocation.trim()) {
        this.taskForm.areaPoints = [this.taskForm.targetLocation.trim()];
        this.taskForm.targetLocation = '';
      } else if (!isArea) {
        const first = this.taskForm.areaPoints.find(p => p && p.trim());
        if (first) {
          this.taskForm.targetLocation = first.trim();
        }
        this.taskForm.areaPoints = [''];
      }
    },

    // 新增/删除区域坐标点
    addAreaPoint() {
      this.taskForm.areaPoints.push('');
    },
    removeAreaPoint(index) {
      if (this.taskForm.areaPoints.length <= 1) return;
      this.taskForm.areaPoints.splice(index, 1);
    },

    // 选择星簇后加载星簇详情，联动过滤载荷类型与分辨率
    async handleClusterChange(name) {
      if (!name) {
        this.clusterDetails = null;
        return;
      }
      try {
        const res = await this.$request.get(`/clusters/getClusterDetailsByName/${encodeURIComponent(name)}`);
        const data = res.data?.data || res.data;
        if (data && Array.isArray(data.sensor_type)) {
          this.clusterDetails = data;
          if (this.taskForm.sensorType && !data.sensor_type.includes(this.taskForm.sensorType)) {
            this.taskForm.sensorType = '';
            ElMessage.info('该星簇不支持原载荷类型，请重新选择');
          }
        } else {
          this.clusterDetails = null;
        }
      } catch (err) {
        this.clusterDetails = null;
        const errorMessage = err.response?.data?.message || err.message || '未知错误';
        ElMessage.warning('获取星簇载荷信息失败: ' + errorMessage);
      }
    },

    // 解析后端返回的坐标字符串为坐标点数组，兼容 "(30.0, 120.0)" 和 "[(30.0, 120.0), (31.0, 121.0)]"
    parseCoordinates(str) {
      if (!str) return [];
      const matches = String(str).match(/-?\d+(?:\.\d+)?\s*,\s*-?\d+(?:\.\d+)?/g) || [];
      return matches.map(m => m.split(',').map(s => s.trim()).join(', '));
    },

    // 后端存储时间为 UTC，编辑回填时转为本地时间字符串
    utcStrToLocal(str) {
      if (!str || str === 'None') return '';
      const d = new Date(String(str).trim().replace(' ', 'T') + 'Z');
      if (isNaN(d.getTime())) return '';
      const pad = n => String(n).padStart(2, '0');
      return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
    },

    // 提交任务（新增或编辑）
    async submitTask() {
      const valid = await this.$refs.taskFormRef.validate().catch(() => false);
      if (!valid) return;

      let coordinates;
      if (this.taskForm.taskType === '区域目标') {
        coordinates = this.taskForm.areaPoints.map(p => (p || '').trim()).filter(Boolean);
        if (!coordinates.length) {
          ElMessage.warning('请至少添加一个区域坐标点');
          return;
        }
      } else {
        if (!this.taskForm.targetLocation || !this.taskForm.targetLocation.trim()) {
          ElMessage.warning('请输入目标位置');
          return;
        }
        coordinates = [this.taskForm.targetLocation.trim()];
      }

      this.submitting = true;
      try {
        const payload = {
          task_name: this.taskForm.taskName,
          priority: this.taskForm.priority,
          is_urgent: this.taskForm.isEmergency ? '是' : '否',
          type: this.taskForm.taskType,
          payload: this.taskForm.sensorType,
          resolution: this.taskForm.resolution,
          timeRanges: [
            this.taskForm.dateRange?.length === 2
              ? `${this.taskForm.dateRange[0]},${this.taskForm.dateRange[1]}`
              : ''
          ],
          cycle: String(this.taskForm.cycle || 60),
          cloud_thickness: String(this.taskForm.cloudThickness ?? 0),
          cluster_name: this.taskForm.clusterName || '',
          appoint_time: this.taskForm.appointTime || '',
          coordinates
        };
        if (this.editingTaskId) {
          const res = await this.$request.post(`/tasks/updateTask/${this.editingTaskId}`, payload);
          ElMessage.success(res.data?.meta?.message || '任务更新成功');
        } else {
          await this.$request.post('/tasks/addSingleTask', payload);
          ElMessage.success('任务添加成功');
        }
        this.addDialogVisible = false;
        this.refreshList();
      } catch (err) {
        const errorMessage = err.response?.data?.meta?.message || err.response?.data?.error || err.response?.data?.message || err.message || '未知错误';
        ElMessage.error((this.editingTaskId ? '编辑失败: ' : '添加失败: ') + errorMessage);
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
          await this.$request.post(`/tasks/startTask/${row.id}`);
          row.status = '执行中';
          ElMessage.success('任务已启动');
        } else {
          // 切换到暂停状态
          await this.$request.post(`/tasks/pauseTask/${row.id}`);
          row.status = '暂停';
          ElMessage.success('任务已暂停');
        }
        this.refreshList();
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
        const res = await this.$request.post(`/tasks/startTask/${row.id}`);
        // 处理不同的响应格式
        const responseData = res.data;
        if (responseData && (responseData.result === 'ok' || responseData.result === 'success')) {
          row.status = '执行中';
          row.isRunning = true;
          ElMessage.success('任务已启动');
          this.refreshList();
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
        const res = await this.$request.post(`/tasks/pauseTask/${row.id}`);
        // 处理不同的响应格式
        const responseData = res.data;
        if (responseData && (responseData.result === 'ok' || responseData.result === 'success')) {
          row.status = '暂停';
          row.isRunning = false;
          ElMessage.success('任务已暂停');
          this.refreshList();
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
        await this.$request.delete(`/tasks/deleteTask/${id}`);
        ElMessage.success('任务删除成功');
        this.refreshList();
      } catch (err) {
        const errorMessage = err.response?.data?.error || err.response?.data?.message || err.message || '未知错误';
        ElMessage.error('删除失败: ' + errorMessage);
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
        const isOldTask = row.source === 'old' || this.activeTab === 'old';
        const url = isOldTask ? `/tasks/exportOldTask/${row.id}` : `/tasks/exportTask/${row.id}`;
        const res = await this.$request.get(url, { responseType: 'blob' });
        this.downloadBlob(res.data, `${row.task_name || 'task'}_${row.id}.xlsx`);
        ElMessage.success('导出成功');
      } catch (err) {
        const errorMessage = err.response?.data?.error || err.response?.data?.message || err.message || '未知错误';
        ElMessage.error('导出失败: ' + errorMessage);
      }
    },
    async exportAllTasks() {
      try {
        const url = this.activeTab === 'new' ? '/tasks/exportAllNewTasks' : '/tasks/exportAllOldTasks';
        const fileName = this.activeTab === 'new' ? '未完成任务列表.xlsx' : '已完成任务列表.xlsx';
        const res = await this.$request.get(url, { responseType: 'blob' });
        this.downloadBlob(res.data, fileName);
        ElMessage.success('导出成功');
      } catch (err) {
        const errorMessage = err.response?.data?.error || err.response?.data?.message || err.message || '未知错误';
        ElMessage.error('导出失败: ' + errorMessage);
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
        'Success': 'success',
        'Failed': 'danger'
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

/* 区域目标多坐标点 */
.area-points {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.area-point-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.area-point-row .el-input {
  flex: 1;
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  padding-top: 16px;
  border-top: 1px solid rgba(0, 220, 255, 0.12);
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
