<template>
  <div class="login-container">
      <el-card class="box-card">
          <div class="login-body">
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
                    @keyup.enter.native="login" 
                    show-password
                    prefix-icon="Lock"
                  />

                  <el-select 
                    v-model="userForm.value" 
                    clearable 
                    placeholder="请选择用户类型" 
                    class="login-input"
                  >
                      <el-option 
                        v-for="item in options" 
                        :key="item.value" 
                        :label="item.label" 
                        :value="item.value"
                      />
                  </el-select>

                  <div class="login-submit">
                      <el-button type="primary" @click="login" class="submit-btn">登录</el-button>
                      <el-button type="warning" @click="$router.push('/register')" class="submit-btn">注册</el-button>
                  </div>
              </el-form>
          </div>
      </el-card>
  </div>
</template>

<script>
export default {
  name: "login",
  data() {
      return {
          userForm: {
              accountNumber: '',
              userPassword: '',
              value: ''
          },
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
          this.$request.post("/login/", { // 向后端发送登录请求
              username: this.userForm.accountNumber, //username从表单对象userForm中获取账号
              password: this.userForm.userPassword,
              // value: this.userForm.value
              value: 1 //暂时写死为管理员登录
          }).then(res => { //this.$request.post() 返回一个 Promise 对象。.then() 是 Promise 的方法，用于处理异步操作成功的结果。回调函数的参数 res 是请求成功后服务端返回的响应数据。箭头函数的作用是定义一个匿名函数，并在箭头函数内部执行异步操作，箭头函数语法：(参数) => { 函数体 }。res 仅在箭头函数内部有效，通过.then()处理异步响应
              console.log(res);
              if (res.data.meta.status === 200) {
                  localStorage.setItem("userInfo", res.data.data.username); //存储用户信息
                  localStorage.setItem("userInfoid", res.data.data.user_id);
                  localStorage.setItem("img_url_touxiang", res.data.data.img_url);
                  localStorage.setItem("jianjie", res.data.data.jianjie);
                  localStorage.setItem("isAdmin", res.data.data.isAdmin);
                  localStorage.setItem("token", res.data.data.token);
                  this.$message.success("登录成功") //提示成功消息
                  if (this.userForm.value == 3) {
                      this.$router.push('/home/index') //跳转页面
                      return
                  }
                  if (res.data.data.isAdmin == 1) { 
                      this.$router.replace({ path: '/satellite/satellite_network' }); 
                  } else { 
                      this.$router.push('/satellite/satellite_network') //路由API区别：push添加新历史记录（浏览器后退可返回上一页）;replace替换当前历史记录（后退跳过当前页）。
                  }
              } else {
                  this.$message.error(res.data.meta.message); //提示错误消息
              }
          });
      }
  } //
}
</script>
<!-- res结构{
  data: {},      // 服务端返回的响应体（核心业务数据），即后端的ret
  status: 200,   // HTTP 状态码（如 200、404、500）
  statusText: 'OK', // HTTP 状态文本（如 "OK"、"Not Found"）
  headers: {},   // 响应头信息（如 Content-Type）
  config: {},    // 请求的配置信息（如 URL、method、headers）
  request: {}    // 底层 XMLHttpRequest 对象（浏览器环境）
} -->
<style scoped>
.login-container {
  background-image: url('/src/assets/bj.jpg'); /* 替换为你的图片路径 */
  background-size: cover; /* 背景图片覆盖整个元素 */
  background-position: center; /* 背景图片居中 */
  background-repeat: no-repeat; /* 不重复背景图片 */
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

.login-body {
  padding: 40px;
  width: 400px;
}

.login-title {
  padding-bottom: 40px;
  text-align: center;
  font-weight: 600;
  font-size: 28px;
  color: #409EFF;
  cursor: pointer;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.login-input {
  width: 100%;
  height: 45px;
}

.login-input :deep(.el-input__wrapper) {
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.05);
}

.login-submit {
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

:deep(.el-input__wrapper),
:deep(.el-select .el-input__wrapper) {
  border-radius: 8px;
}

:deep(.el-select) {
  width: 100%;
}
</style>