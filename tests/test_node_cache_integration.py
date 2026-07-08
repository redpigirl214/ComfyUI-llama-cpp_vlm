import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NODES_PATH = ROOT / "nodes.py"


class NodeCacheIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nodes_source = NODES_PATH.read_text(encoding="utf-8")

    def test_instruct_node_uses_output_cache_helpers(self):
        self.assertIn("from .support.output_cache import", self.nodes_source)
        self.assertIn("make_instruct_cache_key", self.nodes_source)
        self.assertIn("get_cached_instruct_output", self.nodes_source)
        self.assertIn("store_instruct_output", self.nodes_source)

    def test_cache_lookup_happens_before_model_load(self):
        process_start = self.nodes_source.index("    def process(self, llama_model")
        process_source = self.nodes_source[process_start:]

        cache_lookup = process_source.index("get_cached_instruct_output")
        model_load = process_source.index("LLAMA_CPP_STORAGE.load_model(llama_model)")

        self.assertLess(cache_lookup, model_load)

    def test_storage_tracks_output_cache(self):
        self.assertIn("output_cache = {}", self.nodes_source)


if __name__ == "__main__":
    unittest.main()
