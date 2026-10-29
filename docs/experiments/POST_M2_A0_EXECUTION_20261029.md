# M2后A0首批实验：冻结教师能力探针与双H100资源合同（2026-10-29）

**状态：CODE_PREPARED_LOCAL_CHECKED；SERVER_NOT_PREFLIGHTED；NO_NEW_SCIENTIFIC_RESULT。** 本文件给出已写好的首批执行入口和预先冻结的判断规则。旧M2的存储清理仍按原授权继续；A0不引用旧M2的训练端点、推理缓存或大权重。

## 要回答的问题与对照

先只问“同一Potsdam视野内，冻结DINOv3 ViT-S/16 LVD网络的稠密表示，用同样浅层读出，是否比冻结DINOv2 ViT-S/14 LVD网络多提供任务可读出的信息”。两者约为21M量级，但patch尺寸、预训练包与架构仍不同，因此正结果只能称“该表示包在本读出下更有用”，不能归因世界常识、几何机制或纯模型代际。

F0由旧M2 `folds.json`固定：8个原训练tile中用`inner_pairs[0]`的2个作训练内校准，剩6个拟合读出；F0外层4个tile仅在校准通过后评价，属于已使用的**开发折**。每块训练裁剪与外层评价都排除512像素边带；没有新开封存测试。两教师同seed42、同确定性裁剪顺序、相同512输入、只训练384→6的1×1读出、有效batch16、各2000更新。公开预训练与输入归一化必须在启动前固定。标签为NoBoundary，六类顺序白/蓝/青/绿/黄/红，主fg5为**前五类**，黑色忽略。

本入口仅完成A0“同视野像素读出”。原研究计划中的更大视野、周边打乱、关系探针、类别/边界分层仍属A0后续诊断，不能把本轮单一分数误写成完整能力审计；要实施时另立冻结合同。A1的S0–S3也未自动启动。

## 先决条件

1. 服务器ROOT为`/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro`，旧M2运行目录中的小型`plan.json`、`folds.json`、`pretrained.json`仍在；共享RGB和NoBoundary原始数据、公开DINOv2原始权重/源码仍在。A0只盘点文件名和大小，不对数据与模型例行重新哈希。
2. DINOv3源码固定在[官方仓库](https://github.com/facebookresearch/dinov3)的`6876159a11b4df116f30f667f8c9888617df0751`；ViT-S/16 LVD权重由用户按[官方模型页](https://huggingface.co/facebook/dinov3-vits16-pretrain-lvd1689m)条款取得，并自行放在服务器。脚本不自动绕过授权或下载模型。这里用Web/LVD权重，不称卫星预训练。
3. 新A0独立Python环境：Python≥3.10、PyTorch≥2.7.1、CUDA可用，实际需有NumPy和Pillow。旧`remote_sensing`环境是Python3.9/Torch2.2.2，不能直接承诺兼容。先记录GPU驱动/CUDA，再按PyTorch官方对应安装方案建环境；不要在M2原环境中盲升。正式运行前两教师都必须通过实际权重加载与512前向smoke。
4. GitHub分支`rebuild-v1-protocol-20260915`为两台电脑的代码/配置/结果/结论共同权威。执行时用当时分支HEAD固定下载脚本并写入`POST_M2_CODE_COMMIT`；若分支后续变化，已经启动的本轮不随之切换代码。

## 服务器执行顺序

在服务器新环境内运行以下准备命令。先把`POST_M2_DINO3_REPO`指向已检出上述官方commit的本地源码目录、`POST_M2_DINO3_WEIGHTS`指向按条款取得的权重实际文件。**没有权重或新环境时止于inventory，不启动耗时任务。**

```bash
ROOT=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
BRANCH=rebuild-v1-protocol-20260915
COMMIT=$(git ls-remote https://github.com/66322/remote_sensing_frequency.git "refs/heads/$BRANCH" | cut -f1)
test ${#COMMIT} -eq 40 || exit 1
SCRIPT="$ROOT/records/post_m2_a0_capability_20261029/post_m2_a0.py"
mkdir -p "$(dirname "$SCRIPT")"
curl -fL "https://raw.githubusercontent.com/66322/remote_sensing_frequency/$COMMIT/scripts/post_m2_a0.py" -o "$SCRIPT.download" || exit 1
mv "$SCRIPT.download" "$SCRIPT"
export POST_M2_CODE_COMMIT="$COMMIT"
export POST_M2_DINO3_REPO="/你的服务器上的官方dinov3源码目录"
export POST_M2_DINO3_WEIGHTS="/你的服务器上的官方vits16权重文件"
python -u -B "$SCRIPT" inventory
```

`inventory`打印数据、模型文件、物理GPU、运行中程序、cgroup可用CPU/内存；缺文件立即停。随后每一行是**独立关卡**，上一关的`PAIR_PHASE_COMPLETE`与两个子日志正常结束后才运行下一行。长任务可将单行套在`nohup ... > 独立日志 2>&1 < /dev/null &`中，保留PID和日志；不要把所有行交给旧M2控制器或一个无条件串行shell。

```bash
python -u -B "$SCRIPT" pair --phase smoke
python -u -B "$SCRIPT" pair --phase profile
python -u -B "$SCRIPT" pair --phase train
python -u -B "$SCRIPT" pair --phase evaluate --split calibration
python -u -B "$SCRIPT" screen
# 只有screen为READY_FOR_OUTER_DEVELOPMENT_EVALUATION时执行：
python -u -B "$SCRIPT" pair --phase evaluate --split outer
python -u -B "$SCRIPT" status
```

一个子作业失败，父进程终止另一子作业、写失败日志，后继关卡不启动；不自动重试。部分完成或同名输出已存在时也拒绝重跑，先审计。每个模型只保存约几KB的读出头与小JSON、日志，不保存全图logit或旧式大量中间推理。运行目录只需上传小证据；权重头仍是再现本轮需要的最小端点，不能在结论未固化前清除。

## 资源与速度决策

| 阶段 | 两张H100安排 | 计算/空间账本 |
|---|---|---|
| inventory/smoke | 两物理卡0/1各至少40GiB空闲且无现有计算进程；各子进程只可见一张卡。smoke加载真实权重并做真实512前向。 | 无任务训练；模型包和环境仍待服务器验证。 |
| profile | 两模型各自测试DataLoader 0/4/8 worker及microbatch16/8/4的可用组合；每组合32个**丢弃的优化更新**。测数据等待和GPU计算；评价测8/16/32窗口batch、各64窗口及一整张图，记录CPU打包、H2D、教师、读出/放大、拼接、最终argmax的耗时。 | 最多320个额外profile更新，**不计为A0正式2000步，也不算科学结果**；两次整图和若干部分窗口明确计时。 |
| formal train | 一卡一模型、各2000更新；每100步记录实际吞吐/峰值显存。若第500步实耗时超过对应profile中位步耗时估计的2.5倍，停并查共享资源。 | 合计4000正式更新；同一有效batch16和训练样本顺序。GPU时间由实际回执填写，不按M2旧速度估算。 |
| calibration / outer | 每模型2块校准tile；校准通过再每模型4块外层开发tile。整图滑窗512/stride256，只统计整数混淆矩阵与逐tile/池化指标。单tile同窗口数耗时超过profile的2.5倍即停。 | 最多12次正式全tile评价，另加profile的2次。一次前向同时形成所有基本指标，不按指标重跑。 |

并行门槛：cgroup有效CPU≥12核且剩余CPU内存≥12GiB，否则双模型顺序执行；即使并行，每GPU的loader上限为`min(8, floor(有效核数/2)-2)`，数值线程各1。当前输入按6000×6000、RGB uint8+NoBoundary uint8估计：六个拟合tile约0.86GB/进程，两进程约1.73GB，尚不含PIL、worker、模型和缓存；故留12GiB余量。全图GPU累计分数+覆盖约1.0GB/tile，模型中间激活须以实际profile为准。每卡正式启动前要有40GiB空闲，子进程再查至少20GiB实际可用。训练与评价分别实测，不用历史DShuffle/DEntropy的每步耗时套算。

实际wall time预算在profile后再填写：两模型并行时训练≈两者`2000×每步实测`的较大值，顺序时≈两者之和；评价按每模型`6×整图实测`估算，若校准不通过只计前2块。第100/200步实际时间用于修正profile估计。资源竞争造成异常减速时停队，先检查CPU quota、worker数、PIL解码/拷贝、GPU占用和拼接段计时，再决定是否修改共同合同；不能让一个模型改用更少更新来赶时间。

## 冻结筛选与后续开关

只有两模型训练轨迹总体下降、两者训练内校准池化fg5 mIoU都至少50%、DINOv3−DINOv2池化≥+0.3pp且两个校准tile最差差值≥−0.2pp，才进入F0外层开发评价。这些阈值只作低成本筛选，**不是显著性或投稿门槛**；2000步读出未学会时记`INVALID_PROBE`，不能将其当作大模型无能力的证据。

即便A0阳性，A1也不直接把DINOv3接进旧M2 DF配方：先冻结S0强RGB普通上下文、S1普通RGB–DSM、S2 RGB+外部教师、S3 RGB–DSM+外部教师的四臂统一接口与同等训练容量；先性能预检100–200步/整图评价，确认没有四个OOF教师重复前向、分组288次小张量调用及每步GPU→CPU回读。四臂各8k/seed42、同输入顺序、同初始化协议；教师开销和四臂各自GPU时单列。主压力与保护指标沿[总计划](POST_M2_CAPABILITY_PRIOR_PLAN_20261029.md)预注册：S3相对S1受影响ROI至少+0.5pp，并保护clean及健康区域；正向后才做S4普通教师和S5空间错配两控制，各8k，旧M2剩余端点不作为免费教师。A1/A2暂为有条件的下一批，未生成执行队列，不能从本文件直接启动。

GitHub回传需至少包括两份smoke/profile、每模型训练完成/轨迹、校准/外层结果（若执行）、screen、pair日志状态以及简短结论；上传后检查这些关键文件可读即可，不例行逐文件重新哈希。若服务器尚无正式运行，GitHub状态必须保留`NO_NEW_SCIENTIFIC_RESULT`。外层开发结果和最终封存地区分开，论文创新判断须待强控制与独立地区。
