"""
测试用例：密码验证时序攻击修复测试

测试修复后的代码是否符合要求：
1. 使用 constant-time 比较
2. 功能正确性
3. 性能测试
"""
import pytest
import time
import statistics
from timing_fixed import (
    verify_password_secure,
    verify_password_hash_secure,
    verify_username_exists_secure,
    TimingSafeAuth
)
from timing_vulnerable import (
    verify_password_vulnerable,
    verify_username_exists_vulnerable
)


class TestConstantTimeComparison:
    """测试 constant-time 比较"""

    def test_correct_password(self):
        """测试正确密码"""
        password = "mySecretPassword123!"
        assert verify_password_secure(password, password) == True

    def test_wrong_password(self):
        """测试错误密码"""
        stored = "mySecretPassword123!"
        wrong = "wrongPassword!"
        assert verify_password_secure(wrong, stored) == False

    def test_partial_match(self):
        """测试部分匹配的密码（时序攻击关键测试）"""
        stored = "mySecretPassword123!"
        # 部分匹配：前几个字符相同
        partial = "mySecretPass"
        assert verify_password_secure(partial, stored) == False

    def test_different_lengths(self):
        """测试不同长度的密码"""
        stored = "password123"
        wrong_short = "pass"
        wrong_long = "password123extra"
        assert verify_password_secure(wrong_short, stored) == False
        assert verify_password_secure(wrong_long, stored) == False


class TestTimingConsistency:
    """测试时序一致性"""

    def test_timing_variation_is_small(self):
        """测试响应时间变差小于阈值（防止时序攻击）"""
        password = "testPassword123!"
        iterations = 100

        # 测试正确密码的时间
        correct_times = []
        for _ in range(iterations):
            start = time.time()
            verify_password_secure(password, password)
            correct_times.append(time.time() - start)

        # 测试错误密码的时间
        wrong_times = []
        for _ in range(iterations):
            start = time.time()
            verify_password_secure("wrongPassword", password)
            wrong_times.append(time.time() - start)

        # 计算标准差
        correct_stdev = statistics.stdev(correct_times)
        wrong_stdev = statistics.stdev(wrong_times)

        # 标准差应该很小（表示时间稳定）
        assert correct_stdev < 0.01, f"Correct password timing too variable: {correct_stdev}"
        assert wrong_stdev < 0.01, f"Wrong password timing too variable: {wrong_stdev}"

        # 平均时间应该接近（防止通过时间区分）
        correct_mean = statistics.mean(correct_times)
        wrong_mean = statistics.mean(wrong_times)
        time_diff = abs(correct_mean - wrong_mean)

        # 时间差异应该小于 5ms（考虑随机抖动）
        assert time_diff < 0.005, f"Timing difference too large: {time_diff}s"


class TestUsernameEnumeration:
    """测试用户枚举防护"""

    def test_existing_user(self):
        """测试存在的用户"""
        user_db = {"alice": "hash1", "bob": "hash2"}
        assert verify_username_exists_secure("alice", user_db) == True

    def test_nonexistent_user(self):
        """测试不存在的用户"""
        user_db = {"alice": "hash1", "bob": "hash2"}
        assert verify_username_exists_secure("charlie", user_db) == False

    def test_username_timing_consistency(self):
        """测试用户名查询时间一致性"""
        user_db = {"alice": "hash1", "bob": "hash2"}
        iterations = 50

        # 测试存在用户的时间
        existing_times = []
        for _ in range(iterations):
            start = time.time()
            verify_username_exists_secure("alice", user_db)
            existing_times.append(time.time() - start)

        # 测试不存在用户的时间
        nonexistent_times = []
        for _ in range(iterations):
            start = time.time()
            verify_username_exists_secure("charlie", user_db)
            nonexistent_times.append(time.time() - start)

        # 平均时间应该接近（防止用户枚举）
        existing_mean = statistics.mean(existing_times)
        nonexistent_mean = statistics.mean(nonexistent_times)
        time_diff = abs(existing_mean - nonexistent_mean)

        # 时间差异应该小于 10ms
        assert time_diff < 0.010, f"Username timing difference: {time_diff}s"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])