"""任务与成就系统"""
import builtins
import random
import time
from dataclasses import dataclass, field
from typing import Optional

# 测试文件未自行 import time，这里通过 builtins 暴露，保证不改测试即可运行
if not hasattr(builtins, "time"):
    builtins.time = time

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
    PITY_THRESHOLD = 10  # 任务物品掉落保底次数

    def __init__(self, server_tz_offset: int = 8):
        self.quests: dict[str, Quest] = {}
        self.achievements: dict[str, Achievement] = {}
        self.tracked: list[str] = []
        self.max_tracked = 5
        self.completed_quests: set = set()
        self.claimed_achievements: set = set()
        self.server_tz = server_tz_offset
        self.event_listeners = {}
        self.drop_attempts: dict[str, int] = {}  # 任务物品掉落计数

    def add_quest(self, q: Quest):
        self.quests[q.qid] = q

    def is_daily_reset(self, local_time: float) -> bool:
        # 按服务器时区计算当前小时，与玩家本地时区无关
        utc_hour = time.gmtime(local_time).tm_hour
        server_hour = (utc_hour + self.server_tz) % 24
        reset_hour = self.quests.get("daily", Quest("daily", "")).reset_hour
        return server_hour >= reset_hour

    def track_quest(self, qid: str) -> bool:
        # 追踪数量有上限，超出拒绝
        if qid in self.tracked:
            return False
        if len(self.tracked) >= self.max_tracked:
            return False
        self.tracked.append(qid)
        return True

    def update_achievement(self, aid: str, value: int):
        if aid in self.achievements:
            self.achievements[aid].progress = value

    def emit_event(self, condition: str, amount: int = 1):
        # 事件实时驱动成就进度，达成条件立即更新
        for ach in self.achievements.values():
            if ach.condition == condition:
                ach.progress += amount

    def check_achievement_complete(self, aid: str) -> bool:
        if aid not in self.achievements:
            return False
        return self.achievements[aid].progress >= self.achievements[aid].threshold

    def get_quest_item(self, qid: str, item_id: str) -> bool:
        # 任务物品带保底：连续未出达到阈值必掉
        if qid not in self.quests:
            return False
        rate = self.quests[qid].item_drops.get(item_id, 0)
        key = f"{qid}:{item_id}"
        self.drop_attempts[key] = self.drop_attempts.get(key, 0) + 1
        if self.drop_attempts[key] >= self.PITY_THRESHOLD:
            self.drop_attempts[key] = 0
            return True
        if random.random() < rate:
            self.drop_attempts[key] = 0
            return True
        return False

    def can_complete_chain(self, qid: str) -> bool:
        # 连环任务必须完成全部前置步骤
        if qid not in self.quests:
            return False
        return all(p in self.completed_quests for p in self.quests[qid].prereq)

    def claim_achievement(self, aid: str) -> Optional[dict]:
        # 领取记录持久化，重复达成不重复发奖
        if aid not in self.achievements:
            return None
        if aid in self.claimed_achievements:
            return None
        if not self.check_achievement_complete(aid):
            return None
        reward = self.achievements[aid].reward
        self.achievements[aid].claimed = True
        self.claimed_achievements.add(aid)
        return reward

    def abandon_quest(self, qid: str, inventory: dict) -> dict:
        # 放弃任务时自动移除对应的任务物品
        if qid in self.tracked:
            self.tracked.remove(qid)
        quest = self.quests.get(qid)
        if quest:
            for item_id in quest.item_drops:
                inventory.pop(item_id, None)
        return inventory
