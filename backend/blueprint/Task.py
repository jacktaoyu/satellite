import os
from datetime import datetime, timedelta
from sqlalchemy import and_


from flask import Blueprint, request, jsonify, render_template, send_file
from sqlalchemy import not_
from werkzeug.utils import secure_filename

from database import db
from model.TaskModel import NewTaskModel, OldTaskModel
from model.CaseHistoryModel import CaseHistoryModel
from extions import occ

# 创建任务蓝图对象
task_bp = Blueprint('task', __name__, url_prefix='/tasks')


# 获取任务规划方案数据
@task_bp.route('/getPlanData', methods=['GET'])
def get_plan_data():
    plan_data = occ.planning_results
    return plan_data


# 添加文件，批量添加任务
@task_bp.route('/addTasks', methods=['POST'])
def add_tasks():
    # 检查是否上传了文件
    if 'file' not in request.files:
        return jsonify({"error": "没有上传文件"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "没有选择文件"}), 400

    # 确保library目录存在
    library_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'library')
    if not os.path.exists(library_dir):
        os.makedirs(library_dir)

    # 保存文件（文件名安全处理并校验路径必须位于library目录内，防止路径穿越）
    filename = secure_filename(file.filename)
    if not filename:
        return jsonify({"error": "非法的文件名"}), 400
    file_path = os.path.realpath(os.path.join(library_dir, filename))
    if not file_path.startswith(os.path.realpath(library_dir) + os.sep):
        return jsonify({"error": "非法的文件路径"}), 400
    file.save(file_path)

    # 生成任务并添加到队列
    tasks = occ.generate_tasks(file_path)
    if tasks:
        print("批量创建任务完成，已添加到任务队列")
        return "ok"
    else:
        return jsonify({"error": "任务生成失败"}), 400


# # 随机生成批量任务
# @task_bp.route('/addRandomTasks', methods=['POST'])
# def add_random_tasks():
#     point_task_count = request.json.get('pointTask', 10)
#     area_task_count = request.json.get('regionalTask', 10)
#     moving_task_count = request.json.get('trackTask', 10)
#     cluster_name = request.json.get('cluster_name', None)
#     start_time = request.json.get('start_time', datetime.now())
#     end_time = request.json.get('end_time', datetime.now() + timedelta(days=1))
#     occ.generate_random_tasks(point_task_count, area_task_count, moving_task_count, cluster_name, start_time, end_time)
#     return jsonify({"result": "ok"}), 200


# 添加单个任务
@task_bp.route('/addSingleTask', methods=['POST'])
def add_single_task():
    form = request.json
    task = occ.generate_single_task(form)
    return jsonify({"result": "ok"})


# 编辑未完成任务（只更新传入的字段，执行中的任务不允许编辑）
@task_bp.route('/updateTask/<int:task_id>', methods=['POST'])
def update_task(task_id):
    form = request.json or {}
    task = NewTaskModel.query.filter_by(id=task_id).first()
    if not task:
        return jsonify({"meta": {"status": 404, "message": "任务不存在"}}), 404
    if task.status == "正在执行":
        return jsonify({"meta": {"status": 409, "message": "任务执行中，无法编辑"}}), 409
    occ.edit_task(task_id, form)
    return jsonify({"meta": {"status": 200, "message": "任务更新成功"}})


# 根据id删除任务
@task_bp.route('/deleteTaskById/<int:id>', methods=['DELETE'])
def delete_task_by_id(id):
    task = NewTaskModel.query.get(id)
    if task:
        db.session.delete(task)
        db.session.commit()
        return jsonify({"result": "ok"})
    else:
        return jsonify({"error": "任务不存在"}), 404


# 分页查询所有未完成的任务
@task_bp.route('/getNewTasksByPage', methods=['GET'])
def get_new_tasks_by_page():
    # 获取分页参数，如果没有则使用默认值
    page = request.args.get('page', 1, type=int)
    size = request.args.get('size', 10, type=int)

    # 使用分页查询
    pagination = NewTaskModel.query.paginate(page=page, per_page=size, error_out=False)
    tasks = pagination.items

    results = [
        {
            'id': task.id,
            'priority': task.priority,
            'is_emergency': task.is_emergency,
            'sensor_type': task.sensor_type,
            'task_type': task.task_type,
            'resolution': task.resolution,
            'target_location': task.target_location,
            'start_time': task.start_time,
            'end_time': task.end_time,
            'assigned_satellite_name': task.assigned_satellite_name,
        } for task in tasks
    ]

    return {
        'status': 'success',
        'message': '数据获取成功',
        'data': {
            'items': results,
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': pagination.page,
            'per_page': pagination.per_page,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev
        }
    }


# 查询所有未完成的任务
@task_bp.route('/getNewTasksByCondition', methods=['GET'])
def get_new_tasks():
    tasks = NewTaskModel.query.all()

    results = [
        {
            'id': task.id,
            'task_name': task.task_name,
            'priority': task.priority,
            'is_urgent': task.is_emergency,
            'payload': task.sensor_type,
            'type': task.task_type,
            'resolution': task.resolution,
            'coordinates': task.target_location,
            # 'coordinates': task.target_location if type(task.target_target_location[0]) == "list" else [task.target_target_location],
            'start_time': str(task.start_time),
            'end_time': str(task.end_time),
            'appoint_time': str(task.appoint_time),
            'status': task.status,
            'satellite_name': task.assigned_satellite_name,
            "cluster_name": task.cluster_name if task.cluster_name else "",
            'friend_task': task.friend_task_id,  # 合并的友任务id
            'cloud_thickness': task.cloud_thickness
        } for task in tasks
    ]

    return results


# 动态条件查询未完成任务
@task_bp.route('/getNewTasks', methods=['POST'])
def get_new_tasks_by_condition():
    # 获取参数
    form = request.json
    page = form.get('page', 1)
    page_size = form.get('page_size', 10)
    priority = form.get('priority')
    urgent = form.get('urgent')
    task_type = form.get('type')
    payload = form.get('payload')
    status = form.get('status')

    # 构建查询条件
    filters = []

    # 永远过滤掉任务名带“案例”的任务
    # filters.append(not_(NewTaskModel.task_name.like('%案例%')))

    if priority and priority != []:
        filters.append(NewTaskModel.priority.in_(priority))
    if urgent and urgent != []:
        # urgent: ["是", "否"] → is_emergency: [True, False]
        bool_map = {"是": True, "否": False}
        bool_urgent = [bool_map.get(u, False) for u in urgent]
        filters.append(NewTaskModel.is_emergency.in_(bool_urgent))
    if task_type and task_type != []:
        filters.append(NewTaskModel.task_type.in_(task_type))
    if payload and payload != []:
        filters.append(NewTaskModel.sensor_type.in_(payload))
    if status and status != []:
        filters.append(NewTaskModel.status.in_(status))

    query = NewTaskModel.query
    if filters and len(filters) > 0:
        if len(filters) == 1:
            query = query.filter(filters[0])
        else:
            query = query.filter(and_(*filters))

    pagination = query.paginate(page=page, per_page=page_size, error_out=False)
    tasks = pagination.items

    results = [
        {
            'id': task.id,
            'task_name': task.task_name,
            'priority': task.priority,
            'is_urgent': task.is_emergency,
            'payload': task.sensor_type,
            'type': task.task_type,
            'resolution': task.resolution,
            'coordinates': task.target_location,
            'start_time': str(task.start_time),
            'end_time': str(task.end_time),
            'appoint_time': str(task.appoint_time),
            'status': task.status,
            'satellite_name': task.assigned_satellite_name,
            "cluster_name": task.cluster_name if task.cluster_name else "",
            'friend_task': task.friend_task_id,
            'cloud_thickness': task.cloud_thickness
        } for task in tasks
    ]

    return {
        'status': 'success',
        'message': '数据获取成功',
        'data': {
            'items': results,  # 任务列表
            'total': pagination.total,  # 总任务数
            'pages': pagination.pages,  # 总页数
            'current_page': pagination.page,  # 当前页
            'per_page': pagination.per_page,  # 每页任务数
            'has_next': pagination.has_next,  # 是否有下一页
            'has_prev': pagination.has_prev  # 是否有上一页
        }
    }


# 根据id查询未完成的任务的状态
@task_bp.route('/getNewTaskById/<int:id>', methods=['GET'])
def get_new_task_by_id(id):
    task = NewTaskModel.query.filter_by(id=id).first()
    if task:
        return jsonify({'status': task.status})
    return jsonify({"error": "Task not found"}), 404


# 查询所有已经完成的任务
@task_bp.route('/getOldTasksByCondition', methods=['GET'])
def get_old_tasks():
    tasks = OldTaskModel.query.all()
    results = [
        {
            'id': task.id,
            'task_name': task.task_name,
            'priority': task.priority,
            'is_urgent': task.is_emergency,
            'payload': task.sensor_type,
            'type': task.task_type,
            'resolution': task.resolution,
            'coordinates': task.target_location,
            # 'coordinates': task.target_location if type(task.target_target_location[0]) == "list" else [task.target_target_location],
            'start_time': str(task.start_time),
            'end_time': str(task.end_time),
            "appoint_time": str(task.appoint_time),
            'status': task.status,
            'satellite_name': task.assigned_satellite_name,
            'friend_task': task.friend_task_id,  # 合并的友任务id
            'path': task.path,
            'cloud_thickness': task.cloud_thickness
        } for task in tasks
    ]

    return results


# 动态条件查询已经完成的任务
@task_bp.route('/getOldTasks', methods=['POST'])
def get_old_tasks_by_condition():
    # 获取参数
    form = request.json
    page = form.get('page', 1)
    page_size = form.get('page_size', 10)
    priority = form.get('priority')
    urgent = form.get('urgent')
    task_type = form.get('type')
    payload = form.get('payload')
    status = form.get('status')

    # 构建查询条件
    filters = []

    # 永远过滤掉任务名带“案例”的任务
    # filters.append(not_(OldTaskModel.task_name.like('%案例%')))

    if priority and priority != []:
        filters.append(OldTaskModel.priority.in_(priority))
    if urgent and urgent != []:
        # urgent: ["是", "否"] → is_emergency: [True, False]
        bool_map = {"是": True, "否": False}
        bool_urgent = [bool_map.get(u, False) for u in urgent]
        filters.append(OldTaskModel.is_emergency.in_(bool_urgent))
    if task_type and task_type != []:
        filters.append(OldTaskModel.task_type.in_(task_type))
    if payload and payload != []:
        filters.append(OldTaskModel.sensor_type.in_(payload))
    if status and status != []:
        filters.append(OldTaskModel.status.in_(status))

    query = OldTaskModel.query
    if filters and len(filters) > 0:
        if len(filters) == 1:
            query = query.filter(filters[0])
        else:
            query = query.filter(and_(*filters))

    pagination = query.paginate(page=page, per_page=page_size, error_out=False)
    tasks = pagination.items

    results = [
        {
            'id': task.id,
            'task_name': task.task_name,
            'priority': task.priority,
            'is_urgent': task.is_emergency,
            'payload': task.sensor_type,
            'type': task.task_type,
            'resolution': task.resolution,
            'coordinates': task.target_location,
            'start_time': str(task.start_time),
            'end_time': str(task.end_time),
            'appoint_time': str(task.appoint_time),
            'status': task.status,
            'satellite_name': task.assigned_satellite_name,
            'friend_task': task.friend_task_id if task.friend_task_id else "",
            'cloud_thickness': task.cloud_thickness if task.cloud_thickness else "",
            'path': task.path if task.path else ""
        } for task in tasks
    ]

    return {
        'status': 'success',
        'message': '数据获取成功',
        'data': {
            'items': results,  # 任务列表
            'total': pagination.total,  # 总任务数
            'pages': pagination.pages,  # 总页数
            'current_page': pagination.page,  # 当前页
            'per_page': pagination.per_page,  # 每页任务数
            'has_next': pagination.has_next,  # 是否有下一页
            'has_prev': pagination.has_prev  # 是否有上一页
        }
    }


# # 分页查询所有已经完成的任务
# @task_bp.route('/getOldTasksByPage', methods=['GET'])
# def get_old_tasks_page():
#     # 获取分页参数，如果没有则使用默认值
#     page = request.args.get('page', 1, type=int)
#     size = request.args.get('size', 10, type=int)
#
#     # 使用分页查询
#     pagination = OldTaskModel.query.paginate(page=page, per_page=size, error_out=False)
#     tasks = pagination.items
#
#     results = [
#         {
#             'id': task.id,
#             'priority': task.priority,
#             'is_emergency': task.is_emergency,
#             'sensor_type': task.sensor_type,
#             'task_type': task.task_type,
#             'resolution': task.resolution,
#             'target_target_location': task.target_target_location,
#             'start_time': task.start_time,
#             'end_time': task.end_time,
#             'assigned_satellite_name': task.assigned_satellite_name,
#         } for task in tasks
#     ]
#
#     return {
#         'status': 'success',
#         'message': '数据获取成功',
#         'data': {
#             'items': results,
#             'total': pagination.total,
#             'pages': pagination.pages,
#             'current_page': pagination.page,
#             'per_page': pagination.per_page,
#             'has_next': pagination.has_next,
#             'has_prev': pagination.has_prev
#         }
#     }


# 根据id查询已经完成的任务
@task_bp.route('/getOldTaskById/<int:id>', methods=['GET'])
def get_old_task_by_id(id):
    task = OldTaskModel.query.get(id)
    if not task:
        return jsonify({"error": "任务不存在"}), 404
    return jsonify({"result": task.to_dict()})


# # 领取下一个可执行任务（供卫星客户端轮询/领取）
# @task_bp.route('/claimNext', methods=['POST'])
# def claim_next_task():
#     """卫星客户端调用此接口领取下一个等待执行的任务
#     请求 JSON: {"satellite_name": "sat-1"}
#     返回 JSON: 领取到的任务或 {"task": None}
#     """
#     form = request.json or {}
#     satellite_name = form.get('satellite_name', None)

#     # 查找第一个状态为“等待执行”的任务
#     task = NewTaskModel.query.filter_by(status="等待执行").first()
#     if not task:
#         return jsonify({"task": None}), 200

#     # 分配给请求的卫星（如果提供）并标记为执行中
#     if satellite_name:
#         task.assigned_satellite_name = satellite_name
#     task.status = "执行中"
#     db.session.commit()

#     # 返回任务给客户端（包含一个简单的模拟执行时间字段）
#     task_dict = task.to_dict()
#     task_dict['execute_time'] = form.get('execute_time', 2)
#     return jsonify({"task": task_dict}), 200


# # 提交任务执行结果
# @task_bp.route('/submitResult', methods=['POST'])
# def submit_result():
#     """卫星客户端提交任务执行结果
#     请求 JSON 示例: {"task_id": 123, "status": "Success", "result": "...", "path": "..."}
#     """
#     data = request.json or {}
#     task_id = data.get('task_id')
#     status = data.get('status', 'Success')
#     path = data.get('path', None)

#     # 查找原始任务
#     task = NewTaskModel.query.filter_by(id=task_id).first()
#     if not task:
#         return jsonify({"error": "任务不存在"}), 404

#     # 将任务移入已完成表（OldTaskModel）并更新状态
#     try:
#         old = OldTaskModel()
#         # 复制字段（只复制常用字段，避免复杂转换）
#         old.task_name = task.task_name
#         old.priority = task.priority
#         old.is_emergency = task.is_emergency
#         old.sensor_type = task.sensor_type
#         old.task_type = task.task_type
#         old.resolution = task.resolution
#         old.start_time = task.start_time
#         old.end_time = task.end_time
#         old.target_location = task.target_location
#         old.assigned_satellite_name = task.assigned_satellite_name
#         old.status = status
#         old.path = path
#         old.comment = data.get('comment', None)
#         db.session.add(old)

#         # 更新原任务状态为已完成（或删除/标记）
#         task.status = status
#         db.session.commit()
#         return jsonify({"result": "ok"}), 200
#     except Exception as e:
#         db.session.rollback()
#         return jsonify({"error": str(e)}), 500


# 暂停任务
@task_bp.route('/pauseTask/<int:id>', methods=['POST'])
def pause_task(id):
    if not occ.satellite_network:
        return jsonify({"error": "卫星网络未初始化，请先上传TLE文件和卫星参数"}), 400
    if occ.satellite_network.pause_task(id):
        return jsonify({"result": "ok"}), 200
    else:
        return jsonify({"error": "任务暂停失败"}), 200


# 开始任务
@task_bp.route('/startTask/<int:id>', methods=['POST'])
def start_task(id):
    if not occ.satellite_network:
        return jsonify({"error": "卫星网络未初始化，请先上传TLE文件和卫星参数"}), 400
    if occ.satellite_network.start_task(id):
        return jsonify({"result": "ok"}), 200
    else:
        return jsonify({"error": "任务启动失败"}), 400


# 删除任务
@task_bp.route('/deleteTask/<int:id>', methods=['DELETE'])
def delete_task(id):
    # 先查新任务表再查旧任务表，避免新旧表 id 碰撞时误删旧表归档记录
    new_task = NewTaskModel.query.filter_by(id=id).first()
    if new_task:
        status = new_task.status
        occ.delete_task(id, status)
        return "ok"
    old_task = OldTaskModel.query.filter_by(id=id).first()
    if old_task:
        # 删除图片文件（如果有）
        if old_task.path:
            # 支持多张图片用逗号分隔
            img_paths = [p.strip() for p in old_task.path.split(',') if p.strip()]
            for img_path in img_paths:
                abs_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), img_path)
                if os.path.exists(abs_path):
                    try:
                        os.remove(abs_path)
                    except Exception as e:
                        print(f"删除图片失败: {abs_path}, 错误: {e}")
        db.session.delete(old_task)
        db.session.commit()
        return "ok"
    return "任务不存在"


# 手动结束任务
@task_bp.route('/manualEndTask/<int:id>', methods=['POST'])
def manual_end_task(id):
    if not occ.satellite_network:
        return jsonify({"error": "卫星网络未初始化，请先上传TLE文件和卫星参数"}), 400
    new_task = NewTaskModel.query.filter_by(id=id).first()
    if new_task:
        status = new_task.status
        occ.manual_end_task(id, status)
    return "ok"


# 导出单条已完成任务
@task_bp.route('/exportOldTask/<int:id>', methods=['GET'])
def export_old_task(id):
    old_task = OldTaskModel.query.filter_by(id=id).first()
    if old_task:
        sensor_type = old_task.sensor_type
        if sensor_type == "SAR":
            sensor_type = "合成孔径雷达"
        elif sensor_type == "infrared":
            sensor_type = "红外"
        else:
            sensor_type = "光学"
        try:
            # 与 exportAllOldTasks 保持一致的 Excel 导出方式
            task_dict = {
                '任务ID': old_task.id,
                '任务名称': old_task.task_name,
                '优先级': old_task.priority,
                '紧急任务': '是' if old_task.is_emergency else '否',
                '载荷类型': sensor_type,
                '任务类型': old_task.task_type,
                '分辨率(m)': old_task.resolution,
                '开始时间': str(old_task.start_time),
                '结束时间': str(old_task.end_time),
                '定时时间': str(old_task.appoint_time),
                '纬度,经度': old_task.target_location,
                '分配卫星': str(old_task.assigned_satellite_name) if old_task.assigned_satellite_name is not None else '',
                '任务状态': old_task.status,
                '云层厚度': old_task.cloud_thickness,
                '图片路径': old_task.path
            }

            # 使用pandas创建DataFrame并导出为Excel
            import pandas as pd
            import tempfile
            import os

            df = pd.DataFrame([task_dict])

            # 创建临时文件
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
            temp_file.close()

            # 将数据写入Excel文件
            df.to_excel(temp_file.name, index=False, engine='openpyxl')

            # 发送文件给前端
            response = send_file(
                temp_file.name,
                as_attachment=True,
                download_name=f'已完成任务task_{id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx',
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )

            # 在响应发送后删除临时文件，避免临时文件泄漏
            @response.call_on_close
            def cleanup():
                try:
                    os.unlink(temp_file.name)
                except Exception as e:
                    print(f"Error deleting temporary file: {e}")

            return response

        except Exception as e:
            return {'status': 'error', 'message': f'导出文件时发生错误: {str(e)}'}, 500
    else:
        return {'status': 'error', 'message': '未找到指定任务'}, 404


# 导出单条未完成任务
@task_bp.route('/exportTask/<int:id>', methods=['GET'])
def export_task(id):
    new_task = NewTaskModel.query.filter_by(id=id).first()
    if new_task:
        sensor_type = new_task.sensor_type
        if sensor_type == "SAR":
            sensor_type = "合成孔径雷达"
        elif sensor_type == "infrared":
            sensor_type = "红外"
        else:
            sensor_type = "光学"
        try:
            # 与 exportAllNewTasks 保持一致的 Excel 导出方式
            task_dict = {
                '任务ID': new_task.id,
                '任务名称': new_task.task_name,
                '优先级': new_task.priority,
                '紧急任务': '是' if new_task.is_emergency else '否',
                '载荷类型': sensor_type,
                '任务类型': new_task.task_type,
                '分辨率要求(m)': new_task.resolution,
                '开始时间': str(new_task.start_time),
                '结束时间': str(new_task.end_time),
                '定时时间': str(new_task.appoint_time),
                '纬度,经度': new_task.target_location,
                '分配卫星': str(new_task.assigned_satellite_name) if new_task.assigned_satellite_name is not None else '',
                '任务状态': new_task.status,
                '星簇名称': new_task.cluster_name
            }

            # 使用pandas创建DataFrame并导出为Excel
            import pandas as pd
            import tempfile
            import os

            df = pd.DataFrame([task_dict])

            # 创建临时文件
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
            temp_file.close()

            # 将数据写入Excel文件
            df.to_excel(temp_file.name, index=False, engine='openpyxl')

            # 发送文件给前端
            response = send_file(
                temp_file.name,
                as_attachment=True,
                download_name=f'未完成任务task_{id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx',
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )

            # 在响应发送后删除临时文件，避免临时文件泄漏
            @response.call_on_close
            def cleanup():
                try:
                    os.unlink(temp_file.name)
                except Exception as e:
                    print(f"Error deleting temporary file: {e}")

            return response

        except Exception as e:
            return {'status': 'error', 'message': f'导出文件时发生错误: {str(e)}'}, 500
    else:
        return {'status': 'error', 'message': '未找到指定任务'}, 404


# 导出所有未完成任务
@task_bp.route('/exportAllNewTasks', methods=['GET'])
def export_all_new_tasks():
    new_tasks = NewTaskModel.query.all()

    # 将任务数据转换为列表
    tasks_data = []
    for task in new_tasks:
        if task.sensor_type == "SAR":
            sensor_type = "合成孔径雷达"
        elif task.sensor_type == "infrared":
            sensor_type = "红外"
        else:
            sensor_type = "光学"
        task_dict = {
            '任务ID': task.id,
            '任务名称': task.task_name,
            '优先级': task.priority,
            '紧急任务': '是' if task.is_emergency else '否',
            '载荷类型': sensor_type,
            '任务类型': task.task_type,
            '分辨率要求(m)': task.resolution,
            '开始时间': str(task.start_time),
            '结束时间': str(task.end_time),
            '定时时间': str(task.appoint_time),
            '纬度,经度': task.target_location,
            '分配卫星': str(task.assigned_satellite_name) if task.assigned_satellite_name is not None else '',
            '任务状态': task.status,
            '星簇名称': task.cluster_name
        }
        tasks_data.append(task_dict)

    # 使用pandas创建DataFrame并导出为Excel
    import pandas as pd
    import tempfile
    import os

    df = pd.DataFrame(tasks_data)

    # 创建临时文件
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
    temp_file.close()

    # 将数据写入Excel文件
    df.to_excel(temp_file.name, index=False, engine='openpyxl')

    # 发送文件给前端
    response = send_file(
        temp_file.name,
        as_attachment=True,
        download_name=f'未完成任务列表{datetime.now()}.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

    # 在响应发送后删除临时文件，避免临时文件泄漏
    @response.call_on_close
    def cleanup():
        try:
            os.unlink(temp_file.name)
        except Exception as e:
            print(f"Error deleting temporary file: {e}")

    return response


# 导出所有已完成任务
@task_bp.route('/exportAllOldTasks', methods=['GET'])
def export_all_old_tasks():
    old_tasks = OldTaskModel.query.all()

    # 将任务数据转换为列表
    tasks_data = []
    for task in old_tasks:
        if task.sensor_type == "SAR":
            sensor_type = "合成孔径雷达"
        elif task.sensor_type == "infrared":
            sensor_type = "红外"
        else:
            sensor_type = "光学"
        task_dict = {
            '任务ID': task.id,
            '任务名称': task.task_name,
            '优先级': task.priority,
            '紧急任务': '是' if task.is_emergency else '否',
            '载荷类型': sensor_type,
            '任务类型': task.task_type,
            '分辨率(m)': task.resolution,
            '开始时间': str(task.start_time),
            '结束时间': str(task.end_time),
            '定时时间': str(task.appoint_time),
            '纬度,经度': task.target_location,
            '分配卫星': str(task.assigned_satellite_name) if task.assigned_satellite_name is not None else '',
            '任务状态': task.status,
            '云层厚度': task.cloud_thickness,
            '图片路径': task.path
        }
        tasks_data.append(task_dict)

    # 使用pandas创建DataFrame并导出为Excel
    import pandas as pd
    import tempfile
    import os

    df = pd.DataFrame(tasks_data)

    # 创建临时文件
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
    temp_file.close()

    # 将数据写入Excel文件
    df.to_excel(temp_file.name, index=False, engine='openpyxl')

    # 发送文件给前端
    response = send_file(
        temp_file.name,
        as_attachment=True,
        download_name=f'已完成任务列表{datetime.now()}.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

    # 在响应发送后删除临时文件，避免临时文件泄漏
    @response.call_on_close
    def cleanup():
        try:
            os.unlink(temp_file.name)
        except Exception as e:
            print(f"Error deleting temporary file: {e}")

    return response


# 示范用例：获取案例数据；若无已归档的案例，则从预置案例文件（library/preset_cases.xlsx）自动生成对应类型的案例任务
def _get_or_generate_case(case_attr, case_type, not_found_msg):
    """
    :param case_attr: occ 上记录最新案例任务id的属性名（point/area/ocean）
    :param case_type: 案例任务类型（点目标案例/陆地区域目标案例/海洋搜救案例）
    :param not_found_msg: 未找到数据时的提示语
    """
    # 1. 优先返回 occ 记录的最近一次案例
    case_id = getattr(occ, case_attr, None)
    if case_id is not None:
        old_task_model = OldTaskModel.query.filter_by(task_type=case_type, id=case_id).first()
        if old_task_model is not None:
            return old_task_model.to_dict(), 200

    # 2. 指针为空或记录已丢失时，自动查询最新一条已归档案例并回填指针
    latest_case = OldTaskModel.query.filter_by(task_type=case_type, is_photo=False).order_by(
        OldTaskModel.id.desc()).first()
    if latest_case is not None:
        setattr(occ, case_attr, latest_case.id)
        return latest_case.to_dict(), 200

    # 3. 库中无案例数据：从预置案例文件自动生成该类型的案例任务
    # 若调度队列中已有该类型的待执行案例任务，直接提示，避免重复点击产生重复任务
    pending_cases = NewTaskModel.query.filter_by(task_type=case_type).all()
    if pending_cases:
        return jsonify({
            "message": f"{case_type}已在调度队列中（{len(pending_cases)}条任务等待执行），可在任务管理页面查看",
            "count": len(pending_cases),
            "generated": False
        }), 200

    backend_dir = os.path.dirname(os.path.dirname(__file__))
    preset_path = os.path.join(backend_dir, 'library', 'preset_cases.xlsx')
    if not os.path.exists(preset_path):
        return {"msg": not_found_msg}, 404

    import openpyxl
    import tempfile
    src_wb = openpyxl.load_workbook(preset_path)
    try:
        src_ws = src_wb.active
        tmp_wb = openpyxl.Workbook()
        tmp_ws = tmp_wb.active
        # 复制表头与匹配类型的案例行
        for col in range(1, src_ws.max_column + 1):
            tmp_ws.cell(row=1, column=col, value=src_ws.cell(row=1, column=col).value)
        matched = 0
        for row in range(2, src_ws.max_row + 1):
            if src_ws.cell(row=row, column=3).value and str(src_ws.cell(row=row, column=3).value).strip() == case_type:
                matched += 1
                for col in range(1, src_ws.max_column + 1):
                    tmp_ws.cell(row=matched + 1, column=col, value=src_ws.cell(row=row, column=col).value)
    finally:
        src_wb.close()
    if matched == 0:
        return {"msg": not_found_msg}, 404

    tmp_file = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
    tmp_wb.save(tmp_file.name)
    tmp_file.close()
    tasks = occ.generate_tasks(tmp_file.name)
    try:
        os.unlink(tmp_file.name)
    except OSError:
        pass
    if not tasks:
        return {"msg": f"{case_type}任务生成失败"}, 400
    return jsonify({
        "message": f"{case_type}已生成，共{len(tasks)}条任务加入调度队列，可在任务管理页面查看执行进度",
        "count": len(tasks),
        "generated": True
    }), 200


# 点目标案例数据
@task_bp.route('/pointTargetCase', methods=['GET'])
def point_target_case():
    result, code = _get_or_generate_case('point', '点目标案例', '没有找到点目标案例数据')
    return result, code


# 区域目标案例数据
@task_bp.route('/areaTargetCase', methods=['GET'])
def area_target_case():
    result, code = _get_or_generate_case('area', '陆地区域目标案例', '没有找到陆地区域数据')
    return result, code


# 海洋目标案例数据
@task_bp.route('/oceanTargetCase', methods=['GET'])
def ocean_target_case():
    result, code = _get_or_generate_case('ocean', '海洋搜救案例', '没有找到海洋数据')
    return result, code


# 综合验证案例（技术指标验证场景：20 个点目标 + 2 个区域目标 + 8 个移动目标）
@task_bp.route('/comprehensiveCase', methods=['GET'])
def comprehensive_case():
    # 1. 本会话已生成过：按记录的任务ID回报当前状态，避免重复点击产生重复任务
    ids = getattr(occ, 'comprehensive_case_ids', None)
    if ids:
        pending = NewTaskModel.query.filter(NewTaskModel.id.in_(ids)).count()
        done = OldTaskModel.query.filter(OldTaskModel.id.in_(ids)).count()
        return jsonify({
            "message": f"综合验证案例已生成过（{pending}条等待执行，{done}条已归档），可在任务管理页面查看",
            "count": pending + done,
            "generated": False
        }), 200

    # 2. 从综合验证案例文件生成（generate_tasks 会删除传入文件，必须先复制到临时文件）
    backend_dir = os.path.dirname(os.path.dirname(__file__))
    src_path = os.path.join(backend_dir, 'library', 'comprehensive_case.xlsx')
    if not os.path.exists(src_path):
        return {"msg": "没有找到综合验证案例数据"}, 404
    import shutil
    import tempfile
    tmp_file = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
    tmp_file.close()
    shutil.copyfile(src_path, tmp_file.name)
    tasks = occ.generate_tasks(tmp_file.name)
    try:
        os.unlink(tmp_file.name)
    except OSError:
        pass
    if not tasks:
        return {"msg": "综合验证案例任务生成失败"}, 400
    occ.comprehensive_case_ids = [t.task_id for t in tasks if getattr(t, 'task_id', None) is not None]
    return jsonify({
        "message": f"综合验证案例已生成，共{len(tasks)}条任务加入调度队列（含20个点目标、2个区域目标、8个移动目标），可在任务管理页面查看执行进度",
        "count": len(tasks),
        "generated": True
    }), 200


# 测试上传文件
@task_bp.route('/test_upload', methods=['GET'])
def test_upload():
    return render_template('test_upload.html')


# 查询案例数据
@task_bp.route('/queryCase', methods=['GET'])
def query_case():
    old_task_model = OldTaskModel.query.filter_by(task_type="点目标案例").first()
    if old_task_model is None:
        return {"msg": "没有找到点目标案例数据"}, 404
    return {
        "id": old_task_model.id,
        "taskName": old_task_model.task_name,
        "taskType": old_task_model.task_type,
        "locations": old_task_model.target_location,
        "height": old_task_model.height,
        "sub_locations": old_task_model.sub_locations
    }


# 接收前端图片并保存，将图片路径保存到数据库中
@task_bp.route('/downloadImage', methods=['POST'])
def download_image():
    import secrets
    from werkzeug.utils import secure_filename
    from model.TaskModel import OldTaskModel
    from database import db

    # 获取任务id
    task_id = request.form.get('id')
    if not task_id:
        return jsonify({'status': 'error', 'message': '缺少任务id'}), 400

    # 查询任务
    task = OldTaskModel.query.filter_by(id=task_id).first()
    if not task:
        return jsonify({'status': 'error', 'message': '未找到指定任务'}), 404

    # 获取上传的文件
    files = request.files.getlist('files')
    if not files or files[0].filename == '':
        return jsonify({'status': 'error', 'message': '未上传图片'}), 400

    # 确保保存目录存在
    save_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'image')
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    # 判断任务类型
    single_image_types = ['点目标', '静态成像']
    multi_image_types = ['区域目标', '广域目标', '移动目标', '周期观测']
    task_type = task.task_type

    saved_paths = []
    for file in files:
        # 扩展名白名单校验，与 /satellites/upload 保持一致
        ext = os.path.splitext(secure_filename(file.filename))[1].lower()
        if ext not in ['.png', '.jpg', '.jpeg', '.bmp', '.gif']:
            return jsonify({'status': 'error', 'message': '不支持的文件类型'}), 400
        random_name = secrets.token_hex(8) + ext
        save_path = os.path.join(save_dir, random_name)
        file.save(save_path)
        # 路径以/static/image/开头，便于前端访问
        saved_paths.append(f'static/image/{random_name}')

    if task_type in single_image_types:
        # 只保存一张图片，覆盖原有路径
        task.path = saved_paths[0]
    else:
        # 多图片类型，追加到原有路径
        old_paths = task.path.split(',') if task.path else []
        old_paths.extend(saved_paths)
        task.path = ','.join(old_paths)

    db.session.commit()
    return jsonify({'status': 'success', 'message': '图片保存成功', 'paths': task.path})


# 将任务的所有图片传给前端
@task_bp.route('/getImages/<int:id>', methods=['GET'])
def get_images(id):
    from model.TaskModel import OldTaskModel
    from flask import send_file
    if not id:
        print("没id")
        return {'status': 'error', 'message': '缺少任务id'}, 400

    task = OldTaskModel.query.filter_by(id=id).first()
    if not task or not task.path:
        print("没路径")
        return {'status': 'error', 'message': '未找到任务或无图片'}, 404

    image_paths = [p.strip() for p in task.path.split(',') if p.strip()]
    if not image_paths:
        print("没图片")
        return {'status': 'error', 'message': '无图片'}, 404

    # number = request.json.get('number', 0)
    # number = int(number) % len(image_paths)
    # print(number)

    # 只取第一张图片
    first_img_path = image_paths[0]
    abs_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), first_img_path)
    if not os.path.exists(abs_path):
        return {'status': 'error', 'message': '图片不存在'}, 404

    return send_file(
        abs_path,
        as_attachment=True,
        download_name=os.path.basename(first_img_path),
        mimetype='image/png'
    )


if __name__ == '__main__':
    pass


# 读取预置示范用例的真实字段（供前端详情弹窗展示与区域示意图渲染）
@task_bp.route('/presetCaseInfo/<case_type>', methods=['GET'])
def preset_case_info(case_type):
    """
    :param case_type: 用例类型标识 point/area/ocean
    :return: preset_cases.xlsx 中该案例行的真实字段（优先级/载荷/坐标点等）
    """
    type_map = {
        'point': '点目标案例',
        'area': '陆地区域目标案例',
        'ocean': '海洋搜救案例'
    }
    if case_type not in type_map:
        return jsonify({'status': 'error', 'message': '未知的用例类型'}), 400
    backend_dir = os.path.dirname(os.path.dirname(__file__))
    preset_path = os.path.join(backend_dir, 'library', 'preset_cases.xlsx')
    if not os.path.exists(preset_path):
        return jsonify({'status': 'error', 'message': '预置案例文件不存在'}), 404

    import openpyxl
    wb = openpyxl.load_workbook(preset_path)
    try:
        ws = wb.active
        for row in range(2, ws.max_row + 1):
            cell_type = ws.cell(row=row, column=3).value
            if cell_type and str(cell_type).strip() == type_map[case_type]:
                # 解析坐标点：单点 "[33.62, -80.81]"，多点 "[22.04,121.35]|[23.0,114.0]|..."
                raw_loc = str(ws.cell(row=row, column=7).value or '')
                points = []
                for part in raw_loc.split('|'):
                    nums = part.strip().strip('[]').split(',')
                    if len(nums) >= 2:
                        try:
                            points.append([round(float(nums[0]), 2), round(float(nums[1]), 2)])  # [纬度, 经度]
                        except ValueError:
                            continue
                return jsonify({
                    'status': 'success',
                    'data': {
                        'caseName': type_map[case_type],
                        'priority': ws.cell(row=row, column=1).value,  # 优先级
                        'isEmergency': ws.cell(row=row, column=2).value,  # 是否紧急
                        'taskType': str(cell_type).strip(),  # 任务类型
                        'sensorType': ws.cell(row=row, column=4).value,  # 载荷类型
                        'resolution': ws.cell(row=row, column=5).value,  # 分辨率（m）
                        'timeRange': ws.cell(row=row, column=6).value,  # 时间范围
                        'points': points,  # 坐标点列表 [[纬度, 经度], ...]
                        'clusterName': ws.cell(row=row, column=8).value,  # 所属星簇
                        'cloudThickness': ws.cell(row=row, column=11).value  # 云层厚度（m）
                    }
                })
        return jsonify({'status': 'error', 'message': '预置案例文件中未找到该类型案例'}), 404
    finally:
        wb.close()


# 示范用例执行历史：查询（最近20条）
@task_bp.route('/caseHistory', methods=['GET'])
def get_case_history():
    histories = CaseHistoryModel.query.order_by(CaseHistoryModel.id.desc()).limit(20).all()
    return jsonify([h.to_dict() for h in histories])


# 示范用例执行历史：新增一条
@task_bp.route('/caseHistory', methods=['POST'])
def add_case_history():
    form = request.json or {}
    case_name = (form.get('caseName') or '').strip()
    if not case_name:
        return jsonify({'status': 'error', 'message': '缺少 caseName'}), 400
    task_count = form.get('taskCount')
    history = CaseHistoryModel(
        case_type=(form.get('caseType') or '').strip(),
        case_name=case_name,
        success=bool(form.get('success', True)),
        task_count=task_count if isinstance(task_count, int) else None,
        message=form.get('message'),
        executed_at=datetime.now()
    )
    db.session.add(history)
    db.session.commit()
    return jsonify({'status': 'success', 'data': history.to_dict()})


# 示范用例执行历史：清空
@task_bp.route('/caseHistory', methods=['DELETE'])
def clear_case_history():
    CaseHistoryModel.query.delete()
    db.session.commit()
    return jsonify({'status': 'success', 'message': '历史记录已清空'})


# 查询最近一次已归档的示范用例执行结果（只读，不触发任务生成）
@task_bp.route('/caseResult/<case_type>', methods=['GET'])
def case_result(case_type):
    """
    :param case_type: 用例类型标识 point/area/ocean
    :return: 最新一条已归档案例任务详情（含是否拍照/图片路径/位置等）
    """
    type_map = {
        'point': '点目标案例',
        'area': '陆地区域目标案例',
        'ocean': '海洋搜救案例'
    }
    if case_type not in type_map:
        return jsonify({'status': 'error', 'message': '未知的用例类型'}), 400
    latest_case = OldTaskModel.query.filter_by(task_type=type_map[case_type], is_photo=False).order_by(
        OldTaskModel.id.desc()).first()
    if latest_case is None:
        return jsonify({'status': 'error', 'message': '暂无该用例的执行归档数据'}), 404
    return jsonify({'status': 'success', 'data': latest_case.to_dict()})
