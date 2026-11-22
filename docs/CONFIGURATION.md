# 配置说明

配置文件在：

```text
%APPDATA%\PromptWorkbench\config.json
```

首次启动会打开环境设置；也可以从左侧“环境设置”再次打开。

## LLM

`llm_type` 支持：

- `ollama`：Ollama 原生 `/api/chat`
- `openai`：OpenAI 兼容的 `/v1/chat/completions`

OpenAI 兼容方式可以接：

- LM Studio
- vLLM
- llama.cpp server
- OpenAI
- OpenRouter
- DeepSeek
- 其他兼容 `/v1/models` 和 `/v1/chat/completions` 的服务

配置字段：

```json
{
  "llm_type": "ollama",
  "llm_base_url": "http://127.0.0.1:11434",
  "llm_api_key": "",
  "llm_model": "huihui_ai/qwen3.5-abliterated:9b",
  "llm_timeout": 300
}
```

云端示例：

```json
{
  "llm_type": "openai",
  "llm_base_url": "https://openrouter.ai/api/v1",
  "llm_api_key": "你的 API Key",
  "llm_model": "供应商的模型 ID",
  "llm_timeout": 300
}
```

## Strata 等特殊本地网关

如果服务暴露 OpenAI 兼容接口，不需要新增“Strata 类型”，直接用 `openai`：

```json
{
  "llm_type": "openai",
  "llm_base_url": "http://127.0.0.1:8081/v1",
  "llm_api_key": "",
  "llm_model": "从 /v1/models 查到的模型 ID",
  "llm_timeout": 300
}
```

`http://127.0.0.1:8081/v1` 是 DSH 常用的 thinking-off 代理；如果直接用服务自己的 OpenAI 端口，则换成对应地址。

特殊网关需要附加参数时，可以在配置里加：

```json
{
  "llm_extra_headers": {"X-Custom": "value"},
  "llm_extra_body": {"chat_template_kwargs": {"enable_thinking": false}}
}
```

这两个字段会合并进请求。不要放密钥到公开仓库。

如果服务不是 OpenAI 兼容协议，而是完全自定义的请求/响应格式，就需要单独写适配器；当前版本只内置 Ollama 与 OpenAI 兼容两类。


注意：

- API Key 以明文保存在用户配置文件中，不要提交到 GitHub。
- 云端模型是否可用取决于供应商、账号和内容政策。
- 应用不会把提示词发送给除当前配置的 LLM 之外的服务。
- 自动选 LoRA 也使用当前 LLM 配置。

## ComfyUI

```json
{
  "comfy_url": "http://127.0.0.1:18188",
  "comfy_start_script": "",
  "comfy_close_script": "",
  "comfy_workflows_dir": ""
}
```

- `comfy_start_script` 可选；没有时要求 ComfyUI 已经运行。
- `comfy_close_script` 可选；没有时不自动关闭 ComfyUI。
- `comfy_workflows_dir` 是导入工作流时的默认目录。

## LoRA

```json
{
  "lora_roots": [
    "D:\\你的ComfyUI\\models\\loras"
  ],
  "checkpoint_dir": "D:\\你的ComfyUI\\models\\checkpoints",
  "civitai_api_key": ""
}
```

- `lora_roots` 可以有多个，用分号分隔。
- `checkpoint_dir` 是模型中心下载底模的目录；空着时会从 LoRA 根目录推导 `models/checkpoints`。
- `civitai_api_key` 可选，受限资源可能需要；不要提交到仓库。

## 输出

```json
{
  "output_dir": "C:\\Users\\你的用户名\\Pictures\\提示词工作台"
}
```

## 内置工作流模型文件

如果本机模型文件名和默认值不同，修改：

```json
{
  "model_files": {
    "illustrious": {"ckpt_name": "你的 WAI/Illustrious 文件.safetensors"},
    "krea2": {"unet_name": "...", "clip_name": "...", "vae_name": "..."},
    "qwen": {"unet_name": "...", "clip_name": "...", "vae_name": "..."},
    "moss": {"unet_name": "...", "clip_name": "...", "vae_name": "..."},
    "anima": {"unet_name": "...", "clip_name": "...", "vae_name": "..."}
  }
}
```

这些都是 ComfyUI 模型列表里的相对文件名，不是绝对路径。

## 数据目录

历史、设置、导入工作流在：

```text
%APPDATA%\PromptWorkbench\
```

可以通过环境变量覆盖：

```text
PROMPT_WORKBENCH_DATA
PROMPT_WORKBENCH_OUTPUT
```

## 8.0

`tool80_path` 是可选项。没有配置时，“8.0 精修”只提示路径未配置，不影响主功能。
