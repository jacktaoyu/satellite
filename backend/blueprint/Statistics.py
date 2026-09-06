from datetime import datetime, timezone

from flask import Blueprint, jsonify

from database import db
from extions import occ
from model.ClusterModel import ClusterModel
from model.TaskModel import NewTaskModel, OldTaskModel

statistics_bp = Blueprint('statistics', __name__)


# 系统统计数据（供落地页数据看板使用）
@statistics_bp.route('/statistics', methods=['GET'])
def get_statistics():
    # 卫星网络未初始化时容错为 0
    network = occ.satellite_network
    satellite_count = len(network.satellites) if network else 0
    online_clients = len(network.client_sockets) if network else 0
    # 任务统计
    pending_task_count = NewTaskModel.query.count()
    completed_task_count = OldTaskModel.query.count()
    # NewTaskModel.start_time 存的是 UTC naive 时间（入口已统一转 UTC），
    # 与之比较需用 UTC 的“今天”，否则会与本地墙钟差 8 小时
    today = datetime.now(timezone.utc).date()
    today_task_count = NewTaskModel.query.filter(db.func.date(NewTaskModel.start_time) == today).count()
    cluster_count = ClusterModel.query.count()
    return jsonify({
        'status': 'success',
        'data': {
            'satellite_count': satellite_count,
            'today_task_count': today_task_count,
            'pending_task_count': pending_task_count,
            'completed_task_count': completed_task_count,
            'cluster_count': cluster_count,
            'online_clients': online_clients
        }
    })
