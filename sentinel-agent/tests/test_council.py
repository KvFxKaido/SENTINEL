"""
Tests for the council/advisor system.

Ensures advisors provide diverse perspectives, not identical answers.
"""

import pytest
from pathlib import Path

# Add src to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent import SentinelAgent, AdvisorResponse, PromptLoader
from src.state import CampaignManager, MemoryCampaignStore
from src.llm import MockLLMClient


# -----------------------------------------------------------------------------
# String Similarity Utilities
# -----------------------------------------------------------------------------

def normalize_text(text: str) -> str:
    """Normalize text for comparison (lowercase, collapse whitespace)."""
    return " ".join(text.lower().split())


def word_overlap_ratio(text1: str, text2: str) -> float:
    """
    Calculate word-level overlap ratio between two texts.

    Returns a value between 0.0 (no overlap) and 1.0 (identical).
    Uses Jaccard similarity on word sets.
    """
    words1 = set(normalize_text(text1).split())
    words2 = set(normalize_text(text2).split())

    if not words1 or not words2:
        return 0.0

    intersection = words1 & words2
    union = words1 | words2

    return len(intersection) / len(union)


def ngram_overlap_ratio(text1: str, text2: str, n: int = 3) -> float:
    """
    Calculate character n-gram overlap ratio between two texts.

    Returns a value between 0.0 (no overlap) and 1.0 (identical).
    More sensitive to phrasing than word overlap.
    """
    def get_ngrams(text: str, n: int) -> set[str]:
        text = normalize_text(text)
        if len(text) < n:
            return set()  # Empty set for short/empty text
        return {text[i:i+n] for i in range(len(text) - n + 1)}

    ngrams1 = get_ngrams(text1, n)
    ngrams2 = get_ngrams(text2, n)

    if not ngrams1 or not ngrams2:
        return 0.0

    intersection = ngrams1 & ngrams2
    union = ngrams1 | ngrams2

    return len(intersection) / len(union)


def responses_are_diverse(responses: list[str], threshold: float = 0.6) -> bool:
    """
    Check if a list of responses are sufficiently diverse.

    Returns True if all pairwise comparisons have overlap < threshold.
    Default threshold is 0.6 (60% overlap).
    """
    for i in range(len(responses)):
        for j in range(i + 1, len(responses)):
            # Use word overlap as primary metric
            word_overlap = word_overlap_ratio(responses[i], responses[j])
            if word_overlap >= threshold:
                return False
    return True


# -----------------------------------------------------------------------------
# Test Similarity Functions
# -----------------------------------------------------------------------------

class TestSimilarityFunctions:
    """Tests for string similarity utilities."""

    def test_identical_texts_have_full_overlap(self):
        text = "The quick brown fox jumps over the lazy dog."
        assert word_overlap_ratio(text, text) == 1.0
        assert ngram_overlap_ratio(text, text) == 1.0

    def test_completely_different_texts_have_low_overlap(self):
        text1 = "The network observes all traffic patterns."
        text2 = "Survival depends on staying hidden underground."

        word_overlap = word_overlap_ratio(text1, text2)
        assert word_overlap < 0.2  # Very different

    def test_similar_texts_have_high_overlap(self):
        text1 = "The operative should proceed with caution."
        text2 = "The operative must proceed with extreme caution."

        word_overlap = word_overlap_ratio(text1, text2)
        assert word_overlap > 0.5  # Similar

    def test_empty_texts_have_zero_overlap(self):
        assert word_overlap_ratio("", "") == 0.0
        assert word_overlap_ratio("hello", "") == 0.0
        assert ngram_overlap_ratio("", "") == 0.0

    def test_ngram_catches_phrasing_similarity(self):
        # Same words, different order
        text1 = "trust no one in this world"
        text2 = "in this world trust no one"

        # Word overlap is high (same words)
        word_overlap = word_overlap_ratio(text1, text2)
        assert word_overlap > 0.8

        # N-gram overlap is lower (different phrasing)
        ngram_overlap = ngram_overlap_ratio(text1, text2)
        assert ngram_overlap < word_overlap


class TestResponseDiversity:
    """Tests for response diversity checking."""

    def test_identical_responses_not_diverse(self):
        responses = [
            "Proceed with the mission.",
            "Proceed with the mission.",
            "Proceed with the mission.",
        ]
        assert not responses_are_diverse(responses)

    def test_unique_responses_are_diverse(self):
        responses = [
            "Optimal approach: infiltrate via the north corridor.",
            "Trust no one. The north corridor is a trap.",
            "Historical records show three previous attempts via north.",
        ]
        assert responses_are_diverse(responses)

    def test_threshold_controls_sensitivity(self):
        # Very similar responses (just minor word changes)
        responses = [
            "The mission should proceed with caution and care.",
            "The mission should proceed with caution and patience.",
        ]

        # At 0.9 threshold, these should pass (overlap is high but < 90%)
        assert responses_are_diverse(responses, threshold=0.9)

        # At 0.7 threshold, these should fail (too similar)
        assert not responses_are_diverse(responses, threshold=0.7)


# -----------------------------------------------------------------------------
# Test Advisor Prompt Diversity
# -----------------------------------------------------------------------------

class TestAdvisorPromptDiversity:
    """Ensure advisor prompts are sufficiently different."""

    @pytest.fixture
    def prompt_loader(self):
        """Load prompts from the actual prompts directory."""
        prompts_dir = Path(__file__).parent.parent / "prompts"
        return PromptLoader(prompts_dir)

    def test_advisor_prompts_exist(self, prompt_loader):
        """All three advisor prompts should exist."""
        nexus = prompt_loader.load_advisor("nexus")
        ember = prompt_loader.load_advisor("ember")
        witness = prompt_loader.load_advisor("witness")

        assert nexus, "Nexus advisor prompt not found"
        assert ember, "Ember advisor prompt not found"
        assert witness, "Witness advisor prompt not found"

    def test_advisor_prompts_are_diverse(self, prompt_loader):
        """Advisor prompts should have less than 60% word overlap."""
        nexus = prompt_loader.load_advisor("nexus")
        ember = prompt_loader.load_advisor("ember")
        witness = prompt_loader.load_advisor("witness")

        # Check all pairwise comparisons
        nexus_ember = word_overlap_ratio(nexus, ember)
        nexus_witness = word_overlap_ratio(nexus, witness)
        ember_witness = word_overlap_ratio(ember, witness)

        # All should be below 60% overlap
        assert nexus_ember < 0.6, f"Nexus-Ember overlap too high: {nexus_ember:.1%}"
        assert nexus_witness < 0.6, f"Nexus-Witness overlap too high: {nexus_witness:.1%}"
        assert ember_witness < 0.6, f"Ember-Witness overlap too high: {ember_witness:.1%}"

    def test_advisor_prompts_have_unique_keywords(self, prompt_loader):
        """Each advisor prompt should have unique identifying keywords."""
        nexus = prompt_loader.load_advisor("nexus").lower()
        ember = prompt_loader.load_advisor("ember").lower()
        witness = prompt_loader.load_advisor("witness").lower()

        # Nexus keywords
        assert "optimization" in nexus or "efficiency" in nexus
        assert "data" in nexus or "probability" in nexus

        # Ember keywords
        assert "survival" in ember or "autonomy" in ember
        assert "trust" in ember or "betray" in ember

        # Witness keywords
        assert "truth" in witness or "archive" in witness
        assert "history" in witness or "precedent" in witness


# -----------------------------------------------------------------------------
# Test Council System Integration
# -----------------------------------------------------------------------------

class TestCouncilIntegration:
    """Integration tests for the council/advisor system."""

    @pytest.fixture
    def agent_with_mock_responses(self):
        """Create agent with mock LLM returning different advisor responses."""
        store = MemoryCampaignStore()
        manager = CampaignManager(store)

        # Create diverse mock responses for each advisor call
        mock_responses = [
            # Nexus response (first call)
            "Analysis indicates 73% success probability. "
            "Resource allocation suggests north corridor approach. "
            "Recommend proceeding with tactical insertion.",

            # Ember response (second call)
            "I've seen this setup before. It's a trap. "
            "The north corridor is too obvious. "
            "Find another way or don't go at all.",

            # Witness response (third call)
            "Historical records show three similar operations. "
            "Two succeeded via misdirection, one failed at extraction. "
            "Recording this query for the archive.",
        ]

        mock_client = MockLLMClient(responses=mock_responses)

        prompts_dir = Path(__file__).parent.parent / "prompts"
        agent = SentinelAgent(
            manager,
            prompts_dir=prompts_dir,
            client=mock_client,
        )

        return agent, mock_client

    def test_consult_returns_all_advisors(self, agent_with_mock_responses):
        """Consult should return responses from all advisors."""
        agent, mock = agent_with_mock_responses

        results = agent.consult("Should I proceed with the mission?")

        assert len(results) == 3
        advisor_names = {r.advisor for r in results}
        assert advisor_names == {"nexus", "ember", "witness"}

    def test_consult_responses_are_diverse(self, agent_with_mock_responses):
        """Responses from different advisors should be diverse."""
        agent, mock = agent_with_mock_responses

        results = agent.consult("Should I proceed with the mission?")

        response_texts = [r.response for r in results if r.response]
        assert len(response_texts) == 3

        # Check diversity
        assert responses_are_diverse(response_texts, threshold=0.6)

    def test_consult_uses_advisor_prompts(self, agent_with_mock_responses):
        """Each advisor call should use the appropriate advisor prompt."""
        agent, mock = agent_with_mock_responses

        results = agent.consult("What should I do?")

        # Check that calls were made with different system prompts
        assert len(mock.calls) == 3

        system_prompts = [call["system"] for call in mock.calls]

        # All system prompts should be different (different advisor personalities)
        assert len(set(system_prompts)) == 3, "All advisor prompts should be unique"

    def test_detects_hallucinated_identical_responses(self):
        """Should be able to detect when advisors give identical responses."""
        # Simulate hallucination: all advisors return the same thing
        identical_responses = [
            AdvisorResponse("nexus", "NEXUS", "Proceed with caution."),
            AdvisorResponse("ember", "EMBER", "Proceed with caution."),
            AdvisorResponse("witness", "WITNESS", "Proceed with caution."),
        ]

        response_texts = [r.response for r in identical_responses]

        # This should fail diversity check
        assert not responses_are_diverse(response_texts, threshold=0.6)
