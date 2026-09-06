<template>
  <div class="register-container">
    <div class="back-portal" @click="$router.push('/portal')">← 返回首页</div>
    <el-card class="box-card">
      <div class="register-body">
        <!-- 品牌区：与登录页一致的 logo + 系统名 -->
        <div class="brand">
          <div class="brand-logo">
            <svg viewBox="0 0 24 24" fill="none" width="28" height="28">
              <path d="M12 2l2.4 7.6L22 12l-7.6 2.4L12 22l-2.4-7.6L2 12l7.6-2.4L12 2z" fill="#4fc3f7"/>
            </svg>
          </div>
          <div class="brand-name">智能星簇协同运行验证系统</div>
          <div class="brand-sub">SATELLITE CLUSTER COLLABORATIVE PLATFORM</div>
        </div>
        <div class="register-title">用户注册</div>
        <el-form 
          ref="form" 
          :model="registerForm" 
          :rules="rules"
          class="register-form"
        >
          <el-form-item prop="username">
            <el-input 
              v-model="registerForm.username" 
              placeholder="请输入用户名"
              prefix-icon="User"
              class="register-input"
            />
          </el-form-item>

          <el-form-item prop="password">
            <el-input 
              v-model="registerForm.password" 
              type="password"
              placeholder="请输入密码"
              prefix-icon="Lock"
              show-password
              class="register-input"
            />
          </el-form-item>

          <el-form-item prop="confirmPassword">
            <el-input 
              v-model="registerForm.confirmPassword" 
              type="password"
              placeholder="请确认密码"
              prefix-icon="Lock"
              show-password
              class="register-input"
            />
          </el-form-item>

          <div class="register-submit">
            <el-button type="primary" @click="submitForm" class="submit-btn" :loading="submitting">注 册</el-button>
          </div>
          <div class="login-link">已有账号？<span @click="$router.push('/login')">返回登录</span></div>
        </el-form>
      </div>
    </el-card>
  </div>
</template>

<script>
export default {
  name: 'Register',
  data() {
    // 密码验证规则
    const validatePass = (rule, value, callback) => {
      if (value === '') {
        callback(new Error('请输入密码'))
      } else {
        if (this.registerForm.confirmPassword !== '') {
          this.$refs.form.validateField('confirmPassword')
        }
        callback()
      }
    }
    // 确认密码验证规则
    const validatePass2 = (rule, value, callback) => {
      if (value === '') {
        callback(new Error('请再次输入密码'))
      } else if (value !== this.registerForm.password) {
        callback(new Error('两次输入密码不一致!'))
      } else {
        callback()
      }
    }

    return {
      registerForm: {
        username: '',
        password: '',
        confirmPassword: '',
        userType: '3' // 注册仅允许普通用户（管理员由后端/后台创建），前端不再提供用户类型选择
      },
      rules: {
        username: [
          { required: true, message: '请输入用户名', trigger: 'blur' },
          { min: 3, max: 20, message: '长度在 3 到 20 个字符', trigger: 'blur' }
        ],
        password: [
          { required: true, validator: validatePass, trigger: 'blur' },
          { min: 6, message: '密码长度至少为6个字符', trigger: 'blur' }
        ],
        confirmPassword: [
          { required: true, validator: validatePass2, trigger: 'blur' }
        ]
      },
      submitting: false // 注册请求进行中，防止连续点击重复提交/重复弹提示
    }
  },
  methods: {
    submitForm() {
      if (this.submitting) return; // 节流：请求未结束时忽略重复点击
      this.$refs.form.validate((valid) => {
        if (valid) {
          this.submitting = true;
          this.$request.post('/register/', {
            username: this.registerForm.username,
            password: this.registerForm.password,
            value: this.registerForm.userType
          }).then(res => {
            if (res.data.meta.status === 200) {
              this.$message.success('注册成功')
              this.$router.push('/login')
            } else {
              this.$message.error(res.data.meta.message || '注册失败')
            }
          }).catch(() => {
            // 错误提示已由 request.js 响应拦截器统一弹出，这里仅吞掉 rejection，避免重复提示与未捕获异常
          }).finally(() => {
            this.submitting = false;
          })
        }
      })
    }
  }
}
</script>

<style scoped>
@keyframes card-in {
  from { opacity: 0; transform: translateY(24px); }
  to { opacity: 1; transform: translateY(0); }
}

.register-container {
  /* 与登录页一致的深空底色，替代旧的风景图背景 */
  background:
    radial-gradient(ellipse 70% 55% at 68% 42%, rgba(20, 45, 95, 0.55), transparent 70%),
    radial-gradient(ellipse 45% 40% at 25% 75%, rgba(30, 60, 120, 0.35), transparent 70%),
    #050b1a;
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  width: 100%;
  padding: 20px;
}

.back-portal {
  position: fixed;
  top: 24px;
  left: 28px;
  font-size: 13px;
  letter-spacing: 1px;
  color: rgba(160, 190, 235, 0.7);
  cursor: pointer;
  padding: 8px 16px;
  border: 1px solid rgba(120, 180, 255, 0.25);
  border-radius: 999px;
  background: rgba(10, 18, 40, 0.4);
  backdrop-filter: blur(8px);
  transition: color 0.2s ease, border-color 0.2s ease;
  z-index: 10;
}

.back-portal:hover {
  color: #8fd6ff;
  border-color: rgba(120, 180, 255, 0.5);
}

.box-card {
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

.register-body {
  padding: 40px 44px 32px;
  width: 420px;
}

/* 品牌区（与登录页一致） */
.brand {
  text-align: center;
  margin-bottom: 24px;
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
  animation: logo-pulse 3s ease-in-out infinite;
}

@keyframes logo-pulse {
  0%, 100% { box-shadow: 0 0 20px rgba(64, 158, 255, 0.25); }
  50% { box-shadow: 0 0 30px rgba(79, 195, 247, 0.55), 0 0 60px rgba(79, 195, 247, 0.2); }
}

.brand-name {
  font-size: 19px;
  font-weight: 600;
  letter-spacing: 2px;
  color: #e8f1ff;
}

.brand-sub {
  margin-top: 6px;
  font-size: 9px;
  letter-spacing: 1.5px;
  white-space: nowrap;
  color: rgba(160, 190, 235, 0.55);
}

.register-title {
  padding-bottom: 26px;
  text-align: center;
  font-weight: 600;
  font-size: 24px;
  letter-spacing: 4px;
  background: linear-gradient(90deg, #4fc3f7, #7c9eff);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

.register-form {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.register-form :deep(.el-form-item) {
  margin-bottom: 0;
}

.register-input {
  width: 100%;
  height: 46px;
}

/* 输入框深色化（与登录页一致） */
.register-input :deep(.el-input__wrapper) {
  background: rgba(255, 255, 255, 0.06);
  box-shadow: 0 0 0 1px rgba(120, 180, 255, 0.2) inset;
  border-radius: 10px;
  transition: box-shadow 0.25s ease, background 0.25s ease;
}

.register-input :deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px rgba(120, 180, 255, 0.45) inset;
}

.register-input :deep(.el-input__wrapper.is-focus) {
  background: rgba(255, 255, 255, 0.09);
  box-shadow: 0 0 0 1px #4fc3f7 inset, 0 0 16px rgba(79, 195, 247, 0.25);
}

.register-input :deep(.el-input__inner) {
  color: #e8f1ff;
  height: 46px;
}

.register-input :deep(.el-input__inner::placeholder) {
  color: rgba(160, 190, 235, 0.45);
}

.register-input :deep(.el-input__prefix),
.register-input :deep(.el-input__suffix) {
  color: rgba(160, 190, 235, 0.6);
}

.register-submit {
  margin-top: 12px;
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

.login-link {
  text-align: center;
  font-size: 13px;
  color: rgba(160, 190, 235, 0.6);
}

.login-link span {
  color: #4fc3f7;
  cursor: pointer;
  transition: color 0.2s ease;
}

.login-link span:hover {
  color: #8fd6ff;
  text-decoration: underline;
}
</style>
