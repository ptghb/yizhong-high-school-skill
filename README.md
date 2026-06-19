# 唐山一中校史 Skill

基于本地 PDF 与 SQLite 的轻量校史问答 Skill，适合龙虾、Hermes、Codex 等 Agent 在本地直接使用。

## 特点

- 全本地运行，不依赖外部向量数据库
- 无需部署中间件，安装只需一个命令
- 支持片段检索、直接问答、结构化 JSON 导出
- 适合校史、人物、事件、沿革、荣誉等问题

## 快速开始

把 `唐山市第一中学校史.pdf` 放到仓库根目录，然后执行：

```bash
make install
```

安装完成后可直接提问：

```bash
make ask QUESTION="唐山一中是什么时候建立的？"
```

查看原始命中片段：

```bash
make query QUESTION="唐山一中的建校沿革是什么？"
```

导出结构化 JSON：

```bash
make export-json QUESTION="唐山一中是什么时候建立的？"
```

输出 JSON 到文件：

```bash
make export-json \
  QUESTION="唐山一中是什么时候建立的？" \
  OUTPUT="/tmp/tangshan-yizhong-answer.json"
```

## 仓库结构

- `.trae/skills/tangshan-yizhong-history/`：Skill 主目录
- `.trae/skills/tangshan-yizhong-history/SKILL.md`：Trae Skill 定义
- `.trae/skills/tangshan-yizhong-history/install.sh`：安装与建库
- `.trae/skills/tangshan-yizhong-history/query_index.py`：返回命中片段
- `.trae/skills/tangshan-yizhong-history/ask.py`：直接输出带页码答案
- `.trae/skills/tangshan-yizhong-history/export_json.py`：导出结构化 JSON
- `Makefile`：仓库根快捷命令入口

## 适用问题

- 建校时间与前身
- 校名变迁
- 校址迁移
- 重要人物与事件
- 荣誉、称号、实验学校等信息
- 按时间线总结学校发展

## 注意事项

- 默认读取仓库根目录下的 `唐山市第一中学校史.pdf`
- 本地生成的 `.venv`、`history_index.db`、PDF 原件默认不会提交到仓库
- 如果某些页 OCR 噪声较大，建议结合 `make query` 查看原始片段

## Skill 入口

详细 Skill 说明见 [`.trae/skills/tangshan-yizhong-history/SKILL.md`](./.trae/skills/tangshan-yizhong-history/SKILL.md)。
