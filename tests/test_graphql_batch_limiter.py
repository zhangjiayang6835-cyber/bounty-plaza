import pytest
from scripts.graphql_batch_limiter import (
    GraphQLComplexityAnalyzer,
    GraphQLDepthLimitExceeded,
    GraphQLCostLimitExceeded,
    GraphQLBatchLimitExceeded,
)


def test_depth_calculation():
    analyzer = GraphQLComplexityAnalyzer(max_depth=4)
    query_ok = """
    query {
        user {
            profile {
                email
            }
        }
    }
    """
    assert analyzer.calculate_depth(query_ok) == 3

    query_deep = """
    query {
        a {
            b {
                c {
                    d {
                        e
                    }
                }
            }
        }
    }
    """
    assert analyzer.calculate_depth(query_deep) == 5
    with pytest.raises(GraphQLDepthLimitExceeded):
        analyzer.calculate_query_cost(query_deep)


def test_query_cost_and_multiplier():
    analyzer = GraphQLComplexityAnalyzer(
        max_query_cost=50,
        default_field_cost=1,
        custom_field_costs={"users": 5, "heavyOperation": 20}
    )
    query = """
    query {
        users(limit: 5) {
            id
            name
        }
    }
    """
    # users: 5 * 5 = 25, id: 1 * 1 = 1, name: 1 * 1 = 1 -> 27
    cost = analyzer.calculate_query_cost(query)
    assert cost == 27


def test_single_query_cost_exceeded():
    analyzer = GraphQLComplexityAnalyzer(max_query_cost=20)
    query = """
    query {
        a
        b
        c
        d
        e
        f
        g
        h
        i
        j
        k
        l
        m
        n
        o
        p
        q
        r
        s
        t
        u
    }
    """
    with pytest.raises(GraphQLCostLimitExceeded):
        analyzer.calculate_query_cost(query)


def test_batch_query_analysis_and_cost_aggregation():
    analyzer = GraphQLComplexityAnalyzer(
        max_batch_size=5,
        max_query_cost=50,
        max_batch_cost=80
    )
    batch = [
        {"query": "{ user { id name } }"},
        {"query": "{ posts { id title } }"},
        {"query": "{ comments { id text } }"},
    ]
    result = analyzer.analyze_batch(batch)
    assert result["valid"] is True
    assert result["query_count"] == 3
    assert result["total_cost"] > 0
    assert result["max_depth"] == 2


def test_batch_size_limit_exceeded():
    analyzer = GraphQLComplexityAnalyzer(max_batch_size=2)
    batch = [
        "{ user { id } }",
        "{ user { name } }",
        "{ user { email } }"
    ]
    with pytest.raises(GraphQLBatchLimitExceeded):
        analyzer.analyze_batch(batch)


def test_batch_aggregate_cost_exceeded():
    analyzer = GraphQLComplexityAnalyzer(
        max_batch_size=10,
        max_query_cost=30,
        max_batch_cost=40
    )
    # 3 queries costing 20 each will total 60, exceeding batch limit 40
    q = "{ a b c d e f g h i j k l m n o p q r s t }"
    batch = [q, q, q]
    with pytest.raises(GraphQLCostLimitExceeded) as excinfo:
        analyzer.analyze_batch(batch)
    assert "exceeds maximum allowed batch cost" in str(excinfo.value)
