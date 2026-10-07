// import { createApp } from 'vue'
// import './style.css'
// import App from './App.vue'

// createApp(App).mount('#app')


import { createApp } from "vue";
import App from "./App.vue";
import router from "./router";
import request from "@/utils/request.js";
import "normalize.css/normalize.css"; //重置默认css样式
import ElementPlus from "element-plus";
import "element-plus/dist/index.css";
import "./styles/dark-tech.css"; // 管理页深色 HUD 科技风全局覆盖样式
import zhCn from "element-plus/es/locale/lang/zh-cn";
// 图标按需注册：原先全量注册近 300 个图标组件全部打进 vendor 包；
// 这里只注册模板中以 <IconName /> 或字符串 prefix-icon 形式用到的少量图标，
// 其余以 :icon="Xxx" 绑定使用的图标在各页面已自行 import，不受影响
import {
  Aim, Box, Check, CircleCheck, CircleCheckFilled, Clock, Connection, Cpu,
  DataAnalysis, Document, Edit, FullScreen, Histogram, InfoFilled, Lightning,
  List, Location, Lock, MapLocation, Monitor, OfficeBuilding, Operation,
  PieChart, Position, Refresh, Search, SetUp, Ship, Switch, Timer, Tools,
  TrendCharts, Upload, UploadFilled, User,
} from "@element-plus/icons-vue";

const app = createApp(App); // 使用 Vue 3 的 API 创建一个应用实例（`app`）。 `App` 是根组件（通常是 `App.vue`），作为整个应用的入口。 这个 `app` 实例后续可以用来注册全局组件、插件、配置全局属性等。简单理解：这行代码就是“启动一个 Vue 应用，并以 App 组件为根”。

for (const component of [
  Aim, Box, Check, CircleCheck, CircleCheckFilled, Clock, Connection, Cpu,
  DataAnalysis, Document, Edit, FullScreen, Histogram, InfoFilled, Lightning,
  List, Location, Lock, MapLocation, Monitor, OfficeBuilding, Operation,
  PieChart, Position, Refresh, Search, SetUp, Ship, Switch, Timer, Tools,
  TrendCharts, Upload, UploadFilled, User,
]) {
  app.component(component.__name, component);
}

app.config.globalProperties.$request = request; //使用 app.config.globalProperties 配置(注册)全局属性

app.use(router); //使用 app.use() 方法配置(注册)路由
app.use(ElementPlus, { locale: zhCn }); //使用 app.use() 方法配置(注册) ElementPlus
app.mount("#app"); //使用 app.mount() 方法挂载应用
