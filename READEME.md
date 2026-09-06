=============文件目录说明========
技术说明书：已向甲方交付版，包括完整需求和项目实现介绍
setting：项目启动后需要用于上传的信息


==========启动流程========
数据库准备：
cd .\backend\
python -m venv venv<!--创建虚拟环境 -->
.\venv\Scripts\activate<!--激活虚拟环境 -->
flask db init
flask db migrate -m "Initial migration"
flask db upgrade


后端启动：
cd .\backend\
.\venv\Scripts\activate
pip install -r requirements.txt
python app.py


前端启动：
cd .\frontend\
npm install
npm run dev


卫星任务执行客户端启动：
cd .\backend\
.\venv\Scripts\activate
pip install -r requirements.txt
python client.py
待输入服务器IP地址为: 127.0.0.1
