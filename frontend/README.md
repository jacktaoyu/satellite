# Vue 3 + Vite

This template should help get you started developing with Vue 3 in Vite. The template uses Vue 3 `<script setup>` SFCs, check out the [script setup docs](https://v3.vuejs.org/api/sfc-script-setup.html#sfc-script-setup) to learn more.

Learn more about IDE Support for Vue in the [Vue Docs Scaling up Guide](https://vuejs.org/guide/scaling-up/tooling.html#ide-support).


=================项目结构==================
index.html: 项目的主 HTML 文件，包含一个 `div` 元素作为 Vue 应用的挂载点。
package.json: 项目的 npm 配置文件，包含项目的依赖和脚本，是手动编辑的，通常包括项目名称、版本、描述等基本信息。
package-lock.json：是自动生成的，用于锁定依赖的确切版本，确保一致性，npm install的依据。
`public/`: 公共资源目录
`src/`: 源代码目录
    App.vue: Vue 应用的根组件。
    `assets/`: 资源目录
    `components/`: 组件目录
        HelloWorld.vue: 示例组件，展示了一个简单的计数器功能。
    main.js: 应用的入口文件，创建并挂载 Vue 应用。
    style.css: 全局样式文件。
vite.config.js: Vite 的配置文件，配置了 Vue 插件。

================运行流程==============
该项目是一个使用 Vite 和 Vue 构建的前端项目。以下是项目的运行流程介绍：

### 1. 按照vite.config.js启动开发服务器
在项目根目录下运行以下命令启动 Vite 开发服务器：
```sh
npm run dev
```
这会启动一个本地开发服务器，并在浏览器中打开项目。

### 2. 加载 index.html
浏览器请求 index.html 文件，这是项目的入口 HTML 文件。
- `<div id="app"></div>`：这是 Vue 应用的挂载点。
- `<script type="module" src="/src/main.js"></script>`：加载并执行 `src/main.js` 文件，这是 Vue 应用的入口文件。将main.js里的vue实例渲染到index.html里的id=‘app’的标签上。

### 3. 加载 `main.js`
`main.js` 文件创建并挂载 Vue 应用。示例代码如下：
- `import { createApp } from 'vue'`：从 Vue 库中导入 `createApp` 函数。
- `import App from './App.vue'`：导入根组件 `App.vue`。
- `createApp(App).mount('#app')`：创建 Vue 应用实例，并将其挂载到 `#app` 元素上。

### 4. 渲染 Vue 组件
`App.vue` 是 Vue 应用的根组件，定义了应用的结构和逻辑。示例代码如下：
- `<template>`：定义组件的模板。
- `<script>`：定义组件的逻辑，包括导入子组件 `HelloWorld`。

### 5. 加载和渲染子组件
`HelloWorld.vue` 是一个示例子组件，展示了一个简单的计数器功能。
- `<template>`：定义组件的模板。
- `<script>`：定义组件的逻辑，包括数据和方法。

### 总结
1. 启动开发服务器。
2. 加载 index.html，并通过 `<script>` 标签加载 `main.js`。
3. `main.js` 创建并挂载 Vue 应用。
4. 渲染根组件 `App.vue`，并加载和渲染子组件 ，如`Login.vue`。



===============文件注释================
package.json:
{
  "name": "frontend", // 项目名称
  "private": true, // 指示该项目是私有的，不能发布到 npm
  "version": "0.0.0", // 项目版本号
  "type": "module", // 指定模块类型为 ES 模块
  "scripts": {
    "dev": "vite", // 启动开发服务器的命令
    "build": "vite build", // 构建项目的命令
    "preview": "vite preview" // 预览构建结果的命令
  },
  "dependencies": {
    "vue": "^3.5.13" // 项目的运行时依赖，Vue.js 版本 3.5.13 或更高版本
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.2.1", // 开发时依赖的 Vite Vue 插件，版本 5.2.1 或更高版本
    "vite": "^6.2.0" // 开发时依赖的 Vite 构建工具，版本 6.2.0 或更高版本
  }
}