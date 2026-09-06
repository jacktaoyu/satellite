import { createRouter, createWebHistory } from "vue-router";
import { ElMessage } from "element-plus";
import NProgress from "nprogress"; //进度条
import "nprogress/nprogress.css";

NProgress.configure({
  showSpinner: false, //通过将其设置为 false 来关闭加载微调器。
});

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: "/",
      redirect: "/portal",
      hidden: true,
    },
    {
      path: "/portal",
      name: "portal",
      meta: { title: "首页" },
      component: () => import("@/views/portal/Portal.vue"),
      hidden: true,
    },
    {
      path: "/login",
      name: "login",
      meta: { title: "登录" },
      component: () => import("@/views/login/Login.vue"), //@表示src目录
      hidden: true,
    },
    {
      path: "/register",
      name: "register",
      meta: { title: "注册" },
      component: () => import("@/views/login/Register.vue"),
      hidden: true,
    },
    {
      path: "/satellite",
      name: "satellite",
      // 该路由下所有子页面均为管理员专属（main.vue 菜单仅 isAdmin==1 时渲染）
      meta: { title: "卫星", requiresAdmin: true },
      component: () => import("@/views/main/main.vue"),
      children: [
        {
          path: "satellite_network",
          name: "satellite_network",
          meta: { title: "卫星网络" },
          component: () => import("@/views/Satellite_network.vue"),
        },
        {
          path: "Weixing",
          meta: { title: "卫星" },
          component: () => import("@/views/weixing/Weixing.vue"),
        },
        {
          path: "Weixing/info/:name",
          component: () => import("@/views/weixing/Weixing_info.vue"),
        },
        {
          path: "renwu",
          name: "renwu",
          meta: { title: "任务" },
          // component: () => import("@/views/Renwu/Shuxing.vue"),
          children: [
            {
              path: "shuxing",
              name: "shuxing",
              meta: { title: "属性" },
              component: () => import("@/views/Renwu/Shuxing.vue"),
            },
            {
              path: "shezhi",
              name: "shezhi",
              meta: { title: "设置" },
              component: () => import("@/views/Renwu/Shezhi.vue"),
            },
          ],
        },
        {
          path: "Xingcu",
          name: "Xingcu",
          meta: { title: "星簇" },
          component: () => import("@/views/Xingcu.vue"),
        },
        {
          path: "ground_station",
          meta: { title: "地面站" },
          component: () => import("@/views/GroundStation.vue"),
        },
        {
          path: "Yongli",
          name: "Yongli",
          meta: { title: "用例" },
          component: () => import("@/views/Yongli.vue"),
        },
        {
          path: "Xingneng",
          name: "Xingneng",
          meta: { title: "性能" },
          component: () => import("@/views/Xingneng.vue"),
        },
        {
          path: "system_settings",
          name: "system_settings",
          meta: { title: "系统设置" },
          component: () => import("@/views/SystemSettings.vue"),
        },
        {
          path: "network_parameters",
          name: "network_parameters",
          meta: { title: "按载荷批量设置" },
          component: () => import("@/views/NetworkParameters.vue"),
        },
        
      ],
    },

    {
      // 兜底路由：未匹配路径复用登录页（登录页含返回首页入口，且全局守卫会按 token 状态重定向），
      // 保留现状，后续如有需要可替换为独立的 404 页面
      path: "/:pathMatch(.*)*",
      name: "not-found",
      meta: { title: "页面不存在" },
      component: () => import("@/views/login/Login.vue"),
      hidden: true,
    },
  ],
});

import defaultSettings from "@/settings";

//路由全局前置钩子
router.beforeEach((to, from, next) => {
  NProgress.start();
  document.title = `${to.meta.title || ''} - ${defaultSettings.title}`;
  // 注意：此处仅做 localStorage 层面的 UX 拦截，token 可能已过期或伪造；
  // 真正的鉴权在服务端（后端全局 before_request 校验 Ac-Token），服务端返回 401 时由 request.js / authFetch.js 统一清理登录态并跳转登录页
  let token = localStorage.getItem("token");
  if (token) {
    // 管理员专属路由：非管理员重定向到首页并提示
    if (to.matched.some((record) => record.meta.requiresAdmin) && localStorage.getItem("isAdmin") != 1) {
      ElMessage.warning("无权限访问该页面，请联系管理员");
      next({ path: "/portal" });
      return;
    }
    next();
  } else {
    if (to.path === "/portal" || to.path === "/login" || to.path === "/register") {
      next();
    } else {
      next({
        path: "/login",
      });
    }
  }
});

//路由全局后置钩子
router.afterEach(() => {
  NProgress.done();
});

export default router;
