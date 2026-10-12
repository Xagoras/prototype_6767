"""关系树校验与表达式生成测试（指南 5.2/5.3）。"""
import pytest
from fastapi import HTTPException

from app.services.expr import build_expr, relation_roots, validate_relations


def test_valid_nested():
    rels = [
        {"rel_type": "J", "args": [{"kind": "P", "id": 1}, {"kind": "P", "id": 2}]},
        {"rel_type": "M", "args": [{"kind": "R", "id": 0}, {"kind": "P", "id": 4}]},
        {"rel_type": "S", "args": [{"kind": "R", "id": 1}, {"kind": "P", "id": 5}]},
    ]
    validate_relations(rels, {1, 2, 4, 5})
    assert relation_roots(rels) == [2]
    assert build_expr(2, rels, {}) == "S(M(J(P1, P2), P4), P5)"


def test_arity_s_requires_2():
    with pytest.raises(HTTPException):
        validate_relations(
            [{"rel_type": "S", "args": [{"kind": "P", "id": 1}]}], {1})


def test_j_requires_at_least_2():
    with pytest.raises(HTTPException):
        validate_relations(
            [{"rel_type": "J", "args": [{"kind": "P", "id": 1}]}], {1})


def test_unknown_proposition():
    with pytest.raises(HTTPException):
        validate_relations(
            [{"rel_type": "S", "args": [{"kind": "P", "id": 99},
                                        {"kind": "P", "id": 1}]}], {1})


def test_cycle_detected():
    rels = [
        {"rel_type": "S", "args": [{"kind": "R", "id": 1}, {"kind": "P", "id": 1}]},
        {"rel_type": "S", "args": [{"kind": "R", "id": 0}, {"kind": "P", "id": 2}]},
    ]
    with pytest.raises(HTTPException):
        validate_relations(rels, {1, 2})


def test_self_reference():
    rels = [
        {"rel_type": "S", "args": [{"kind": "R", "id": 0}, {"kind": "P", "id": 1}]},
    ]
    with pytest.raises(HTTPException):
        validate_relations(rels, {1})


def test_multi_root():
    rels = [
        {"rel_type": "S", "args": [{"kind": "P", "id": 1}, {"kind": "P", "id": 2}]},
        {"rel_type": "A", "args": [{"kind": "P", "id": 3}, {"kind": "P", "id": 2}]},
    ]
    validate_relations(rels, {1, 2, 3})
    assert sorted(relation_roots(rels)) == [0, 1]
