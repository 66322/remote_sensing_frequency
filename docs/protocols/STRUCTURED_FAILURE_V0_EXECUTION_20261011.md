# Structured Failure v0.1：当前配对实验之后的零训练后继

设计日期2026-10-11，执行准备完成日期2026-10-12（Asia/Shanghai）。状态READY_NOT_REGISTERED_SERVER_RUNTIME_UNVERIFIED。用户明确要求“可以将下一阶段的实验排队，安排在后面”。本版本落实核心Phase 1A，允许当前队列技术完成并退出后自动接续；不再要求助手先完成科学结果解读才启动固定旧模型诊断。科学结论仍待两轮原件独立验收，不用前轮分数选择模型、改变mask或自动开训练。

前序唯一目录research_post_t_paired_v2_20261011T182543_3880702、执行44e4df5afbaeb603e6441e7ef14ff09f228bc027；最后已知查询仍2026-10-11T23:34:24.796568+08:00，非实时。原队列、参数、阶段检查不修改。没有新服务器PID或注册回报。

## 范围与固定工作量

Potsdam Val2仅3_11/5_10；native512/stride256、batch8、FP32/TF32，原RGB [0,1]置0后进入原专家归一化，DSM保持原输入。四系统：D25 P6 RGB-only、S1-0、同S1-0权重M000_masked(A1B1C0)、M000_context(A1B0C0)。后两者原生拼接S1-0支持外预测；并非重新训练的S1-3对比。所有checkpoint、输入配置和继承代码绑定来自现有配对执行快照。

四mask族pixel/random/gradient/matched，20固定随机实现，两tile。640缺失逻辑输出case＋8clean逻辑基准；另有6个已有rgb_U同源端点复现检查（S1/M000masked/M000context×2tile），总654逻辑输出。优化器调用0、训练0、训练seed不增加。后继共42队列任务：两个clean/端点任务＋40个tile×mask实现任务；每个正式任务包含四族×四系统共16个输出。Phase 1B、GT边界、尺寸扫描、Vaihingen、DSM反向族与新训练均不派发。

## 掩码可行性与冻结算法

真实6000×6000图域，每mask精确9,000,000像素。block族均549个128方块＋一个72方块，136网格间距、每实现0—7随机相位，不重叠/不裁边、至少8像素空隙。三block族共用候选格和72块位置；仅primitive组成受控，完整空间布局/距离不完全一致，不能称纯位置因果干预。

DSM原归一化输入，Sobel3 reflect梯度幅值，逐tile90百分位严格大于；块内高梯度比例评分。结构组使用exp(2×clip(z,-3,3))固定权重无放回选549块；随机块均匀无放回。matched从独立均匀初始化进行最多50000次随机交换，只接受语义误差下降的交换。NB六类比例最大差1pp、Car差0.2pp、NB覆盖差1pp；所有比例实际分母记录。matched使用GT，仅为标签辅助诊断，模型和路由不读取GT。须每对gradient高梯度占比大于matched，否则HOLD，不能在结果后放宽。

PCG64随机流由SHA256(协议/tile/实现ID/role)确定，numpy/scipy版本入manifest。20实现全部事前生成，检查每族不同canonical SHA；CPU可行性不通过则HOLD、0正式推理、不自动换q、匹配容差或seed。真实mask匹配尚未验证，CPU合成通过不等于真实mask可行。保存全图packbits压缩数组、canonical与文件SHA、primitive位置、类别计数、边界覆盖、匹配误差及梯度对比。生成器在前序结束后才读取影像，登记等待期间不扫描数据。

## 指标、原件和判定

保存Full/NB、missing/observed/healthy/edge/all范围的同模型clean与missing int64 6×6矩阵；clean→missing和同missing输入S1→candidate两套逐类伤害/救回计数与分母，健康区域为空记None。保留每幅预测压缩数组与SHA，支持离线复算；GPU峰值和native推理秒单列。额外记录每窗口4/8/16尺度全有效支持计数、整窗缺失数和缺失像素到可见RGB距离分布；这些是掩码推导的支持诊断，不是学得激活机制证明。

每mask ID先池化两tile矩阵再算NB fg5，主PE固定S1-0：D(gradient)−D(matched)，D为相同缺失位置上clean减missing的指标百分点损伤。CE=D(random)−D(pixel)，允许负值；PE_total另报；CB为同权重context减masked，并报告placement/geometry交互及扣除clean差异后的damage reduction。20个PE的均值为主，不改用跨seed非线性池化结果。

开发线索门槛：主PE≥0.30pp、两tile平均PE均正，且no-Car PE≥0.15pp或4/5类平均差正。主PE<0.15且完整有效为NO_SUPPORT_THIS_PROTOCOL；其他/缺分母为INCONCLUSIVE。条件于两tile与固定模型，5000次mask ID成组bootstrap；不将像素当独立重复，不报告未建立交换性假设的精确p值，不自动20→40。原F/H/R主候选R16和保护/科学gate不变。

## 等待、资源与中止

登记只复制绑定的轻量执行代码、运行合成CPU检查、启动等待控制器；不申请CUDA。每30秒读取前序状态；必须PAIRED_COMPLETE_AWAITING_REVIEW、八任务COMPLETE、前序controller和worker退出、controller锁释放，然后取得共享post_ab_successor.lock，核验前序原件绑定与screen散列。前序停止/失败/绑定错误立即HOLD，不绕过。

之后单进程CPU生成160个mask（最多4h），两个GPU完成clean/旧端点检查，再共享调度40个正式任务。每卡最多一worker，任务累计活跃时间上限8h；没有全队24h截止。运行优先恢复用户主动释放的同一任务，复用已完整绑定的case；中断的case重新推理，训练更新始终0。技术失败不重试，停止新派发并请求其他worker退出，保留现场。

物理GPU0/1均可用，沿用H100设备UUID检查。原配对控制文件与后继控制文件中最新明确release/rejoin请求生效；释放的卡不会因切换队列重新占用。新管理入口在原配对仍活动时同时写两队列控制请求，因此可用一条命令释放当前阶段及后继的同一张卡。必须等待对应worker退出并确认nvidia-smi后再使用卡；rejoin仅开放未来派发，不恢复技术失败。

GPU/影像/大文件本体仅服务器，全部记录、执行快照、cache、临时文件位于/home/jovyan/zzx对应后继目录。磁盘主要为压缩mask和预测，未实测压缩率；654张uint8原预测约23.5GB，mask uint8原始表示5.76GB，实际packbits/npz应更小但不作保证。每worker沿原native评价分配整tile logits，CPU内存与GPU显存首正式任务实测；OOM即HOLD，不自动缩batch。完整时间需首批实测，不能把训练step速度用于诊断ETA。

## 一次登记

使用对话提供的完整发布SHA设置COMMIT。在用户服务器终端执行：

```bash
(
set -e
ROOT=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
PY=/home/jovyan/miniconda3/envs/d18_dino/bin/python
cd "$ROOT"
git fetch origin rebuild-v1-protocol-20260915
# COMMIT使用本次对话给出的完整发布SHA，不复用旧44e4df5a。
B="$ROOT/records/bootstrap_structured_v0_$(date +%Y%m%dT%H%M%S)_$$"
mkdir -p "$B"
git show "$COMMIT:scripts/enqueue_structured_v0.py" > "$B/enqueue.py"
"$PY" -u -B "$B/enqueue.py" --root "$ROOT" --commit "$COMMIT"
)
```

STRUCTURED_QUEUE_REGISTERED是唯一新登记；重复执行只输出STRUCTURED_ALREADY_REGISTERED，不再启动。没有前序完成时应WAITING_PREDECESSOR。注册目录若不完整则保留HOLD，不删除重建。

## 查询、释放与上传

```bash
ROOT=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
PY=/home/jovyan/miniconda3/envs/d18_dino/bin/python
S=$("$PY" -B -c 'from pathlib import Path; p=list(Path("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records").glob("research_structured_failure_v0_*/plan.json")); assert len(p)==1,p; print(p[0].parent)')
"$PY" -B "$S/code/scripts/manage_structured_v0.py" --directory "$S" --action status
# 需要使用GPU0时才执行；GPU1对应改为1。
"$PY" -B "$S/code/scripts/manage_structured_v0.py" --directory "$S" --action release --gpu 0
# 使用结束后显式重新开放。
"$PY" -B "$S/code/scripts/manage_structured_v0.py" --directory "$S" --action rejoin --gpu 0
```

上述三种动作分别按需要执行，不要整段连续执行release和rejoin。原队列完成后仍按其原上传器上传F/H/R原件；新队列不自动推送GitHub。后继达到STRUCTURED_COMPLETE_AWAITING_REVIEW且进程退出后：

```bash
"$PY" -u -B "$S/code/scripts/upload_structured_v0.py" --root "$ROOT" --directory "$S"
```

轻量原件含整数计数/配置/代码/日志/manifest及服务器数组索引，JSON可无损编码；数组与权重不上传普通Git。上传结果回传后独立回读SHA并复算。任何新训练、Phase1B或样本增加均不由此控制器触发。
