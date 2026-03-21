class Cluster:
    def __init__(self, name):
        """
        初始化星簇
        """
        self.cluster_id = None
        self.name = name
        self.orbits = set()  # 集合， 星簇的轨道
        self.sensor_type = set()  # 集合， 星簇的支持的载荷类型
        self.resolution = set()  # 分辨率
        self.payload_resolution_map = {}  # 载荷类型到分辨率的映射，格式：{'光学': {0.5, 1.0}, '红外': {0.5}}
        self.stars = []  # 星簇的卫星列表
        self.satellite_count = 0  # 星簇中的卫星数量（不包括子星簇）
        self.tasks_list = []  # 任务列表
        self.sub_clusters = []  # 子星簇列表，小的星簇可以合并为大星簇

    def append_sta(self, sta):
        """
        添加卫星到星簇
        """
        # if self.name == "Cluster_4_SAR:0.5,1.0":
        #     print(sta.resolution_capability)
        self.stars.append(sta)
        self.satellite_count = len(self.stars)
        self.orbits.add(sta.orbit)
        self.resolution.add(sta.resolution_capability)
        self.sensor_type.add(sta.star_payload)

        # 更新载荷类型到分辨率的映射
        if sta.star_payload not in self.payload_resolution_map:
            self.payload_resolution_map[sta.star_payload] = set()
        self.payload_resolution_map[sta.star_payload].add(sta.resolution_capability)

    def __str__(self):
        return f"Cluster {self.cluster_id} with {len(self.stars)} stars and {len(self.sub_clusters)} sub-clusters"

    def get_all_sats(self):
        """
        递归获取星簇中所有卫星
        """
        sats = []
        if self.sub_clusters:
            for sub_cluster in self.sub_clusters:
                sats.extend(sub_cluster.get_all_sats())
        else:
            sats = self.stars
        return sats

    def get_all_stars_ids(self):
        """
        获取星簇中所有卫星的id, 包括子星簇
        """
        sats = self.get_all_sats()
        return [sta.sat_name for sta in sats]

    def get_all_sub_clusters_ids(self):
        """
        获取星簇中所有子星簇的id
        """
        return [sub_cluster.cluster_id for sub_cluster in self.sub_clusters]

    def get_all_params(self):
        """
        获取星簇的参数
        """
        return self.cluster_id, list(self.sensor_type), list(
            self.resolution), self.satellite_count, self.get_all_stars_ids(), self.get_all_sub_clusters_ids(), self.payload_resolution_map
