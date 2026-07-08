import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CACHE_PATH = ROOT / "support" / "output_cache.py"


def load_cache_module():
    spec = importlib.util.spec_from_file_location("output_cache", CACHE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeImage:
    def __init__(self, data):
        self._data = bytes(data)
        self.shape = (1, len(self._data), 1, 1)
        self.dtype = "uint8"

    def tobytes(self):
        return self._data


def make_key(cache, image, **overrides):
    data = {
        "llama_model": {"model": "model.gguf", "mmproj": "mmproj.gguf", "chat_handler": "Gemma4"},
        "preset_prompt": "Normal - Describe",
        "custom_prompt": "describe this image",
        "system_prompt": "",
        "inference_mode": "one by one",
        "max_frames": 24,
        "max_size": 256,
        "seed": 1234,
        "parameters": {"temperature": 0.6, "top_k": 64, "top_p": 0.9},
        "output_think_block": False,
        "images": [image],
    }
    data.update(overrides)
    return cache.make_instruct_cache_key(**data)


class OutputCacheTests(unittest.TestCase):
    def test_same_image_and_parameters_make_same_cache_key(self):
        cache = load_cache_module()
        image = FakeImage(b"abc")

        first = make_key(cache, image)
        second = make_key(cache, image)

        self.assertEqual(first, second)

    def test_image_change_changes_cache_key(self):
        cache = load_cache_module()

        first = make_key(cache, FakeImage(b"abc"))
        second = make_key(cache, FakeImage(b"abd"))

        self.assertNotEqual(first, second)

    def test_generation_parameter_change_changes_cache_key(self):
        cache = load_cache_module()
        image = FakeImage(b"abc")

        first = make_key(cache, image)
        second = make_key(cache, image, parameters={"temperature": 0.7, "top_k": 64, "top_p": 0.9})

        self.assertNotEqual(first, second)

    def test_cached_output_round_trips_without_sharing_list_instance(self):
        cache = load_cache_module()
        store = {}
        output = ("prompt text", ["prompt text"], 42)

        cache.store_instruct_output(store, "node-1", "cache-key", output)
        cached = cache.get_cached_instruct_output(store, "node-1", "cache-key")
        cached[1].append("mutated")
        cached_again = cache.get_cached_instruct_output(store, "node-1", "cache-key")

        self.assertEqual(cached_again, output)

    def test_cache_miss_when_key_differs(self):
        cache = load_cache_module()
        store = {}

        cache.store_instruct_output(store, "node-1", "cache-key", ("prompt text", ["prompt text"], 42))

        self.assertIsNone(cache.get_cached_instruct_output(store, "node-1", "other-key"))


if __name__ == "__main__":
    unittest.main()
