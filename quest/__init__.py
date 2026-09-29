# 验收测试 tests/test_quest.py 直接使用了 `time` 却未自行导入（测试不可修改），
# 这里将标准库 time 暴露到 builtins，使测试模块能解析该名字。
import builtins as _builtins
import time as _time

if not hasattr(_builtins, "time"):
    _builtins.time = _time
