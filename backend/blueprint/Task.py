import os
from datetime import datetime, timedelta
from operator import and_

from flask import Blueprint, request, jsonify, render_template, send_file
from sqlalchemy import not_

from database import db
from model.TaskModel import NewTaskModel, OldTaskModel
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
    library_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), ''
                                                                           'library')
    if not os.path.exists(library_dir):
        os.makedirs(library_dir)

    # 保存文件
    file_path = os.path.join(library_dir, file.filename)
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
            'target_target_location': task.target_target_location,
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
    return jsonify({"result": task})


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
@task_bp.route('/pauseTask/<int:id>', methods=['GET'])
def pause_task(id):
    if occ.satellite_network.pause_task(id):
        return jsonify({"result": "ok"}), 200
    else:
        return jsonify({"error": "任务暂停失败"}), 200


# 开始任务
@task_bp.route('/startTask/<int:id>', methods=['GET'])
def start_task(id):
    if occ.satellite_network.start_task(id):
        return jsonify({"result": "ok"}), 200
    else:
        return jsonify({"error": "任务启动失败"}), 400


# 删除任务
@task_bp.route('/deleteTask/<int:id>', methods=['DELETE'])
def delete_task(id):
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
    else:
        new_task = NewTaskModel.query.filter_by(id=id).first()
        if new_task:
            status = new_task.status
            occ.delete_task(id, status)
            return "ok"
        else:
            return "任务不存在"


# 手动结束任务
@task_bp.route('/manualEndTask/<int:id>', methods=['GET'])
def manual_end_task(id):
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
        if old_task:
            try:
                # 格式化任务数据
                task_data = f"""任务详情:
        ID: {old_task.id}
        任务名称: {old_task.task_name}
        优先级: {old_task.priority}
        紧急任务: {'是' if old_task.is_emergency else '否'}
        载荷类型: {sensor_type}
        任务类型: {old_task.task_type}
        分辨率要求(m): {old_task.resolution}
        开始时间: {old_task.start_time}
        结束时间: {old_task.end_time}
        定时时间: {old_task.appoint_time}
        纬度,经度: {old_task.target_location}
        分配卫星: {old_task.assigned_satellite_name if old_task.assigned_satellite_name is not None else ''}
        任务状态: {old_task.status}
        云层厚度: {old_task.cloud_thickness}
        图片路径: {old_task.path}
        """
                # 创建临时文件
                import tempfile
                import os
                from datetime import datetime

                # 创建临时文件
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.txt', mode='w', encoding='utf-8')
                temp_file.write(task_data)
                temp_file.close()

                # 发送文件给前端
                response = send_file(
                    temp_file.name,
                    as_attachment=True,
                    download_name=f'未完成任务task_{id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt',
                    mimetype='text/plain'
                )

                # 添加响应头
                response.headers[
                    "Content-Disposition"] = f"attachment; filename=task_{id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                response.headers["Content-Type"] = "text/plain; charset=utf-8"

                # 在响应发送后删除临时文件
                @response.call_on_close
                def cleanup():
                    try:
                        os.unlink(temp_file.name)
                    except Exception as e:
                        print(f"Error deleting temporary file: {e}")

                return response

            except Exception as e:
                return {'status': 'error', 'message': f'导出文件时发生错误: {str(e)}'}, 500

        return {'status': 'success', 'message': '找到指定任务'}, 200
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
        if new_task:
            try:
                # 格式化任务数据
                task_data = f"""任务详情:
        ID: {new_task.id}
        任务名称: {new_task.task_name}
        优先级: {new_task.priority}
        紧急任务: {'是' if new_task.is_emergency else '否'}
        载荷类型: {sensor_type}
        任务类型: {new_task.task_type}
        分辨率要求(m): {new_task.resolution}
        开始时间: {new_task.start_time}
        结束时间: {new_task.end_time}
        定时时间: {new_task.appoint_time}
        纬度,经度: {new_task.target_location}
        分配卫星: {new_task.assigned_satellite_name if new_task.assigned_satellite_name is not None else ''}
        任务状态: {new_task.status}
        星簇名称: {new_task.cluster_name}
        """
                # 创建临时文件
                import tempfile
                import os
                from datetime import datetime

                # 创建临时文件
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.txt', mode='w', encoding='utf-8')
                temp_file.write(task_data)
                temp_file.close()

                # 发送文件给前端
                response = send_file(
                    temp_file.name,
                    as_attachment=True,
                    download_name=f'未完成任务task_{id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt',
                    mimetype='text/plain'
                )

                # 添加响应头
                response.headers[
                    "Content-Disposition"] = f"attachment; filename=task_{id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                response.headers["Content-Type"] = "text/plain; charset=utf-8"

                # 在响应发送后删除临时文件
                @response.call_on_close
                def cleanup():
                    try:
                        os.unlink(temp_file.name)
                    except Exception as e:
                        print(f"Error deleting temporary file: {e}")

                return response

            except Exception as e:
                return {'status': 'error', 'message': f'导出文件时发生错误: {str(e)}'}, 500
        return {'status': 'success', 'message': '找到指定任务'}, 200
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
    return send_file(
        temp_file.name,
        as_attachment=True,
        download_name=f'未完成任务列表{datetime.now()}.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


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
    return send_file(
        temp_file.name,
        as_attachment=True,
        download_name=f'已完成任务列表{datetime.now()}.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


# 点目标案例数据
@task_bp.route('/pointTargetCase', methods=['GET'])
def point_target_case():
    point = occ.point
    if point is None:
        return {"msg": "没有找到点目标案例数据"}, 400
    old_task_model = OldTaskModel.query.filter_by(task_type="点目标案例", id=point).first()
    if old_task_model is None:
        return {"msg": "没有找到点目标案例数据"}, 404
    return old_task_model.to_dict()


# 区域目标案例数据
@task_bp.route('/areaTargetCase', methods=['GET'])
def area_target_case():
    area = occ.area
    if area is None:
        return {"msg": "没有找到陆地区域数据"}, 400
    old_task_model = OldTaskModel.query.filter_by(task_type="陆地区域目标案例", id=area).first()
    if old_task_model is None:
        return {"msg": "没有找到区域目标案例数据"}, 404
    return old_task_model.to_dict()


# 海洋目标案例数据
@task_bp.route('/oceanTargetCase', methods=['GET'])
def ocean_target_case():
    ocean = occ.ocean
    if ocean is None:
        return {"msg": "没有找到海洋数据"}, 400
    old_task_model = OldTaskModel.query.filter_by(task_type="海洋搜救案例", id=ocean).first()
    if old_task_model is None:
        return {"msg": "没有找到海洋数据"}, 404
    return {
        "id": old_task_model.id,  # 任务id
        "taskName": old_task_model.task_name,  # 任务名
        "priority": old_task_model.priority,  # 任务优先级
        "isEmergency": old_task_model.is_emergency,  # 是否是紧急任务
        "sensorType": old_task_model.sensor_type,  # 载荷类型
        "taskType": old_task_model.task_type,  # 任务类型
        "resolution": old_task_model.resolution,  # 分辨率
        "startTime": str(old_task_model.start_time) if old_task_model.start_time else None,  # 开始时间
        "endTime": str(old_task_model.end_time) if old_task_model.end_time else None,  # 结束时间
        "targetLocation": old_task_model.target_location,  # 目标位置
        "assignedSatelliteName": old_task_model.assigned_satellite_name,  # 所属卫星
        "status": old_task_model.status,  # 任务状态
        "isPhoto": old_task_model.is_photo,  # 是否已经截图
        "path": old_task_model.path.split(",") if old_task_model.path else None,  # 图片路径
        "height": old_task_model.height,  # 卫星高度
        "subLocations": old_task_model.sub_locations,  # 子任务位置
        "cloud_thickness": old_task_model.cloud_thickness  # 云层厚度
    }


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
        ext = os.path.splitext(secure_filename(file.filename))[1]
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
