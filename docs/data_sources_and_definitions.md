# 数据来源、口径与使用边界

## 官方数据核实

- 上游：[bradleyboehmke/completejourney](https://github.com/bradleyboehmke/completejourney)，版本说明为 Complete Journey 2.0，项目许可 CC0。
- `transactions_sample`：75,000 条抽样收据行，官方完整交易表为 1,469,307 行、11 字段。
- `promotions_sample`：360,535 条抽样记录；官方完整促销表为 20,940,529 行、5 字段。
- `products`：92,331 个商品、7 字段。
- 官方促销样本只覆盖 2 家门店；demo 强制保留这 2 家门店，再加入 6 家交易活跃门店。因此跨店展示效果的覆盖有限。
- 展示编码：0 无额外陈列，1 店前，2 店后，3 前端架，4 中部端架，5 后端架，6 侧通道端架，7 通道内，9 二次陈列，A 架内。

## 三类数据不可混用

| 类型 | 表/字段 | 标签 | 允许的表述 |
|---|---|---|---|
| 真实匿名数据 | transactions/products/promotions 及其描述性聚合 | `real_anonymized` / `descriptive_real_anonymized` | 观察到销售、折扣、展示编码 |
| 模型估计数据 | expected sales、predicted incremental、confidence | `model_estimate` | 模型预测、反事实估计 |
| 模拟业务配置 | 容量、位置 ID、当前配置、成本、适配、政策、审计 | `simulated` | 情景模拟、流程演示 |

所有导出结果都保留 `data_source` 或可追溯到带该字段的上游表。`predicted_incremental_sales` 绝不应称为“实际提升”。

## 指标口径

- `actual_sales`：源交易 `sales_value` 的观察值汇总。
- `sales_per_product`：观察销售额 / 组内不同商品数，只是效率描述。
- `expected_sales_without_special_display`：将模型的 `display_location` 设为 0 后的预测。
- `predicted_incremental_sales`：同一模型的展示情景预测减去无额外展示情景预测。
- `confidence`：由品类 × 位置样本支持度映射，范围 0–1；不是统计置信区间。
- 品类覆盖率：方案中不同品类数 / 候选品类数。
- 品牌集中度：方案中分类的 modal brand 份额最大值。源数据 brand 只有 Private/National，demo top categories 的 modal brand 可能单一，因此该指标需谨慎解释；硬约束采用品类最大槽位数。

## 不能做出的因果结论

陈列位并非随机分配。选品、库存、价格策略、门店客流、促销策划和执行质量均可能同时影响展示与销售。固定效应/历史控制只能降低部分混杂，不能替代随机试验、差分中的差分平行趋势验证或可靠工具变量。促销前后、mailer 叠加、跨店排名均标记为描述性分析。

## 许可与使用

上游包在 `DESCRIPTION` 中声明 CC0。仓库代码采用 MIT；引用作品集时仍应注明 84.51° Complete Journey 与上游整理项目。

