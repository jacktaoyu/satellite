<!-- <template>
    <div class="yongli-container">
      <el-button @click="takeScreenshot">截图</el-button>
      <img v-if="imageUrl" :src="imageUrl" class="screenshot" /> 
    </div>
  </template>
  
  <script setup>
  // import { ref, inject } from 'vue';
  
  // const imageUrl = ref(null);
  // const captureScreenshot = inject('captureScreenshot');
  
  // async function takeScreenshot() {
  //   const minLon = 116.3;
  //   const minLat = 39.9;
  //   const maxLon = 116.5;
  //   const maxLat = 40.1;
  //   imageUrl.value = await captureScreenshot(minLon, minLat, maxLon, maxLat);
  //   }
  </script>
  
  <style scoped>
  /* .yongli-container {
    padding: 20px;
  }
  .screenshot {
    margin-top: 20px;
    max-width: 100%;
    border: 1px solid #ddd;
  } */
  </style> -->
<!-- 显示组件 -->
<template>
  <div>
    <img v-if="imageUrl" :src="imageUrl" alt="Canvas截图" />
  </div>
</template>

<script>
export default {
  props: ['imageUrl'],
};
</script>