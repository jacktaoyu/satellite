from database import db


class ClusterModel(db.Model):
    """
    星簇表
    """
    __tablename__ = "t_cluster"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)  # 主键id,自增
    name = db.Column(db.String(255), nullable=False)  # 星簇名
    satellite_count = db.Column(db.Integer)  # 星簇中卫星的数量
    orbits = db.Column(db.String(255))  # 星簇中卫星的轨道
    payload_resolution = db.Column(db.String(60))  # 载荷分辨率映射
    status = db.Column(db.Boolean)  # 星簇状态


class ClusterStarRelation(db.Model):
    """
    星簇和卫星关系表
    """
    __tablename__ = "t_cluster_star_relation"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sat_name = db.Column(db.String(255), nullable=False)
    cluster_id = db.Column(db.Integer, nullable=False)
