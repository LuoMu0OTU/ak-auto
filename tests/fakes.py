"""测试共享的假对象（Fake 控制器 / Tasker）。

供 scheduler / ExecutionController / 各任务的单元测试复用，
避免每处复制一份；真实游戏不在测试路径上。
"""
from __future__ import annotations

import threading


class FakeNode:
    def __init__(self, name: str) -> None:
        self.name = name


class FakeStatus:
    def __init__(self, ok: bool) -> None:
        self.succeeded = ok
        self.failed = not ok
        self.running = False
        self.pending = False


class FakeDetail:
    def __init__(self, ok: bool, nodes: list[str]) -> None:
        self.status = FakeStatus(ok)
        self.nodes = [FakeNode(n) for n in nodes]


class FakeJob:
    """立即完成的 Job。"""

    def __init__(self, ok: bool = True, nodes: list[str] | None = None) -> None:
        self._detail = FakeDetail(ok, nodes or ["Fake@Done"])

    @property
    def done(self) -> bool:
        return True

    def wait(self) -> None:
        return None

    def get(self) -> FakeDetail:
        return self._detail


class BlockingJob:
    """任务一直挂到 release 被置位（模拟运行中的 MaaFw 任务）。"""

    def __init__(self, release: threading.Event, ok: bool = True, nodes: list[str] | None = None) -> None:
        self._release = release
        self._ok = ok
        self._nodes = nodes or ["Fake@Done"]

    @property
    def done(self) -> bool:
        return self._release.is_set()

    def wait(self) -> None:
        self._release.wait()

    def get(self) -> FakeDetail:
        return FakeDetail(self._ok, self._nodes)


class FakeResource:
    node_list = ["Fake", "Fake@Done", "Recruit", "Fight", "ReturnToHome"]


class FakeTasker:
    """普通假 Tasker：post_task 立即完成（可配置成败与节点）。"""

    resource = FakeResource()

    def __init__(self, ok: bool = True, nodes: list[str] | None = None) -> None:
        self.ok = ok
        self.nodes = nodes or ["Fake@Done"]
        self.posted: list[str] = []

    def post_task(self, entry: str) -> FakeJob:
        self.posted.append(entry)
        return FakeJob(self.ok, self.nodes)


class BlockingTasker:
    """可控假 Tasker：post_stop 模拟 MaaFw 停止并释放当前任务。"""

    resource = FakeResource()

    def __init__(self) -> None:
        self.release = threading.Event()
        self.stop_called = threading.Event()
        self.posted: list[str] = []

    def post_task(self, entry: str) -> BlockingJob:
        self.posted.append(entry)
        return BlockingJob(self.release)

    def post_stop(self) -> FakeJob:
        self.stop_called.set()
        self.release.set()  # 模拟 MaaFw：stop 之后 job 结束
        return FakeJob(ok=True, nodes=[])
