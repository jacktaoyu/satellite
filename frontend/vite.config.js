import { fileURLToPath, URL } from "node:url";
import cesium from 'vite-plugin-cesium';
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

// https://cn.vitejs.dev/config/
export default defineConfig({
  server: {
    host: "127.0.0.1",
    port: 5173,
  }, //指定开发服务器运行的地址和端口
  plugins: [
    vue(),
    cesium()
  ], //指定要使用的插件
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    }, //路径别名（alias）配置："@" 定义了一个别名符号 @；fileURLToPath(new URL("./src", import.meta.url))将 src 目录转换为绝对路径,这样在代码中可以使用 @ 来引用 src 目录下的文件
       // 示例'../../components/Component.vue' = '@/components/Component.vue'
  },
});

  // server: {
  //   proxy: {
  //     '/api': {
  //       target: 'http://localhost:3000',
  //       changeOrigin: true,
  //       rewrite: (path) => path.replace(/^\/api/, '')
  //     }
  //   }
  // }

