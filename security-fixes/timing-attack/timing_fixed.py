"""
修复代码：密码验证时序攻击修复

使用 constant-time 比较函数和随机延迟来防止时序攻击。
"""
import secrets
import time
import random
import hashlib


def verify_password_secure(user_input: str, stored_password: str) -> bool:
    """
    ✅ 修复代码：使用 constant-time 比较

    修复：
    1. 使用 secrets.compare_digest() 进行常量时间比较
    2. 无论密码是否匹配，都比较所有字符
    3. 添加随机延迟抖动，防止精确测量
    """
    # 安全：使用 Python 标准库的 constant-time 比较函数
    # secrets.compare_digest() 无论输入如何，执行时间都相同
    result = secrets.compare_digest(user_input, stored_password)

    # 添加随机延迟抖动（防止精确测量）
    # 延迟范围：1-5ms，足以模糊攻击者的测量
    delay = random.uniform(0.001, 0.005)
    time.sleep(delay)

    return result


def verify_password_hash_secure(user_input: str, stored_hash: str, salt: str) -> bool:
    """
    ✅ 替代方案：使用哈希后比较

    对用户输入和存储的哈希进行比较，避免直接比较密码
    """
    # 对用户输入进行哈希
    input_hash = hashlib.pbkdf2_hmac(
        'sha256',
        user_input.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    )

    # 使用 constant-time 比较哈希值
    result = secrets.compare_digest(
        input_hash.hex(),
        stored_hash
    )

    # 添加随机延迟
    delay = random.uniform(0.001, 0.005)
    time.sleep(delay)

    return result


def verify_username_exists_secure(username: str, user_db: dict) -> bool:
    """
    ✅ 修复代码：防止用户枚举

    修复：
    1. 无论用户是否存在，都执行相同的操作
    2. 添加固定延迟，使响应时间一致
    """
    start_time = time.time()

    # 检查用户是否存在
    exists = username in user_db

    # 确保无论结果如何，都花费相同的时间
    # 使用固定延迟（而不是随机）
    elapsed = time.time() - start_time
    target_delay = 0.05  # 50ms 固定延迟

    if elapsed < target_delay:
        time.sleep(target_delay - elapsed)

    return exists


class TimingSafeAuth:
    """
    ✅ 完整的时序安全认证类

    综合应用所有修复措施：
    1. Constant-time 比较
    2. 固定延迟
    3. 随机抖动
    """

    def __init__(self, min_delay: float = 0.05, jitter_range: tuple = (0.001, 0.005)):
        self.min_delay = min_delay
        self.jitter_range = jitter_range

    def verify(self, user_input: str, stored_value: str) -> bool:
        """
        时序安全的验证方法
        """
        start = time.time()

        # Constant-time 比较
        result = secrets.compare_digest(user_input, stored_value)

        # 确保至少经过 min_delay 时间
        elapsed = time.time() - start
        if elapsed < self.min_delay:
            time.sleep(self.min_delay - elapsed)

        # 添加随机抖动
        jitter = random.uniform(*self.jitter_range)
        time.sleep(jitter)

        return result