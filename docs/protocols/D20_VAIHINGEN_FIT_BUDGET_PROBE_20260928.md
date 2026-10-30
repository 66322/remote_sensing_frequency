# D20 Vaihingen 正式预算前的训练区吞吐测量

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: plan/run preparation
- Origin Date: 2026-09-28
- Verification Status: IMPLEMENTED_LOCAL_CHECKS_ONLY; server CUDA timing pending
- Version Label: v1

三组一步短流程已于服务器通过，精简证据归档 `8401bcd`。它验证了训练、保存、
重载和评估能执行，但约4–6秒的单组运行时间包含初始化、数据加载及哈希计算，
不能用来估算正式8,000步预算。单步 mIoU 也不作为方法比较。

本测量只在 GPU0 上运行 P2，读取旧训练区12块的 TOP、DSM 和训练标签，
**不读取17块开发标签、不评估开发区、不读取 Potsdam Test6、不保存模型权重**。
TOP仍按近红外、红、绿原顺序输入，DSM每块独立 minmax。按原 D18 路径
使用512裁块、microbatch 2、梯度累积8（每步16个裁块）、clean 和原扰动
两条分支，连续20个优化步骤；丢弃头3步，从其余17步取中位数，并记录逐步耗时、
数据加载耗时和显存峰值。此阶段只用于可行性和资源估算，不用训练损失选模。

服务器在项目根目录执行：

```bash
cd /home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
conda activate remote_sensing
git pull --ff-only origin rebuild-v1-protocol-20260915
bash scripts/run_rebuild_v1_d20_vaihingen_fit_budget_probe.sh
tail -n 10 records/rebuild_v1_d20_vaihingen_fit_budget_probe_20260928/status.tsv
```

完整日志留在 `records/rebuild_v1_d20_vaihingen_fit_budget_probe_20260928/`，
`records/rebuild_v1_d20_vaihingen_fit_budget_probe_compact_20260928/`
自动收集摘要、状态和代码配置哈希供跨电脑交接。正式8,000步的时间投影只计算
P2训练步骤，不包含初始化、12块加载、全图评价和队列等待；不能当作总结束时间。

测量通过后才根据吞吐、显存与训练区切分制定 P0/P1/P2 seed42 的统一正式预算、
完整开发条件评价及门槛。US3D 传输/使用条件仍独立处理；Vaihingen 不升级为
跨地域最终确认来源。
