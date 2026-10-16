# Post-A/B条件队列执行协议（2026-10-04）

用户指令：“按规划进行队列排队吧”。该指令授权按候选池登记和接续；原阶段门槛与失败配方不变。计划来源：[8类候选池](POST_AB_FOLLOWUP_PLAN_20261004.md)。

## 实际排队范围

已实现一份条件预约队列，登记N1四组、N2六组、N3五组、N4四组、N5四组、N6三组，共26个训练任务ID。**当前只有N1四组可执行**。其余22项为RESERVED_PROTOCOL_PENDING，包含研究内容和触发依赖，没有伪装成可运行worker。E0为原汇总报告的只读提取；E1内容相关缺失评估尚待锁定条件与掩码规则，登记为RESERVED_CONDITION_PROTOCOL_PENDING。

原规划的后续机制仍有实现与协议细节需要结果支持。因此控制器在N1完成后写N1_COMPLETE_AWAITING_STAGE_PROTOCOL并退出，提交结果后再按原规划落地下一阶段。该暂停是科学分阶段安排和当前实现边界，不是要求用户重复授权。后续路线已获得“按规划排队”授权，应继续开发接续，不再重复询问资源或启动意愿。

原C2双侧gate失败，N6三项自动SKIPPED_GATE。N2按N1筛选固定基座：N1-3通过全部门槛则选N1-3；否则选预定普通适应基座N1-2，不挑事后最高分。N4需暴露失衡证据且不重复D8，N5需E1内容缺失缺口，N3需匹配区域划分及D12差异。F不启动；不重训A/B/C、不加种子。

## N1四组冻结实现

| ID | GPU | 特征入口 | 专家适应 |
|---|---:|---|---|
| N1-0 | 0 | 末端分类器前特征 | 冻结 |
| N1-1 | 1 | 编码器block索引5/8/11，三种投影尺度 | 冻结 |
| N1-2 | 0 | 末端分类器前特征 | 两侧last4与heads |
| N1-3 | 1 | 与N1-1相同入口 | 与N1-2相同适应范围 |

两卡第一波N1-0/1，第二波各卡释放后N1-2/3。原DINO和DSM编码器均12块，接口不同显式取tensor/tuple。DINO各层token空间网格相同，**不是原生多尺度DINO**：去除非patch tokens，恢复patch网格后投影到输入stride4/8/16；DSM还原自己的方形token网格。称为“多深度、三种投影尺度信息入口”，不声称早期跨注意力已实现。

全部组都用相同固定通道分组到32宽、每尺度32→32投影、96→128汇合、同一512→128→6分类头。末端对照也采用相同三尺度投影，匹配learned capacity；固定通道压缩本身是本轮信息瓶颈/外推边界，报告时保留。

部分解冻严格调用原Expert.configure(True)：RGB encoder最后4块、rgb投影和decoder；DSM transformer.encoder.layer最后4块、decoder、segmentation_head。其他参数冻结，BN统计保持eval。encoder学习率继承已冻结plan的2e-5，heads2e-4；学习率调度、AdamW配置均继承。两侧解冻实际名单保存model_capacity.json，不仅写模块名。

每update为16张物理batch的clean和aug两个view联合loss，非梯度累积：
每view 0.5×fusion CE + 0.125×(RGB own CE + DSM own CE)，valid像素归一化。冻结组own CE常数项不改变梯度，所有格保持同一目标定义。所有组从同一已绑定P6/D15专家checkpoint重新初始化自身匹配头，不加载事后最佳A/B头。

known missing像素严格回退该组自己的可得模态logits；adapted own不是冻结锚点。科学joint计数和fixed_*指标始终另用原P6/D15冻结锚点，避免把适应后的参考变化当成保护。masked RGB/DSM数据在forward入口清零，无标签、退化ID或质量分数进入forward。

## 预算、门槛与记录

Potsdam fit12/Val2 3_11/5_10；seed42、8000更新、batch16无累积；native512/stride256/NoBoundary fg5。4000/8000按clean完整/RGB-only/DSM-only三状态平均选模，平分早选，fixed8000共同年龄报告。总首批32000更新；其余候选登记不等于承诺208000全部执行。

固定主要候选N1-3，相对N1-1和N1-2分别：
- S_available≥+0.3pp；
- clean、dsm_missing、rgb_missing各自≥−0.1pp；
- primary最差condition×tile≥−0.2pp；
- 两tile按同family等权的增量均>0；
- fixed8000综合增量同号。

另报告冻结多尺度效应、末端适应效应和差分交互、双侧harm/retention。门槛为单seed开发筛选，不是统计确认；像素、窗口和退化条件不是独立重复。新方案未要求“保护”成立，不用这些安全下限替代原A/B严格harm门槛。

CPU本地检查：合计8项，覆盖容量匹配/梯度流、禁用输入干预与精确回退、未释放原队列不能接管、失败暂停、22项预约永不被误派发、固定候选/共同年龄门槛以及整数计数损坏拒绝。使用本地Torch2.7.1 CPU；服务器先在原绑定Torch2.2.2环境重新做同套CPU检查及全条件接口检查。**尚未验证真实权重GPU前向、CUDA反向或耗时**，这些由服务器N1首个实际作业及梯度检查记录，不把CPU检查写成正式实验结果。技术失败暂停，不自动重试。

新目录records/research_post_ab_followup_<timestamp>_<pid>，全部代码、logs、temporary、cache、checkpoint、计数和轻量上传在/home/jovyan/zzx对应目录。nohup控制器、每卡至多一个worker；重复登记只显示已有队列，不重建。不会终止原队列或其他GPU进程，不另作资源审计。

## 安全接续

先读原queue_status及PID/worker存活、controller.lock：原18主体COMPLETE、F实际SKIPPED_GATE、controller/worker均退出且锁释放才接续。完成后验证原plan、code_manifest、18份complete、selected checkpoint和selected/fixed summary SHA绑定，记录predecessor_binding.json。原队列异常或状态冲突写HOLD并退出，不修复、不重训、不抢卡。

控制器自身与跨目录登记锁防止重复派发。新作业异常时停止发新作业，允许已经运行的另一卡收尾；明确诊断后才恢复。原/新完整状态均保留“最后观测时间”，未收到服务器回报不写正在运行。

## 服务器登记命令

助手无法直连服务器。下列命令由用户执行；登记后后台等待原队列释放。提交号由本次最终回复给出，不能随意改为未核验版本。

```bash
(
set -e
ROOT=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
cd "$ROOT"
git fetch origin rebuild-v1-protocol-20260915
COMMIT=本次发布的完整提交号
EXP_PY=$(python -c 'import json; print(json.load(open("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/rebuild_v1_d21_queue_20260928/plan.json"))["python"])')
BOOT_DIR="$ROOT/records/post_ab_bootstrap_$(date +%Y%m%dT%H%M%S)_$$"
mkdir -p "$BOOT_DIR"
git show "$COMMIT":scripts/enqueue_post_ab.py > "$BOOT_DIR/enqueue_post_ab.py"
"$EXP_PY" -u -B "$BOOT_DIR/enqueue_post_ab.py" --root "$ROOT" --commit "$COMMIT"
)
```

看到POST_AB_QUEUE_REGISTERED后回传该行及目录；显示ALREADY_REGISTERED就检查已有队列。控制器输出及PID保存在显示的目录。不因排队脚本返回0就声称已开始训练。N1完成后用对应code/scripts/upload_post_ab_records.py前台上传轻量记录（有--prepare-only可先验证体积）；助手回读并实现条件下一阶段。不得在后台写凭据或自动force push。
