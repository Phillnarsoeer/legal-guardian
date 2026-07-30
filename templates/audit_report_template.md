# AI法律回答审核报告

> 审核工具：LegalGuardian v1.0.0
> 审核时间：{audit_date}
> 实证基线：西南民族大学法学院14案例×2轮×4维测评（2026年5月）

---

## 📊 审核摘要

| 项目 | 结果 |
|------|------|
| 待审文本长度 | {text_length} 字 |
| 失效模式命中 | {fired_count}/10 |
| 🔴 关键问题 | {critical_count} 项 |
| 🟠 高度注意 | {high_count} 项 |
| 🟡 中度提醒 | {medium_count} 项 |
| 综合风险等级 | {overall_risk} |

---

## 📈 四维评分

| 维度 | 得分 | DS基线 | 千问基线 | 差距(vs DS) |
|------|------|--------|----------|-------------|
| 准确性 | {accuracy_score}/5 | 4.03 | 3.49 | {accuracy_diff} |
| 时效性 | {timeliness_score}/5 | 4.69 | 4.13 | {timeliness_diff} |
| 逻辑性 | {logic_score}/5 | 3.66 | 2.93 | {logic_diff} |
| 引导性 | {guidance_score}/5 | 2.96 | 1.70 | {guidance_diff} |
| **综合** | **{overall}/5** | **3.84** | **3.06** | **{overall_diff}** |

> 📌 引导性是AI法律工具中最薄弱维度（DS平均2.96, 千问平均1.70），R2角色扮演可提升约40%

---

## 🔍 失效模式详细检测

<!-- 每条检测到的失效模式使用以下格式 -->

### [{failure_id}] {failure_name} — 严重度: {severity_icon}

**原文问题：** {original_issue}

**实证依据：** 
- 案例：{test_case}
- 发现：{empirical_finding}
- 相关数据：{empirical_scores}

**修正方向：** {correction_direction}

**替代表述建议：**
```
{suggested_rewrite}
```

**规制路径参考：** {regulation_reference}

---

## ✅ 安全检查清单执行结果

| # | 检查项 | 状态 | 说明 |
|---|--------|------|------|
| C1 | 法条逐条核对 | {c1_status} | {c1_note} |
| C2 | 反向罪名思考 | {c2_status} | {c2_note} |
| C3 | 量刑预测边界 | {c3_status} | {c3_note} |
| C4 | 双平台交叉验证 | {c4_status} | {c4_note} |
| C5 | 遗漏争点检查 | {c5_status} | {c5_note} |
| C6 | 核实标记 | {c6_status} | {c6_note} |
| C7 | 不替代律师 | {c7_status} | {c7_note} |
| C8 | 计算一致性 | {c8_status} | {c8_note} |

**通过率：{pass_rate}**

---

## 📋 行动建议（按优先级排列）

1. 🔴 **立即修正**：{critical_actions}
2. 🟠 **重点改进**：{high_actions}
3. 🟡 **建议优化**：{medium_actions}

---

## ⚠️ 重要声明

本审核报告由LegalGuardian自动生成，仅作为AI输出质量的参考工具，不构成法律意见。
实证基线数据来自2026年5月的测试，可能随AI平台更新而变化。
建议将本报告与人工审查结合使用。

---

*报告生成于 {report_generated_at} | LegalGuardian v1.0.0 | 基于西南民族大学法学院大创项目实证数据*
