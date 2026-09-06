<template>
  <div class="register-container">
    <el-card class="box-card">
      <div class="register-body">
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
            />
          </el-form-item>

          <el-form-item prop="password">
            <el-input 
              v-model="registerForm.password" 
              type="password"
              placeholder="请输入密码"
              prefix-icon="Lock"
              show-password
            />
          </el-form-item>

          <el-form-item prop="confirmPassword">
            <el-input 
              v-model="registerForm.confirmPassword" 
              type="password"
              placeholder="请确认密码"
              prefix-icon="Lock"
              show-password
            />
          </el-form-item>

          <div class="register-submit">
            <el-button type="primary" @click="submitForm" class="submit-btn" :loading="submitting">注册</el-button>
            <el-button @click="$router.push('/login')" class="submit-btn">返回登录</el-button>
          </div>
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
.register-container {
  background-image: url('/src/assets/bj.jpg');
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  width: 100%;
  padding: 20px;
}

.box-card {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 15px;
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.1);
  backdrop-filter: blur(10px);
}

.register-body {
  padding: 40px;
  width: 400px;
}

.register-title {
  padding-bottom: 40px;
  text-align: center;
  font-weight: 600;
  font-size: 28px;
  color: #409EFF;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.register-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.register-form :deep(.el-form-item) {
  margin-bottom: 0;
}

.register-form :deep(.el-input__wrapper) {
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.05);
  border-radius: 8px;
}

.register-form :deep(.el-input__inner) {
  height: 45px;
}

.register-submit {
  margin-top: 30px;
  display: flex;
  justify-content: center;
  gap: 20px;
}

.submit-btn {
  width: 120px;
  height: 40px;
  font-size: 16px;
}

:deep(.el-button) {
  border-radius: 8px;
}
</style>
