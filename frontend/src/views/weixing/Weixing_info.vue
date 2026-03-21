<template>
  <el-card shadow="never" style="margin-top: 10px;">
    <h3>卫星详情：{{ satelliteInfo.name }}</h3>
    <el-descriptions :column="2" border>
      <el-descriptions-item label="名称">{{ satelliteInfo.name || '无' }}</el-descriptions-item>
      <el-descriptions-item label="轨道">{{ satelliteInfo.orbit || '无' }}</el-descriptions-item>
      <el-descriptions-item label="载荷类型">{{ satelliteInfo.loadType || '无' }}</el-descriptions-item>
      <el-descriptions-item label="卫星位置(km)">{{ satelliteInfo.position || '无' }}</el-descriptions-item>
      <el-descriptions-item label="速度(km/s)">{{ satelliteInfo.speed || '无' }}</el-descriptions-item>
      <el-descriptions-item label="星下点位置(纬度，经度)">{{ satelliteInfo.sub_point || '无' }}</el-descriptions-item>
      <el-descriptions-item label="飞行圈数">{{ satelliteInfo.turns || '无' }}</el-descriptions-item>
      <el-descriptions-item label="存储容量(GB)">{{ satelliteInfo.storage || '无' }}</el-descriptions-item>
      <el-descriptions-item label="电池容量(Wh)">{{ satelliteInfo.battery || '无' }}</el-descriptions-item>
      <el-descriptions-item label="分辨率(m)">{{ satelliteInfo.resolution || '无' }}</el-descriptions-item>
      <el-descriptions-item label="幅宽(km)">{{ satelliteInfo.width || '无' }}</el-descriptions-item>
      <el-descriptions-item label="侧摆角(°)">{{ satelliteInfo.sideAngle || '无' }}</el-descriptions-item>
      <el-descriptions-item label="俯仰角(°)">{{ satelliteInfo.pitchAngle || '无' }}</el-descriptions-item>
      <el-descriptions-item label="载荷转动角速度(°/s)">{{ satelliteInfo.angleVelocity || '无' }}</el-descriptions-item>
      <el-descriptions-item label="稳定时间(s)">{{ satelliteInfo.settlingTime || '无' }}</el-descriptions-item>
      <el-descriptions-item label="云层遮挡阈值(m)">{{ satelliteInfo.threshold || '无' }}</el-descriptions-item>
      <el-descriptions-item label="状态">{{ satelliteInfo.status || '无' }}</el-descriptions-item>
      <el-descriptions-item label="是否可用">{{ satelliteInfo.is_available || '无' }}</el-descriptions-item>
      <el-descriptions-item label="连接的高轨卫星">{{ satelliteInfo.connecting_geo || '无' }}</el-descriptions-item>
      <el-descriptions-item label="执行中的任务">{{ satelliteInfo.running_task || '无' }}</el-descriptions-item>
      <el-descriptions-item label="任务总数">{{ satelliteInfo.task_num || '无' }}</el-descriptions-item>
      <el-descriptions-item label="下行速率(G)">{{ satelliteInfo.downlink_rate || '无' }}</el-descriptions-item>
      <el-descriptions-item label="成像功率(W)">{{ satelliteInfo.imaging_powers || '无' }}</el-descriptions-item>
      <el-descriptions-item label="太阳能功率(W)">{{ satelliteInfo.sunlight_powers || '无' }}</el-descriptions-item>
      <el-descriptions-item label="空闲功率(W)">{{ satelliteInfo.eclipse_powers || '无' }}</el-descriptions-item>
      <el-descriptions-item label="机动功率(W)">{{ satelliteInfo.maneuver_powers || '无' }}</el-descriptions-item>
    </el-descriptions>
    <el-button style="margin-top: 20px;" @click="$router.back()">返回</el-button>
  </el-card>
</template>

<script>
export default {
  name: "WeixingInfo",
  data() {
    return {
      satelliteInfo: {}
    };
  },
  created() {
    // 获取路由参数
    const name = this.$route.params.name;

    // 这里可以根据实际情况从后端获取数据
    // 示例：从本地存储或接口获取卫星详情
    // 假设有接口 /ts/?name=xxx
    this.$request.get(`/satellites/getSatelliteByName/${name}`).then(res => {
      if (res.data) {
        this.satelliteInfo = res.data;
      } else {
        // 没查到数据时的处理
        this.satelliteInfo = { name, guidao: '无', jinji: '无', leixing: '无', zaihe: '无', shijian: '无', shijianfan: '无', quyu: '无' };
      }
    }).catch(() => {
      this.satelliteInfo = { name, guidao: '无', jinji: '无', leixing: '无', zaihe: '无', shijian: '无', shijianfan: '无', quyu: '无' };
    });
  }
};
</script>

<style scoped>
h3 {
  margin-bottom: 20px;
    color: #4c4081;
}
::v-deep .el-descriptions__cell {
  height: 10px;           /* 行高 */
  padding: 1px 1px;      /* 上下和左右间距 */
  font-size: 1px;        /* 文字大小 */
}
::v-deep .el-descriptions__label {
  min-width: 120px;
}
::v-deep .el-descriptions__content {
  min-width: 250px;
}
.el-descriptions {
  font-size: 100px;
}
::v-deep .el-descriptions {
  border-radius: 10px; /* 设置整体圆角 */
  overflow: hidden;    /* 防止内容溢出圆角 */
}
</style>