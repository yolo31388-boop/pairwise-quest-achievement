"""任务与成就系统 - 含7个bug"""
import time
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Quest:
    qid: str
    title: str
    type: str = "normal"  # normal/daily/chain
    prereq: list = field(default_factory=list)
    item_drops: dict = field(default_factory=dict)  # item_id -> drop_rate
    reset_hour: int = 4  # 服务器时间
    tracked: bool = False

@dataclass
class Achievement:
    aid: str
    name: str
    condition: str
    threshold: int
    reward: dict = field(default_factory=dict)
    claimed: bool = False
    progress: int = 0

class QuestManager:
    def __init__(self, server_tz_offset: int = 8):
        self.quests: dict[str, Quest] = {}
        self.achievements: dict[str, Achievement] = {}
        self.tracked: list[str] = []
        self.max_tracked = 5
        self.completed_quests: set = set()
        self.claimed_achievements: set = set()
        self.server_tz = server_tz_offset
        self.event_listeners = {}  # bug: 成就进度不实时监听
        self.drop_attempts: dict[str, int] = {}  # 任务物品掉落计数

    def add_quest(self, q: Quest):
        self.quests[q.qid] = q

    def is_daily_reset(self, local_time: float) -> bool:
        # bug1: 用本地时间而不是服务器时间
        local_hour = time.localtime(local_time).tm_hour
        return local_hour >= self.quests.get("daily", Quest("daily","")).reset_hour

    def track_quest(self, qid: str) -> bool:
        # bug2: 追踪数量无上限
        if qid in self.tracked:
            return False
        self.tracked.append(qid)
        return True

    def update_achievement(self, aid: str, value: int):
        # bug3: 成就进度只在调用时更新，不实时监听
        if aid in self.achievements:
            self.achievements[aid].progress = value

    def check_achievement_complete(self, aid: str) -> bool:
        if aid not in self.achievements:
            return False
        return self.achievements[aid].progress >= self.achievements[aid].threshold

    def get_quest_item(self, qid: str, item_id: str) -> bool:
        # bug4: 任务物品无保底
        if qid not in self.quests:
            return False
        rate = self.quests[qid].item_drops.get(item_id, 0)
        return random.random() < rate  # 无保底机制

    def can_complete_chain(self, qid: str) -> bool:
        # bug5: 连环任务不检查前置
        if qid not in self.quests:
            return False
        return True  # 应该检查prereq是否都在completed_quests

    def claim_achievement(self, aid: str) -> Optional[dict]:
        # bug6: 成就奖励可重复领取
        if aid not in self.achievements:
            return None
        if not self.check_achievement_complete(aid):
            return None
        # bug6续: 不检查claimed_achievements
        reward = self.achievements[aid].reward
        self.achievements[aid].claimed = True
        return reward

    def abandon_quest(self, qid: str, inventory: dict) -> dict:
        # bug7: 放弃任务不移除任务物品
        if qid in self.tracked:
            self.tracked.remove(qid)
        return inventory  # 应该移除对应任务物品
