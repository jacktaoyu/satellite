<template>
  <el-container>
    <el-aside :style="{ width: isCollapse ? 'fit-content' : '200px' }">
      <div class="logo">智能星簇协同运行验证系统</div>
      <el-menu router :collapse="isCollapse" :default-active="$route.path" active-text-color="#fff"
        background-color="#011528" text-color="hsla(0,0%,100%,.65)" :collapse-transition="true">
        <div v-if="isAdmin == 1">
          <el-menu-item index="/satellite/satellite_network"><el-icon><House /></el-icon>卫星网络</el-menu-item>
          <el-menu-item index="/satellite/system_settings"><el-icon><SetUp /></el-icon>系统设置</el-menu-item>
          <el-menu-item index="/satellite/weixing"><el-icon><SetUp /></el-icon>卫星管理</el-menu-item>
          <el-sub-menu index="/satellite/renwu">
            <template #title>
              <el-icon><SetUp /></el-icon>
              <span>任务管理</span>
            </template>
            <el-menu-item index="/satellite/renwu/shuxing">任务属性</el-menu-item>
            <el-menu-item index="/satellite/renwu/shezhi">任务设置</el-menu-item>
          </el-sub-menu>
          <el-menu-item index="/satellite/xingcu"><el-icon><SetUp /></el-icon>星簇管理</el-menu-item>
          <el-menu-item index="/satellite/yongli"><el-icon><SetUp /></el-icon>示范用例</el-menu-item>
          <el-menu-item index="/satellite/xingneng"><el-icon><SetUp /></el-icon>性能分析</el-menu-item>
          <el-menu-item index="/satellite/"><el-icon><SetUp /></el-icon>系统版本</el-menu-item>
        </div>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header>
        <div style="cursor: pointer;height:100%;padding: 0 12px;display: flex;align-items: center;"
          @click="isCollapse = !isCollapse">
          <!-- <el-icon color="#909399" :size="24" v-if="isCollapse">
            <Expand />
          </el-icon>
          <el-icon color="#909399" :size="24" v-else>
            <Fold />
          </el-icon> -->
        </div>
        <el-dropdown style="cursor: pointer;height:100%;display: flex;line-height: 60px;">
          <div style="padding: 0 12px;display: flex;align-items: center;justify-content: center;">
            <el-avatar :size="26" src="https://gw.alipayobjects.com/zos/antfincdn/XAosXuNZyF/BiazfanxmamNRoxxVxka.png" />
            <span style="margin-left:10px;color:#909399;">{{ nickname }}</span>
          </div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item disabled>个人中心</el-dropdown-item>
              <el-dropdown-item disabled>个人设置</el-dropdown-item>
              <el-dropdown-item divided @click="quitLogin">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </el-header>
      <el-main>
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script>
export default {
  data() {
    return {
      isCollapse: false,
      nickname: "",
    }
  },
  created() {
    this.nickname = localStorage.getItem("nickname");
    this.isAdmin = localStorage.getItem("isAdmin");
  },
  methods: {
    quitLogin() {
      localStorage.clear()
      this.$router.push('/login')
      this.$message.success('退出成功')
    }
  }
}
</script>

<style scoped>
.el-container {
  height: 100vh;
}

.el-aside {
  color: #fff;
  z-index: 10;
  background-color: #011528;
  box-shadow: 2px 0 6px rgba(0, 21, 41, 0.35);
}

.el-header {
  line-height: 60px;
  padding: 0 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background-color: #fff;
  z-index: 9;
  box-shadow: 0 1px 4px rgba(0, 21, 41, 0.08);
}

.el-main {
  background-color: #f0f2f5;
  position: relative;
}

.el-menu {
  border: none;
}

.el-menu-item.is-active {
  background-color: #1890ff !important;
}

.el-menu-item {
  background-color: #000b16;
}

.el-menu-item:hover {
  color: #fff !important;
}

.logo {
  height: 60px;
  line-height: 60px;
  text-align: center;
  /* margin-left: 20px; */
}
</style>