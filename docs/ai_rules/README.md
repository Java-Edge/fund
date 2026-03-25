# AI 规则目录

这里是运行时 prompt 的规则来源，也是后续策略维护的主入口。

## 文档分层

- [core_principles.md](/Users/javaedge/soft/PyCharmProjects/fund/docs/ai_rules/core_principles.md)：全局共通原则
- [entry_rules.md](/Users/javaedge/soft/PyCharmProjects/fund/docs/ai_rules/entry_rules.md)：入场与偏积极判断规则
- [reduction_rules.md](/Users/javaedge/soft/PyCharmProjects/fund/docs/ai_rules/reduction_rules.md)：减仓与偏防守判断规则
- [position_sizing_rules.md](/Users/javaedge/soft/PyCharmProjects/fund/docs/ai_rules/position_sizing_rules.md)：仓位和集中度约束
- [risk_exceptions.md](/Users/javaedge/soft/PyCharmProjects/fund/docs/ai_rules/risk_exceptions.md)：信号冲突、数据不足、例外情形
- [output_format_rules.md](/Users/javaedge/soft/PyCharmProjects/fund/docs/ai_rules/output_format_rules.md)：输出结构与表达约束

## 维护原则

- 新增交易策略时，优先决定它属于哪一类规则，再追加到对应文档。
- 不要先改 Python prompt；只有规则装配逻辑变化时才改代码。
- 如果规则需要让 Codex 直接遵循，记得同步检查专用 skill。

## 统一规则格式

请优先参考 [rule_template.md](/Users/javaedge/soft/PyCharmProjects/fund/docs/ai_rules/rule_template.md)。

推荐每条规则都按以下字段写：

- 规则名称
- 触发条件
- 证据要求
- 输出限制
- 风险提示
