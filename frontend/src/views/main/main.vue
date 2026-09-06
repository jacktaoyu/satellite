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
          <el-menu-item index="/satellite/ground_station"><el-icon><Position /></el-icon>地面站</el-menu-item>
          <el-menu-item index="/satellite/yongli"><el-icon><SetUp /></el-icon>示范用例</el-menu-item>
          <el-menu-item index="/satellite/xingneng"><el-icon><SetUp /></el-icon>性能分析</el-menu-item>
        </div>
        <!-- 非管理员账号暂无任何菜单项，给出明确提示而不是空白侧边栏 -->
        <div v-else class="menu-empty-tip">当前账号无可用功能模块，请联系管理员开通权限</div>
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
            <span style="margin-left:10px;color:#7fd4ff;">{{ nickname }}</span>
          </div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item disabled>个人中心</el-dropdown-item>
              <el-dropdown-item @click="openPwdDialog">个人设置</el-dropdown-item>
              <el-dropdown-item divided @click="quitLogin">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </el-header>
      <el-main class="tech-main" :style="{ padding: $route.path === '/satellite/satellite_network' ? '0' : '20px' }">
        <router-view />
      </el-main>
    </el-container>

    <!-- 修改密码弹窗（技术说明书 3.7.5） -->
    <el-dialog v-model="pwdDialogVisible" title="修改密码" width="420px" destroy-on-close>
      <el-form :model="pwdForm" class="pwd-form">
        <el-form-item>
          <el-input v-model="pwdForm.username" placeholder="请输入新账号..." prefix-icon="User" />
        </el-form-item>
        <el-form-item>
          <el-input v-model="pwdForm.password" type="password" placeholder="请输入新密码..." prefix-icon="Lock"
            show-password />
        </el-form-item>
        <el-form-item>
          <el-input v-model="pwdForm.confirmPassword" type="password" placeholder="请再次输入密码..." prefix-icon="Lock"
            show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button type="primary" style="width: 100%" @click="submitPwd" :loading="pwdSubmitting">提交</el-button>
      </template>
    </el-dialog>
  </el-container>
</template>

<script>
export default {
  data() {
    return {
      isCollapse: false,
      nickname: "",
      isAdmin: 0,
      pwdDialogVisible: false,
      pwdSubmitting: false,
      pwdForm: {
        username: "",
        password: "",
        confirmPassword: "",
      },
    }
  },
  created() {
    this.nickname = localStorage.getItem("nickname");
    this.isAdmin = localStorage.getItem("isAdmin");
  },
  methods: {
    openPwdDialog() {
      // 用户名默认填入当前登录用户名，密码每次清空
      this.pwdForm.username = localStorage.getItem("userInfo") || this.nickname || "";
      this.pwdForm.password = "";
      this.pwdForm.confirmPassword = "";
      this.pwdDialogVisible = true;
    },
    async submitPwd() {
      const { username, password, confirmPassword } = this.pwdForm;
      if (!username || !password || !confirmPassword) {
        this.$message.warning('用户名、新密码和确认密码不能为空');
        return;
      }
      if (password !== confirmPassword) {
        this.$message.error('两次输入的密码不一致');
        return;
      }
      this.pwdSubmitting = true;
      try {
        await this.$request.post('/updatePassword', { username, password, confirmPassword });
        this.$message.success('密码修改成功');
        this.pwdDialogVisible = false;
        this.pwdForm.password = "";
        this.pwdForm.confirmPassword = "";
      } catch (err) {
        // 失败信息（含后端 400 的 meta.message）由 request.js 响应拦截器统一弹出
      } finally {
        this.pwdSubmitting = false;
      }
    },
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
  background: linear-gradient(90deg, #061224, #0a1e3d);
  border-bottom: 1px solid rgba(0, 220, 255, 0.25);
  z-index: 9;
  box-shadow: 0 1px 4px rgba(0, 21, 41, 0.35);
}

.el-main {
  background-color: #0b1530;
  position: relative;
}

.el-menu {
  border: none;
}

.el-menu-item.is-active {
  background-color: #00a0c6 !important;
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