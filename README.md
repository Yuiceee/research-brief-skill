# Research Brief Skill · 图文研究汇报

将研究资料整理成完整的图文报告，融合科研进展的解释深度与合作方沟通的可读性。

默认以简洁标题直接进入研究背景，正文围绕问题和结果配图展开，结论到位即止。有分布、趋势、对比或结构的结论默认配图，不画仅重复表格的装饰图。正文只写经得起复述的结论，过程状态不进结果口径。不自动添加独立摘要、封面、延伸追问或来源章节；PDF 页脚只留页码。材料核对和来源追溯保存在独立工作底稿。不把计算候选写成实验验证，不机械套用投稿论文结构。

## 安装到本地 Codex

将 `skills/research-brief` 目录复制到 `~/.codex/skills/research-brief`。若该目录已存在，先比较差异，再更新对应文件。安装后在新会话中使用：

```text
请使用 $research-brief 读取这些项目材料，生成包含背景、工作、结果和结论的图文研究报告，交付离线 HTML 和可编辑正文。
```

该 skill 也允许根据科研进展、阶段总结等请求自动选用；无需每次显式调用。

## 内容

- [SKILL.md](skills/research-brief/SKILL.md)：适用范围、写作风格与完整工作流。
- [证据与图形口径](skills/research-brief/references/evidence-and-figures.md)：数据、版本、结构图与结论边界。
- [HTML 生成与检查](skills/research-brief/references/html-delivery.md)：本地模板、生成工具和交付方法。
- [设计来源](skills/research-brief/references/provenance.md)：参考思想与本 skill 的选择。

使用生成工具需要 Python 3.9+，依赖见 `skills/research-brief/scripts/requirements.txt`。HTML 图片内嵌，无远程资源依赖；可编辑 Markdown 与配图一同保留，证据附件仅在用户要求时加入交付包。

本仓库只收录通用 skill 与工具，不包含项目报告、研究数据或内部材料。
