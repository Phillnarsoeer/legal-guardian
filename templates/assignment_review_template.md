# 法学作业评估报告

> 评估工具：LegalGuardian v4.3.0 — 模块C：法学作业评估
> 评估时间：{evaluation_date}
> 作业类型：{course_type}

---

## 📊 总体评分

| 项目 | 结果 |
|------|------|
| **总分** | **{total_score}/100** |
| **等级** | **{grade}** |
| 红线触发 | {red_line_status} |
| 失效模式命中 | {failure_count}/24 |

---

## 📈 五维详细评分

### D1 法律依据准确性（权重30%）

| 指标 | 结果 |
|------|------|
| 原始得分 | {d1_score}/5 |
| 加权贡献 | {d1_weighted}/30 |
| 引用法律 | {laws_found} |
| 条款引用 | {articles_status} |
| 评价 | {d1_assessment} |

**问题：** {d1_issues}

---

### D2 论证逻辑严密性（权重25%）

| 指标 | 结果 |
|------|------|
| 原始得分 | {d2_score}/5 |
| 加权贡献 | {d2_weighted}/25 |
| 三段论完整度 | {syllogism}/3 |
| 多角度分析 | {multi_perspective} |
| 评价 | {d2_assessment} |

**问题：** {d2_issues}

---

### D3 法理深度（权重20%）

| 指标 | 结果 |
|------|------|
| 原始得分 | {d3_score}/5 |
| 加权贡献 | {d3_weighted}/20 |
| 深度维度覆盖 | {depth_coverage}/4 |
| 评价 | {d3_assessment} |

**问题：** {d3_issues}

---

### D4 实务操作性（权重15%）

| 指标 | 结果 |
|------|------|
| 原始得分 | {d4_score}/5 |
| 加权贡献 | {d4_weighted}/15 |
| 实务元素覆盖 | {practical_coverage}/5 |
| 评价 | {d4_assessment} |

**问题：** {d4_issues}

---

### D5 学术规范（权重10%）

| 指标 | 结果 |
|------|------|
| 原始得分 | {d5_score}/5 |
| 加权贡献 | {d5_weighted}/10 |
| 结构完整性 | {structure_status} |
| 参考文献 | {references_status} |
| 评价 | {d5_assessment} |

**问题：** {d5_issues}

---

## 🔍 失效模式检测结果

<!-- 仅在检测到失效模式时显示 -->
| 编号 | 模式名称 | 检测概率 | 严重度 |
|------|---------|---------|--------|
| {failure_rows} |

---

## 💬 综合评价

**表现最好：** {best_dimension}

**最需改进：** {worst_dimension}

**详细反馈：**
{feedback_list}

---

## 📋 改进计划

| 优先级 | 维度 | 当前 | 目标 | 行动建议 |
|--------|------|------|------|---------|
| {improvement_rows} |

---

## ⚠️ 评分说明

- 评分锚定于实证基线：5分=DS最佳测试表现(准确性5.0)，3分=DS综合平均(3.84)，1分=千问引导性平均(1.70)
- 🔴 红线：D1法律依据准确性为0时，总分直接计0分
- 本评分由LegalGuardian自动生成，仅供参考，不能替代教师的人工评判
- 建议将本报告与教师的专业评价结合使用

---

*报告生成于 {report_generated_at} | LegalGuardian v4.3.0*
