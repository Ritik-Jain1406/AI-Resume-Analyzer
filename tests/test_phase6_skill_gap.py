"""
tests/test_phase6_skill_gap.py
---------------------------------
Unit tests for the Phase 6 skill gap analysis pipeline.
"""

from matching.learning_resources import format_time_estimate, get_resource
from matching.skill_gap import analyze_skill_gap


JD_TEXT = """
We are looking for a Backend Engineer with strong Python and Django
experience. Kubernetes experience is required, as is Kubernetes
familiarity with container orchestration. Bonus points for Communication
skills and a collaborative mindset.
"""


def test_get_resource_known_skill_returns_curated_url():
    name, url = get_resource("Python", "Programming")
    assert url.startswith("https://")
    assert "python" in url.lower()


def test_get_resource_unknown_skill_falls_back_to_search():
    name, url = get_resource("SomeMadeUpSkillXYZ", "Other")
    assert "coursera.org/search" in url


def test_format_time_estimate_soft_skill_is_ongoing():
    assert format_time_estimate("Soft Skills") == "Ongoing practice"


def test_format_time_estimate_programming_has_weeks():
    estimate = format_time_estimate("Programming")
    assert "week" in estimate


def test_analyze_skill_gap_empty_input():
    plan = analyze_skill_gap([], JD_TEXT)
    assert plan.total_missing == 0
    assert plan.gap_items == []
    assert plan.roadmap  # still has a "no gaps" message


def test_analyze_skill_gap_prioritizes_core_and_mentioned_skills():
    missing = ["Python", "Kubernetes", "Communication"]
    plan = analyze_skill_gap(missing, JD_TEXT)

    assert plan.total_missing == 3
    by_skill = {item.skill: item for item in plan.gap_items}

    # Kubernetes: mentioned twice, early in the JD -> should be High priority
    assert by_skill["Kubernetes"].priority == "High Priority"
    assert by_skill["Kubernetes"].mention_count == 2

    # Communication: Soft Skills category, mentioned once, later in JD -> lower priority
    assert by_skill["Communication"].priority in ("Medium Priority", "Low Priority")

    # counts should be internally consistent
    total_by_tier = plan.high_priority_count + plan.medium_priority_count + plan.low_priority_count
    assert total_by_tier == plan.total_missing


def test_analyze_skill_gap_items_sorted_by_priority():
    missing = ["Python", "Kubernetes", "Communication"]
    plan = analyze_skill_gap(missing, JD_TEXT)
    priorities = [item.priority for item in plan.gap_items]
    order = {"High Priority": 0, "Medium Priority": 1, "Low Priority": 2}
    assert priorities == sorted(priorities, key=lambda p: order[p])


def test_analyze_skill_gap_roadmap_groups_by_phase():
    missing = ["Python", "Kubernetes", "Communication"]
    plan = analyze_skill_gap(missing, JD_TEXT)
    assert any("High Priority" in step for step in plan.roadmap)


def test_analyze_skill_gap_every_item_has_resource_and_time():
    missing = ["Python", "Kubernetes", "Communication"]
    plan = analyze_skill_gap(missing, JD_TEXT)
    for item in plan.gap_items:
        assert item.resource_url.startswith("https://")
        assert item.estimated_time
