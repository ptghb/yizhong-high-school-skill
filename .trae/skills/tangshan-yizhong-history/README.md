# 唐山一中校史 Skill

基于本地 PDF 和 SQLite 的轻量校史问答 Skill。

特点：

- 不依赖外部向量数据库
- 不依赖单独部署服务
- 安装只需一个命令
- 适合龙虾、Hermes、Codex 统一调用

## 目录

- `SKILL.md`：Trae Skill 定义
- `install.sh`：一键安装与建库
- `build_index.py`：PDF 提取与索引构建
- `query_index.py`：返回命中片段
- `ask.py`：直接输出基于证据的答案
- `export_json.py`：导出结构化 JSON
- `history_index.db`：本地 SQLite 索引

## 一键安装

在项目根目录执行：

```bash
bash .trae/skills/tangshan-yizhong-history/install.sh
```

或者使用更短的命令：

```bash
make -C .trae/skills/tangshan-yizhong-history install
```

默认直接使用当前目录下已提交的 `history_index.db`。

只有在本地索引不存在，或者你想强制重建索引时，才需要 PDF。

如果 PDF 路径不同：

```bash
bash .trae/skills/tangshan-yizhong-history/install.sh --rebuild "/你的/PDF/绝对路径.pdf"
```

## 用法

查询命中片段：

```bash
.trae/skills/tangshan-yizhong-history/.venv/bin/python \
  .trae/skills/tangshan-yizhong-history/query_index.py "唐山一中的建校沿革是什么？"
```

直接输出答案：

```bash
.trae/skills/tangshan-yizhong-history/.venv/bin/python \
  .trae/skills/tangshan-yizhong-history/ask.py "唐山一中是什么时候建立的？"
```

导出结构化 JSON：

```bash
.trae/skills/tangshan-yizhong-history/.venv/bin/python \
  .trae/skills/tangshan-yizhong-history/export_json.py "唐山一中是什么时候建立的？"
```

使用 `make`：

```bash
make -C .trae/skills/tangshan-yizhong-history ask QUESTION="唐山一中是什么时候建立的？"
make -C .trae/skills/tangshan-yizhong-history query QUESTION="唐山一中的建校沿革是什么？"
make -C .trae/skills/tangshan-yizhong-history export-json QUESTION="唐山一中是什么时候建立的？"
```

输出到文件：

```bash
make -C .trae/skills/tangshan-yizhong-history export-json \
  QUESTION="唐山一中是什么时候建立的？" \
  OUTPUT="/tmp/tangshan-yizhong-answer.json"
```

## 推荐调用方式

适用于龙虾、Hermes、Codex 的统一流程：

1. 先执行 `ask.py` 获取答案和依据页码。
2. 如果问题复杂，再执行 `query_index.py` 查看更多原始片段。
3. 如果需要给其他 Agent 或脚本消费，执行 `export_json.py`。
4. 最终回答时保留页码，不补造 PDF 中没有的信息。

## 适合的问题

- 建校时间和前身
- 校名变迁
- 校址迁移
- 重要历史阶段
- 重要人物、事件、荣誉
- 按时间线总结学校发展

## 说明

- 当前方案是本地轻量检索，不调用外部大模型。
- `ask.py` 会根据问题类型输出不同结构，如建校、沿革、校址、人物、荣誉。
- `ask.py` 仍然属于抽取式归纳，不是自由生成。
- `export_json.py` 会输出 `question`、`question_type`、`summary`、`key_points`、`passages` 等字段。
- `install.sh` 默认复用仓库里的 `history_index.db`，不会重复解析 PDF。
- 如果 PDF 某些页面 OCR 噪声较重，建议结合 `query_index.py` 查看原始片段。
