<template>
  <el-card class="box-card">
      <div class="login-body">
          <!-- 品牌区 -->
          <div class="brand">
              <div class="brand-logo">
                  <svg viewBox="0 0 24 24" fill="none" width="28" height="28">
                      <path d="M12 2L14.5 9.5L22 12L14.5 14.5L12 22L9.5 14.5L2 12L9.5 9.5L12 2Z"
                            fill="url(#logoGrad)"/>
                      <defs>
                          <linearGradient id="logoGrad" x1="2" y1="2" x2="22" y2="22">
                              <stop stop-color="#4fc3f7"/>
                              <stop offset="1" stop-color="#7c4dff"/>
                          </linearGradient>
                      </defs>
                  </svg>
              </div>
              <div class="brand-name">智能星簇协同运行验证系统</div>
              <div class="brand-sub">SATELLITE CLUSTER COLLABORATIVE PLATFORM</div>
          </div>

          <div class="login-title">用户登录</div>

          <el-form ref="form" :model="userForm" class="login-form">
              <el-input 
                placeholder="请输入账号..." 
                v-model="userForm.accountNumber" 
                class="login-input"
                prefix-icon="User"
              />
              
              <el-input 
                placeholder="请输入密码..." 
                v-model="userForm.userPassword" 
                class="login-input"
                @keyup.enter="login" 
                show-password
                prefix-icon="Lock"
              />

              <el-select 
                v-model="userForm.value" 
                clearable 
                placeholder="请选择用户类型" 
                class="login-input"
                popper-class="login-select-popper"
              >
                  <el-option 
                    v-for="item in options" 
                    :key="item.value" 
                    :label="item.label" 
                    :value="item.value"
                  />
              </el-select>

              <div class="login-submit">
                  <el-button type="primary" @click="login" class="submit-btn" :loading="loading">登 录</el-button>
              </div>
              <div class="register-link">
                  还没有账号？<span @click="$router.push('/register')">立即注册</span>
              </div>
          </el-form>
      </div>
  </el-card>
</template>

<script>
export default {
  name: "login-card",
  data() {
      return {
          userForm: {
              accountNumber: '',
              userPassword: '',
              value: ''
          },
          loading: false, // 登录请求进行中，防止连续点击重复提交/重复弹提示
          options: [
              {
                  value: '1',
                  label: '管理员'
              },
              // {
              //     value: '2',
              //     label: '老板'
              // },
              {
                  value: '3',
                  label: '用户'
              }
          ],
      };
  },

  methods: {
      login() { //login方法会在用户触发登录操作（如点击按钮）时执行。
          if (this.loading) return; // 节流：请求未结束时忽略重复点击
          if (!this.userForm.value) { // 必须选择用户类型（后端会校验与账号实际类型是否匹配）
              this.$message.warning("请选择用户类型");
              return;
          }
          this.loading = true;
          this.$request.post("/login/", { // 向后端发送登录请求
              username: this.userForm.accountNumber, //username从表单对象userForm中获取账号
              password: this.userForm.userPassword,
              // value: this.userForm.value
              value: this.userForm.value
          }).then(res => { //this.$request.post() 返回一个 Promise 对象。.then() 是 Promise 的方法，用于处理异步操作成功的结果。回调函数的参数 res 是请求成功后服务端返回的响应数据。箭头函数的作用是定义一个匿名函数，并在箭头函数内部执行异步操作，箭头函数语法：(参数) => { 函数体 }。res 仅在箭头函数内部有效，通过.then()处理异步响应
              if (res.data.meta.status === 200) {
                  localStorage.setItem("userInfo", res.data.data.username); //存储用户信息
                  localStorage.setItem("nickname", res.data.data.username); //存储昵称
                  localStorage.setItem("userInfoid", res.data.data.user_id);
                  localStorage.setItem("img_url_touxiang", res.data.data.img_url);
                  localStorage.setItem("jianjie", res.data.data.jianjie);
                  localStorage.setItem("isAdmin", res.data.data.isAdmin);
                  localStorage.setItem("token", res.data.data.token);
                  this.$message.success("登录成功") //提示成功消息
                  this.$router.push('/satellite/satellite_network')
              } else {
                  this.$message.error(res.data.meta.message); //提示错误消息
              }
          }).catch(() => {
              // 错误提示已由 request.js 响应拦截器统一弹出，这里仅吞掉 rejection，避免控制台未捕获异常
          }).finally(() => {
              this.loading = false;
          });
      }
  } //
}
</script>

<style scoped>
@keyframes card-in {
  from { opacity: 0; transform: translateY(24px); }
  to { opacity: 1; transform: translateY(0); }
}

.box-card {
  position: relative;
  background: rgba(10, 18, 40, 0.55);
  border: 1px solid rgba(120, 180, 255, 0.22);
  border-radius: 16px;
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.45), 0 0 40px rgba(64, 158, 255, 0.08);
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
  animation: card-in 0.6s ease-out;
}

.box-card :deep(.el-card__body) {
  padding: 0;
}

.login-body {
  padding: 44px 44px 36px;
  width: 420px;
}

/* 品牌区 */
.brand {
  text-align: center;
  margin-bottom: 28px;
}

.brand-logo {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 52px;
  height: 52px;
  border-radius: 14px;
  background: rgba(64, 158, 255, 0.12);
  border: 1px solid rgba(120, 180, 255, 0.3);
  box-shadow: 0 0 20px rgba(64, 158, 255, 0.25);
  margin-bottom: 14px;
}

.brand-name {
  font-size: 19px;
  font-weight: 600;
  letter-spacing: 2px;
  color: #e8f1ff;
}

.brand-sub {
  margin-top: 6px;
  font-size: 10px;
  letter-spacing: 3px;
  color: rgba(160, 190, 235, 0.55);
}

.login-title {
  padding-bottom: 28px;
  text-align: center;
  font-weight: 600;
  font-size: 24px;
  letter-spacing: 4px;
  background: linear-gradient(90deg, #4fc3f7, #7c9eff);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.login-input {
  width: 100%;
  height: 46px;
}

/* 输入框深色化 */
.login-input :deep(.el-input__wrapper) {
  background: rgba(255, 255, 255, 0.06);
  box-shadow: 0 0 0 1px rgba(120, 180, 255, 0.2) inset;
  border-radius: 10px;
  transition: box-shadow 0.25s ease, background 0.25s ease;
}

.login-input :deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px rgba(120, 180, 255, 0.45) inset;
}

.login-input :deep(.el-input__wrapper.is-focus) {
  background: rgba(255, 255, 255, 0.09);
  box-shadow: 0 0 0 1px #4fc3f7 inset, 0 0 16px rgba(79, 195, 247, 0.25);
}

.login-input :deep(.el-input__inner) {
  color: #e8f1ff;
}

.login-input :deep(.el-input__inner::placeholder) {
  color: rgba(160, 190, 235, 0.45);
}

.login-input :deep(.el-input__prefix),
.login-input :deep(.el-input__suffix) {
  color: rgba(160, 190, 235, 0.6);
}

.login-submit {
  margin-top: 14px;
  display: flex;
  justify-content: center;
}

.submit-btn {
  width: 100%;
  height: 46px;
  font-size: 16px;
  letter-spacing: 6px;
  border: none;
  border-radius: 10px;
  background: linear-gradient(90deg, #3a9cfd, #6a5cff);
  box-shadow: 0 6px 20px rgba(74, 124, 255, 0.35);
  transition: transform 0.2s ease, box-shadow 0.2s ease, filter 0.2s ease;
}

.submit-btn:hover {
  transform: translateY(-2px);
  filter: brightness(1.1);
  box-shadow: 0 10px 26px rgba(74, 124, 255, 0.5);
}

.submit-btn:active {
  transform: translateY(0);
}

.register-link {
  text-align: center;
  font-size: 13px;
  color: rgba(160, 190, 235, 0.6);
}

.register-link span {
  color: #4fc3f7;
  cursor: pointer;
  transition: color 0.2s ease;
}

.register-link span:hover {
  color: #8fd6ff;
  text-decoration: underline;
}

:deep(.el-select) {
  width: 100%;
}

/* 新版 el-select 深色化（使用 .el-select__wrapper） */
.login-input :deep(.el-select__wrapper) {
  background: rgba(255, 255, 255, 0.06);
  box-shadow: 0 0 0 1px rgba(120, 180, 255, 0.2) inset;
  border-radius: 10px;
  min-height: 46px;
  transition: box-shadow 0.25s ease, background 0.25s ease;
}

.login-input :deep(.el-select__wrapper:hover) {
  box-shadow: 0 0 0 1px rgba(120, 180, 255, 0.45) inset;
}

.login-input :deep(.el-select__wrapper.is-focused) {
  background: rgba(255, 255, 255, 0.09);
  box-shadow: 0 0 0 1px #4fc3f7 inset, 0 0 16px rgba(79, 195, 247, 0.25);
}

.login-input :deep(.el-select__placeholder) {
  color: rgba(160, 190, 235, 0.45);
}

.login-input :deep(.el-select__selected-item),
.login-input :deep(.el-select__placeholder.is-transparent) {
  color: #e8f1ff;
}

.login-input :deep(.el-select__suffix) {
  color: rgba(160, 190, 235, 0.6);
}
</style>

<!-- 下拉弹层挂载在 body 上，需要非 scoped 样式 -->
<style>
.login-select-popper.el-select__popper {
  background: rgba(12, 22, 48, 0.95);
  border: 1px solid rgba(120, 180, 255, 0.25);
  backdrop-filter: blur(12px);
}

.login-select-popper .el-select-dropdown__item {
  color: #cfdcf5;
}

.login-select-popper .el-select-dropdown__item:hover,
.login-select-popper .el-select-dropdown__item.is-hovering {
  background: rgba(64, 158, 255, 0.15);
}

.login-select-popper .el-select-dropdown__item.is-selected {
  color: #4fc3f7;
}

.login-select-popper .el-popper__arrow::before {
  background: rgba(12, 22, 48, 0.95);
  border-color: rgba(120, 180, 255, 0.25);
}
</style>
