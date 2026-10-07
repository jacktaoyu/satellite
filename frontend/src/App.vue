<script setup>

</script>

<template>
  <RouterView />
</template>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html,
body,
#app {
  height: 100%;
}

body {
  font-family: 'Arial', 'PingFang SC', 'Microsoft YaHei', sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  height: 100vh;
  /* 全局深空底色：避免路由切换/加载间隙闪出浅色背景 */
  background-color: #030812;
  color: #cfe8ff;
}

/* ---------- 全局滚动条：深色科技风 ---------- */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}
::-webkit-scrollbar-track {
  background: rgba(0, 220, 255, 0.04);
}
::-webkit-scrollbar-thumb {
  background: rgba(0, 220, 255, 0.22);
  border-radius: 4px;
}
::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 220, 255, 0.4);
}
</style>
