<template>
  <el-card shadow="never" style="margin-top: 10px;">

    <!-- 表格区域 -->
    <el-table :data="tableData" stripe>
      <el-table-column prop="name" label="卫星名称" width="100" />
      <el-table-column prop="orbit" label="轨道" show-overflow-tooltip/>
      <!-- <el-table-column label="图书图片">
        <template #default="scope">
        <img :src="'http://127.0.0.1:5001/upimg/' + scope.row.img_url" width="100" height="100">
        </template>
      </el-table-column> -->
      <el-table-column prop="battery" label="电池容量(Wh)" />
      <el-table-column prop="storage" label="存储容量(GB)" />
      <el-table-column prop="loadType" label="载荷" />
      <el-table-column prop="resolution" label="分辨率(m)" />
      
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="scope">
          <div v-if="isAdmin == 1">
          <el-button link type="primary" size="small" @click="showDetail(scope.row)">详情</el-button>
          <el-button link type="primary" size="small" @click="editItem(scope.row)">编辑</el-button>
          <el-button link type="primary" size="small" @click="editItem(scope.row)">导出</el-button>
          <el-popconfirm title="确定要删除吗?" @confirm="deleteItem(scope.row.id)">
            <template #reference>
              <el-button link type="primary" size="small">删除</el-button>
            </template>
          </el-popconfirm>
        </div>
        </template>
      </el-table-column>


    </el-table>
    <!-- 分页 -->
    <el-pagination background @size-change="handleSizeChange" @current-change="handleCurrentChange"
      layout="sizes, total, prev, pager, next" :total="totalNum" :currentPage="search.pageNum"
      :pageSize="search.pageSize">
    </el-pagination>

    
  </el-card>
</template>


<script>
import sDrawer from "@/components/s-drawer.vue"
import { ElMessage } from 'element-plus';

export default {
  components: {
    sDrawer,
  },
  watch: {
    visible(value) {
      if (!value) {
        this.form = {}
      }
    }
  },
  data() {
    return {
      form: {
        // id: '',
      },

      xydata: [],
      value1: [],
      value2: [],

      visible: false,
      tableData: [],
      totalNum: 100,
      search: {
        pageNum: 1,
        pageSize: 10,
        // token: "",
      },

    };
  },
  created() {

    // this.search.token = localStorage.getItem("token");
    this.getList();
    // this.getcbs();
    // this.getzz();
    this.isAdmin = localStorage.getItem("isAdmin");
    // this.mj_id = localStorage.getItem("userInfoid");
    // if (this.isAdmin==2){
    //   this.form.maijia_id = this.mj_id
    // }
  },
  methods: {
    async getList() {
      try {
        // 注意：/getAllSatellites 是 POST 请求
        const res = await this.$request.post(
          "/satellites/getAllSatellites",
          { sate_name: "" } // 查询全部
        );
        // 假设后端直接返回数组
        if (Array.isArray(res.data)) {
          const start = (this.search.pageNum - 1) * this.search.pageSize;
          const end = start + this.search.pageSize;
          this.tableData = res.data.slice(start, end);
          this.totalNum = res.data.length;
        }
      } catch (err) {
        console.error('获取卫星列表失败:', err);
        // 检查是否是卫星网络未初始化的错误
        if (err.response?.status === 503 || 
            err.response?.data?.error?.includes('尚未初始化') ||
            err.message?.includes('Cannot read properties of null')) {
          ElMessage.warning('系统尚未初始化完成，请先上传 TLE 文件和卫星参数文件');
        } else {
          ElMessage.error('获取卫星列表失败: ' + (err.response?.data?.error || err.message || '未知错误'));
        }
        // 设置空数据
        this.tableData = [];
        this.totalNum = 0;
      }
    },
    // async getList() {
    //   const res = await this.$request.get(
    //     "/ts/",
    //     { params: this.search }
    //   );
      
    //   if (res.data.code === 200) {
    //     // this.tableData = res.data.data.sort((a, b)      
    //     console.log(res.data,'1111111111111111111111')
    //     this.tableData = res.data.data;
    //     this.totalNum = res.data.zs
    //   }
    // },

    // 老板接口
    // async getcbs() {
    //   const res = await this.$request.get(
    //     "/cbs/",
    //     { params: this.search }
    //   );
      
    //   if (res.data.code === 200) {
    //     // this.tableData = res.data.data.sort((a, b)      
    //     console.log(res.data)
    //     this.cbsdata = res.data.data;
    //   }
    // },

    // // 分类接口
    // async getzz() {
    //   const res = await this.$request.get(
    //     "/zz/",
    //     { params: this.search }
    //   );
      
    //   if (res.data.code === 200) {
    //     // this.tableData = res.data.data.sort((a, b)      
    //     console.log(res.data)
    //     this.zzdata = res.data.data;
    //   }
    // },

    // 每页条数改变时触发 选择一页显示多少行
    handleSizeChange(val) {
      console.log(`每页 ${val} 条`);
      this.search.pageSize = val;
      this.getList();
    },
    // 当前页改变时触发 跳转其他页
    handleCurrentChange(val) {
      console.log(`当前页: ${val}`);
      this.search.pageNum = val;
      this.getList();
    },
    resetSearch() {
      let search = {
        pageNum: this.search.pageNum,
        pageSize: this.search.pageSize,
      };
      this.search = search;
      this.getList();
    },
    editItem(row) {
      this.form = this.$deepClone(row)
      this.visible = true
    },
    // async saveData() {
    //   if (this.form.id) {
    //     const res = await this.$request.put('/ts/' + this.form.id + '/', this.form)
    //     if (res.data.code === 200) {
    //     ElMessage.success(res.data.message)
    //     this.getList()
    //     this.visible = false
    //   }
    //   } else {
    //     const res = await this.$request.post('/ts/', this.form)
    //     if (res.data.code === 200) {
    //       console.log(res.data,'dddddddddddddddd')
    //     this.$message.success(res.data.message)
    //     this.getList()
    //     this.visible = false
    //   }
    //   }
    //   // const res = await this.$request.post(this.form.id ? '/guanli/' : '/guanli/', this.form)
    //   // if (res.data.code === 200) {
    //   //   this.$message.success(res.data.message)
    //   //   this.getList()
    //   //   this.visible = false
    //   // }
    // },
    async deleteItem(id) {
      const res = await this.$request.delete("/ts/" + id + '/')
      if (res.data.code === 200) {
        this.$message.success(res.data.message)
        this.getList()
      }
    },

        // 照片文件超出个数限制时的钩子
        handleExceed(files, fileList) {
      this.$notify.warning({
      title: '警告',
      message: `只能选择 ${this.limitNum} 个文件，当前共选择了 ${files.length + fileList.length} 个`
      })
    },
    // 上传照片文件之前的钩子
    handleBeforeUpload(file) {
      const size = file.size / 1024 / 1024
          if (size > 1) {
            this.$notify.warning({
            title: '警告',
            message: '图片大小必须小于1M'
          })
      }
    },
    handleSuccess1(res) {
        console.log(res.data,'777777777777777777777777777777777777777')
        this.form.img_url = res.data.file
        this.dialogImageUrl = ''
        this.$notify({
            title: '通知',
            message: '上传照片成功~',
            type: 'success',
            duration: 5000
      })
    },

    showDetail(row) {
        // this.detailData = row;
        // this.detailVisible = true;
        this.$router.push(`/satellite/weixing/info/${row.name}`);
    },

  },
};
</script>

<style scoped>
.el-pagination {
  margin-top: 10px;
}

.el-row {
  margin-bottom: 20px;
}

.el-row:last-child {
  margin-bottom: 0px;
}
</style>