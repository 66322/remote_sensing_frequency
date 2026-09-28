# D20 Vaihingen 同域开发：P0/P1/P2 seed42 正式匹配队列

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: plan/run preparation
- Origin Date: 2026-09-28
- Verification Status: IMPLEMENTED_LOCAL_CHECKS_ONLY; server formal CUDA pending
- Version Label: v1

## 依据与证据等级

三组一步短流程在服务器全部通过，归档`8401bcd`。训练区 P2 20步测量于
2026-09-28 16:23:08 +08:00完成并归档`abe10e4`：12块加载11.26秒，
去除3步预热后每步中位0.222秒、最大0.233秒；GPU显存峰值0.36 GiB，
进程内存峰值2.258 GiB。8,000步 P2 **训练部分**中位投影约0.49小时，
不含数据哈希、全图评价、队列等待和其他两组。20步短样本的投影有不确定性。

Vaihingen 旧训练区和这17块开发候选均属同一镶嵌图，有历史方法开发曝光。
本轮只供同域开发，不能称作未见地域或外部最终复验。US3D来源/许可与
独立地域最终确认保持单独未完成状态。

## 已冻结的执行与评价

- 数据：旧训练12块和已审计开发17块；历史旧评估4块排除。训练标签来自
  `gts_for_participants`，开发标签来自`gts_complete_full`。TOP为近红外/红/绿，
  按原TIFF顺序除以255，沿用冻结DINO三通道统计；DSM逐块minmax。不能称TOP为RGB。
- P0光学单流，P1光学+由光学生成的灰度，P2光学+DSM。三组同seed42、
  DINOv2 ViT-S/14冻结编码器、相同512裁块、microbatch2、累积8、每步有效16，
  各8,000步，原D18优化器/学习率/质量扰动概率，固定最后一步权重。不看开发结果
  选择checkpoint。GPU0并行P0、GPU1并行P1；二者成功后P2接续GPU0。
- 开发评价对17块完整FullGT逐像素评价；512裁块、stride512、推理batch4。
  条件为clean、4种光学质量、4种辅助质量/缺失和2种诊断，共11项。
  三组相同变换定义。每块/条件记录整数混淆矩阵、逐类和汇总mIoU，原始预测
  留在服务器；GitHub只归档摘要和配对整数计数。FullGT包含类别边界，
  不能与原Potsdam NoBoundary绝对分数直接比较。
- 三个计分家族是clean、4种光学质量、2种辅助质量；每家族先平均条件mIoU，
  再三家族等权平均。完整缺失、局部缺失、错位和固定光学对比度单列，
  不纳入综合门槛。
- P2相对P0/P1中综合较强者至少+0.2pp；相对P0的clean不低于−0.1pp，
  各家族不低于−0.3pp；17块各自clean不低于−0.1pp、各家族不低于−0.3pp。
  这是冻结的开发资源门槛，空间相关像素不能当作独立样本作显著性推断。
  若未通过，如实归档，不自动补seed17、不改变阈值重筛。

配置：`configs/rebuild_v1/d20_vaihingen_formal_seed42_20260928.json`。
队列预先计算29块的全部87个输入文件SHA256并冻结清单，训练和评价绑定清单、
代码、DINO权重与检查点哈希。训练每500步原子保存，可在同一配置/数据不变时恢复；
每100步写剩余训练时间投影，评价每块/条件保存进度。任何一组失败停止后续判断。

## 服务器运行与观察

在项目根目录：

```bash
cd /home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
conda activate remote_sensing
git pull --ff-only origin rebuild-v1-protocol-20260915
mkdir -p records/rebuild_v1_d20_vaihingen_seed42_20260928/queue
nohup bash scripts/run_rebuild_v1_d20_vaihingen_seed42_queue.sh \
  > records/rebuild_v1_d20_vaihingen_seed42_20260928/queue/launcher.log 2>&1 &
```

进度：

```bash
tail -n 20 records/rebuild_v1_d20_vaihingen_seed42_20260928/status.tsv
tail -n 3 records/rebuild_v1_d20_vaihingen_seed42_20260928/queue/P0_train.log
cat runs/rebuild_v1/D20_VAI_P0_seed42_8000_20260928/progress.json
```

终点检查`QUEUE COMPLETE 0`、三组训练/评价摘要及`decision.json`。
原始结果在`runs/rebuild_v1/D20_VAI_<arm>_seed42_8000_20260928/`
和`records/rebuild_v1_d20_vaihingen_seed42_20260928/`；
精简归档在`records/rebuild_v1_d20_vaihingen_seed42_compact_20260928/`。
权重和逐像素预测仅留服务器。队列不自动追加seed17或独立final。
