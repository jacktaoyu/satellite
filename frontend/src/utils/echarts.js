// echarts 按需装配：项目实际只用到 饼图/柱状图/折线图/雷达图 + 常用组件，
// 全量 import 'echarts' 会打入 1MB+ 的 vendor 包，按需引入后体积显著下降。
// 注意：新增图表类型时务必在此补充对应的 Chart 注册，否则该图表静默不渲染。
import * as echarts from 'echarts/core';
import { PieChart, BarChart, LineChart, RadarChart } from 'echarts/charts';
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  TitleComponent,
  DataZoomComponent,
} from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import { LinearGradient } from 'echarts/lib/util/graphic';

echarts.use([
  PieChart, BarChart, LineChart, RadarChart,
  GridComponent, TooltipComponent, LegendComponent, TitleComponent, DataZoomComponent,
  CanvasRenderer,
]);

// 重新导出新对象而不是给 module namespace 赋值（ESM 命名空间对象不可写，
// 直接 echarts.graphic = ... 会抛 TypeError），兼容页面中 new echarts.graphic.LinearGradient(...) 的既有写法
export default { ...echarts, graphic: { LinearGradient } };
