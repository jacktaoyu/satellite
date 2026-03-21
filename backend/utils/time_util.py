from datetime import timedelta


def get_now_time_from_start(start_time, interval):
    return start_time + timedelta(seconds=interval)
