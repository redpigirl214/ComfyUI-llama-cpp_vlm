import importlib.util
import math
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NODES_PATH = ROOT / "nodes.py"


class FakeLLM:
    def __init__(self):
        self.calls = 0

    def create_chat_completion(self, **kwargs):
        self.calls += 1
        return {"choices": [{"message": {"content": f"prompt-{self.calls}"}}]}


def install_fake_modules(package_name):
    plugin_package = types.ModuleType(package_name)
    plugin_package.__path__ = [str(ROOT)]
    support_package = types.ModuleType(f"{package_name}.support")
    support_package.__path__ = [str(ROOT / "support")]

    cqdm_module = types.ModuleType(f"{package_name}.support.cqdm")
    cqdm_module.cqdm = lambda iterable=None, **kwargs: iterable

    gguf_layers_module = types.ModuleType(f"{package_name}.support.gguf_layers")
    gguf_layers_module.get_layer_count = lambda path: 1

    prompt_module = types.ModuleType(f"{package_name}.support.prompt_enhancer_preset")

    torch_module = types.ModuleType("torch")
    torch_module.Tensor = object
    torch_module.from_numpy = lambda value: value

    numpy_module = types.ModuleType("numpy")
    numpy_module.uint8 = "uint8"
    numpy_module.float32 = "float32"
    numpy_module.linspace = lambda start, stop, count, dtype=None: list(range(count))
    numpy_module.clip = lambda value, min_value, max_value: value
    numpy_module.array = lambda value, dtype=None: value
    numpy_module.zeros = lambda shape, dtype=None: []

    image_module = types.SimpleNamespace(fromarray=lambda value: value, Resampling=types.SimpleNamespace(LANCZOS=1))
    pil_module = types.ModuleType("PIL")
    pil_module.Image = image_module
    pil_module.ImageDraw = types.SimpleNamespace(Draw=lambda image: None)

    scipy_module = types.ModuleType("scipy")
    scipy_ndimage_module = types.ModuleType("scipy.ndimage")
    scipy_ndimage_module.gaussian_filter = lambda value, sigma: value

    folder_paths_module = types.ModuleType("folder_paths")
    folder_paths_module.models_dir = "."
    folder_paths_module.folder_names_and_paths = {}
    folder_paths_module.get_filename_list = lambda name: []

    comfy_module = types.ModuleType("comfy")
    comfy_mm_module = types.ModuleType("comfy.model_management")
    comfy_mm_module.unload_all_models = lambda *args, **kwargs: None
    comfy_mm_module.soft_empty_cache = lambda: None
    comfy_mm_module.processing_interrupted = lambda: False
    comfy_utils_module = types.ModuleType("comfy.utils")
    comfy_utils_module.ProgressBar = lambda total: types.SimpleNamespace(update=lambda value: None)
    comfy_module.model_management = comfy_mm_module
    comfy_module.utils = comfy_utils_module

    llama_module = types.ModuleType("llama_cpp")
    llama_module.Llama = lambda *args, **kwargs: FakeLLM()
    llama_chat_module = types.ModuleType("llama_cpp.llama_chat_format")
    for name in (
        "Llava15ChatHandler",
        "Llava16ChatHandler",
        "MoondreamChatHandler",
        "NanoLlavaChatHandler",
        "Llama3VisionAlphaChatHandler",
        "MiniCPMv26ChatHandler",
    ):
        setattr(llama_chat_module, name, type(name, (), {}))

    sys.modules.update(
        {
            package_name: plugin_package,
            f"{package_name}.support": support_package,
            f"{package_name}.support.cqdm": cqdm_module,
            f"{package_name}.support.gguf_layers": gguf_layers_module,
            f"{package_name}.support.prompt_enhancer_preset": prompt_module,
            "torch": torch_module,
            "numpy": numpy_module,
            "PIL": pil_module,
            "scipy": scipy_module,
            "scipy.ndimage": scipy_ndimage_module,
            "folder_paths": folder_paths_module,
            "comfy": comfy_module,
            "comfy.model_management": comfy_mm_module,
            "comfy.utils": comfy_utils_module,
            "llama_cpp": llama_module,
            "llama_cpp.llama_chat_format": llama_chat_module,
        }
    )


def load_nodes_module():
    package_name = "llama_cpp_vlm_behavior_test"
    install_fake_modules(package_name)
    spec = importlib.util.spec_from_file_location(f"{package_name}.nodes", NODES_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[f"{package_name}.nodes"] = module
    spec.loader.exec_module(module)
    return module


class InstructCacheBehaviorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nodes = load_nodes_module()

    def setUp(self):
        self.nodes.LLAMA_CPP_STORAGE.llm = FakeLLM()
        self.nodes.LLAMA_CPP_STORAGE.chat_handler = None
        self.nodes.LLAMA_CPP_STORAGE.current_config = {"chat_handler": "None"}
        self.nodes.LLAMA_CPP_STORAGE.messages.clear()
        self.nodes.LLAMA_CPP_STORAGE.sys_prompts.clear()
        self.nodes.LLAMA_CPP_STORAGE.output_cache.clear()
        self.node = self.nodes.llama_cpp_instruct_adv()

    def call_process(self, **overrides):
        data = {
            "llama_model": {"model": "model.gguf", "mmproj": "None", "chat_handler": "None"},
            "preset_prompt": "Normal - Describe",
            "custom_prompt": "describe this image",
            "system_prompt": "",
            "inference_mode": "one by one",
            "max_frames": 24,
            "max_size": 256,
            "seed": 1234,
            "force_offload": False,
            "save_states": False,
            "输出think块": False,
            "unique_id": "node.42",
            "parameters": {"temperature": 0.6, "top_k": 64},
            "images": None,
            "queue_handler": None,
        }
        data.update(overrides)
        return self.node.process(**data)

    def test_identical_stateless_call_reuses_cached_output(self):
        first = self.call_process()
        second = self.call_process()

        self.assertEqual(first, ("prompt-1", ["prompt-1"], "42"))
        self.assertEqual(second, first)
        self.assertEqual(self.nodes.LLAMA_CPP_STORAGE.llm.calls, 1)

    def test_seed_change_recomputes_output(self):
        self.call_process()
        second = self.call_process(seed=5678)

        self.assertEqual(second, ("prompt-2", ["prompt-2"], "42"))
        self.assertEqual(self.nodes.LLAMA_CPP_STORAGE.llm.calls, 2)

    def test_generation_parameter_change_recomputes_output(self):
        self.call_process()
        second = self.call_process(parameters={"temperature": 0.7, "top_k": 64})

        self.assertEqual(second, ("prompt-2", ["prompt-2"], "42"))
        self.assertEqual(self.nodes.LLAMA_CPP_STORAGE.llm.calls, 2)

    def test_prompt_change_recomputes_output(self):
        self.call_process()
        second = self.call_process(custom_prompt="describe this image differently")

        self.assertEqual(second, ("prompt-2", ["prompt-2"], "42"))
        self.assertEqual(self.nodes.LLAMA_CPP_STORAGE.llm.calls, 2)

    def test_model_config_change_recomputes_output(self):
        self.call_process()
        second = self.call_process(
            llama_model={"model": "other-model.gguf", "mmproj": "None", "chat_handler": "None"}
        )

        self.assertEqual(second, ("prompt-2", ["prompt-2"], "42"))
        self.assertEqual(self.nodes.LLAMA_CPP_STORAGE.llm.calls, 2)

    def test_output_think_block_change_recomputes_output(self):
        self.call_process()
        second = self.call_process(输出think块=True)

        self.assertEqual(second, ("prompt-2", ["prompt-2"], "42"))
        self.assertEqual(self.nodes.LLAMA_CPP_STORAGE.llm.calls, 2)

    def test_save_states_true_bypasses_output_cache(self):
        first = self.call_process(save_states=True)
        second = self.call_process(save_states=True)

        self.assertEqual(first, ("prompt-1", ["prompt-1"], "42"))
        self.assertEqual(second, ("prompt-2", ["prompt-2"], "42"))
        self.assertEqual(self.nodes.LLAMA_CPP_STORAGE.llm.calls, 2)


class ModelLoaderChangeFingerprintTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nodes = load_nodes_module()

    def setUp(self):
        self.nodes.LLAMA_CPP_STORAGE.llm = None

    def fingerprint(self, **overrides):
        data = {
            "model": "model.gguf",
            "mmproj": "mmproj.gguf",
            "chat_handler": "Gemma4",
            "n_ctx": 8192,
            "vram_limit": -1,
            "image_min_tokens": 0,
            "image_max_tokens": 0,
            "启用思考": False,
        }
        data.update(overrides)
        return self.nodes.llama_cpp_model_loader.IS_CHANGED(**data)

    def test_model_loader_fingerprint_is_stable_without_loaded_model(self):
        first = self.fingerprint()
        second = self.fingerprint()

        self.assertEqual(first, second)
        self.assertNotIsInstance(first, float)

    def test_model_loader_fingerprint_changes_when_loader_inputs_change(self):
        base = self.fingerprint()

        self.assertNotEqual(base, self.fingerprint(model="other-model.gguf"))
        self.assertNotEqual(base, self.fingerprint(n_ctx=4096))
        self.assertNotEqual(base, self.fingerprint(启用思考=True))


class ComfyUICacheControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nodes = load_nodes_module()

    def test_instruct_node_forces_process_entry_for_internal_cache(self):
        marker = self.nodes.llama_cpp_instruct_adv.IS_CHANGED()

        self.assertTrue(math.isnan(marker))

    def test_parameters_fingerprint_changes_when_top_k_changes(self):
        base = self.nodes.llama_cpp_parameters.IS_CHANGED(
            max_tokens=1024,
            top_k=64,
            top_p=0.9,
            min_p=0.05,
            typical_p=1.0,
            temperature=0.6,
            repeat_penalty=1.1,
            frequency_penalty=0.0,
            present_penalty=0.0,
            mirostat_mode=0,
            mirostat_eta=0.1,
            mirostat_tau=5.0,
            state_uid=-1,
        )
        changed = self.nodes.llama_cpp_parameters.IS_CHANGED(
            max_tokens=1024,
            top_k=65,
            top_p=0.9,
            min_p=0.05,
            typical_p=1.0,
            temperature=0.6,
            repeat_penalty=1.1,
            frequency_penalty=0.0,
            present_penalty=0.0,
            mirostat_mode=0,
            mirostat_eta=0.1,
            mirostat_tau=5.0,
            state_uid=-1,
        )

        self.assertNotEqual(base, changed)


if __name__ == "__main__":
    unittest.main()
