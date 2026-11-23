# 本地出图工作台 0.3.0-beta

Windows 本地出图工作台：Ollama 生成提示词，ComfyUI 出图。

## 本版重点

- 高级模式 P0/P1/P2 改造
- 就绪状态条：底模缺失、LoRA 兼容、ComfyUI 状态
- Seed / Steps / CFG / Sampler / Scheduler / 宽高参数面板
- LoRA 强度、启用/旁路、触发词复制、底模兼容标记
- 工作流导入校验、最近两张结果对比、提示词计数
- 首次切换高级模式引导；环境设置可重看简洁/高级引导
- Seed 实际值显示、固定并写入保存版本历史
- 托盘最小化、ComfyUI 启停、随机提示词、收藏夹
- 错误面板、模型完整性检查、停止后续、更新日志、界面缩放

## 下载

- 便携版：`local-image-workbench-0.3.0-beta-portable.zip`
- 不要求另装 Python
- 仍需 ComfyUI、Ollama 和模型文件

## 说明

- 不包含模型权重
- 参数面板只覆盖内置工作流，导入工作流保持原生参数
- 代码签名只有钩子，没有证书，SmartScreen 仍会提示未知发布者
- 正式升级后，旧 0.2.0 便携包保留为回滚点
