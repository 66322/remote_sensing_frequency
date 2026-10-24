# Post-T paired v2 结果验收（2026-10-12）

2026-10-12关键原件复核补充：R16−H16=+0.348562pp，两tile分别+0.328642/+0.356335pp，原screen中这一配对passed=True；R16总gate=False的直接原因是六E相对R0的五项底线失败，不是R−H配对未过。F/H/R独立8k/16k预算比较未通过收益门槛；R16自身8k→16k轨迹仍+0.618217pp，因此只关闭当前配方下盲目延长预算的依据，不宣称后半程不学习或普遍收敛。DSM特征内容干预是已存在的更直接线索：R16在块缺失条件C−Z=+4.009563pp、C−S=+9.114377pp；仍是固定模型推理敏感性，不是同预算RGB-only配对训练因果结论。

[关键复核](LATEST_RESULTS_KEY_REVIEW_20261012.md)；下文预算解释均限定于当前配方/日程，不推为普遍收敛。

状态：**REVIEWED / PAIRED_SCREEN_FALSE / NO_FURTHER_DISPATCH / NOT_ACCEPTED_AS_SUCCESS**。

权威轻量原件提交：`0283f74e6c8242694737ea75faa225c8af60a8c2`，目录：
`records/research_post_t_paired_v2_20261011T182543_3880702/evidence_20261012T111558374371_191546/`。

仓库冻结汇总明确输出：`PAIRED_SCREEN False NO_FURTHER_DISPATCH`。因此本轮可以保留机制线索，但不能把 R16 写成已经通过完整预注册门槛的成功方法，也不能据此自动派发后继。

## 1. 冻结问题

三种适应位置：

- **F**：只训练私有融合解码器；RGB 专家保持冻结。
- **H**：F + RGB `net.rgb` 与 `decoder[:-1]` 完整接口适应。
- **R**：H + RGB encoder 最后 4 个 block。

每种机制各比较 8k / 16k 预算，共 6 个训练任务、72,000 optimizer updates；所有任务从同一个 S1-0 step8000 初值开始，数据流按协议成对冻结。主候选事前固定为 R16，不允许结果后换候选。

主评价为 Potsdam Val2 两张 tile (`3_11`,`5_10`) 的 NB pooled mIoU_fg5，仍属于开发证据，不是 Test6 / held4 / final。

## 2. 固定端点 RGB_U 结果

| 机制 | 8k 固定端点 | 16k 固定端点 | 16k-8k |
|---|---:|---:|---:|
| F | 83.8566 | 83.8579 | **+0.0013 pp** |
| H | 84.4411 | 84.5318 | **+0.0907 pp** |
| R | **84.8964** | 84.8804 | **-0.0160 pp** |

16k 固定横向比较：

- `R16 - F16 = +1.0225 pp`
- `R16 - H16 = +0.3486 pp`
- `H16 - F16 = +0.6739 pp`

8k 固定横向比较：

- `R8 - F8 = +1.0398 pp`
- `R8 - H8 = +0.4553 pp`
- `H8 - F8 = +0.5845 pp`

这些数字说明机制排序总体为 **R > H > F**，但把训练从 8k 延长到 16k 并没有形成稳定预算收益。

## 3. 当前独立8k/16k方案未建立预算收益

协议的预算信号要求 F 和 R 的 `16k-8k` 都至少 +0.30 pp，且两张 tile 都为正。

实际 pooled 结果已经在第一层就失败：

- F：+0.0013 pp
- R：-0.0160 pp
- H：+0.0907 pp（即使 H 不是该预算 gate 的必要条件，也同样很小）

所以不能再解释为“8k 太短，只要继续训练到 16k 就会明显提高”。特别是 R8 与 R16 几乎等价，R8 还略高 0.016 pp。

这对后续规划很重要：**不要再把 GPU 预算用于盲目延长步数。**

## 4. R 相对 H/F 的含义

R16 相对 F16 的 pooled RGB_U 提升 +1.0225 pp，说明允许 RGB 专家更深层参与适应确实与更好的已知 RGB 局部缺失开发性能相关。

R16 相对 H16 只有 +0.3486 pp，刚超过事前 +0.30 pp 的 pooled 效应量线；两tile分别+0.328642/+0.356335pp，原screen该配对passed=True。整轮最终 `PAIRED_SCREEN=False` 来自六E相对R0的五项底线失败；不能把总gate失败误写成该配对失败。R/H容量不同，因此尚不能将局部增量归为纯编码机制或独立泛化。

更稳妥的机制表述是：

> **完整 RGB 接口适应已经贡献了大部分收益；继续开放最后 4 个 encoder block 可能有小幅增益，但完整预注册验收没有通过。**

这也符合协议预先规定的保守解释：若 R-H 未形成完整稳定增量，则优先保留更简单的 H 式接口作为机制线索，而不是宣称深层 encoder 适应已成立。

## 5. R16 技术保护不是问题

R16 的训练/评价保护文件显示：冻结状态初始与最终 digest 完全一致，`native_outside_support_equal=true`。它没有偷偷修改冻结基座或改变 support 外输出。

R16 的 secondary selection 选择 16k，RGB_U mIoU_fg5 = **84.8804**；其中 clean、RGB missing、DSM missing、DSM_U、worst protected tile 五项选择保护检查全部为 true。

因此本轮 `PAIRED_SCREEN=False` 不应被解释成“R16 技术实现坏了”。它表示**完整科学 screen 中至少有冻结条件未满足**；仓库总判定必须保持 False，不能用某一个局部通过项覆盖总 gate。

## 6. 验证选点与固定预算不要混用

F16 的 validation-selected checkpoint 实际是 12k，RGB_U = **83.9432**，比其固定 16k 端点约高 0.0853 pp。H16/R16 的 secondary selection 则选择 16k。

这进一步说明不同机制的最优开发步数不一致。但协议明确规定主机制/预算结论使用 fixed endpoint；validation-selected checkpoint 只能作为次要结果，不能拿 F12 与 R16 混成“16k 主比较”。

所以结果表必须同时保留：

- **fixed endpoint**：回答机制 × 预算的预注册问题；
- **selected checkpoint**：作为开发集选点的次要工程参考。

## 7. 当前科学结论

1. **预算线关闭**：8k→16k 没有一致收益，继续盲目加训练步数价值低。
2. **适应位置有信号**：R/H 均明显优于 F，说明只调融合解码器不足，RGB 专家接口参与适应更重要。
3. **深层尾块独立增量证据偏弱**：R-H 只有约 +0.35 pp，而且完整 paired screen 为 False；不宜把“最后 4 block”单独包装为已验证贡献。
4. **R16 技术保护正常**：冻结状态与 support 外输出保护通过，负判定属于科学 gate，而非实现损坏。
5. **不能自动扩实验**：不加 seed、不扫步数、不扫尾块数量、不后验换候选、不启用 Test6/final。

## 8. 与 Structured Failure v0.1 合并后的含义

Structured Failure v0.1 随后得到：RGB-only 对结构化 RGB 缺失高度敏感，而 S1 显著削弱这种损伤；但 naive `M000_context` 路由明显恶化。

两轮合起来，下一研究问题已经不应继续围绕“训练更久”“再开放更多 encoder block”或“证明 S1 有结构位置故障”。更有价值的问题是：

> **在 RGB / DSM 质量变化时，如何显式估计模态可靠性，并控制融合/路由，使模型只在辅助模态真正可靠时利用它，同时保留 clean 双模态收益？**

这条路线同时解释了：

- 为什么双模态能显著缓解 RGB 缺失；
- 为什么错误/naive context 路由会放大损伤；
- 为什么单纯增加训练预算不能继续带来收益。

## 9. 限制

- 单 seed42、Val2 两张 tile；不是独立地区或最终测试。
- F/H/R 可训练容量不同，R-H 不能完全排除容量因素。
- 8k 与 16k 的 LR schedule 也随预算变化，因此不是“纯更新次数”因果干预。
- `PAIRED_SCREEN=False` 是权威总判定；任何局部 pooled 数值都不能覆盖它。

当前决策：**Post-T paired v2 科学收口，不自动续跑。下一阶段进入新的 reliability/routing 设计评审。**
