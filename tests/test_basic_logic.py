import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import detect_persona, calculate_budget_score


def test_eco_purist_persona():
    persona, weights = detect_persona("strict eco")
    assert persona == "🌱 Eco Purist"
    assert weights["carbon"] == 0.45

def test_budget_first_persona():
    persona, weights = detect_persona("budget first")
    assert persona == "💰 Resource Optimiser"
    assert weights["budget"] == 0.45

def test_balanced_persona():
    persona, weights = detect_persona("balanced")
    assert persona == "⚖ Balanced Explorer"
    assert weights["carbon"] == 0.35

def test_comfort_persona():
    persona, weights = detect_persona("comfort first")
    assert persona == "✨ Comfort Seeker"
    assert weights["community"] == 0.35

def test_budget_score_affordable():
    assert calculate_budget_score(100, 1000) == 95

def test_budget_score_medium():
    assert calculate_budget_score(120, 800) == 85

def test_budget_score_within_budget():
    assert calculate_budget_score(180, 1000) == 70

def test_budget_score_over_budget():
    assert calculate_budget_score(500, 1000) == 40