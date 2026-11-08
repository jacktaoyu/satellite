import json
from datetime import datetime

from sqlalchemy.exc import IntegrityError

from database import db
from model.TaskModel import NewTaskModel, OldTaskModel, TaskResultModel


class TaskResultError(ValueError):
    """可安全返回给客户端的业务错误。"""


class TaskResultService:
    @staticmethod
    def process_result(task, result, height=None, locations=None, archive=True, archive_task=None):
        """持久化结果收件，并在同一事务中归档任务；重复结果幂等成功。"""
        task_uuid = result.get('task_uuid')
        task_id = result.get('task_id')
        if not task_uuid or task_id is None:
            raise TaskResultError('结果缺少 task_uuid 或 task_id')
        try:
            task_id = int(task_id)
        except (TypeError, ValueError):
            raise TaskResultError('task_id 格式错误')

        receipt = TaskResultModel.query.filter_by(task_uuid=task_uuid).first()
        if receipt:
            if receipt.task_id is not None and receipt.task_id != task_id:
                raise TaskResultError('任务 UUID 与数字 ID 不匹配')
            return {'duplicate': True, 'archived': False, 'task_uuid': task_uuid}

        if task is not None:
            if str(getattr(task, 'task_uuid', '')) != str(task_uuid) or task.task_id != task_id:
                raise TaskResultError('任务 UUID 与数字 ID 不匹配')

        new_task = None
        old_task = OldTaskModel.query.filter_by(task_uuid=task_uuid).first()
        if old_task and old_task.id != task_id:
            raise TaskResultError('历史任务 UUID 与数字 ID 冲突')

        target_task = archive_task if archive_task is not None else task
        if archive:
            if target_task is None:
                raise TaskResultError('未知任务结果')
            archive_uuid = str(getattr(target_task, 'task_uuid', task_uuid))
            archive_id = target_task.task_id
            new_task = NewTaskModel.query.filter_by(task_uuid=archive_uuid).first()
            existing_old = OldTaskModel.query.filter_by(task_uuid=archive_uuid).first()
            if existing_old:
                if existing_old.id != archive_id:
                    raise TaskResultError('历史任务 UUID 冲突')
                old_task = existing_old
            elif new_task is None:
                if task.parent_task_id:
                    # 尚未轮到主任务归档的子任务只保留收件记录。
                    archive = False
                else:
                    raise TaskResultError('未知任务结果')
            elif new_task.id != archive_id:
                raise TaskResultError('任务 UUID 与数字 ID 不匹配')
        elif task is None and old_task is None:
            raise TaskResultError('未知任务结果')

        received_at = datetime.utcnow()
        raw_payload = json.dumps(result, ensure_ascii=False)
        status = 'Success' if result.get('result') == '成功' else 'Failed'
        receipt = TaskResultModel(
            task_uuid=task_uuid,
            task_id=task_id,
            status=status,
            result_payload=raw_payload,
            execution_duration_ms=result.get('execution_duration_ms'),
            received_at=received_at
        )
        db.session.add(receipt)
        try:
            if archive and new_task is not None:
                old_task = OldTaskModel(
                    id=new_task.id,
                    task_uuid=new_task.task_uuid,
                    task_name=new_task.task_name,
                    priority=new_task.priority,
                    is_emergency=new_task.is_emergency,
                    sensor_type=new_task.sensor_type,
                    task_type=new_task.task_type,
                    resolution=new_task.resolution,
                    start_time=new_task.start_time,
                    end_time=new_task.end_time,
                    user_start_time=new_task.user_start_time,
                    user_end_time=new_task.user_end_time,
                    battery_before=new_task.battery_before,
                    battery_after=new_task.battery_after,
                    storge_before=new_task.storge_before,
                    storge_after=new_task.storge_after,
                    light_power=new_task.light_power,
                    appoint_time=new_task.appoint_time,
                    target_location=new_task.target_location,
                    assigned_satellite_name=new_task.assigned_satellite_name,
                    status=status,
                    friend_task_id=new_task.friend_task_id,
                    is_photo=False,
                    path=None,
                    height=height,
                    sub_length=len(locations) if locations else None,
                    sub_locations=str(locations) if locations else None,
                    cloud_thickness=new_task.cloud_thickness,
                    comment=new_task.comment,
                    result_payload=raw_payload,
                    result_received_at=received_at
                )
                db.session.delete(new_task)
                db.session.add(old_task)
            db.session.commit()
            return {
                'duplicate': old_task is not None and new_task is None,
                'archived': archive and new_task is not None,
                'task_uuid': task_uuid
            }
        except IntegrityError:
            db.session.rollback()
            receipt = TaskResultModel.query.filter_by(task_uuid=task_uuid).first()
            if receipt and (receipt.task_id is None or receipt.task_id == task_id):
                return {'duplicate': True, 'archived': False, 'task_uuid': task_uuid}
            raise TaskResultError('任务结果或历史 UUID 冲突')
        except Exception:
            db.session.rollback()
            raise
