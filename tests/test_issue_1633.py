#!/usr/bin/env python3
"""test_issue_1633.py — 回归测试: hunt_bounties.py 边界输入防御性处理

复现 Issue #1633 报告的 "Unhandled boundary failure / logic exception":
- extract_amounts(None) / 非字符串输入崩溃
- get_existing_sources() 遇到 body 为 null 的 Issue 崩溃
- search_github() / get_existing_sources() 网络或 JSON 异常未处理
- is_real_money() 非 dict 输入崩溃
- main() 遇到缺失 html_url 的条目 KeyError
"""

import json
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import hunt_bounties as hb


class TestExtractAmountsBoundaries(unittest.TestCase):
    """extract_amounts 必须对 None / 非字符串 / 空输入安全返回 []"""

    def test_none_input(self):
        self.assertEqual(hb.extract_amounts(None), [])

    def test_empty_string(self):
        self.assertEqual(hb.extract_amounts(""), [])

    def test_non_string_inputs(self):
        for bad in (123, 12.5, ["$100"], {"a": 1}, b"$100"):
            self.assertEqual(hb.extract_amounts(bad), [])

    def test_normal_extraction_still_works(self):
        self.assertIn(100, hb.extract_amounts("Reward: $100"))
        self.assertIn(50, hb.extract_amounts("50 USDT"))
        self.assertIn(1000, hb.extract_amounts("bounty of $1,000"))


class TestIsRealMoneyBoundaries(unittest.TestCase):
    """is_real_money 必须对非 dict / 缺字段输入安全返回 False"""

    def test_non_dict_input(self):
        for bad in (None, "text", 42, [], True):
            self.assertFalse(hb.is_real_money(bad))

    def test_missing_title_and_body(self):
        self.assertFalse(hb.is_real_money({}))

    def test_null_body(self):
        self.assertFalse(hb.is_real_money({"title": "task", "body": None}))

    def test_valid_real_money_still_accepted(self):
        item = {"title": "Fix bug", "body": "Reward $100 USD"}
        self.assertTrue(hb.is_real_money(item))


class TestNetworkBoundaries(unittest.TestCase):
    """网络/JSON 异常必须被捕获并安全降级, 不得抛出未处理异常"""

    def _resp(self, payload):
        m = mock.Mock()
        m.read.return_value = json.dumps(payload).encode()
        m.__enter__ = lambda s: s
        m.__exit__ = mock.Mock(return_value=False)
        return m

    def test_search_github_network_error(self):
        import urllib.error
        with mock.patch("urllib.request.urlopen",
                        side_effect=urllib.error.URLError("boom")):
            self.assertEqual(hb.search_github(), [])

    def test_search_github_malformed_payload(self):
        with mock.patch("urllib.request.urlopen",
                        return_value=self._resp({"unexpected": True})):
            self.assertEqual(hb.search_github(), [])
        with mock.patch("urllib.request.urlopen",
                        return_value=self._resp(["not", "a", "dict"])):
            self.assertEqual(hb.search_github(), [])

    def test_get_existing_sources_null_body(self):
        # body 为 JSON null 时 .get("body", "") 返回 None, 修复前 re.search 抛 TypeError
        payload = [{"body": None}, {"body": "原始链接: https://x.com/a"}]
        with mock.patch("urllib.request.urlopen", return_value=self._resp(payload)):
            sources = hb.get_existing_sources()
        self.assertIn("https://x.com/a", sources)

    def test_get_existing_sources_network_error(self):
        import urllib.error
        with mock.patch("urllib.request.urlopen",
                        side_effect=urllib.error.URLError("boom")):
            self.assertEqual(hb.get_existing_sources(), set())

    def test_get_existing_sources_malformed_payload(self):
        with mock.patch("urllib.request.urlopen",
                        return_value=self._resp({"message": "Not Found"})):
            self.assertEqual(hb.get_existing_sources(), set())


class TestMainBoundaries(unittest.TestCase):
    """main() 遇到缺失 html_url 的条目不得 KeyError 崩溃"""

    def test_main_skips_items_without_html_url(self):
        items = [
            {"title": "no url here", "body": "$100 reward"},  # 缺 html_url
            {"title": "ok", "body": "$100 reward",
             "html_url": "https://github.com/other/repo/issues/1"},
        ]
        with mock.patch.object(hb, "GH_TOKEN", "tok"), \
             mock.patch.object(hb, "search_github", return_value=items), \
             mock.patch.object(hb, "get_existing_sources", return_value=set()), \
             mock.patch.object(hb, "create_issue", return_value=1) as ci:
            rc = hb.main()
        self.assertEqual(rc, 0)
        self.assertEqual(ci.call_count, 1)  # 只创建合法条目, 不崩溃


if __name__ == "__main__":
    unittest.main()
