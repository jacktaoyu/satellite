<template>
  <div class="task-manage">
    <!-- 搜索工具栏 -->
    <el-card shadow="never" class="search-card">
      <div class="search-bar">
        <div class="search-left">
          <el-input
            v-model="search.keyword"
            placeholder="任务名称 / 数字ID / 业务UUID"
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
          <el-button type="primary" plain :icon="Download" :disabled="activeTab === 'gantt'" @click="exportAllTasks">导出当前列表</el-button>
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
            <el-table-column prop="resultReceivedAt" label="结果接收时间" width="160" />
            <el-table-column label="操作" width="150" fixed="right">
              <template #default="scope">
                <el-button link type="primary" :icon="View" @click="showOldDetail(scope.row)">详情</el-button>
                <el-button link type="success" :icon="Download" @click="exportTask(scope.row)">导出</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <!-- 任务甘特图：按时间轴展示各任务的起止区间，直观看执行冲突与排布 -->
        <el-tab-pane label="任务甘特图" name="gantt">
          <div class="gantt-toolbar">
            <span class="gantt-tip">展示待执行任务的时间分布（最多 40 条，按开始时间排序）</span>
            <el-button link :icon="Refresh" @click="loadGantt">刷新</el-button>
          </div>
          <div v-if="ganttEmpty" class="gantt-empty">暂无带起止时间的任务数据，请先完成任务规划</div>
          <div v-show="!ganttEmpty" ref="ganttChart" class="gantt-chart" v-loading="ganttLoading"></div>
        </el-tab-pane>
      </el-tabs>

      <!-- 分页 -->
      <div v-if="activeTab !== 'gantt'" class="pagination-wrapper">
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
    <el-dialog v-model="addDialogVisible" class="task-dialog" :title="editingTaskId ? '编辑任务' : '新增任务'" width="600px" destroy-on-close @closed="handleDialogClosed">
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

    <!-- 任务详情弹窗：历史任务展示真实结果、目标地图与执行时间线 -->
    <el-dialog
      v-model="detailVisible"
      class="task-dialog"
      :class="{ 'task-result-dialog': currentTask && currentTask.source === 'old' }"
      :title="currentTask && currentTask.source === 'old' ? '任务执行结果' : '任务详情'"
      :width="currentTask && currentTask.source === 'old' ? '1180px' : '700px'"
      top="4vh"
      @opened="initTaskResultMap"
      @closed="destroyTaskResultMap"
    >
      <div v-if="currentTask && currentTask.source === 'old'" class="task-result-layout">
        <section class="result-summary-panel">
          <div class="result-status" :class="{ 'is-failed': currentTask.status !== 'Success' }">
            <el-icon :size="30"><CircleCheck v-if="currentTask.status === 'Success'" /><CircleClose v-else /></el-icon>
            <div>
              <strong>{{ currentTask.status === 'Success' ? '任务执行成功' : '任务执行失败' }}</strong>
              <span>{{ currentTask.task_name || '-' }}</span>
            </div>
            <el-tag :type="currentTask.status === 'Success' ? 'success' : 'danger'" effect="dark">
              {{ currentTask.status === 'Success' ? 'Success' : (currentTask.status || 'Failed') }}
            </el-tag>
          </div>

          <div class="result-section">
            <h3>目标参数</h3>
            <dl class="result-facts">
              <div><dt>目标类型</dt><dd>{{ currentTask.type || '-' }}</dd></div>
              <div><dt>目标位置</dt><dd>{{ currentTask.targetLocation || '未提供坐标' }}</dd></div>
              <div><dt>执行卫星</dt><dd class="satellite-value">{{ currentTask.satellite_name || '未分配' }}</dd></div>
              <div><dt>载荷 / 分辨率</dt><dd>{{ currentTask.payload || '-' }} / {{ currentTask.resolution === '' ? '-' : currentTask.resolution + ' m' }}</dd></div>
            </dl>
          </div>

          <div class="result-section execution-timeline">
            <h3>执行完成时间线</h3>
            <el-timeline>
              <el-timeline-item type="primary" :hollow="true" :timestamp="currentTask.startTime || '-'">
                <strong>任务开始</strong>
                <span>任务进入卫星执行流程</span>
              </el-timeline-item>
              <el-timeline-item type="primary" :timestamp="currentTask.endTime || '-'">
                <strong>卫星执行完成</strong>
                <span>{{ currentTask.satellite_name || '执行卫星' }} 完成{{ currentTask.type || '目标' }}观测</span>
              </el-timeline-item>
              <el-timeline-item :type="currentTask.status === 'Success' ? 'success' : 'danger'" :timestamp="currentTask.resultReceivedAt || currentTask.endTime || '-'">
                <strong>结果反馈</strong>
                <span>控制中心已接收并归档客户端执行结果</span>
              </el-timeline-item>
            </el-timeline>
          </div>

          <div class="result-identity">
            <span>业务 UUID</span>
            <code>{{ currentTask.task_uuid || '-' }}</code>
          </div>
        </section>

        <section class="result-map-panel">
          <div class="result-map-heading">
            <div>
              <h3>目标观测结果</h3>
              <p>{{ resultTargetDescription }}</p>
            </div>
            <span>真实卫星影像</span>
          </div>
          <div v-if="hasTaskMapData" ref="taskResultMap" class="task-result-map"></div>
          <div v-else class="task-result-map-empty">
            <el-icon :size="30"><MapLocation /></el-icon>
            <strong>该任务未提供有效目标坐标</strong>
            <span>结果数据已归档，但无法绘制目标位置</span>
          </div>
          <div class="map-legend">
            <span><i class="legend-result"></i>{{ resultTargetDescription }}</span>
            <span>Esri World Imagery · 高德注记</span>
          </div>
        </section>

        <el-collapse class="result-raw-data">
          <el-collapse-item title="查看客户端原始回传数据" name="payload">
            <pre class="result-payload">{{ formatResultPayload(currentTask.resultPayload) }}</pre>
          </el-collapse-item>
        </el-collapse>
      </div>

      <el-descriptions :column="2" border v-else-if="currentTask">
        <el-descriptions-item label="任务ID">{{ currentTask.id }}</el-descriptions-item>
        <el-descriptions-item label="业务UUID" :span="2">{{ currentTask.task_uuid || '-' }}</el-descriptions-item>
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
import * as Cesium from 'cesium';
import echarts from '@/utils/echarts.js';
import { utcToTimestamp } from '@/utils/time.js';
import { 
  Search, Refresh, Plus, View, Delete, Edit, VideoPlay, VideoPause, Download, CircleClose, CircleCheck, Close, MapLocation
} from '@element-plus/icons-vue';

export default {
  name: 'TaskManage',
  components: {
    Search, Refresh, Plus, View, Delete, Edit, VideoPlay, VideoPause, Download, CircleClose, CircleCheck, Close, MapLocation
  },
  data() {
    return {
      loading: false,
      activeTab: 'new',
      tableData: [],
      oldTaskData: [],
      ganttLoading: false,   // 甘特图加载中
      ganttEmpty: false,     // 甘特图无数据占位
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
    },
    taskTargetPoints() {
      if (!this.currentTask || this.currentTask.source !== 'old') return [];
      return this.parseCoordinates(this.currentTask.targetLocation)
        .map(point => point.split(',').map(value => Number(value.trim())))
        .filter(point => point.length === 2 && Number.isFinite(point[0]) && Number.isFinite(point[1])
          && Math.abs(point[0]) <= 90 && Math.abs(point[1]) <= 180);
    },
    hasTaskMapData() {
      return this.taskTargetPoints.length > 0;
    },
    resultTargetDescription() {
      if (!this.currentTask) return '目标结果';
      const isArea = ['区域目标', '广域目标'].includes(this.currentTask.type) || this.taskTargetPoints.length > 2;
      return isArea ? '区域边界与观测标注' : '点目标与观测标注';
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
      if (!this.addDialogVisible && !this.detailVisible) {
        this.doSearch();
        this.getStats();
      }
    }, 5000);
    this._onVisibility = () => {
      if (!document.hidden && !this.addDialogVisible && !this.detailVisible) {
        this.doSearch();
        this.getStats();
      }
    };
    document.addEventListener('visibilitychange', this._onVisibility);
  },
  beforeUnmount() {
    if (this._pollTimer) { clearInterval(this._pollTimer); this._pollTimer = null; }
    if (this._onVisibility) { document.removeEventListener('visibilitychange', this._onVisibility); this._onVisibility = null; }
    // 销毁甘特图和结果地图实例，释放图表与 WebGL 资源
    if (this._ganttInst) { this._ganttInst.dispose(); this._ganttInst = null; }
    this.destroyTaskResultMap();
  },
  methods: {
    normalizeTask(task = {}, source = 'new') {
      return {
        id: task.id,
        task_uuid: task.task_uuid || task.taskUuid || '',
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
        resultPayload: task.result_payload ?? task.resultPayload ?? '',
        resultReceivedAt: task.result_received_at || task.resultReceivedAt || '',
        source,
      };
    },
    buildQueryParams() {
      const params = {
        page: this.search.pageNum,
        page_size: this.search.pageSize
      };
      if (this.search.keyword.trim()) params.search = this.search.keyword.trim();
      if (this.search.taskType) params.type = [this.search.taskType];
      if (this.search.sensorType) params.payload = [this.search.sensorType];
      if (this.search.status) params.status = [this.search.status];
      return params;
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
        const params = this.buildQueryParams();
        const res = await this.$request.post('/tasks/getNewTasks', params);
        const responseData = res.data.data || res.data;
        if (responseData) {
          const items = (responseData.items || responseData || []).map((item) => this.normalizeTask(item, 'new'));
          this.tableData = items.map(item => ({
            ...item,
            isRunning: item.status === '执行中' || item.status === '运行中' || item.status === '正在执行'
          }));
          this.totalNum = responseData.total ?? items.length;
          if (responseData.current_page) this.search.pageNum = responseData.current_page;
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
        const params = this.buildQueryParams();
        const res = await this.$request.post('/tasks/getOldTasks', params);
        const responseData = res.data.data || res.data;
        if (responseData) {
          const items = (responseData.items || responseData || []).map((item) => this.normalizeTask(item, 'old'));
          this.oldTaskData = items;
          this.totalNum = responseData.total ?? items.length;
          if (responseData.current_page) this.search.pageNum = responseData.current_page;
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
        const res = await this.$request.get('/tasks/getTaskStats');
        const data = res.data.data || res.data || {};
        this.stats = {
          total: data.total || 0,
          waiting: data.waiting || 0,
          running: data.running || 0,
          completed: data.completed || 0
        };
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
      } else if (tab === 'gantt') {
        this.loadGantt();
      } else {
        this.getOldTasks();
      }
    },

    // 加载任务甘特图：取待执行任务的起止时间绘制时间轴条形图
    async loadGantt() {
      this.ganttLoading = true;
      try {
        const res = await this.$request.get('/tasks/getNewTasksByCondition');
        const tasks = (res.data?.data || res.data || []).map((t) => this.normalizeTask(t, 'new'));
        const rows = tasks
          .map((t) => ({
            name: t.task_name || `任务${t.id}`,
            sat: t.satellite_name || '-',
            status: t.status || '',
            start: utcToTimestamp(t.startTime),
            end: utcToTimestamp(t.endTime)
          }))
          .filter((r) => !isNaN(r.start) && !isNaN(r.end) && r.end > r.start)
          .sort((a, b) => a.start - b.start)
          .slice(0, 40);
        this.ganttEmpty = rows.length === 0;
        if (rows.length === 0) return;
        this.$nextTick(() => this.renderGantt(rows));
      } catch (err) {
        console.error('加载甘特图数据失败:', err);
        this.ganttEmpty = true;
        ElMessage.warning('甘特图数据加载失败，请确认后端服务已启动');
      } finally {
        this.ganttLoading = false;
      }
    },

    // 渲染甘特图（ECharts custom 系列：横轴时间，纵轴任务，颜色按状态区分）
    renderGantt(rows) {
      const el = this.$refs.ganttChart;
      if (!el) return;
      if (!this._ganttInst) this._ganttInst = echarts.init(el);
      const statusColor = {
        '正在执行': '#ffd657',
        '等待规划': '#7fd4ff',
        '已完成': '#7cffb2'
      };
      const categories = rows.map((r) => r.name);
      const inst = this._ganttInst;
      inst.setOption({
        tooltip: {
          formatter: (p) => {
            const r = rows[p.dataIndex];
            const fmt = (ts) => new Date(ts).toLocaleString('zh-CN', { hour12: false });
            return `${r.name}<br/>执行卫星：${r.sat}<br/>状态：${r.status || '-'}<br/>开始：${fmt(r.start)}<br/>结束：${fmt(r.end)}`;
          }
        },
        grid: { top: 10, left: 150, right: 30, bottom: 30 },
        xAxis: {
          type: 'time',
          axisLabel: { color: '#9fc6e8', fontSize: 10 },
          splitLine: { lineStyle: { color: 'rgba(0,220,255,0.1)' } }
        },
        yAxis: {
          type: 'category',
          data: categories,
          inverse: true,
          axisLabel: {
            color: '#cfe8ff', fontSize: 11, width: 130, overflow: 'truncate'
          },
          axisLine: { lineStyle: { color: 'rgba(0,220,255,0.3)' } }
        },
        series: [{
          type: 'custom',
          renderItem: (params, api) => {
            const idx = api.value(0);
            const start = api.coord([api.value(1), idx]);
            const end = api.coord([api.value(2), idx]);
            const height = Math.min(api.size([0, 1])[1] * 0.5, 18);
            return {
              type: 'rect',
              shape: {
                x: start[0],
                y: start[1] - height / 2,
                width: Math.max(end[0] - start[0], 2),
                height: height,
                r: 3
              },
              style: {
                fill: statusColor[api.value(3)] || '#00dcff',
                shadowBlur: 6,
                shadowColor: 'rgba(0,220,255,0.35)'
              }
            };
          },
          encode: { x: [1, 2], y: 0 },
          data: rows.map((r, i) => [i, r.start, r.end, r.status])
        }]
      }, true);
      inst.resize();
    },

    // 搜索（重置页码）
    handleSearch(e) {
      if (e) e.preventDefault();
      this.search.pageNum = 1;
      this.doSearch();
    },

    // 执行搜索（不重置页码，用于分页）
    doSearch() {
      if (this.activeTab === 'new') {
        this.getList();
      } else if (this.activeTab === 'gantt') {
        this.loadGantt();
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

    // 历史结果地图使用任务真实坐标，点目标显示标注，区域目标显示边界和任务名
    initTaskResultMap() {
      this.destroyTaskResultMap();
      const pts = this.taskTargetPoints;
      const el = this.$refs.taskResultMap;
      if (!el || !pts.length) return;
      this._taskResultViewer = new Cesium.Viewer(el, {
        baseLayer: false,
        animation: false,
        timeline: false,
        geocoder: false,
        homeButton: false,
        sceneModePicker: false,
        baseLayerPicker: false,
        navigationHelpButton: false,
        fullscreenButton: false,
        infoBox: false,
        selectionIndicator: false,
        requestRenderMode: true,
        maximumRenderTimeChange: Infinity,
        sceneMode: Cesium.SceneMode.SCENE2D
      });
      const viewer = this._taskResultViewer;
      viewer.imageryLayers.removeAll();
      viewer.imageryLayers.addImageryProvider(new Cesium.UrlTemplateImageryProvider({
        url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        maximumLevel: 13
      }));
      viewer.imageryLayers.addImageryProvider(new Cesium.UrlTemplateImageryProvider({
        url: 'https://webst0{s}.is.autonavi.com/appmaptile?style=8&x={x}&y={y}&z={z}',
        subdomains: ['1', '2', '3', '4'],
        maximumLevel: 13
      }));
      if (viewer._cesiumWidget?._creditContainer) {
        viewer._cesiumWidget._creditContainer.style.display = 'none';
      }
      viewer.scene.backgroundColor = Cesium.Color.fromCssColorString('#07111f');

      const positions = pts.map(point => Cesium.Cartesian3.fromDegrees(point[1], point[0]));
      const isArea = ['区域目标', '广域目标'].includes(this.currentTask.type) || pts.length > 2;
      const labelStyle = {
        font: 'bold 16px "Microsoft YaHei", sans-serif',
        fillColor: Cesium.Color.WHITE,
        outlineColor: Cesium.Color.BLACK,
        outlineWidth: 4,
        style: Cesium.LabelStyle.FILL_AND_OUTLINE,
        pixelOffset: new Cesium.Cartesian2(0, -24),
        disableDepthTestDistance: Number.POSITIVE_INFINITY
      };
      positions.forEach((position, index) => {
        viewer.entities.add({
          position,
          point: {
            pixelSize: 14,
            color: Cesium.Color.fromCssColorString('#ff5f56'),
            outlineColor: Cesium.Color.WHITE,
            outlineWidth: 3,
            disableDepthTestDistance: Number.POSITIVE_INFINITY
          },
          label: !isArea ? {
            ...labelStyle,
            text: pts.length === 1 ? (this.currentTask.task_name || '观测目标') : `目标点 ${index + 1}`
          } : undefined
        });
      });
      if (isArea && positions.length > 2) {
        viewer.entities.add({
          polygon: {
            hierarchy: new Cesium.PolygonHierarchy(positions),
            material: Cesium.Color.fromCssColorString('#00dcff').withAlpha(0.24)
          }
        });
        viewer.entities.add({
          polyline: {
            positions: positions.concat(positions[0]),
            width: 3,
            material: Cesium.Color.fromCssColorString('#00f0ff'),
            clampToGround: true
          }
        });
        const center = pts.reduce((acc, point) => [acc[0] + point[0] / pts.length, acc[1] + point[1] / pts.length], [0, 0]);
        viewer.entities.add({
          position: Cesium.Cartesian3.fromDegrees(center[1], center[0]),
          label: {
            ...labelStyle,
            text: `${this.currentTask.task_name || '任务'} · 观测区域`,
            pixelOffset: new Cesium.Cartesian2(0, 0)
          }
        });
      }
      const lats = pts.map(point => point[0]);
      const lons = pts.map(point => point[1]);
      const latSpan = Math.max(...lats) - Math.min(...lats);
      const lonSpan = Math.max(...lons) - Math.min(...lons);
      const latPadding = Math.max(0.12, latSpan * 0.35);
      const lonPadding = Math.max(0.12, lonSpan * 0.35);
      viewer.camera.setView({
        destination: Cesium.Rectangle.fromDegrees(
          Math.min(...lons) - lonPadding, Math.min(...lats) - latPadding,
          Math.max(...lons) + lonPadding, Math.max(...lats) + latPadding
        )
      });
      viewer.scene.requestRender();
    },

    destroyTaskResultMap() {
      if (this._taskResultViewer) {
        if (!this._taskResultViewer.isDestroyed()) this._taskResultViewer.destroy();
        this._taskResultViewer = null;
      }
    },

    formatResultPayload(payload) {
      if (!payload) return '暂无回传数据';
      if (typeof payload !== 'string') return JSON.stringify(payload, null, 2);
      try {
        return JSON.stringify(JSON.parse(payload), null, 2);
      } catch (err) {
        return payload;
      }
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
        '正在执行': 'primary',
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

/* 历史任务执行结果：左侧结果与时间线，右侧真实目标影像 */
:deep(.task-result-dialog) {
  max-width: 94vw;
}

:deep(.task-result-dialog .el-dialog__header) {
  padding: 18px 22px 12px;
  border-bottom: 1px solid rgba(0, 220, 255, 0.16);
}

:deep(.task-result-dialog .el-dialog__title) {
  font-size: 20px;
  font-weight: 600;
  letter-spacing: 0.04em;
}

:deep(.task-result-dialog .el-dialog__body) {
  max-height: calc(88vh - 126px);
  padding: 14px 20px 6px;
  overflow-y: auto;
}

:deep(.task-result-dialog .el-dialog__footer) {
  padding: 12px 20px 16px;
  border-top: 1px solid rgba(0, 220, 255, 0.12);
}

.task-result-layout {
  display: grid;
  grid-template-columns: 380px minmax(0, 1fr);
  gap: 14px 20px;
}

.result-summary-panel,
.result-map-panel {
  min-width: 0;
}

.result-status {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 68px;
  padding: 12px 14px;
  color: #7cffb2;
  background: rgba(40, 180, 120, 0.1);
  border: 1px solid rgba(124, 255, 178, 0.3);
  border-radius: 6px;
}

.result-status.is-failed {
  color: #ff8f8f;
  background: rgba(255, 95, 86, 0.08);
  border-color: rgba(255, 95, 86, 0.3);
}

.result-status > div {
  flex: 1;
  min-width: 0;
}

.result-status strong,
.result-status span {
  display: block;
}

.result-status strong {
  margin-bottom: 4px;
  font-size: 19px;
}

.result-status span {
  overflow: hidden;
  color: #d7e9f8;
  font-size: 14px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.result-section {
  margin-top: 16px;
}

.result-section h3,
.result-map-heading h3 {
  margin: 0 0 10px;
  color: #d9f3ff;
  font-size: 16px;
  font-weight: 600;
}

.result-facts {
  margin: 0;
}

.result-facts > div {
  display: grid;
  grid-template-columns: 98px minmax(0, 1fr);
  gap: 10px;
  padding: 8px 0;
  border-bottom: 1px solid rgba(159, 198, 232, 0.12);
}

.result-facts dt,
.result-facts dd {
  margin: 0;
  font-size: 14px;
  line-height: 1.45;
}

.result-facts dt {
  color: #8fb3ce;
}

.result-facts dd {
  color: #e2f1fc;
  overflow-wrap: anywhere;
}

.result-facts .satellite-value {
  color: #00dcff;
  font-weight: 600;
}

.execution-timeline {
  padding-top: 2px;
}

.execution-timeline :deep(.el-timeline) {
  padding-left: 4px;
}

.execution-timeline :deep(.el-timeline-item) {
  padding-bottom: 12px;
}

.execution-timeline :deep(.el-timeline-item__timestamp) {
  color: #8fb3ce;
  font-size: 12px;
}

.execution-timeline :deep(.el-timeline-item__content) {
  color: #d9edfb;
  font-size: 14px;
}

.execution-timeline strong,
.execution-timeline span {
  display: block;
}

.execution-timeline span {
  margin-top: 3px;
  color: #9fc6e8;
  font-size: 12px;
}

.result-identity {
  padding: 9px 11px;
  background: rgba(0, 220, 255, 0.05);
  border-radius: 4px;
}

.result-identity span,
.result-identity code {
  display: block;
}

.result-identity span {
  margin-bottom: 4px;
  color: #8fb3ce;
  font-size: 12px;
}

.result-identity code {
  color: #b8d9ed;
  font-size: 12px;
  overflow-wrap: anywhere;
}

.result-map-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  min-height: 52px;
}

.result-map-heading h3 {
  margin-bottom: 4px;
  font-size: 18px;
}

.result-map-heading p {
  margin: 0;
  color: #9fc6e8;
  font-size: 13px;
}

.result-map-heading > span {
  flex-shrink: 0;
  padding: 4px 8px;
  color: #00dcff;
  background: rgba(0, 220, 255, 0.08);
  border: 1px solid rgba(0, 220, 255, 0.24);
  border-radius: 3px;
  font-size: 12px;
}

.task-result-map,
.task-result-map-empty {
  width: 100%;
  height: 430px;
  overflow: hidden;
  background: #07111f;
  border: 1px solid rgba(0, 220, 255, 0.28);
  border-radius: 5px;
}

.task-result-map-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: #8fb3ce;
}

.task-result-map-empty strong {
  color: #d9edfb;
  font-size: 16px;
}

.task-result-map-empty span {
  font-size: 13px;
}

.map-legend {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding-top: 9px;
  color: #8fb3ce;
  font-size: 12px;
}

.map-legend span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.legend-result {
  display: inline-block;
  width: 10px;
  height: 10px;
  background: #ff5f56;
  border: 2px solid #fff;
  border-radius: 50%;
}

.result-raw-data {
  grid-column: 1 / -1;
  border-top: 1px solid rgba(0, 220, 255, 0.12);
  border-bottom: 0;
}

.result-raw-data :deep(.el-collapse-item__header) {
  height: 38px;
  color: #9fc6e8;
  font-size: 13px;
}

.result-payload {
  margin: 0;
  max-height: 180px;
  overflow: auto;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  font: 12px/1.6 'Courier New', monospace;
  color: #cfe8ff;
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
  .search-right {
    flex-direction: row;
    flex-wrap: wrap;
  }
  .search-right .el-button {
    min-height: 40px;
    margin: 0;
  }
  .pagination-wrapper {
    justify-content: flex-start;
    overflow-x: auto;
  }
  .gantt-chart {
    height: 360px;
  }
  :deep(.task-dialog) {
    width: 94% !important;
    max-height: 88vh;
    margin-top: 6vh;
    overflow-y: auto;
  }
  :deep(.task-dialog .el-descriptions__cell) {
    overflow-wrap: anywhere;
  }
  .task-result-layout {
    grid-template-columns: minmax(0, 1fr);
  }
  .task-result-map,
  .task-result-map-empty {
    height: 340px;
  }
  .result-map-heading,
  .map-legend {
    flex-direction: column;
  }
  .result-raw-data {
    grid-column: 1;
  }
}

/* 任务甘特图 */
.gantt-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.gantt-tip { font-size: 12px; color: #9fc6e8; }
.gantt-chart { width: 100%; height: 480px; }
.gantt-empty {
  padding: 60px 0;
  text-align: center;
  font-size: 13px;
  color: #68809a;
  border: 1px dashed rgba(0, 220, 255, 0.18);
  border-radius: 6px;
}
</style>
