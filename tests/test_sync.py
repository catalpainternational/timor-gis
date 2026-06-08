"""Unit tests for the provider-sync building blocks (no DB required)."""

from timor_locations.sync.codes import CodeAllocator
from timor_locations.sync.matching import score_pair
from timor_locations.sync.normalize import normalize, phonetic_key


class TestNormalize:
    def test_accents_punctuation_case(self):
        assert normalize("Açumanu") == normalize("Acumanu")
        assert normalize("Caibada Macasa'e") == "caibadamacasae"

    def test_trailing_roman_to_digit(self):
        assert normalize("Lore II") == normalize("Lore 2")
        assert normalize("Iliomar I") == normalize("Iliomar 1")

    def test_phonetic_folds_orthographic_classes(self):
        # c/k, ss/s, u/o, f/w drift all collapse
        assert phonetic_key("Aissirimou") == phonetic_key("Aisirimou")
        assert phonetic_key("Catrai Caraic") == phonetic_key("Catrai Karaik")
        assert phonetic_key("Fatu") == phonetic_key("Watu")


class TestScorePair:
    def test_respellings_score_high(self):
        assert score_pair("Daudere", "Daudare") >= 0.85
        assert score_pair("Vemasse", "Vemase") >= 0.85

    def test_distinct_names_score_low(self):
        assert score_pair("Bebonuk", "Bobonaro") < 0.7


class TestCodeAllocator:
    def test_mints_lowest_free_in_parent_block(self):
        existing = {30100 + i for i in range(1, 12)}  # 30101..30111 taken
        alloc = CodeAllocator(existing)
        assert alloc.mint_suco(301) == 30112  # lowest free under post 301
        assert alloc.mint_suco(301) == 30113  # never reuses

    def test_mint_post_in_municipality_block(self):
        alloc = CodeAllocator({301, 302, 303, 304, 305, 306})  # Baucau posts
        assert alloc.mint_post(3) == 307

    def test_reserve_blocks_reuse(self):
        alloc = CodeAllocator(set())
        alloc.reserve(30113)
        assert alloc.mint_suco(301) == 30101
        alloc.reserve(30101)
        # next mint skips reserved ones
        assert alloc.mint_suco(301) == 30102
