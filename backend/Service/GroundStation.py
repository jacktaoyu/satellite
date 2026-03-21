class GroundStation:
    def __init__(self, name, location):
        self.name = name
        self.location = location
        self.connecting_satellite = set()
