<template>
  <div class="backend-data">
    <div class="content">
      <div class="message-box">
        <h1>{{ message }}</h1>
        <p class="status">系统状态: <span :class="status">{{ status }}</span></p>
      </div>
      
      <!-- <div class="health-box" v-if="healthStatus">
        <h2>服务器健康状态</h2>
        <div class="health-info">
          <p>状态: <span :class="healthStatus.status">{{ healthStatus.status }}</span></p>
          <p>版本: {{ healthStatus.version }}</p>
        </div>
      </div> -->
    </div>
  </div>
</template>

<script>

export default {
  name: 'BackendData',
  data() {
    return {
      message: '加载中...',
      status: '加载中...',
      healthStatus: null
    }
  },
  methods: {
    // async created() {
    //   try {
    //     // 获取欢迎信息
    //     const response = await this.$request.get('/satellite/example')
    //     this.message = response.data.message
    //     this.status = response.data.status

    //     // // 获取健康状态
    //     // const healthResponse = await this.$request.get('/satellite/example1')
    //     // this.healthStatus = healthResponse.data
    //   } catch (error) {
    //     console.error('Error fetching data:', error)
    //     this.message = '获取数据失败'
    //     this.status = 'error'
    //   }
    // }

    async created() { //login方法会在用户触发登录操作（如点击按钮）时执行。
          this.$request.get("/satellite/example").then(res => {
            this.message = res.message
            this.status = res.status
            console.log(res);
          });
        }
  }
}
</script>

<style scoped>
.backend-data {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background-color: #f5f7fa;
}

.content {
  width: 100%;
  max-width: 600px;
  padding: 2rem;
}

.message-box, .health-box {
  background: white;
  border-radius: 12px;
  padding: 2rem;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  margin-bottom: 2rem;
}

h1 {
  color: #2c3e50;
  font-size: 2.5rem;
  margin-bottom: 1rem;
}

h2 {
  color: #2c3e50;
  font-size: 1.8rem;
  margin-bottom: 1rem;
}

.status {
  font-size: 1.2rem;
  margin: 1rem 0;
}

.health-info p {
  font-size: 1.1rem;
  margin: 0.5rem 0;
  color: #666;
}

.success {
  color: #42b983;
  font-weight: bold;
}

.error {
  color: #ff4757;
  font-weight: bold;
}

.healthy {
  color: #42b983;
  font-weight: bold;
}

span {
  font-weight: 600;
}
</style> 