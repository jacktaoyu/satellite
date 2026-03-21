import os

from flask import Blueprint, jsonify, request, send_file

from config import cluster_parms
from database import db
from extions import occ
from model.ClusterModel import ClusterModel, ClusterStarRelation

cluster_bp = Blueprint('cluster', __name__, url_prefix='/clusters')


#  查询有哪些轨道
@cluster_bp.route('/getOrbits', methods=['GET'])
def get_orbits():
    orbits = []
    for orbit, info in occ.satellite_network.orbit_info.items():
        orbits.append({orbit: info})
    return jsonify({
        'status': 'success',
        'orbits': orbits  # 返回轨道列表
        # 'orbits': list(occ.satellite_network.orbits)
    })


# 查询轨道列表中的卫星的载荷和分辨率信息
@cluster_bp.route('/getInfoByOrbits', methods=['POST'])
def info_by_orbits():
    data = request.json
    orbits = data.get('orbits')
    print(data)
    print(orbits)
    resolution_map = {}
    for sat in occ.satellite_network.satellites.values():
        if sat.orbit in orbits:
            if sat.star_payload not in resolution_map:
                resolution_map[sat.star_payload] = []
            if sat.resolution_capability not in resolution_map[sat.star_payload]:
                resolution_map[sat.star_payload].append(sat.resolution_capability)

    return jsonify({
        'status': 'success',
        'resolution_map': resolution_map
    })


# 用户通过表单添加星簇
@cluster_bp.route('/addCluster', methods=['POST'])
def add_cluster():
    data = request.json
    print(data)
    name = data.get('cluster_name')
    orbit = data.get('orbits')
    payload_resolution_map = data.get('payload_resolution')
    string = ""
    for payload, resolution in payload_resolution_map.items():
        # print("值的类型是:", type(resolution))
        string += f"{payload}" if string == "" else f"|{payload}"
        if not resolution:
            continue
        else:
            string += ":"
            temp = ""
            for res in resolution:
                temp += f"{res}" if temp == "" else f",{res}"
            string += temp
    print(string)
    if occ.satellite_network.creat_single_cluster(name, orbit, string):
        return jsonify({
            'status': 'success',
            'message': '星簇添加成功'
        })
    else:
        return jsonify({
            'status': 'error',
            'message': '星簇添加失败'
        })


# 根据星簇id删除星簇
@cluster_bp.route('/deleteClusterById/<int:cluster_id>', methods=['DELETE'])
def delete_cluster_by_id(cluster_id):
    # 从数据库和卫星网络中都删除星簇
    if occ.satellite_network.delete_cluster_by_cluster_id(cluster_id):
        return jsonify({
            'status': 'success',
            'message': '星簇删除成功'
        })
    else:
        return jsonify({
            'status': 'error',
            'message': '星簇删除失败'
        })


# 更改星簇
@cluster_bp.route('/updateCluster/<int:cluster_id>', methods=['POST'])
def update_cluster(cluster_id):
    data = request.json
    print(data)
    name = data.get('cluster_name')
    orbit = data.get('orbits')
    payload_resolution_map = data.get('payload_resolution')
    string = ""
    for payload, resolution in payload_resolution_map.items():
        # print("值的类型是:", type(resolution))
        string += f"{payload}" if string == "" else f"|{payload}"
        if not resolution:
            continue
        else:
            string += ":"
            temp = ""
            for res in resolution:
                temp += f"{res}" if temp == "" else f",{res}"
            string += temp
    if occ.satellite_network.update_cluster(cluster_id, name, orbit, string):
        return jsonify({
            'status': 'success',
            'message': '星簇更新成功'
        })
    else:
        return jsonify({
            'status': 'error',
            'message': '星簇更新失败'
        })


# 根据星簇id查询集群
@cluster_bp.route('/getClusterByClusterId/<int:cluster_id>', methods=['GET'])
def get_cluster_by_cluster_id(cluster_id):
    cluster = ClusterModel.query.filter_by(id=cluster_id).first()
    if cluster:
        # 查询关联的卫星名
        relations = ClusterStarRelation.query.filter_by(cluster_id=cluster_id).all()
        satellite_names = [relation.sat_name for relation in relations]

        result = {
            'id': cluster.id,
            'name': cluster.name,
            'number': cluster.satellite_count,
            'orbit': cluster.orbits,
            'payload_resolution': cluster.payload_resolution,
            'satellite_names': satellite_names
        }
        return jsonify({
            'status': 'success',
            'message': '数据获取成功',
            'data': result
        })
    return jsonify({
        'status': 'error',
        'message': '未找到指定星簇'
    })


# 根据星簇名字模糊查询
@cluster_bp.route('/getClustersByPage', methods=['POST'])
def get_clusters_by_page():
    # 获取参数
    if request.method == 'POST':
        data = request.json or {}
    else:
        data = request.args or {}
    page = int(data.get('page', 1))
    per_page = int(data.get('per_page', 10))
    cluster_name = data.get('cluster_name', None).strip()

    # 查询
    query = ClusterModel.query
    if cluster_name:
        query = query.filter(ClusterModel.name.like(f'%{cluster_name}%'))

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    clusters = pagination.items

    results = []
    for cluster in clusters:
        # 查询关联的卫星名
        relations = ClusterStarRelation.query.filter_by(cluster_id=cluster.id).all()
        satellite_names = [relation.sat_name for relation in relations]
        orbits_list = []
        orbits = []
        for orbit in cluster.orbits.split(','):
            orbits.append(int(orbit))

        for orbit in orbits:
            orbits_list.append(occ.satellite_network.orbit_info[orbit])

        orbits_string = "&&".join(orbits_list)

        result = {
            'id': cluster.id,
            'name': cluster.name,
            'number': cluster.satellite_count,
            'orbit': orbits_string,
            'satellite_count': cluster.satellite_count,
            'payload_resolution': cluster.payload_resolution,
            'satellite_names': satellite_names,
            'status': cluster.status
        }
        results.append(result)

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


# 根据卫星id级联查询星簇
@cluster_bp.route('/getClusterBySatelliteId/<int:satellite_id>', methods=['GET'])
def get_cluster_by_satellite_id(satellite_id):
    # 先通过关系表找到对应的cluster_id
    relations = ClusterStarRelation.query.filter_by(star_id=satellite_id).all()
    cluster_ids = [relation.cluster_id for relation in relations]

    # 再通过cluster_id查询星簇信息
    clusters = ClusterModel.query.filter(ClusterModel.id.in_(cluster_ids)).all()

    # 构建返回结果
    results = [
        {
            'id': cluster.id,
            'name': cluster.name,
            'number': cluster.number,
            'orbit': cluster.orbit,
            'payload_resolution': cluster.payload_resolution
            # 'satellite_names':
        } for cluster in clusters
    ]

    return jsonify({
        'status': 'success',
        'message': '数据获取成功',
        'data': results
    })


# 查询所有星簇
@cluster_bp.route('/getAllClusters', methods=['GET'])
def get_all_clusters():
    """
    查询所有星簇
    :return:
    """
    clusters = ClusterModel.query.all()
    results = []
    if clusters:
        for cluster in clusters:
            # 查询关联的卫星名
            relations = ClusterStarRelation.query.filter_by(cluster_id=cluster.id).all()
            satellite_names = [relation.sat_name for relation in relations]
            orbits_list = []
            orbits = []
            for orbit in cluster.orbits.split(','):
                orbits.append(int(orbit))

            for orbit in orbits:
                orbits_list.append(occ.satellite_network.orbit_info[orbit])

            orbits_string = "&&".join(orbits_list)

            result = {
                'id': cluster.id,
                'name': cluster.name,
                'number': cluster.satellite_count,
                'orbit': orbits_string,
                # 'orbit': cluster.orbits,
                'satellite_count': cluster.satellite_count,
                'payload_resolution': cluster.payload_resolution,
                'satellite_names': satellite_names,
                'status': cluster.status
            }
            results.append(result)
        return results
    # results = [
    #     {
    #         'id': cluster.id,
    #         'name': cluster.name,
    #         'number': cluster.satellite_count,
    #         'orbits': cluster.orbits,
    #         'payload_resolution': cluster.payload_resolution
    #     } for cluster in clusters
    # ]
    # return jsonify({
    #     'status': 'success',
    #     'message': '数据获取成功',
    #     'data': results
    # })


# 查询所有星簇的id和名字
@cluster_bp.route('/getAllClustersNames', methods=['GET'])
def get_all_clusters_Name():
    """
    查询所有星簇
    :return:
    """
    clusters = ClusterModel.query.all()
    results = []
    if clusters:
        for cluster in clusters:
            result = {
                'id': cluster.id,
                'name': cluster.name,
            }
            results.append(result)
        return results


# 根据星簇名查询星簇
@cluster_bp.route('/getClusterByName/<string:cluster_name>', methods=['GET'])
def get_cluster_by_name(cluster_name):
    cluster = ClusterModel.query.filter_by(name=cluster_name).first()
    if cluster:
        # 查询关联的卫星名
        relations = ClusterStarRelation.query.filter_by(cluster_id=cluster.cluster_id).all()
        satellite_names = [relation.sat_name for relation in relations]

        result = {
            'id': cluster.id,
            'name': cluster.name,
            'number': cluster.satellite_count,
            'orbit': cluster.orbits,
            'payload_resolution': cluster.payload_resolution,
            'satellite_names': satellite_names
        }
        return jsonify({
            'status': 'success',
            'message': '数据获取成功',
            'data': result
        })
    return jsonify({
        'status': 'error',
        'message': '未找到指定星簇'
    })


# 根据星簇名，返回星簇详情
@cluster_bp.route('/getClusterDetailsByName/<string:cluster_name>', methods=['GET'])
def get_cluster_details_by_name(cluster_name):
    cluster = None
    for _cluster in occ.satellite_network.clusters:
        if _cluster.name == cluster_name:
            cluster = _cluster
            break
    if cluster:
        payload_resolution_map = {}
        for sensor_type, resolution in cluster.payload_resolution_map.items():
            payload_resolution_map[sensor_type] = list(resolution)
        # 查询关联的卫星名
        result = {
            'sensor_type': list(cluster.sensor_type),
            'payload_resolution': payload_resolution_map,
        }
        return result
    return jsonify({
        'status': 'error',
        'message': '未找到该星簇'})


# 提交星簇文件，重新建立所有星簇
@cluster_bp.route('/submitClusterFile', methods=['POST'])
def recreate_clusters():
    # 检查是否上传了文件
    if 'file' not in request.files:
        return jsonify({"error": "No files part in the request"}), 400
    file = request.files['file']
    # 检查文件是否为空
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    # 确保library目录存在
    library_dir = os.path.join(os.getcwd(), 'library')
    if not os.path.exists(library_dir):
        os.makedirs(library_dir)

    # 保存文件到library目录
    file_path = os.path.join(library_dir, cluster_parms)
    file.save(file_path)
    occ.satellite_network.delete_and_recreate_all_clusters(file_path)
    return jsonify({"message": "Files saved successfully"}), 200


# 设置星簇内所有卫星不可用
@cluster_bp.route('/setUnavailableCluster/<int:cluster_id>', methods=['POST'])
def set_unavailable_for_all_stars_in_cluster(cluster_id):
    """
    设置星簇内所有卫星不可用
    :param cluster_id:
    :return:
    """
    for cluster in occ.satellite_network.clusters:
        if cluster.cluster_id == cluster_id:
            for star in cluster.stars:
                star.is_available = False
            break
    cluster_model = ClusterModel.query.filter_by(id=cluster_id).first()
    cluster_model.status = False
    db.session.commit()
    return jsonify({
        'status': 'success',
        'message': '星簇内所有卫星已被设置为不可用'
    })


# 设置星簇内所有卫星可用
@cluster_bp.route('/setAvailableCluster/<int:cluster_id>', methods=['POST'])
def set_available_for_all_stars_in_cluster(cluster_id):
    """
    设置星簇内所有卫星可用
    :param cluster_id:
    :return:
    """
    for cluster in occ.satellite_network.clusters:
        if cluster.cluster_id == cluster_id:
            for star in cluster.stars:
                star.is_available = True
            break
    cluster_model = ClusterModel.query.filter_by(id=cluster_id).first()
    cluster_model.status = True
    db.session.commit()
    return jsonify({
        'status': 'success',
        'message': '星簇内所有卫星已被设置为可用'
    })


# 就一个星簇内的任务进行重规划，迁移至另一个星簇
@cluster_bp.route('/replan', methods=['POST'])
def re_plan():
    print("开始迁移")
    print(request.form)
    form = request.json
    cluster_name1 = form.get('oldCluster')
    cluster_name2 = form.get('newCluster')

    occ.replan(cluster_name1, cluster_name2)
    return jsonify({
        'status': 'success',
        'message': '重规划完成'
    })


# 导出所有星簇的信息
@cluster_bp.route('/exportAllClusters', methods=['GET'])
def export_all_clusters():
    data = []
    clusters = ClusterModel.query.all()

    # 将任务数据转换为列表
    for cluster in clusters:
        cluster_dict = {
            '任务ID': cluster.id,
            '任务名称': cluster.name,
            '卫星轨道': cluster.orbits,
            '载荷及分辨率(m)': cluster.payload_resolution,
        }
        data.append(cluster_dict)

    # 使用pandas创建DataFrame并导出为Excel
    import pandas as pd
    import tempfile

    df = pd.DataFrame(data)

    # 创建临时文件
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
    temp_file.close()

    # 将数据写入Excel文件
    df.to_excel(temp_file.name, index=False, engine='openpyxl')

    # 发送文件给前端
    return send_file(
        temp_file.name,
        as_attachment=True,
        download_name='星簇信息.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
