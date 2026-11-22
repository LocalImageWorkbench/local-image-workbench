# 给 DSH 的一键配置提示词

可以直接用发布版里的生成器：左侧“环境设置” → “生成 DSH 提示词”。

它会根据当前表单检查：

- LoRA 根目录
- 底模目录
- 工作流目录
- skills 目录
- 提示词库
- 输出目录
- ComfyUI 启停脚本
- Illustrious/MOSS/Krea2/Qwen/Anima 的模型文件

生成的提示词可以复制到剪贴板，也会保存到：

`%APPDATA%\PromptWorkbench\dsh-setup-prompt.md`

API Key 不会写进提示词。

下面是一份通用版本，也可以直接发给 DSH。它只针对发布版目录，不要让它改本地版 `D:\prompt-workbench`。

```text
请在这台 Windows 机器上配置“提示词工作台”发布版，目录是 D:\prompt-workbench-release。

要求：
1. 不要修改 D:\prompt-workbench 本地版。
2. 检查 Ollama 是否运行，默认 http://127.0.0.1:11434。
3. 检查 ComfyUI 是否运行，默认 http://127.0.0.1:18188。
4. 找到 ComfyUI 的 models\loras 目录，以及 user\default\workflows 目录。
5. 如果存在可用的 ComfyUI 启停脚本，找到并填入；没有就留空，不要猜。
6. 读取本机 config.json 中已有的 model_files 默认值，核对模型文件是否真的存在；缺失就报告，不要改文件名。
7. 将结果写入 %APPDATA%\PromptWorkbench\config.json，保留已有 UI 设置和 API Key，不要泄露 Key。
8. 输出目录默认使用 用户\Pictures\提示词工作台，除非我指定其他目录。
9. 完成后运行发布版的环境设置连接检测，并用 Python 测试 config 和 llm_client 模块。
10. 只报告：修改了哪些字段、哪些路径存在、哪些依赖缺失、下一步需要我提供什么。

不要自动下载模型、LoRA、ComfyUI 或 Ollama。
不要启动/停止我的本地工作台。
```

如果使用云端 LLM，在配置完成后再打开“环境设置”，填写：

- LLM 类型：openai
- LLM 地址：供应商的 OpenAI 兼容 base URL
- API Key
- 默认模型 ID

不要把 API Key 发到聊天里，也不要提交到 GitHub。
