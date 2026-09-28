"""任务与成就系统 - 红态测试"""
import pytest
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from quest.achievement import QuestManager, Quest, Achievement
import random

class TestDailyReset:
    def test_reset_uses_server_time(self):
        qm = QuestManager(server_tz_offset=8)
        qm.add_quest(Quest("daily", "日常", type="daily", reset_hour=4))
        # 模拟UTC时间20:00（北京时间凌晨4点）
        utc_time = time.mktime(time.strptime("2026-01-01 20:00:00", "%Y-%m-%d %H:%M:%S"))
        assert qm.is_daily_reset(utc_time) == True  # bug1: 用本地时间可能错

class TestTrackLimit:
    def test_track_has_limit(self):
        qm = QuestManager()
        for i in range(7):
            qm.add_quest(Quest(f"q{i}", f"任务{i}"))
            qm.track_quest(f"q{i}")
        assert len(qm.tracked) <= 5  # bug2: 7个

class TestAchievementRealTime:
    def test_achievement_updates_on_event(self):
        qm = QuestManager()
        qm.achievements["kill_10"] = Achievement("kill_10", "击杀10", "kill", 10)
        # 模拟事件触发（应该实时更新）
        qm.update_achievement("kill_10", 5)
        assert qm.achievements["kill_10"].progress == 5
        # 再触发一次
        qm.update_achievement("kill_10", 10)
        assert qm.check_achievement_complete("kill_10") == True

class TestQuestItemPity:
    def test_quest_item_has_pity(self):
        qm = QuestManager()
        q = Quest("q1", "任务1", item_drops={"item1": 0.1})
        qm.add_quest(q)
        # 连续尝试50次，按保底应该至少出一次
        got = False
        for i in range(50):
            if qm.get_quest_item("q1", "item1"):
                got = True
                break
        assert got == True  # bug4: 10%概率50次不出的概率极低但可能

class TestChainPrereq:
    def test_chain_requires_prereq(self):
        qm = QuestManager()
        qm.add_quest(Quest("step1", "第一步"))
        qm.add_quest(Quest("step2", "第二步", prereq=["step1"]))
        assert qm.can_complete_chain("step2") == False  # bug5: 返回True
        qm.completed_quests.add("step1")
        assert qm.can_complete_chain("step2") == True

class TestAchievementClaim:
    def test_achievement_cannot_claim_twice(self):
        qm = QuestManager()
        qm.achievements["a1"] = Achievement("a1", "成就1", "kill", 1, reward={"gold": 100})
        qm.update_achievement("a1", 1)
        r1 = qm.claim_achievement("a1")
        assert r1 == {"gold": 100}
        r2 = qm.claim_achievement("a1")
        assert r2 is None  # bug6: 又领到了

class TestAbandonRemovesItems:
    def test_abandon_removes_quest_items(self):
        qm = QuestManager()
        q = Quest("q1", "任务1", item_drops={"quest_item_1": 1.0})
        qm.add_quest(q)
        inv = {"quest_item_1": 3, "normal_item": 5}
        result = qm.abandon_quest("q1", inv)
        assert "quest_item_1" not in result  # bug7: 还在
        assert result["normal_item"] == 5
