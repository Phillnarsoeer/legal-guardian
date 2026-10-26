# LegalGuardian v5.0.0 冒烟测试报告

- 时间: 2026-10-27 00:07:19
- 根目录: `C:\Users\123\Desktop\skill\LegalGuardian_v4.3.0`
- 运行命令: `python tests/run_smoke.py`

| 状态 | 编号 | 检查项 | 用时 |
|---|---|---|---|
| PASS | E1 | Python 版本 >= 3.9 | 0.0s |
| PASS | E2 | SKILL.md frontmatter 可解析且 name=legal-guardian | 0.0s |
| PASS | E3 | manifest.yaml name/version = legal-guardian/5.0.0 | 0.0s |
| PASS | E4 | legal-guardian.skill 为合法 zip 且含精简包 8 项（不含 test_data/产品技术文档） | 0.0s |
| PASS | E5 | 已安装 skill 目录存在 (~/.claude/skills/legal-guardian) | 0.0s |
| PASS | D1 | 失效模式 F1-F24 齐全且连续 | 0.0s |
| PASS | D2 | 安全检查清单恰为 8 项 (C1-C8) | 0.0s |
| PASS | D3 | 提问模板恰为 5 个 (T1-T5) | 0.0s |
| PASS | D4 | 题型评分标准 T1-T8 共 8 种 | 0.0s |
| PASS | D5 | 案例库 5515 例 (test_data/cases/all_cases.json) | 0.0s |
| PASS | D6 | RAG 检索块 5515 条 (test_data/rags/chunks.json) | 0.0s |
| PASS | D7 | 训练样本 22060 + 验证 5515 (test_data/training) | 0.1s |
| PASS | D8 | benchmark meta.total_items 与实际条目一致 | 0.0s |
| PASS | D9 | reference/ 已精简：无 v2.0.0 残留数据文件 | 0.0s |
| PASS | D10 | 新增脚本齐全：rag / regulation / report / statute / logic / vericot / fol | 0.0s |
| PASS | D11 | 报告面板齐全：report_panel.html + 3 份示例数据 | 0.0s |
| PASS | D12 | 逻辑矩阵齐全：20 单元 + 8 项检查 | 0.0s |
| PASS | S1 | 失效检测: F1 样本命中 repealed_law | 0.1s |
| PASS | S2 | 失效检测: 多模式样本命中 F1 | 0.1s |
| PASS | S3 | 失效检测: 干净样本零误报 | 0.1s |
| PASS | S4 | 失效检测: F2 罪名定性降维可触发 | 0.1s |
| PASS | S5 | 失效检测: 显式三段论文本不命中 F17 | 0.1s |
| PASS | S6 | 纠正引擎: F1 纠正含实证依据 (铁律1) | 0.1s |
| PASS | S7 | 安全检查: 输出恰 8 项清单 | 0.2s |
| PASS | S8 | 模板匹配: 废止法陷阱推荐 T4 前提挑战型 | 0.1s |
| PASS | S9 | 模板匹配: 量刑预测推荐 T2 案例对比型 | 0.1s |
| PASS | S10 | 作业评估 v2: 识别 T8 且给出分数 | 0.1s |
| PASS | S11 | 红线规则: 引用已废止法 → D1 归零 | 0.1s |
| PASS | S12 | 四维评分引擎: 输出 4 维 + 综合分 | 0.1s |
| PASS | S13 | 校准 --quick: 复现评级 A (100%/MAE0.0) | 0.1s |
| PASS | S14 | 校准全量: 复现评级 A (v5.0.0 全量 26 项) | 0.1s |
| PASS | S15 | 答案键验证: 畸形键返回结构化错误 | 0.1s |
| PASS | S16 | 法条检索: 离线命中本地知识库 (故意伤害) | 0.1s |
| PASS | S17 | 确定性: 同输入两次检测结果逐字节一致 (铁律8) | 0.2s |
| PASS | S20 | 模块E: F24 在知识点覆盖<80%时触发 | 0.1s |
| PASS | S21 | 案例检索: RAG 命中民间借贷案例 (5515库) | 0.1s |
| PASS | S22 | 模块D: 三维规制评估输出 13 条目 | 0.1s |
| PASS | S23 | 红线扩展: 虚构法条命中 → D1 归零 | 0.1s |
| PASS | S24 | 确定性: RAG 两次检索逐字节一致 | 0.2s |
| PASS | S25 | 报告构建器: 全链路输出 9 模块且 JSON 合法 | 0.2s |
| PASS | S26 | 逻辑体检: 干净样本 0 命中，混合样本命中 L01/L04/L08 | 0.2s |
| PASS | S27 | VeriCoT 完整版: 有效论证 valid，缺失事实命中 V15 | 0.2s |
| PASS | I1 | 三阶段链路: 检测→纠正→安全 全通 | 0.2s |
| PASS | I2 | 竞赛场景: 教学大纲审核推荐 T1+T4 | 0.1s |

**汇总**: PASS=44 FAIL=0 KNOWN=0 SKIP=0

`FAIL` = 意外失败；`KNOWN` = 已记录已知缺陷（详见测试方案文档"已知问题清单"）。
