export default{
  title: "卫星可视化系统"
}

//settings.js 里的 `title` 是一个 JavaScript 配置项，通常用于在 Vue 或其他前端框架中动态设置网页标题或显示系统名称。
//`index.html` 里的 `<title>` 标签是静态的，决定了页面初始加载时浏览器标签栏显示的标题。

//如果没有调用 settings.js 里的 `title`，网页标题会以 `index.html` 文件中的 `<title>` 标签为准。只有在代码里主动设置 `document.title` 时，才会覆盖 `index.html` 的标题。否则，浏览器显示的就是 `index.html` 里的内容。例如，下面这样才会覆盖：
// import settings from './settings.js';
// document.title = settings.title;

//如果不需要 settings.js 文件中的 `title` 配置，直接删除该文件即可，不会影响项目运行（前提是没有其他地方引用它）。如果有地方引用了 `settings.title`，比如设置网页标题或显示系统名称，删除后相关功能会失效或报错。  