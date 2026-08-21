# templates/ 改写模板目录说明

> **重要（2026-08-21 更新）**：当前**活动模板**已迁移至 [config.json](../config.json) 的 `templates` 段（多模板匹配机制，含政策公示类 / 干货科普类 / 客户案例复盘类），由 `process_articles.py` 的 `match_template()` 关键词打分匹配。本目录下的 `.md` 文件为**早期参考资产**，暂未被代码读取，保留供创作框架参考；如需启用请迁移到 `config.json` 的 `templates.list`。

> 本目录存放多种文章改写模板。每个模板 = 一个 `.md` 文件，包含「YAML 元数据头（供大模型匹配）+ 正文创作框架（供大模型改写）」两部分。
> 新增模板前，**必读本文第 2 节命名规范**与第 4 节新增步骤。

---

## 1. 目录用途

- 多模板体系：不同品类文章匹配不同模板进行改写
- 两阶段工作流：
  - **匹配阶段**——大模型读取本目录所有模板的「元数据头」+ 待改写文章，选出最匹配的 `template_id`
  - **改写阶段**——只加载选中模板的「完整创作框架」+ 文章，按框架改写输出

---

## 2. 文件命名规范（强制）

### 2.1 命名公式

```
{domain}-{topic}.md
```

### 2.2 强制规则

1. **全小写英文**，单词之间用连字符 `-` 连接
2. **禁止**：中文、空格、下划线 `_`、大写字母、特殊符号
3. **文件名必须与文件内 `template_id` 一一对应**：`template_id` 用下划线，文件名用连字符
   - 例：`template_id: policy_sci_tech` ↔ 文件名 `policy-sci-tech.md`
4. 一个 `domain` 前缀对应一个业务赛道，便于按前缀聚类查找（如 `ls templates/policy-*.md`）

### 2.3 domain 受控词表（领域，须从此表选取）

新增领域时，**必须先在本表登记**再使用：

| domain | 中文 | 覆盖范围 |
|---|---|---|
| `policy` | 政策科创类 | 政策解读 / 补贴申领 / 科创项目申报 / 资质认定 / 避坑复盘 |
| `trademark` | 商标类 | 商标注册 / 驳回复审 / 撤三 / 侵权维权 |
| `patent` | 专利类 | 发明 / 实用新型 / 外观设计 / 优先审查 |
| `copyright` | 版权类 | 软件著作权 / 作品登记 |
| `certification` | 认证资质类 | 高新 / 专精特新 / ISO / 体系认证 |
| `overseas` | 海外知识产权类 | 马德里 / 亚马逊品牌备案 / 海关备案 / 海外维权 |
| `general` | 通用类 | 跨业务综合 / 兜底模板 |

### 2.4 topic（细分主题）

- 小写英文，连字符连接，描述该领域下的具体子主题/子类型
- 自由命名，但须简短、可读、与 `template_id` 后缀一致
- 同一 `domain` 下不可出现重复 `topic`

### 2.5 命名示例

| 文件名 | template_id | 说明 |
|---|---|---|
| `policy-sci-tech.md` | `policy_sci_tech` | 政企科创政策类 |
| `trademark-ecommerce.md` | `trademark_ecommerce` | 电商商标避坑类 |
| `patent-manufacture.md` | `patent_manufacture` | 工厂专利申报类 |
| `overseas-crossborder.md` | `overseas_crossborder` | 跨境海外知识产权类 |
| `general-default.md` | `general_default` | 通用兜底模板 |

---

## 3. 模板文件结构规范

每个 `.md` 文件必须包含以下两部分：

### 3.1 YAML 元数据头（`---` 包裹，供匹配阶段读取）

| 字段 | 必填 | 说明 |
|---|---|---|
| `template_id` | 是 | 与文件名对应（下划线形式） |
| `category_name` | 是 | 中文品类简称 |
| `category_full` | 是 | 完整品类描述 |
| `version` | 是 | 模板版本（语义化 X.Y.Z） |
| `content_attributes` | 是 | 内容属性列表 |
| `target_audience` | 是 | 目标受众列表 |
| `business_purpose` | 是 | 商业目的 |
| `match_keywords` | 是 | 匹配关键词列表（建议 ≥ 10 个，LLM 据此判断命中度） |
| `match_signals` | 是 | 匹配信号列表（同时满足多条时优先匹配） |
| `subtypes` | 是 | 同品类子类型 |
| `not_match` | 是 | 不匹配条件（出现时应改用其他模板） |
| `content_differentiator` | 否 | 内容核心差异 |

### 3.2 正文创作框架（供改写阶段读取）

建议结构：
1. 顶层核心框架（万能模型 + 底层原理）
2. 核心创作原则
3. 全板块标准化写法（每板块含：写作目的 / 固定框架 / 底层原理 / 标准化写法 / 禁忌）
4. 全文结构总模板（极简汇总）

---

## 4. 新增模板步骤

1. 按 `{domain}-{topic}.md` 命名新建文件（domain 须来自第 2.3 节词表）
2. 复制现有模板的元数据头结构，逐字段填写；`template_id` 与文件名对应
3. `match_keywords` 至少 10 个，`match_signals` 至少 3 条，`not_match` 至少 2 条
4. 编写正文创作框架
5. 若引入新 `domain`，先在第 2.3 节词表登记，再使用
