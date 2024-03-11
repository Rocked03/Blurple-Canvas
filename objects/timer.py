from datetime import datetime, timedelta


def strf_delta(t_delta, fmt):
    d = {"d": t_delta.days}
    d["h"], rem = divmod(t_delta.seconds, 3600)
    d["m"], d["s"] = divmod(rem, 60)
    d["s"] += t_delta.microseconds / 1e6
    return fmt.format(**d)


def format_delta(t_delta):
    if t_delta.days:
        return strf_delta(t_delta, "{d}d {h}h {m}m {s:.2f}s")
    if t_delta.seconds >= 3600:
        return strf_delta(t_delta, "{h}h {m}m {s:.2f}s")
    if t_delta.seconds >= 60:
        return strf_delta(t_delta, "{m}m {s:.2f}s")
    return strf_delta(t_delta, "{s:.2f}s")


class Timer:
    def __init__(self):
        self.start = datetime.now()
        self.true_start = self.start

    def mark_raw(self) -> timedelta:
        delta = datetime.now() - self.start
        self.start = datetime.now()
        return delta

    def mark(self, message: str = None, **kwargs):
        msg = self.mark_msg(message, **kwargs)
        if message:
            print(msg)

    def mark_msg(self, message: str, total: bool = False, time: bool = False) -> str:
        if total:
            msg = f"{message} in {format_delta(self.total())}"
        else:
            msg = f"{message} in {format_delta(self.mark_raw())}"
        if time:
            msg += f" ({datetime.now()})"
        return msg

    def total(self):
        return datetime.now() - self.true_start
