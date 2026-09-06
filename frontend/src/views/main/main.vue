<template>
  <el-container>
    <el-aside :style="{ width: isCollapse ? 'fit-content' : '224px' }" class="tech-aside">
      <div class="logo" @click="$router.push('/satellite/satellite_network')">
        <span class="logo-mark">
          <svg viewBox="0 0 24 24" fill="none" width="18" height="18">
            <path d="M12 2L14.5 9.5L22 12L14.5 14.5L12 22L9.5 14.5L2 12L9.5 9.5L12 2Z" fill="url(#asideLogoGrad)"/>
            <defs>
              <linearGradient id="asideLogoGrad" x1="2" y1="2" x2="22" y2="22">
                <stop stop-color="#00f0ff"/>
                <stop offset="1" stop-color="#7c4dff"/>
              </linearGradient>
            </defs>
          </svg>
        </span>
        <transition name="fade">
          <span v-if="!isCollapse" class="logo-text">智能星簇协同运行验证系统</span>
        </transition>
      </div>
      <el-menu router :collapse="isCollapse" :default-active="$route.path" active-text-color="#eafcff"
        background-color="transparent" text-color="rgba(160, 200, 235, 0.62)" :collapse-transition="true">
        <div v-if="isAdmin == 1">
          <el-menu-item index="/satellite/satellite_network"><el-icon><Monitor /></el-icon><span>卫星网络</span></el-menu-item>
          <el-menu-item index="/satellite/system_settings"><el-icon><SetUp /></el-icon><span>系统设置</span></el-menu-item>
          <el-menu-item index="/satellite/weixing"><el-icon><Satellite /></el-icon><span>卫星管理</span></el-menu-item>
          <el-sub-menu index="/satellite/renwu">
            <template #title>
              <el-icon><List /></el-icon>
              <span>任务管理</span>
            </template>
            <el-menu-item index="/satellite/renwu/shuxing"><el-icon><Document /></el-icon><span>任务属性</span></el-menu-item>
            <el-menu-item index="/satellite/renwu/shezhi"><el-icon><Operation /></el-icon><span>任务设置</span></el-menu-item>
          </el-sub-menu>
          <el-menu-item index="/satellite/xingcu"><el-icon><Connection /></el-icon><span>星簇管理</span></el-menu-item>
          <el-menu-item index="/satellite/ground_station"><el-icon><Position /></el-icon><span>地面站</span></el-menu-item>
          <el-menu-item index="/satellite/yongli"><el-icon><Aim /></el-icon><span>示范用例</span></el-menu-item>
          <el-menu-item index="/satellite/xingneng"><el-icon><TrendCharts /></el-icon><span>性能分析</span></el-menu-item>
        </div>
        <!-- 非管理员账号暂无任何菜单项，给出明确提示而不是空白侧边栏 -->
        <div v-else class="menu-empty-tip">当前账号无可用功能模块，请联系管理员开通权限</div>
      </el-menu>
      <div class="aside-footer" v-if="!isCollapse">
        <span class="sys-dot"></span>SYSTEM ONLINE · V2.6
      </div>
    </el-aside>
    <el-container>
      <el-header class="tech-header">
        <div class="header-left">
          <div class="collapse-btn" @click="isCollapse = !isCollapse">
            <el-icon :size="18">
              <Expand v-if="isCollapse" />
              <Fold v-else />
            </el-icon>
          </div>
          <div class="header-title">
            <span class="header-page-name">{{ $route.meta.title || '卫星网络' }}</span>
            <span class="header-breadcrumb">SATELLITE CLUSTER OPERATION CONSOLE</span>
          </div>
        </div>
        <div class="header-right">
          <div class="header-status">
            <span class="sys-dot"></span>LINK NORMAL
          </div>
          <el-dropdown style="cursor: pointer;height:100%;display: flex;">
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
        </div>
      </el-header>
      <el-main class="tech-main" :style="{ padding: $route.path === '/satellite/satellite_network' ? '0' : '20px' }">
        <!-- 路由过渡：页面切换淡入上移，弱化生硬跳变 -->
        <router-view v-slot="{ Component }">
          <transition name="page-fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
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
import {
  Monitor, SetUp, List, Connection, Position, Aim, TrendCharts, Expand, Fold,
  Document, Operation
} from '@element-plus/icons-vue';

// 自定义卫星图标（组件库无内置卫星图标，与整体线框风格保持一致）
const Satellite = {
  name: 'SatelliteIcon',
  template: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"
    stroke-linecap="round" stroke-linejoin="round" width="1em" height="1em">
    <rect x="9.2" y="9.2" width="5.6" height="5.6" rx="1" transform="rotate(45 12 12)"/>
    <path d="M6.5 6.5 3.8 3.8M2 7.5h2.6M7.5 2v2.6M17.5 17.5l2.7 2.7M22 16.5h-2.6M16.5 22v-2.6"/>
  </svg>`
};

export default {
  components: {
    Monitor, SetUp, List, Connection, Position, Aim, TrendCharts, Expand, Fold,
    Document, Operation, Satellite
  },
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

/* ---------- 侧边栏：深空渐变 + 玻璃拟态 ---------- */
.el-aside.tech-aside {
  color: #cfe8ff;
  z-index: 10;
  position: relative;
  background: linear-gradient(180deg, #04101f 0%, #020a16 60%, #02070f 100%);
  border-right: 1px solid rgba(0, 220, 255, 0.14);
  box-shadow: 4px 0 18px rgba(0, 8, 24, 0.55);
  display: flex;
  flex-direction: column;
}
/* 侧栏顶部青色氛围光 */
.el-aside.tech-aside::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 180px;
  background: radial-gradient(ellipse at 50% -20%, rgba(0, 220, 255, 0.14), transparent 70%);
  pointer-events: none;
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 10px;
  cursor: pointer;
  border-bottom: 1px solid rgba(0, 220, 255, 0.16);
  background: linear-gradient(90deg, rgba(0, 220, 255, 0.1), transparent 75%);
  flex-shrink: 0;
  overflow: hidden;
}

.logo-mark {
  width: 30px;
  height: 30px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  background: rgba(0, 220, 255, 0.1);
  border: 1px solid rgba(0, 220, 255, 0.35);
  box-shadow: 0 0 10px rgba(0, 220, 255, 0.35);
}

.logo-text {
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 1px;
  white-space: nowrap;
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  background: linear-gradient(180deg, #ffffff, #7fd4ff);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  filter: drop-shadow(0 0 6px rgba(0, 220, 255, 0.35));
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.25s;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.el-menu {
  border: none;
  flex: 1;
  padding: 8px;
  background: transparent;
}

.el-menu-item,
:deep(.el-sub-menu__title) {
  height: 42px;
  line-height: 42px;
  margin: 4px 0;
  border-radius: 6px;
  border: 1px solid transparent;
  color: rgba(160, 200, 235, 0.62);
  background-color: transparent;
  transition: all 0.22s ease;
}

.el-menu-item .el-icon,
:deep(.el-sub-menu__title) .el-icon {
  color: inherit;
}

.el-menu-item:hover,
:deep(.el-sub-menu__title):hover {
  color: #00f0ff !important;
  background: rgba(0, 220, 255, 0.08) !important;
}

/* 当前选中菜单项：青色渐变光带 + 左侧发光指示条 */
.el-menu-item.is-active {
  position: relative;
  color: #eafcff !important;
  font-weight: 600;
  background: linear-gradient(90deg, rgba(0, 220, 255, 0.24), rgba(0, 220, 255, 0.05)) !important;
  border: 1px solid rgba(0, 220, 255, 0.4);
  box-shadow: 0 0 14px rgba(0, 220, 255, 0.22);
}
.el-menu-item.is-active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 20px;
  border-radius: 2px;
  background: #00f0ff;
  box-shadow: 0 0 8px rgba(0, 240, 255, 0.9);
}

/* 子菜单面板 */
:deep(.el-menu--inline) {
  background: rgba(2, 10, 22, 0.6);
  border-radius: 6px;
}
:deep(.el-menu--inline .el-menu-item) {
  min-width: auto;
  padding-left: 20px !important;
}

.menu-empty-tip {
  padding: 20px 14px;
  font-size: 12px;
  line-height: 1.8;
  color: #68809a;
}

/* 侧栏底部系统状态装饰 */
.aside-footer {
  flex-shrink: 0;
  padding: 12px 18px;
  font-size: 11px;
  letter-spacing: 2px;
  color: #4d657f;
  border-top: 1px solid rgba(0, 220, 255, 0.1);
  font-family: 'Courier New', monospace;
  display: flex;
  align-items: center;
  gap: 8px;
}

.sys-dot {
  display: inline-block;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #52ffa8;
  box-shadow: 0 0 8px rgba(82, 255, 168, 0.8);
  animation: dot-pulse 2s ease-in-out infinite;
}
@keyframes dot-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.35; }
}

/* ---------- 顶栏：渐变 + 底部发光线 ---------- */
.el-header.tech-header {
  line-height: 60px;
  padding: 0 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: linear-gradient(90deg, #04101f, #071a33 55%, #04101f);
  border-bottom: 1px solid rgba(0, 220, 255, 0.22);
  z-index: 9;
  box-shadow: 0 2px 14px rgba(0, 8, 24, 0.5);
}

.header-left {
  height: 100%;
  display: flex;
  align-items: center;
  gap: 4px;
}

.collapse-btn {
  cursor: pointer;
  height: 34px;
  width: 34px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  color: #9fc6e8;
  border: 1px solid transparent;
  transition: all 0.2s;
}
.collapse-btn:hover {
  color: #00f0ff;
  background: rgba(0, 220, 255, 0.1);
  border-color: rgba(0, 220, 255, 0.3);
}

.header-title {
  margin-left: 10px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 3px;
  line-height: 1.3;
}
.header-page-name {
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 2px;
  color: #e8f6ff;
}
.header-breadcrumb {
  font-size: 10px;
  letter-spacing: 2px;
  color: #4d657f;
  font-family: 'Courier New', monospace;
  transform: scale(0.92);
  transform-origin: left center;
}

.header-right {
  height: 100%;
  display: flex;
  align-items: center;
}

.header-status {
  margin-right: 14px;
  padding: 4px 12px;
  font-size: 11px;
  letter-spacing: 1.5px;
  font-family: 'Courier New', monospace;
  color: #8ee0c0;
  display: flex;
  align-items: center;
  gap: 7px;
  border: 1px solid rgba(82, 255, 168, 0.25);
  border-radius: 20px;
  background: rgba(82, 255, 168, 0.06);
}

.el-main {
  background:
    radial-gradient(1200px 500px at 85% -10%, rgba(0, 140, 220, 0.08), transparent 60%),
    radial-gradient(900px 420px at 5% 110%, rgba(80, 60, 200, 0.07), transparent 60%),
    #0b1530;
  position: relative;
}

/* 路由切换过渡：旧页淡出 + 新页淡入上移 */
.page-fade-enter-active {
  transition: opacity 0.28s ease, transform 0.28s ease;
}
.page-fade-leave-active {
  transition: opacity 0.16s ease;
}
.page-fade-enter-from {
  opacity: 0;
  transform: translateY(8px);
}
.page-fade-leave-to {
  opacity: 0;
}
</style>