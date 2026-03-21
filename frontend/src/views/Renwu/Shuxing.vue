<template>
  <el-card shadow="never" style="margin-top: 10px;">

    <!-- 表格区域 -->
    <el-table :data="tableData" stripe>
      <el-table-column prop="id" label="编号" width="100" />
      <el-table-column prop="youxian" label="优先级" />
      <!-- <el-table-column label="图书图片">
        <template #default="scope">
        <img :src="'http://127.0.0.1:5001/upimg/' + scope.row.img_url" width="100" height="100">
        </template>
      </el-table-column> -->
      <el-table-column prop="jinji" label="是否紧急" />
      <el-table-column prop="leixing" label="任务类型" />
      <el-table-column prop="zaihe" label="要求载荷" />
      <el-table-column prop="shijian" label="执行时间" />
      <el-table-column prop="shijianfan" label="时间范围" />
      <el-table-column prop="quyu" label="区域" />
      <el-table-column label="操作" width="120" fixed="right">
        <template #default="scope">
          <div v-if="isAdmin == 1">
          <el-button link type="primary" size="small" @click="editItem(scope.row)">编辑</el-button>
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
    // 添加示例数据
    this.tableData = [{
      id: '001',
      youxian: '1',
      jinji: '是',
      leixing: '点任务',
      zaihe: 'SAR',
      shijian: '1',
      shijianfan: '[0,1]',
      quyu: '[100,100]'
    },{
      id: '001',
      youxian: '1',
      jinji: '是',
      leixing: '点任务',
      zaihe: 'SAR',
      shijian: '1',
      shijianfan: '[0,1]',
      quyu: '[100,100]'
    }];
    // this.search.token = localStorage.getItem("token");
    this.getList();
    this.getcbs();
    this.getzz();
    this.isAdmin = localStorage.getItem("isAdmin");
    this.mj_id = localStorage.getItem("userInfoid");
    if (this.isAdmin==2){
      this.form.maijia_id = this.mj_id
    }
  },
  methods: {
    async getList() {
      const res = await this.$request.get(
        "/ts/",
        { params: this.search }
      );
      
      if (res.data.code === 200) {
        // this.tableData = res.data.data.sort((a, b)      
        console.log(res.data,'1111111111111111111111')
        this.tableData = res.data.data;
        this.totalNum = res.data.zs
      }
    },

    // 老板接口
    async getcbs() {
      const res = await this.$request.get(
        "/cbs/",
        { params: this.search }
      );
      
      if (res.data.code === 200) {
        // this.tableData = res.data.data.sort((a, b)      
        console.log(res.data)
        this.cbsdata = res.data.data;
      }
    },

    // 分类接口
    async getzz() {
      const res = await this.$request.get(
        "/zz/",
        { params: this.search }
      );
      
      if (res.data.code === 200) {
        // this.tableData = res.data.data.sort((a, b)      
        console.log(res.data)
        this.zzdata = res.data.data;
      }
    },

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
    async saveData() {
      if (this.form.id) {
        const res = await this.$request.put('/ts/' + this.form.id + '/', this.form)
        if (res.data.code === 200) {
        this.$message.success(res.data.message)
        this.getList()
        this.visible = false
      }
      } else {
        const res = await this.$request.post('/ts/', this.form)
        if (res.data.code === 200) {
          console.log(res.data,'dddddddddddddddd')
        this.$message.success(res.data.message)
        this.getList()
        this.visible = false
      }
      }
      // const res = await this.$request.post(this.form.id ? '/guanli/' : '/guanli/', this.form)
      // if (res.data.code === 200) {
      //   this.$message.success(res.data.message)
      //   this.getList()
      //   this.visible = false
      // }
    },
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