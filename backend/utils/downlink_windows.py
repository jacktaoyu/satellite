def _window_bounds(window):
    if isinstance(window, dict):
        start = window.get('start', window.get('start_time'))
        end = window.get('end', window.get('end_time'))
    elif (isinstance(window, (list, tuple)) and len(window) == 2
          and not any(isinstance(value, (dict, list, tuple)) for value in window)):
        start, end = window
    else:
        return None
    if start is None or end is None:
        return None
    return start, end


def normalize_downlink_windows(windows):
    """把 list/tuple、单窗口 dict、窗口 ID 映射 dict 统一为二元素元组列表。"""
    if not windows:
        return []
    if isinstance(windows, dict):
        if _window_bounds(windows):
            candidates = [windows]
        else:
            candidates = windows.values()
    elif _window_bounds(windows):
        candidates = [windows]
    else:
        candidates = windows

    normalized = []
    for window in candidates:
        bounds = _window_bounds(window)
        if bounds is not None:
            normalized.append(bounds)
    return normalized
