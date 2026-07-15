"""
漏洞代码：密码验证时序攻击示例

此代码存在时序攻击漏洞，攻击者可通过响应时间推断密码。
"""
import time


def verify_password_vulnerable(user_input: str, stored_password: str) -> bool:
    """
    ❌ 漏洞代码：使用逐字符比较

    问题：
    1. === 操作符在第一个不匹配字符就返回
    2. 不同密码长度会导致不同的响应时间
    3. 攻击者可以通过测量响应时间逐字符推断密码
    """
    # 危险：逐字符比较，早退（early exit）
    if len(user_input) != len(stored_password):
        return False

    for i in range(len(stored_password)):
        if user_input[i] != stored_password[i]:
            # 在第一个不匹配的字符就返回
            # 攻击者可以通过响应时间推断到第几位匹配
            return False

    return True


def verify_username_exists_vulnerable(username: str, user_db: dict) -> bool:
    """
    ❌ 漏洞代码：用户枚举

    问题：
    1. 用户存在/不存在时响应时间不同
    2. 攻击者可以枚举有效用户名
    """
    # 用户存在时返回快，不存在时返回慢
    return username in user_db