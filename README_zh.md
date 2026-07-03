# ComfyUI-llama-cpp_vlm - Gemma4 思考控制个人 Fork

这是 [lihaoyun6/ComfyUI-llama-cpp_vlm](https://github.com/lihaoyun6/ComfyUI-llama-cpp_vlm) 的个人 fork。原仓库本身基于 [kijai/ComfyUI-llama-cpp](https://github.com/kijai/ComfyUI-llama-cpp)。

这个 fork 主要用于在 ComfyUI 中更方便地使用 Gemma4 GGUF 视觉模型做图片反推提示词，尤其是处理模型输出中混入 think/channel 思考内容的问题。

## 本 fork 的改动

- 在 `Llama-cpp Model Loader` 增加 `启用思考`。
  - 当 `chat_handler` 为 `Gemma4` 时，会把该选项传给 `Gemma4ChatHandler(enable_thinking=...)`。
  - 默认值：`false`。
- 在 `Llama-cpp Instruct` 增加 `输出think块`。
  - 默认值：`false`。
  - 关闭时，会清理 `<think>...</think>`、`<|channel>thought ... <channel|>` 等常见思考/通道标记。
- 调整 `Llama-cpp Parameters` 默认采样参数：

```text
temperature: 0.6
top_k: 64
top_p: 0.9
min_p: 0.05
repeat_penalty: 1.1
```

这些默认值来自 HauhauCS Gemma4 未审查模型卡片中的推荐采样参数。

## 测试模型

本 fork 主要按下面这个模型进行测试和参数调整：

[HauhauCS/Gemma4-12B-QAT-Uncensored-HauhauCS-Balanced](https://huggingface.co/HauhauCS/Gemma4-12B-QAT-Uncensored-HauhauCS-Balanced)

模型卡片中列出的主要文件：

```text
Gemma4-12B-QAT-Uncensored-HauhauCS-Balanced-Q4_K_M.gguf
mmproj-Gemma4-12B-QAT-Uncensored-HauhauCS-Balanced-BF16.gguf
```

将 GGUF 模型文件放到：

```text
ComfyUI/models/LLM
```

然后在 `Llama-cpp Model Loader` 中选择主模型和对应的 `mmproj` 文件。

## 图片反推提示词建议设置

日常图片反推提示词建议：

```text
启用思考: false
输出think块: false
temperature: 0.6
top_k: 64
top_p: 0.9
min_p: 0.05
repeat_penalty: 1.1
frequency_penalty: 0.0
present_penalty: 0.0
```

如果只是想观察模型原始 think/channel 输出，可开启 `输出think块`。

如果开启 `启用思考`，生成时间可能明显变长，因为模型可能会先生成更多 reasoning token。

## 安装

将此 fork 克隆到 ComfyUI 的 `custom_nodes`：

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/redpigirl214/ComfyUI-llama-cpp_vlm.git
```

只有在当前 ComfyUI 环境缺少依赖时，才考虑安装 requirements：

```bash
python -m pip install -r ComfyUI-llama-cpp_vlm/requirements.txt
```

已有 ComfyUI 环境建议先检查依赖版本，避免破坏现有环境。

## 致谢

- 原 fork：[lihaoyun6/ComfyUI-llama-cpp_vlm](https://github.com/lihaoyun6/ComfyUI-llama-cpp_vlm)
- 上游项目：[kijai/ComfyUI-llama-cpp](https://github.com/kijai/ComfyUI-llama-cpp)
- [llama-cpp-python](https://github.com/JamePeng/llama-cpp-python)
- [ComfyUI](https://github.com/comfyanonymous/ComfyUI)
