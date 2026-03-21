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

          <el-form-item prop="userType">
            <el-select 
              v-model="registerForm.userType"
              placeholder="请选择用户类型"
              style="width: 100%"
            >
              <el-option
                v-for="item in userTypes"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </el-form-item>

          <div class="register-submit">
            <el-button type="primary" @click="submitForm" class="submit-btn">注册</el-button>
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
        userType: ''
      },
      userTypes: [
        {
          value: '1',
          label: '管理员'
        },
        // {
        //   value: '2',
        //   label: '老板'
        // },
        {
          value: '3',
          label: '用户'
        }
      ],
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
        ],
        userType: [
          { required: true, message: '请选择用户类型', trigger: 'change' }
        ]
      }
    }
  },
  methods: {
    submitForm() {
      this.$refs.form.validate((valid) => {
        if (valid) {
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
          }).catch(err => {
            this.$message.error('注册失败：' + err.message)
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
