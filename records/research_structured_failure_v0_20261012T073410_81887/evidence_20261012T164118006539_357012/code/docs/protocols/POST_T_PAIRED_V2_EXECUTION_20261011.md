# Post-T v2执行说明：双卡共享队列，可释放任一卡

状态：READY_NOT_REGISTERED_GPU_RUNTIME_UNVERIFIED。2026-10-11用户要求落实六核心实验，并明确GPU0＋GPU1、预留一天以上且未完成继续、需要一张卡时保存退出并将未完成部分转另一卡排队。本文件覆盖先前只GPU0的资源规则，科学协议不变。尚无新服务器目录、PID或运行回报；最后旧队列查询仍2026-10-11T13:48:26.474610+08:00，26/26已完成退出。

## 固定工作量和执行链

CONTENT_PRE（24case/0训练）→[H8,F8,R8]→[R16,H16,F16]→CONTENT_POST（24case/0训练）。共8个队列任务，其中6项新训练共72000优化器调用；每个预算阶段内按列出顺序派发到可用卡，每张卡最多1worker，最多2worker。内容批次内部串行，阶段切换需前阶段完整技术验收。8k不按成绩筛掉16k；科学负结果照常完整报告。

F只私有融合解码，H加入私有RGB投影net.rgb及decoder[:-1]，R再加末4编码块；最终分类器与原基座/DSM冻结。统一S1-0初值，6个独立新优化器，同预算和8/16k公共前缀真实CPU batch逐步散列一致。固定预算终点为主；validation选择的保护合格checkpoint单列次要结果。主候选R16、全部旧科学门槛见[细则](POST_T_PAIRED_ADAPTATION_BUDGET_20261011.md)。

执行源码：enqueue复制已验Post-T完整manifest并从本次提交覆盖新增入口；prepare查33项已验收绑定、复用掩码/参考、核对六份完整配置；controller先前测再双卡训练，最终content与原计数汇总；upload只上传轻量证据。原26项不重复登记、训练或再做整轮历史分析。

代码已实现，17项本地CPU合成检查通过：初始F/H/R前向等价、真实Expert hook梯度、最终分类器冻结、零支持反传、LR分组/日程、DSM干预隔离、batch配对/续写、CPU优化器/RNG续训等价、两卡派发、单卡release后另一卡续跑、失败不重试、前序释放门禁、原计数/端点续评及无损上传。真实H100/实权重/跨卡CUDA逐位一致尚未验证，不能把CPU通过当正式实验。服务器登记会在绑定Torch2.2.2+cu121环境重做CPU检查；首正式worker校准真实显存/步速，C干预和step0必须复现旧端点。

## 资源、退出和停止

按一天以上预留，无全队24h截止。固定任务完成即停，不为凑时长新增作业。先前单卡30—60h仅未实测粗排；两卡不等于墙钟减半，阶段依赖、共享I/O、保存和用户占卡影响时长，首批正式进度后再估。

release仅写该物理GPU控制标志。对应worker在完整optimizer step边界/推理进度检查点检测，原子保存模型、优化器、global_step、随机状态与计数后退出；进程退出才释放显存。controller将该同一任务标记PAUSED_USER，优先排到另一张启用且空闲的卡，带--resume恢复同一输出目录；其余待办继续排队，不从step0重训。推理仅复用完整case，未完成case重新推理，0新优化器更新。不会SIGSTOP持有显存，也不会因为release中止另一卡。已释放卡即使空闲也不派新任务，直到显式rejoin。

释放不是瞬时操作：正在加载、计算、保存或某段无轮询的CPU核验时要等它抵达安全点。先status确认对应worker LIVE=False，再nvidia-smi确认卡可用后使用。不要用kill -9代替release；技术崩溃不属于正常续跑，禁止隐式回滚ledger或自动重试。GPU迁移记录每个session的卡号/UUID/起始step；恢复检查plan/code/权重绑定、冻结状态和batch ledger年龄。跨卡CUDA数值一致须结合真实记录报告，不预先宣称逐位一致。

没有24h总截止，但每个任务累计活跃时间保护保留：8k训练＋评价12h、16k24h、每个内容批次4h；排队/停用等待不计。OOM、非有限loss/梯度、绑定/技术保护错误、超时即HOLD，保留现场，不自动改batch/精度、加seed或重跑失败配方；另一活动worker收到技术HOLD保存退出。controller自身异常需先检查已有worker，不重复启动控制器。

## 1. 一次登记并启动

在服务器终端执行；下列用fetch得到的该分支提交冻结代码，不切换/覆盖服务器工作树。若对话给了完整发布SHA，可把COMMIT的取值替换为该SHA。入口如发现本族已登记，只报告已有目录，不重复启动。

```bash
(
set -e
ROOT=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
PY=/home/jovyan/miniconda3/envs/d18_dino/bin/python
cd "$ROOT"
git fetch origin rebuild-v1-protocol-20260915
COMMIT=$(git rev-parse FETCH_HEAD)
B="$ROOT/records/bootstrap_post_t_paired_v2_$(date +%Y%m%dT%H%M%S)_$$"
mkdir -p "$B"
git show "$COMMIT:scripts/enqueue_post_t_paired_v2.py" > "$B/enqueue.py"
"$PY" -u -B "$B/enqueue.py" --root "$ROOT" --commit "$COMMIT"
)
```

预期报告PAIRED_QUEUE_REGISTERED、真实目录、controller PID、GPU=0,1、TRAININGS=6、NEW_STEPS=72000、CONTENT_CASES=48；之后应查询进度，登记成功不等于GPU已开始。源队列尚未释放/绑定不符/CPU失败会保留登记现场并HOLD，不自动创建第二套。

## 2. 设置查询与控制变量

新终端执行一次，自动选唯一已登记本族目录；如缺失或有多个则停止，不猜目录。

```bash
ROOT=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
PY=/home/jovyan/miniconda3/envs/d18_dino/bin/python
D=$("$PY" -B -c 'from pathlib import Path; p=sorted(Path("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records").glob("research_post_t_paired_v2_*/plan.json")); assert len(p)==1, p; print(p[0].parent)')
```

查询：

```bash
"$PY" -B "$D/code/scripts/manage_post_t_paired_v2.py" --directory "$D" --action status
nvidia-smi
tail -n 35 "$D"/nohup_*.log
```

## 3. 需要使用某张卡

释放GPU0（需要GPU1时把0改1），其他卡继续：

```bash
"$PY" -B "$D/code/scripts/manage_post_t_paired_v2.py" --directory "$D" --action release --gpu 0
```

稍后用status与nvidia-smi确认对应worker退出。请求回报RELEASE_REQUESTED_NOT_YET_CONFIRMED仅表示已发出释放要求；另卡忙时断点任务PAUSED_USER排队，属于正常状态。已完成任务保持COMPLETE。两个GPU都release则全部等待，无新训练。

用完后若希望该卡重新参加本轮：

```bash
"$PY" -B "$D/code/scripts/manage_post_t_paired_v2.py" --directory "$D" --action rejoin --gpu 0
```

rejoin使其参与后续派发，不打断另一卡；若controller已技术HOLD，它不会自动重启失败队列。

## 4. 全部完成后上传

status必须为PAIRED_COMPLETE_AWAITING_REVIEW，全部8项COMPLETE，controller/worker退出。上传器重新校验完成绑定和大文件SHA，只写轻量JSON/JSONL、配置、代码、日志及服务器大文件索引；权重、预测、影像留服务器。JSON/JSONL用无损gzip-base64信封，原字节和SHA可恢复。上传动作不启动训练。

```bash
"$PY" -u -B "$D/code/scripts/upload_post_t_paired_v2.py" --root "$ROOT" --directory "$D"
```

将PAIRED_GITHUB_COMMIT与PAIRED_GITHUB_RECORDS回传。助手回读清单与原字节、完成绑定、原计数、15对batch公共前缀、轨迹、六组固定对比、内容C端点/敏感性、保护与成本，再写研究决定；不凭screen布尔值预写成功，不自动追加训练。需要先看轻量体积可加--prepare-only，不推送。

所有服务器记录、执行快照、缓存、归档位于/home/jovyan/zzx相应实验目录；无SSH。Test6/held4/final关闭。主线及恢复旁支角色保持，不加seed、不自动扩DSM镜像或频域族。
