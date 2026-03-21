<template>
    <div id="cesiumContainer">
    </div>
</template>
  
<script setup>
  import { onMounted } from "vue";
  import * as Cesium from "cesium";
  import { provide } from 'vue';
  import { set } from "nprogress";
  import axios from 'axios';  // 添加这行
 
  
  onMounted(() => {
    // 设置 Cesium 的访问令牌
    Cesium.Ion.defaultAccessToken =
      "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiJhOTgxNzcyYS0zODlhLTRlMmQtYmQwNS0zYmQxODM2YTVjNzAiLCJpZCI6MjgwMTA2LCJpYXQiOjE3NDA3OTc0MjJ9.i8onOXvmyEYPLLkzb9lCWJPnq_mkiK4NaZc2N-VYsMQ"; 
    // ArcGIS影像图层 对浏览器会有压力
    // const esri = new Cesium.ArcGisMapServerImageryProvider({
    //   url:"https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer",
    //   enablePickFeatures:false
    // })
    const esri = new Cesium.OpenStreetMapImageryProvider({
      url: 'https://tile.openstreetmap.org/'
    });
    // 创建 Cesium 视图
    let viewer = new Cesium.Viewer("cesiumContainer", {
      // imageryProvider:esri ,// 自定义影像图层 ,默认是谷歌的影像图层
      // imageryProvider: new Cesium.IonImageryProvider({ assetId: 3812, accessToken: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiJhMTg2Mzk0My02NWJmLTQ1ODgtOWRiMy0wODM1ZTkwNGM1NTYiLCJpZCI6MjM0NzYsInNjb3BlcyI6WyJhc2wiLCJhc3IiLCJhc3ciLCJnYyJdLCJpYXQiOjE1ODM0NjEyMDN9.qXnJKCaIHS7JkIPRySJmmbdHvyj1ihQ2CI3itKy9MvY'}), // Bing 卫星影像
      // terrainProvider: Cesium.createWorldTerrain(), // 全球地形
      // timeline:false, // 时间轴控件
      // // shouldAnimate:true, // 是否播放动画
      // animation:false, // 动画控件
      // geocoder:false, // 地理编码搜索控件
      // homeButton:false, // 主页控件
      // sceneModePicker:false, // 投影方式控件
      // baseLayerPicker:false, // 图层选择控件
      // navigationHelpButton:false, // 帮助控件
      // navigationInstructionsInitiallyVisible:false,
      // fullscreenButton:false, //全屏控件
      // selectionIndicator:false,//选取指示器组件
      infoBox: false, // 信息框，If set to false, the InfoBox widget will not be created.点击的详情弹窗entity的description可以描述html显示在弹窗中,也可以通过viewer.infoBox.frame来接入访问
      contextOptions: {
          webgl:{
            alpha: true,
            depth:true,
            stencil:true,
            antialias:true,
            premultipliedAlpha:true,
            //通过canvas.toDataURL()实现截图需要将该项设置为true
            preserveDrawingBuffer:true,
            failIfMajorPerformanceCaveat:true
          }
        }
      // terrainProvider:Cesium.createWorldTerrain({
      //   requestWaterMask:true, // 水面特效 对浏览器会有压力
      // }),
    });
    //去掉版权信息
    viewer.clock.shouldAnimate = true;
    viewer._cesiumWidget._creditContainer.style.display = "none"
    // // 把cesium的动画开关打开
    // viewer.clock.shouldAnimate = true;
    // window.viewer = viewer;
    // localStorage.setItem("viewer", viewer);
    // 加载 CZML 数据
    const czmldata = Cesium.CzmlDataSource.load("/src/assets/wx.czml");
    viewer.dataSources.add(czmldata);
  
    // 别忘记把 Cesium 的动画开关打开
    viewer.clock.shouldAnimate = true;
  
    // 在 CZML 数据加载完成后，为特定卫星添加扫描圆锥并绑定点击事件
    czmldata.then((dataSource) => {
      console.log("CZML 数据加载完成");
  
      // 找到 ID 为 'Sat_1_1' 的卫星
      const satellite1 = dataSource.entities.getById("Satellite/Sat_1_1");
      const satellite2 = dataSource.entities.getById("Satellite/Sat_2_1");
      const satellite3 = dataSource.entities.getById("Satellite/Sat_3_1");
      // 找到所有 ID 以 "Sat_" 开头的卫星实体
      const satelliteEntities = [];
      dataSource.entities.values.forEach(entity => {
          if (entity.id.includes("Sat_")) {
              satelliteEntities.push(entity);
          }
      });
      // const satelliteEntities = dataSource.entities.values.filter(entity => 
      // entity.id.startsWith("Sat_"));
      console.log("satelliteEntities:", satelliteEntities);
      if (!satellite1) {
        console.error("未找到 ID 为 'Sat_1_1' 的卫星");
        return;
      }
  
      console.log("找到卫星：", satellite1);

      // 创建视锥体
      // orientation - 相机镜头对准的方法.
      //   heading - 代表镜头左右方向, 正值为右, 负值为左, 360度和0度是一样的
      // pitch - 代表镜头上下方向, 正值为上, 负值为下.
      //   roll - 代表镜头左右倾斜.正值, 向右倾斜, 负值向左倾斜
      // 默认hpr都为0，是正向朝北，沿着Y轴，按照东北上参考坐标系
      // 在全局作用域声明存储所有视锥体的Map
      let frustumPrimitives = new Map();
      let outlinePrimitives = new Map();
      function createFrustum(satellite) {
        // var height = 10000
        var length = 1000000
        const heading = Cesium.Math.toRadians(0);//正值绕Z轴顺时针旋转视角
        const pitch = Cesium.Math.toRadians(-90);//正值绕X轴向上旋转视角，默认值为-90
        const roll = Cesium.Math.toRadians(0);//正值绕Y轴瞬时针旋转视角

        function addFrustum(satellite) {
          // 如果已存在轮廓线，先移除
          if (frustumPrimitives.has(satellite.id)) {
            viewer.scene.primitives.remove(frustumPrimitives.get(satellite.id));
          }
          var position = satellite.position.getValue(viewer.clock.currentTime);
          // var position = new Cesium.CallbackProperty((time) => {
          //   return satellite.position.getValue(time);})
          // var secondPos = Cesium.Cartesian3.fromDegrees(108, 34, 0);
          let frustum = new Cesium.PerspectiveFrustum({
            // 查看的视场角，绕Z轴旋转，以弧度方式输入
            // fov: Cesium.Math.PI_OVER_THREE,
            fov: Cesium.Math.toRadians(50),
            // 视锥体的宽度/高度纵横比
            // aspectRatio: viewer.canvas.clientWidth / viewer.canvas.clientHeight
            aspectRatio: 1,
            // 近面距视点的距离
            near: 1,
            // 远面距视点的距离
            far: length,
          });
          // 东北上坐标系
          const heading = Cesium.Math.toRadians(0);//绕Z轴顺时针
          const pitch = Cesium.Math.toRadians(0);//绕Y轴逆时针
          const roll = Cesium.Math.toRadians(180);//绕X轴顺时针
          const hpr = new Cesium.HeadingPitchRoll(heading, pitch, roll);
          // hpr为0，朝向正上
          const orientation = Cesium.Transforms.headingPitchRollQuaternion(
            position,
            hpr
          );
          viewer.scene.globe.depthTestAgainstTerrain = true
          var converter = Cesium.Transforms.eastNorthUpToFixedFrame;
          var hprRollZero = new Cesium.HeadingPitchRoll();
          var modelMatrix = Cesium.Transforms.headingPitchRollToFixedFrame(position, hprRollZero, Cesium.Ellipsoid.WGS84, converter);
          let geometry = new Cesium.FrustumGeometry({
            frustum: frustum,
            origin: position,
            orientation: orientation,
            vertexFormat: Cesium.VertexFormat.POSITION_ONLY,
          });
          let instance = new Cesium.GeometryInstance({
            geometry: geometry,
            attributes: {
              color: Cesium.ColorGeometryInstanceAttribute.fromColor(
                // new Cesium.Color(0, 1, 0, 0.1)
                new Cesium.Color(0.0, 0.8627, 1.0, 0.5098)
              ),
            },
          });
          const frustumPrimitive = new Cesium.Primitive({
            geometryInstances: instance,
            appearance: new Cesium.PerInstanceColorAppearance({
              closed: true,
              flat: true,
            }),
            asynchronous: false,
          });
          viewer.scene.primitives.add(frustumPrimitive);
          frustumPrimitives.set(satellite.id, frustumPrimitive);
        }
        // 创建轮廓线     
        function addOutline(satellite) {
          // 如果已存在轮廓线，先移除
          if (outlinePrimitives.has(satellite.id)) {
            viewer.scene.primitives.remove(outlinePrimitives.get(satellite.id));
          }
          let frustum = new Cesium.PerspectiveFrustum({
            // 查看的视场角，绕Z轴旋转，以弧度方式输入
            // fov: Cesium.Math.PI_OVER_THREE,
            fov: Cesium.Math.toRadians(50),
            // 视锥体的宽度/高度纵横比
            // aspectRatio: viewer.canvas.clientWidth / viewer.canvas.clientHeight
            aspectRatio: 1,
            // 近面距视点的距离
            near: 1,
            // 远面距视点的距离
            far: length,
          });
          // var position = new Cesium.CallbackProperty((time) => {
          //   return satellite.position.getValue(time);})
          var position = satellite.position.getValue(viewer.clock.currentTime);
          // 东北上坐标系
          const heading = Cesium.Math.toRadians(0);//绕Z轴顺时针
          const pitch = Cesium.Math.toRadians(0);//绕Y轴逆时针
          const roll = Cesium.Math.toRadians(180);//绕X轴顺时针
          const hpr = new Cesium.HeadingPitchRoll(heading, pitch, roll);
          // hpr为0，朝向正上
          const orientation = Cesium.Transforms.headingPitchRollQuaternion(
            position,
            hpr
          );
          let geometry = new Cesium.FrustumOutlineGeometry({
            frustum: frustum,
            origin: position,
            orientation: orientation,
            vertexFormat: Cesium.VertexFormat.POSITION_ONLY,
          });
          let instance = new Cesium.GeometryInstance({
            geometry: geometry,
            attributes: {
              color: Cesium.ColorGeometryInstanceAttribute.fromColor(
                // new Cesium.Color(0.933, 0.698, 0.08, 1.0)
                new Cesium.Color(1.0, 1.0, 1.0, 1.0)
                // material: new Cesium.ColorMaterialProperty(
              //   Cesium.Color.fromCssColorString("#00dcff82")withAlpha(0.5)
              // ),
              ),
              
            },
          });
          const outlinePrimitive = new Cesium.Primitive({
            geometryInstances: instance,
            appearance: new Cesium.PerInstanceColorAppearance({
              closed: true,
              flat: true,
            }),
            asynchronous: false,
          });
          // return instance;
          viewer.scene.primitives.add(outlinePrimitive);
          outlinePrimitives.set(satellite.id, outlinePrimitive);
        }
        addFrustum(satellite);
        addOutline(satellite);
      }  
      viewer.clock.onTick.addEventListener(function () {
        satelliteEntities.forEach(satellite => {
          createFrustum(satellite);
          // 更新视锥体位置和方向
          // const satellitePosition = satellite.position.getValue(viewer.clock.currentTime);
          // // const satelliteOrientation = satellite.orientation.getValue(viewer.clock.currentTime);
          // frustumPrimitives.get(satellite.id).modelMatrix = Cesium.Transforms.headingPitchRollToFixedFrame(satellitePosition, new Cesium.HeadingPitchRoll(0, 0, 0), Cesium.Ellipsoid.WGS84);
          // outlinePrimitives.get(satellite.id).modelMatrix = Cesium.Transforms.headingPitchRollToFixedFrame(satellitePosition, new Cesium.HeadingPitchRoll(0, 0, 0), Cesium.Ellipsoid.WGS84);
        });
        // createFrustum(satellite1);
      });
      console.log("扫描视锥体绑定完成");

      // 为卫星实体绑定点击事件
      viewer.screenSpaceEventHandler.setInputAction((event) => {
        const pickedEntity = viewer.scene.pick(event.position);
        if (Cesium.defined(pickedEntity)) {
          const entity = pickedEntity.id; // 获取点击的实体
          if (entity) {
            // 获取卫星的详细信息
            const name = entity.name || "未知卫星";
            const position = Cesium.Cartographic.fromCartesian(entity.position.getValue(viewer.clock.currentTime));
            const lat = Cesium.Math.toDegrees(position.latitude);
            const lng = Cesium.Math.toDegrees(position.longitude);
            const height = position.height;
  
            // 显示详细信息
            alert(`卫星名称: ${name}\n纬度: ${lat.toFixed(2)}°\n经度: ${lng.toFixed(2)}°\n高度: ${height.toFixed(2)} 米`);
          }
        }
      }, Cesium.ScreenSpaceEventType.LEFT_CLICK);
    }).catch((error) => {
      console.error("加载 CZML 数据失败：", error);
    });

// 辅助函数：将 base64 转换为 Blob
    function dataURLtoBlob(dataurl) {
      const arr = dataurl.split(',');
      const mime = arr[0].match(/:(.*?);/)[1];
      const bstr = atob(arr[1]);
      let n = bstr.length;
      const u8arr = new Uint8Array(n);
      
      while(n--){
        u8arr[n] = bstr.charCodeAt(n);
      }
      
      return new Blob([u8arr], {type: mime});
    }

    function captureAreaScreenshot(minLon, minLat, maxLon, maxLat) {
    // 创建矩形区域
      const rectangle = Cesium.Rectangle.fromDegrees(minLon, minLat, maxLon, maxLat);
      // 添加矩形区域
      viewer.entities.add({
        name: '目标区域',
        rectangle: {
          coordinates: Cesium.Rectangle.fromDegrees(minLon, minLat, maxLon, maxLat),
          material: Cesium.Color.RED.withAlpha(0.3),
          outline: true,
          outlineColor: Cesium.Color.RED,
          outlineWidth: 2
        }
      });
      // 将相机飞行到指定区域
      viewer.camera.flyTo({
        destination: rectangle,
        duration: 2,
        complete: function() {
          // 等待场景渲染完成
          setTimeout(() => {
            // 获取 canvas 元素
            const canvas = viewer.scene.canvas;
            
            // 创建下载链接
            const link = document.createElement('a');
            link.download = 'screenshot.png'; //`area_${minLon}_${minLat}_${maxLon}_${maxLat}.png`;
            
            // 将 canvas 转换为图片 URL
            link.href = canvas.toDataURL('image/png');
            // 触发下载
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
          }, 5000); // 等待 1 秒确保场景完全渲染
        }
      });
    }
    // function captureAreaScreenshot(minLon, minLat, maxLon, maxLat) {
    //   return new Promise((resolve) => {
    //     const rectangle = Cesium.Rectangle.fromDegrees(minLon, minLat, maxLon, maxLat);
    //     viewer.camera.flyTo({
    //       destination: rectangle,
    //       duration: 2,
    //       complete: function() {
    //         setTimeout(() => {
    //           const canvas = viewer.scene.canvas;
    //           const imageUrl = canvas.toDataURL('image/png');
    //           resolve(imageUrl);
    //         }, 5000); // 等待 5 秒确保场景完全渲染
    //       }
    //     });
    //   });
    // }

    async function captureAndSaveToServer(minLon, minLat, maxLon, maxLat) {
      // 创建矩形区域并飞到该区域（保持原有代码）
      const rectangle = Cesium.Rectangle.fromDegrees(minLon, minLat, maxLon, maxLat);
      // viewer.entities.add({
      //   name: '目标区域',
      //   rectangle: {
      //     coordinates: rectangle,
      //     material: Cesium.Color.RED.withAlpha(0.3),
      //     outline: true,
      //     outlineColor: Cesium.Color.RED,
      //     outlineWidth: 2
      //   }
      // });
      // 将相机飞行到指定区域
      viewer.camera.flyTo({
        destination: rectangle,
        duration: 2,
        complete: function() {
          // 等待场景渲染完成
          setTimeout(() => {
            // 获取 canvas 元素
            const canvas = viewer.scene.canvas;
            
            // 创建下载链接
            // const link = document.createElement('a');
            // link.download = 'screenshot.png'; //`area_${minLon}_${minLat}_${maxLon}_${maxLat}.png`;
            
            // // 将 canvas 转换为图片 URL
            // link.href = canvas.toDataURL('image/png');
            // // 触发下载
            // document.body.appendChild(link);
            // link.click();
            // document.body.removeChild(link);


            const dataURL = canvas.toDataURL('image/png');
      
            // 将DataURL转换为Blob以便上传
            // const blob = await (await fetch(dataURL)).blob();
            const blob = dataURLtoBlob(dataURL);
            // const blob = dataURL.blob();
            
            // 创建FormData并添加截图
            const formData = new FormData();

            // // 生成文件名(包含时间戳和坐标)
            const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
            const fileName = `${timestamp}_area_${minLon}_${minLat}_${maxLon}_${maxLat}.png`;
                
            formData.append('screenshot', blob, fileName);
            
            // 发送到服务器
            try {
              const response = axios.post('http://localhost:5001/api/save-screenshot', formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
              });
              
              if (response.data.success) {
                console.log('截图已保存到服务器:', response.data.filePath);
                this.$message.success('截图保存成功');
              } else {
                console.error('保存失败:', response.data.message);
                this.$message.error('保存失败');
              }
            } catch (error) {
              console.error('网络错误:', error);
              this.$message.error('网络错误，请重试');
            }
          }, 5000); // 等待 1 秒确保场景完全渲染
        }
      });
      // // 等待场景渲染完成
      // await viewer.camera.flyTo({ destination: rectangle, duration: 5000 });
      
      // // 获取Canvas并转换为Blob
      // const canvas = viewer.scene.canvas;


      // const dataURL = canvas.toDataURL('image/png');
      
      // // 将DataURL转换为Blob以便上传
      // const blob = await (await fetch(dataURL)).blob();
      
      // // 创建FormData并添加截图
      // const formData = new FormData();
      // // 生成文件名(包含时间戳和坐标)
      // const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
      // const fileName = `${timestamp}_area_${minLon}_${minLat}_${maxLon}_${maxLat}.png`;
          
      // formData.append('screenshot', blob, fileName);
      
      // // 发送到服务器
      // try {
      //   const response = await axios.post('http://localhost:5000/api/save-screenshot', formData, {
      //     headers: { 'Content-Type': 'multipart/form-data' }
      //   });
        
      //   if (response.data.success) {
      //     console.log('截图已保存到服务器:', response.data.filePath);
      //     this.$message.success('截图保存成功');
      //   } else {
      //     console.error('保存失败:', response.data.message);
      //     this.$message.error('保存失败');
      //   }
      // } catch (error) {
      //   console.error('网络错误:', error);
      //   this.$message.error('网络错误，请重试');
      // }
    }
    // captureAndSaveToServer(116.3, 39.9, 116.5, 40.1);
    async function pointCaptureAndSaveToServer(longitude, latitude, height) {
    //   viewer.camera.flyTo({
    //     destination: Cesium.Cartesian3.fromDegrees(longitude, latitude, height),
    //     orientation: {
    //       heading: Cesium.Math.toRadians(0),
    //       pitch: Cesium.Math.toRadians(-90),
    //       roll: 0
    //     },
    //     duration: 3
    //   });
      // 将相机飞行到指定区域
    const pointEntity = viewer.entities.add({
        position: Cesium.Cartesian3.fromDegrees(longitude, latitude, 0),
        point: {
          pixelSize: 10,  // 调整点的大小为更合理的值
          color: Cesium.Color.RED,
          outlineColor: Cesium.Color.WHITE,
          outlineWidth: 2,
        },
        label: {
          text: `坐标点(${longitude.toFixed(2)}, ${latitude.toFixed(2)})`,
          font: '14px sans-serif',
          fillColor: Cesium.Color.WHITE,
          style: Cesium.LabelStyle.FILL_AND_OUTLINE,
          outlineWidth: 2,
          verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
          pixelOffset: new Cesium.Cartesian2(0, -10)
        }
      });
      viewer.camera.flyTo({
        destination: Cesium.Cartesian3.fromDegrees(longitude, latitude, height),
        
        duration: 2,
        complete: function() {
          // 等待场景渲染完成
          setTimeout(() => {
            // 获取 canvas 元素
            const canvas = viewer.scene.canvas;
            
            // 创建下载链接
            // const link = document.createElement('a');
            // link.download = 'screenshot.png'; //`area_${minLon}_${minLat}_${maxLon}_${maxLat}.png`;
            
            // // 将 canvas 转换为图片 URL
            // link.href = canvas.toDataURL('image/png');
            // // 触发下载
            // document.body.appendChild(link);
            // link.click();
            // document.body.removeChild(link);


            const dataURL = canvas.toDataURL('image/png');
      
            // 将DataURL转换为Blob以便上传
            // const blob = await (await fetch(dataURL)).blob();
            const blob = dataURLtoBlob(dataURL);
            // const blob = dataURL.blob();
            
            // 创建FormData并添加截图
            const formData = new FormData();

            // // 生成文件名(包含时间戳和坐标)
            const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
            const fileName = `${timestamp}_area_${longitude}_${latitude}.png`;
                
            formData.append('screenshot', blob, fileName);
            
            // 发送到服务器
            try {
              const response = axios.post('http://localhost:5001/api/save-screenshot', formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
              });
              
              if (response.data.success) {
                console.log('截图已保存到服务器:', response.data.filePath);
                this.$message.success('截图保存成功');
              } else {
                console.error('保存失败:', response.data.message);
                this.$message.error('保存失败');
              }
            } catch (error) {
              console.error('网络错误:', error);
              this.$message.error('网络错误，请重试');
            }
          }, 10000); // 等待 1 秒确保场景完全渲染
        }
      });
      // // 等待场景渲染完成
      // await viewer.camera.flyTo({ destination: rectangle, duration: 5000 });
      
      // // 获取Canvas并转换为Blob
      // const canvas = viewer.scene.canvas;


      // const dataURL = canvas.toDataURL('image/png');
      
      // // 将DataURL转换为Blob以便上传
      // const blob = await (await fetch(dataURL)).blob();
      
      // // 创建FormData并添加截图
      // const formData = new FormData();
      // // 生成文件名(包含时间戳和坐标)
      // const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
      // const fileName = `${timestamp}_area_${minLon}_${minLat}_${maxLon}_${maxLat}.png`;
          
      // formData.append('screenshot', blob, fileName);
      
      // // 发送到服务器
      // try {
      //   const response = await axios.post('http://localhost:5000/api/save-screenshot', formData, {
      //     headers: { 'Content-Type': 'multipart/form-data' }
      //   });
        
      //   if (response.data.success) {
      //     console.log('截图已保存到服务器:', response.data.filePath);
      //     this.$message.success('截图保存成功');
      //   } else {
      //     console.error('保存失败:', response.data.message);
      //     this.$message.error('保存失败');
      //   }
      // } catch (error) {
      //   console.error('网络错误:', error);
      //   this.$message.error('网络错误，请重试');
      // }
    }
    pointCaptureAndSaveToServer(116.3, 39.9, 1000);
    // // 使用示例：
    function showAreaTarget(minLon, minLat, maxLon, maxLat, height) {
     
      // 添加截图按钮
      const screenshotButton = document.createElement('button');
      screenshotButton.innerHTML = '截图保存';
      screenshotButton.style.position = 'absolute';
      screenshotButton.style.top = '10px';
      screenshotButton.style.right = '10px';
      screenshotButton.style.zIndex = '1000';
      screenshotButton.onclick = () => captureAreaScreenshot(minLon, minLat, maxLon, maxLat);
      document.body.appendChild(screenshotButton);
    }
    // showAreaTarget(116.3, 39.9, 116.5, 40.1, 100);


    // // 添加地面站覆盖区域显示函数
    // function showGroundStationCoverage(longitude, latitude, height) {
    //   viewer.camera.flyTo({
    //     destination: Cesium.Cartesian3.fromDegrees(longitude, latitude, height),
    //     orientation: {
    //       heading: Cesium.Math.toRadians(0),
    //       pitch: Cesium.Math.toRadians(-90),
    //       roll: 0
    //     },
    //     duration: 3
    //   });
    // }
    //   // 添加地面站覆盖区域
    //   viewer.entities.add({
    //     name: '地面站覆盖区域',
    //     position: Cesium.Cartesian3.fromDegrees(longitude, latitude),
    //     ellipse: {
    //       semiMinorAxis: 1000.0,  // 覆盖半径（米）
    //       semiMajorAxis: 1000.0,
    //       material: Cesium.Color.BLUE.withAlpha(0.3),
    //       outline: true,
    //       outlineColor: Cesium.Color.BLUE,
    //       outlineWidth: 2
    //     }
    //   });
    // }

    // // 添加区域目标显示函数
    // function showAreaTarget(minLon, minLat, maxLon, maxLat, height) {
    //   // 相机飞行到区域中心
    //   const centerLon = (minLon + maxLon) / 2;
    //   const centerLat = (minLat + maxLat) / 2;
      
    //   viewer.camera.flyTo({
    //     destination: Cesium.Cartesian3.fromDegrees(centerLon, centerLat, height),
    //     orientation: {
    //       heading: Cesium.Math.toRadians(0),
    //       pitch: Cesium.Math.toRadians(-90),
    //       roll: 0
    //     },
    //     duration: 3
    //   });

    //   // 添加矩形区域
    //   viewer.entities.add({
    //     name: '目标区域',
    //     rectangle: {
    //       coordinates: Cesium.Rectangle.fromDegrees(minLon, minLat, maxLon, maxLat),
    //       material: Cesium.Color.RED.withAlpha(0.3),
    //       outline: true,
    //       outlineColor: Cesium.Color.RED,
    //       outlineWidth: 2
    //     }
    //   });
    // }

    // // // 示例：显示北京地面站覆盖区域
    // // showGroundStationCoverage(116.4, 39.9, 1000);

    // // 示例：显示北京某个区域（例如：天安门区域）
    // showAreaTarget(116.3, 39.9, 116.4, 40.0, 1000);
    // console.log("北京");
    // if (!viewer.value) 
    //   console.log("区域失败");
    // else
    //   console.log("区域成功");
    // const canvas = viewer.value.scene.canvas;
    // const image = canvas.toDataURL('image/png');

    // // 创建下载链接
    // const link = document.createElement('a');
    // link.href = image;
    // link.download = 'cesium-screenshot.png';
    // link.click();
    //卫星地面站网络构建
    const Positions_of_GroundStations = {
    '重庆站':  { id: '重庆站',     lon: 105.11,  lat: 28.10, radius: 300000 },
    '雄安站':  { id: '雄安站',     lon: 115.38,  lat: 38.10, radius: 300000 },
    '喀什站':  { id: '喀什站',     lon: 79.57,   lat: 40.18, radius: 300000 },
    '文昌站':  { id: '文昌站',     lon: 110.28,  lat: 19.21, radius: 300000 },
    '佳木斯站':{ id: '佳木斯站',    lon: 129.29,  lat: 45.56, radius: 300000 }};
    const Networking_Dicts = {'重庆站': {'dst1':'雄安站','dst2':'喀什站', 'dst3':'文昌站'},'喀什站': {'dst1':'雄安站'},'佳木斯站': {'dst1':'雄安站'}, '文昌站': {'dst1':'雄安站'}};

    // 卫星地面站建立
    const GroundStations = new Cesium.CustomDataSource("GroundStations");
    viewer.dataSources.add(GroundStations);
    Object.keys(Positions_of_GroundStations).forEach(i => {Create_for_GroundStations(Positions_of_GroundStations[i].id, Positions_of_GroundStations[i].lon, Positions_of_GroundStations[i].lat, Positions_of_GroundStations[i].radius)});
    function Create_for_GroundStations(id, lon, lat, radius) {
      GroundStations.entities.add({
         name: id,
         label: {
              text: `${id}`,
              heightReference:Cesium.HeightReference.CLAMP_TO_GROUND,
              font: "12pt sans-serif",
              pixelOffset: new Cesium.Cartesian2(0.0, 3),
              pixelOffsetScaleByDistance: new Cesium.NearFarScalar(3e3, 1.0, 8.0e5, 8.0),
              fillColor: Cesium.Color.WHITE,
         },
         position: Cesium.Cartesian3.fromDegrees(lon,lat),
         wall: {
           positions: new Cesium.CallbackProperty(() => {
             return Cesium.Cartesian3.fromDegreesArrayHeights(positionArr);
           }, false),
           material: new Cesium.Color.fromCssColorString("#00dcff82"),
         },
         ellipsoid: {
           radii: new Cesium.Cartesian3(radius, radius, radius),
           maximumCone: Cesium.Math.toRadians(90),
           material: new Cesium.Color.fromCssColorString("#00dcff82"),  //Cesium.Color.RED.withAlpha(0.8):颜色和透明度；
           outline: true,
           outlineColor: new Cesium.Color.fromCssColorString("#00dcff82"),
           outlineWidth: 1,
         },
      });
      var heading = 0;
      var positionArr = calcPoints(lon, lat, radius,heading);
      viewer.clock.onTick.addEventListener(() => {
        heading += 5.0;
        positionArr = calcPoints(lon, lat, radius,heading);
      });
    }
    function calcPoints(x1, y1, radius, heading){
      var m = Cesium.Transforms.eastNorthUpToFixedFrame(Cesium.Cartesian3.fromDegrees(x1, y1));
      var rx = radius * Math.cos(heading * Math.PI / 180.0);
      var ry = radius * Math.sin(heading * Math.PI / 180.0);
      var translation = Cesium.Cartesian3.fromElements(rx, ry, 0);
      var d = Cesium.Matrix4.multiplyByPoint(m, translation, new Cesium.Cartesian3());
      var c = Cesium.Cartographic.fromCartesian(d);
      var x2 = Cesium.Math.toDegrees(c.longitude);
      var y2 = Cesium.Math.toDegrees(c.latitude);
      return computeCirclularFlight(x1, y1, x2, y2, 0, 90);
    }
    function computeCirclularFlight(x1, y1, x2, y2, fx, angle) {
      let positionArr = [];
      positionArr.push(x1);
      positionArr.push(y1);
      positionArr.push(0);
      var radius = Cesium.Cartesian3.distance(Cesium.Cartesian3.fromDegrees(x1, y1), Cesium.Cartesian3.fromDegrees(x2, y2));
      for (let i = fx; i <= fx + angle; i++) {
        let h = radius * Math.sin(i * Math.PI / 180.0);
        let r = Math.cos(i * Math.PI / 180.0);
        let x = (x2 - x1) * r + x1;
        let y = (y2 - y1) * r + y1;
        positionArr.push(x);
        positionArr.push(y);
        positionArr.push(h);
      }
      return positionArr;
    }

    //卫星地面站网络建立
    const Networking_for_GroundStation = new Cesium.CustomDataSource("Networking_for_GroundStation");
    viewer.dataSources.add(Networking_for_GroundStation);
    Object.keys(Networking_Dicts).forEach(key => {Creat_Networks_for_GroundSations(key, Networking_Dicts[key])});
    function Creat_Networks_for_GroundSations(src, dst_dicts){
      Object.keys(dst_dicts).forEach(key =>{
        Networking_for_GroundStation.entities.add({
          polyline: {
              positions: Cesium.Cartesian3.fromDegreesArray([Positions_of_GroundStations[src].lon, Positions_of_GroundStations[src].lat,
                Positions_of_GroundStations[dst_dicts[key]].lon, Positions_of_GroundStations[dst_dicts[key]].lat,
                  ]),
              width: 5, // 线宽
              material: new  Cesium.Color.fromCssColorString('#FFFACD') // 线颜色 red , green , blue , alpha#FFFACD
          }
        });
      });
    }

  });
</script>

<style >
    #cesiumContainer{
        width: 100%;
        height: 100%;
        overflow: hidden;
    }
</style>

  
  
  