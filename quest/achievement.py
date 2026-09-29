"""任务与成就系统"""
import random
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
    def __init__(self, server_tz_offset: int = 8, max_tracked: int = 5, pity_threshold: int = 10):
        self.quests: dict[str, Quest] = {}
        self.achievements: dict[str, Achievement] = {}
        self.tracked: list[str] = []
        self.max_tracked = max_tracked
        self.completed_quests: set = set()
        self.claimed_achievements: set = set()  # 领取记录，成就记录被删也不丢
        self.server_tz = server_tz_offset
        self.pity_threshold = pity_threshold  # 任务物品保底次数
        self.event_listeners: dict[str, list] = {}  # condition -> [callback]
        self.drop_attempts: dict[tuple, int] = {}  # (qid, item_id) -> 连续未出次数

    def add_quest(self, q: Quest):
        self.quests[q.qid] = q

    def is_daily_reset(self, timestamp: float) -> bool:
        # 按固定服务器时间点判断，与本地时区无关：
        # 时间戳是绝对的UTC纪元秒，换算到服务器时区再比较小时
        reset_hour = self.quests.get("daily", Quest("daily", "")).reset_hour
        server_hour = time.gmtime(timestamp + self.server_tz * 3600).tm_hour
        return server_hour >= reset_hour

    def track_quest(self, qid: str) -> bool:
        if qid in self.tracked:
            return False
        if len(self.tracked) >= self.max_tracked:
            print(f"追踪列表已满（上限{self.max_tracked}个），无法追踪 {qid}")
            return False
        self.tracked.append(qid)
        return True

    # ---- 成就：实时事件监听 ----
    def add_event_listener(self, condition: str, callback):
        self.event_listeners.setdefault(condition, []).append(callback)

    def emit_event(self, condition: str, amount: int = 1):
        """游戏事件入口：实时推进匹配条件的成就，达成即触发监听"""
        for ach in self.achievements.values():
            if ach.condition == condition and not self.check_achievement_complete(ach.aid):
                ach.progress += amount
                if self.check_achievement_complete(ach.aid):
                    for cb in self.event_listeners.get(condition, []):
                        cb(ach)

    def update_achievement(self, aid: str, value: int):
        if aid in self.achievements:
            self.achievements[aid].progress = value
            ach = self.achievements[aid]
            if self.check_achievement_complete(aid):
                for cb in self.event_listeners.get(ach.condition, []):
                    cb(ach)

    def check_achievement_complete(self, aid: str) -> bool:
        if aid not in self.achievements:
            return False
        return self.achievements[aid].progress >= self.achievements[aid].threshold

    def get_quest_item(self, qid: str, item_id: str) -> bool:
        if qid not in self.quests:
            return False
        rate = self.quests[qid].item_drops.get(item_id, 0)
        key = (qid, item_id)
        self.drop_attempts[key] = self.drop_attempts.get(key, 0) + 1
        # 保底：连续未出达到阈值必出
        if self.drop_attempts[key] >= self.pity_threshold:
            self.drop_attempts[key] = 0
            return True
        if random.random() < rate:
            self.drop_attempts[key] = 0
            return True
        return False

    def can_complete_chain(self, qid: str) -> bool:
        if qid not in self.quests:
            return False
        return all(p in self.completed_quests for p in self.quests[qid].prereq)

    def claim_achievement(self, aid: str) -> Optional[dict]:
        if aid not in self.achievements:
            return None
        if not self.check_achievement_complete(aid):
            return None
        # 领取记录独立于成就记录持久保存，重复达成不重复发奖
        if aid in self.claimed_achievements or self.achievements[aid].claimed:
            return None
        reward = self.achievements[aid].reward
        self.achievements[aid].claimed = True
        self.claimed_achievements.add(aid)
        return reward

    def abandon_quest(self, qid: str, inventory: dict) -> dict:
        if qid in self.tracked:
            self.tracked.remove(qid)
        # 放弃任务时移除对应的任务物品
        quest = self.quests.get(qid)
        if quest:
            for item_id in quest.item_drops:
                inventory.pop(item_id, None)
        return inventory
