import { createRouter, createWebHistory } from "vue-router";
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
      redirect: "/login",
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
      meta: { title: "卫星" },
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
          component: () => import("@/views/weixing/weixing.vue"),
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
        
      ],
    },

    // {
    //   path: "/satellite",
    //   name: "satellite",
    //   meta: { title: "卫星" },
    //   component: () => import("@/views/main/main.vue"),
    //   children: [
    //     {
    //       path: "example",
    //       name: "example",
    //       meta: { title: "示例" },
    //       component: () => import("@/components/BackendData.vue"),
    //     },
    //   ],
    // },

  ],
});

import defaultSettings from "@/settings";

//路由全局前置钩子
router.beforeEach((to, from, next) => {
  NProgress.start();
  document.title = `${to.meta.title || ''} - ${defaultSettings.title}`;
  let token = localStorage.getItem("token");
  if (token) {
    next();
  } else {
    if (to.path === "/login" || to.path === "/register") {
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




// import { createRouter, createWebHistory } from "vue-router";
// import NProgress from "nprogress"; //进度条
// import "nprogress/nprogress.css";
// import defaultSettings from "../settings";

// NProgress.configure({
//   showSpinner: false, //通过将其设置为 false 来关闭加载微调器。
// });

// const routes = [
//   {
//     path: '/',
//     redirect: '/login'
//   },
//   {
//     path: '/login',
//     name: 'login',
//     component: () => import('../views/login/Login.vue')
//   },
//   {
//     path: '/register',
//     name: 'register',
//     component: () => import('../views/login/Register.vue')
//   },
//   {
//     path: '/home',
//     name: 'home',
//     component: () => import('../components/BackendData.vue')
//   },
//   // {
//   //   path: "/media",
//   //   name: "media",
//   //   meta: { title: "媒体" },
//   //   component: () => import("@/views/main/main.vue"),
//   //   children: [
//   //     {
//   //       path: "list",
//   //       name: "media-list",
//   //       meta: { title: "媒体资源列表" },
//   //       component: () => import("@/views/media/media-list.vue"),
//   //     },
//   //   ],
//   // },

//   // {
//   //   path: "/user",
//   //   name: "user",
//   //   meta: { title: "用户" },
//   //   component: () => import("@/views/main/main.vue"),
//   //   children: [
//   //     {
//   //       path: "list",
//   //       name: "user-list",
//   //       meta: { title: "出版社管理" },
//   //       component: () => import("@/views/user/user-list.vue"),
//   //     },
//   //   ],
//   // },

//   // {
//   //   path: "/dd",
//   //   name: "dd",
//   //   meta: { title: "用户" },
//   //   component: () => import("@/views/main/main.vue"),
//   //   children: [
//   //     {
//   //       path: "ddgl",
//   //       name: "user-list",
//   //       meta: { title: "用户列表" },
//   //       component: () => import("@/views/ddgl/ddgl.vue"),
//   //     },
//   //   ],
//   // },

// //   // 卖家管理
// //   {
// //     path: "/cs",
// //     name: "cs",
// //     meta: { title: "卖家管理" },
// //     component: () => import("@/views/main/main.vue"),
// //     children: [
// //       {
// //         path: "csgl",
// //         name: "csgl",
// //         meta: { title: "卖家管理" },
// //         component: () => import("@/views/csgl/csgl.vue"),
// //       },
// //     ],
// //   },

// //   // 商品管理
// //   {
// //     path: "/sp",
// //     name: "sp",
// //     meta: { title: "商品管理" },
// //     component: () => import("@/views/main/main.vue"),
// //     children: [
// //       {
// //         path: "spgl",
// //         name: "spgl",
// //         meta: { title: "商品管理" },
// //         component: () => import("@/views/spgl/spgl.vue"),
// //       },
// //     ],
// //   },
// ]

// const router = createRouter({
//   history: createWebHistory(import.meta.env.BASE_URL),
//   routes
// });

// import defaultSettings from "@/settings";

// //路由全局前置钩子
// router.beforeEach((to, from, next) => {
//   NProgress.start();
//   document.title = `${defaultSettings.title}`;
//   let token = localStorage.getItem("token");
//   if (token) {
//     next();
//   } else {
//     if (to.path == "/login") {
//       next();
//     } else {
//       next({
//         path: "/login",
//       });
//     }
//   }
// });

// // //路由全局后置钩子
// router.afterEach(() => {
//   NProgress.done();
// });

// export default router;
