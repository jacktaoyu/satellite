// import { createApp } from 'vue'
// import './style.css'
// import App from './App.vue'

// createApp(App).mount('#app')


import { createApp } from "vue";
import App from "./App.vue";
import router from "./router";
import request from "@/utils/request.js";
import "normalize.css/normalize.css"; //重置默认css样式
// import deepClone from "@/utils/deepClone.js"; //深拷贝函数
import ElementPlus from "element-plus";
import "element-plus/dist/index.css";
import zhCn from "element-plus/es/locale/lang/zh-cn";
import * as ElementPlusIconsVue from "@element-plus/icons-vue";
// import { uploadFile } from "@/utils/utils.js";

// import * as echarts from 'echarts';




const app = createApp(App); // 使用 Vue 3 的 API 创建一个应用实例（`app`）。 `App` 是根组件（通常是 `App.vue`），作为整个应用的入口。 这个 `app` 实例后续可以用来注册全局组件、插件、配置全局属性等。简单理解：这行代码就是“启动一个 Vue 应用，并以 App 组件为根”。

for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component);
}

app.config.globalProperties.$request = request; //使用 app.config.globalProperties 配置(注册)全局属性
// app.config.globalProperties.$deepClone = deepClone;
// app.config.globalProperties.$uploadFile = uploadFile;
// app.config.globalProperties.$echarts = echarts;

app.use(router); //使用 app.use() 方法配置(注册)路由
app.use(ElementPlus, { locale: zhCn }); //使用 app.use() 方法配置(注册) ElementPlus
app.mount("#app"); //使用 app.mount() 方法挂载应用
