# 本地出图工作台（Prompt Workbench）

Windows 本地出图工作台，连接 Ollama 生成/修改提示词，并连接 ComfyUI 出图。宣传语：提示词工作台 · 快捷本地出图。

## 当前状态

这是 **v0.3.0-beta 预览版**，面向已经安装 ComfyUI 和 Ollama（或其他 OpenAI 兼容 LLM）的用户。便携版不要求另装 Python，但仍需要 ComfyUI、Ollama 和模型文件。

2026-11-22 起，本目录是开发主线；旧的本地自用版已归档，不再加新功能。迁移说明见 `docs/MIGRATION.md`。

开发测试机是笔记本 RTX 5090；这只是开发和测试环境说明，**不是最低配置**，也不代表其他显卡会有相同速度。

- 不随仓库分发模型权重、LoRA、工作流或 Civitai 资源。
- 不包含露骨示例图。
- 仅支持 Windows 10/11。
- 内置工作流默认需要与 `config.json` 中 `model_files` 匹配的模型文件名；换模型需要改配置。
- 便携版首次启动仍需要选择/确认 ComfyUI 路径、模型和 LLM。

## 宣传片

B 站演示视频：

https://www.bilibili.com/video/BV12kyjz9EKA/

- 16:9 主封面：https://github.com/LocalImageWorkbench/local-image-workbench/releases/download/v0.2.0-beta/cover-16x9-local-image-workbench.png
- 4:3 个人空间封面：https://github.com/LocalImageWorkbench/local-image-workbench/releases/download/v0.2.0-beta/cover-4x3-local-image-workbench.png

### 高级模式\n\n- 就绪状态条：底模缺失、LoRA 兼容、ComfyUI 状态\n- Seed / Steps / CFG / Sampler / Scheduler / 宽高参数面板\n- 正向/负向字符计数\n- LoRA 强度、启用/旁路、触发词复制、底模兼容标记\n- 工作流导入校验、最近两张结果对比\n- 首次切换引导；设置页可重看简洁/高级引导\n\n### 发布硬化

- 生成结束/失败后自动刷新 LLM 与 ComfyUI 状态。
- 角色搜索、浏览器挑选、推荐包、DSH 页面、C 站教程防止重复弹窗。
- API Key 输入默认遮罩，可点“显示/隐藏”。
- 运行日志：`%APPDATA%\PromptWorkbench\logs\app.log`，自动轮转。
- 配置带 `config_version`，旧配置自动补默认项。
- NVIDIA 读取精确显存；AMD/Intel 可显示型号，但不伪造显存。
- “停止”会调用 ComfyUI `/interrupt`；下载支持取消，`.part` 文件下次续传。
- 首次向导自动扫描常见 ComfyUI 目录，预填 LoRA、checkpoint、工作流和启动脚本。
- 首次向导提供“测试一张”，真实出 1 张 832×1216 测试图后才算闭环。
- 提供免 Python 的便携版 `dist\PromptWorkbench\PromptWorkbench.exe`。
- 侧栏“检查更新”读取 `update.json`，只提示新版本并打开 Release，不自动执行下载。
- 界面启用 DPI 感知、统一提高最小字号，侧栏和 37 个常用操作接入线性图标。
- 更新失败或环境不适配时，可生成带给 DSH 的修复提示词（版本、错误、环境路径，不含 API Key）。
- 设置页提供“更新修复提示词”，不会自动升级 Python/ComfyUI/CUDA。

## 环境要求

- Windows 10/11
- Python 3.10+
- Ollama，或任意 OpenAI 兼容接口（LM Studio、vLLM、llama.cpp server、OpenAI、OpenRouter、DeepSeek 等）
- ComfyUI（默认 18188）
- 对应底模、LoRA、文本编码器和 VAE
- ComfyUI 自定义节点按工作流需要自行安装

## 安装与运行

**便携版**：`dist\PromptWorkbench\PromptWorkbench.exe`，不要求用户另装 Python；仍需自备 ComfyUI/Ollama/模型。

**源码版**：双击或在 PowerShell 运行 `setup.ps1`。它会安装依赖、跑环境自检，然后启动工作台。

如果手动安装：

1. 安装 Python 3.10+，勾选 `Add Python to PATH`。
2. 安装依赖：`pip install -r requirements.txt`
3. 启动 Ollama 和 ComfyUI。
4. 运行：`pythonw app.pyw`
5. 首次启动会打开环境设置，填写：
   - LLM 类型（`ollama` 或 `openai`）
   - LLM 地址、API Key、默认模型 ID
   - ComfyUI 地址
   - LoRA 根目录
   - 输出目录
   - ComfyUI 启动/关闭脚本（可选）
   - 工作流目录
   - skills 目录（默认使用随包 `skills/`）
6. 保存后重启工作台。

一键配置不会静默安装 ComfyUI、Ollama 或模型；它只处理 Python 依赖、配置和连接检测。

## 配置与数据

- 配置：`%APPDATA%\PromptWorkbench\config.json`
- 历史、设置、导入工作流：`%APPDATA%\PromptWorkbench\`
- 默认输出：`Pictures\提示词工作台`
- 可用 `PROMPT_WORKBENCH_DATA` 覆盖数据目录。
- 可用 `PROMPT_WORKBENCH_OUTPUT` 覆盖默认输出目录。

## 功能

- 简洁模式默认开启：三步首次向导、环境状态、一键准备
- 9B + Illustrious/WAI 推荐包，可一键补齐底模
- 画角色搜索：英文/罗马音优先，没结果才补中文原文；新角色提示用联网 AI 查英文名，可一键复制翻译提示词
- “浏览器挑选”按 SFW/NSFW 跳 civitai.com/civitai.red，带底模和容错别名筛选
- 红色 C 站首次跳转前显示 3 页原站截图：完整页头/放大眼睛/菜单/账号设置，各自红框
- 红色 C 站下载后可复制 DSH 接入提示词（不需要 API Key）
- 画幅竖/方/横、随机灵感、人物/服装/场景/光线快捷补充
- 底模卡片默认折叠，只显示当前底模和换底模
- 生成结果支持再来一张、打开输出；可停止生成
- 错误自动翻译成中文操作建议
- 高级模式保留工作流、底模、LoRA、导入、搜索等能力
- 9B/27B 本地提示词；统一 LLM 客户端支持 Ollama 和 OpenAI 兼容接口
- 模型中心：Civitai 搜索、大小确认、下载进度和 SHA256 校验
- 空工作流、多 LoRA 自动治理、导入 ComfyUI 工作流
- 简洁模式自动读取 NVIDIA 显存，按风格和显存推荐底模，不强制
- 底模缺文件时显示红色警告，可直接生成/复制 DSH 部署提示词
- 环境设置可生成针对当前缺失项的 DSH 配置提示词，可复制或保存
- 简洁模式默认 Illustrious；可切换 MOSS、Krea2、Qwen 2.1、Anima 五套底模卡片
- 选中的底模、风格、画幅和张数会记住
- 历史记录单击选中、双击载入、支持单条/批量删除
- 生成进度 1/N、缩略图结果页
- 历史记录单击选中、双击载入左侧，支持单条/批量删除（不删图片文件）
- 8.0 精修入口（可选）

## 配置文档

- 基础配置与云端 LLM：`docs/CONFIGURATION.md`
- 简洁模式说明：`docs/BEGINNER-MODE.md`
- 精简模型栈与风格推荐：`docs/MODEL-PRESETS.md`
- DSH 模型部署提示词：`docs/DSH-MODEL-DEPLOY.md`
- 模型中心与下载网络：`docs/MODEL-CENTER.md`
- 模型能力/NSFW 选型：`docs/MODEL-GUIDE.md`
- 让 DSH 一键检查/配置：`docs/DSH-SETUP-PROMPT.md`
- 迁移与主线：`docs/MIGRATION.md`
- 记忆功能现状：`docs/MEMORY.md`

## 已知限制

- 内置工作流绑定固定模型文件名，当前通过 `config.json` 的 `model_files` 修改。
- 复杂 UI 工作流含自定义节点/子图时，需要先在 ComfyUI 导出 API JSON。
- 没有自动安装 ComfyUI/Ollama/模型的向导。
- 没有安装器/代码签名；已提供便携版和更新提示，不做自动替换。
- 没有完整自动化测试；当前只有纯模块测试。
- 公开仓库不要提交 `docs` 中的露骨测试图、`data` 中的个人历史或任何模型文件。

## 内容边界

软件允许成年虚构角色的 NSFW 提示词，但保留硬限制：

- 仅 18+ 成年虚构角色
- 禁止未成年、幼态、儿童化、年龄不明
- 禁止真实人物性化
- 公开仓库、README、Issue 中不要上传露骨素材

## 开发

```powershell
python -m unittest discover -s tests -v
```

纯模块测试不需要 ComfyUI/Ollama。

## 许可

代码使用 MIT License。随包 `skills/` 和第三方工作流/模型的授权需要单独核对，见 `THIRD_PARTY_NOTICES.md`。



## 国内补充下载

- 夸克整合发布包（便携版 + SFW/NSFW 清单）：https://pan.quark.cn/s/c9c289247c6d?pwd=NXHp 提取码：NXHp
- 发布包 SHA256：`b627c5b6cc65ba5931f56c8fcc40524cc38873097000371dafd00fefd32ee78e`
- 单独清单：SFW `https://pan.quark.cn/s/e04b7874df45?pwd=YLU8` 提取码 `YLU8`；NSFW（仅 18+）`https://pan.quark.cn/s/0cf0359df13f?pwd=HdzU` 提取码 `HdzU`
- 旧便携包链接已不再作为主下载，请使用上面的整合包。

夸克是补充发行渠道，不是 GitHub 镜像；不含模型权重，NSFW 仅限 18+。


## 用户文档

- 使用说明：`使用说明.md`（便携包同目录）
- 完整更新日志：`CHANGELOG.md`（GitHub 仓库）


## 快捷键（0.4 起）

- `Ctrl+Enter`：开始生成图片（简洁/高级通用）
- `Ctrl+S`：保存版本
- `Ctrl+L`：聚焦提示词
- `Ctrl+F`：搜索工作流
- `Ctrl+Z`：撤销清空
- `Ctrl+Q`：退出程序


## 随机提示词

内置 112 条本地提示词，按人物、场景、动物、静物、科幻奇幻、建筑室内、美食、时尚服装、交通机械、古风历史、植物自然、抽象艺术分类；默认混合随机，可切换到单一类型。


## V5 随机库

- 精选库（默认）+ 模板组合 + 混合三种方式
- 支持导入/导出 andom-library.json`n


## SFW / NSFW 随机库

SFW 与 NSFW 使用独立提示词库；NSFW 混合时按权重偏向人物/私房，SFW 模式不会回退到 NSFW。


## 角色主题随机（V5.1）

LoRA 可标角色/姿势/风格；随机角色后仅组合同底模的姿势/风格 LoRA，最多三层。

