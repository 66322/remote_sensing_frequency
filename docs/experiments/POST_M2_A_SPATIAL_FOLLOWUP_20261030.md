# A空间读出自动接续：不重启Full（2026-10-30）

目的：原A0仅比较冻结骨干与线性头，不能排除读出容量限制。沿已授权首批预算，新增DINOv2/DINOv3匹配空间头，补成骨干×读出2×2开发诊断；不要求DINOv3胜出，不增加种子。原Full入口只有11项B/G/Q/S，没有把空间头串入自动队尾。本次修订补齐接续，不重放原A0或Full。

## 来源、范围与状态

- 权威分支rebuild-v1-protocol-20260915。已安装Full载荷固定d15f34e8d53f935aa17542123c2227fab14cb810，原A0科学源c22a046407daf42064cbb161429f2648c9b86d66。上述冻结文件、manifest和运行目录不修改。
- 新外置入口：scripts/queue_post_m2_a_spatial_20261030.py。固定代码提交见[发布回执](../../records/post_m2_a_spatial_followup_20261030_release/publication_receipt.json)。
- 新结果目录：ROOT/records/post_m2_a_spatial_followup_20261030_r1；ROOT=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro。
- 现成A0绑定：ROOT/records/post_m2_a0_ipcfix_20261030。原pair已完成各2k及校准、外层。修复前旧失败目录不改。
- 新入口已实现、本地17项受影响检查通过；尚未收到目标接续注册、profile或空间头正式更新回执。发布代码不等于已入队。
- 服务器用户操作，无SSH。新入口通过既有remote_sensing/bin/python运行，Python3.11.13/Torch2.7.1+cu126；不安装、升级或下载数据/权重。

## 交接与停止

1. start只读取已有小回执、源绑定和DINOv3路径，建立排他注册，后台启动脱离终端的单次等待进程。重复start只显示状态；派发失败/旧注册不自动重试，不删锁或started。
2. 等待Full的train_complete.json为COMPLETE或COMPLETE_WITH_INVALID_ROUTES且来源匹配，然后取得原controller.lock，确认GPU0/1空闲。正常接续不等Full的GitHub上传；空间结果独立成目录，避免与Full导出/上传并发写同一面板。
3. Full出现工程first_failure、控制器退出/被替换但无正常完成回执，停止新接续。Full某路线因自己的科学资格INVALID而正常结束，不阻断独立的空间读出。未知GPU进程占卡时报告并停止，不等待或终止对方。只授权物理GPU0/1。
4. 等待期间不导入Torch、不构造模型、不准备大数组、不占CUDA。源/数据/环境检查复用已有证据；交接只核对原文件大小/mtime绑定，不重新哈希权重、解码全数据或重新跑原profile。
5. GPU放行后每卡一个新常驻进程，复用该骨干与六拟合tile跨profile/train。训练结束释放拟合数组，校准/外层逐tile处理；无整轮磁盘logit缓存。记录resident_dino*.json的实际模型加载次数、拟合读取次数、缓存峰值与释放状态。单进程拟合缓存保护上限沿原12GiB配置，不是预计实际峰值。
6. 复用原spatial.execute的头、样本流、精度、有效batch16、损失、随机种子、步数和评价；原实现profile各候选及正式头构造前均重新seed42，复用已冻结eval骨干不改变头初始化。代码文件不热改；仅在新进程内版本化绑定缓存与DataLoader timeout30s。短TMPDIR/TEMP/TMP和tempfile缓存沿已验短目录算法。
7. 按profile→train→calibration→原screen→条件outer自动推进。两个新头各仅1步预热+3步计时，合计最多8个丢弃更新，不重测原线性头或骨干配置。短测仅粗估；各正式2000步、seed42，总4000步，已含原首批96k预算，新增预算为0。两空间头各19,254参数；不能声称空间头与2,310参数线性头同容量。
8. 原内筛保持：两空间头学会且两者内校准NB fg5均≥50才开outer；不以原A0线性阳性、DINOv3优势或Full分数作为前置。未学会/未过资格保存INVALID，不当科学阴性，不扩队列。工程首败停止后续phase，保存原栈，只清理本入口创建的工作进程组。
9. 原取数30s超时，新阶段300s无已记录进度则停；profile阶段上限720s，其他阶段24h，Full接续等待最多24h且不占GPU。原训练2.5倍短测慢速保护保留。没有自动重试、加种子、改配方或访问封存集。

## 数据、保留与上传

所有阶段使用原A0已有F0 train6/cal2/outer4和原公共DINO权重，无新增数据。原A0较弱的外层DINOv3总体分数不取消独立读出诊断。C/P/E/F、A1/A2和频率子实验仍未入队。

保留新头端点、本地轨迹、原始6×6整数计数、逐tile指标、screen、源绑定、各phase日志、首次失败和进程释放回执。模型及公共输入不上传普通Git；无自动删除。工作进程退出、GPU锁释放后再导出summary/gates、manifest与evidence.jsonl.gz；沿已有GitHub认证上传到records/新run名。认证/网络失败写UPLOAD_PENDING，仅续传现成产物，不重训/重推理，也不影响已经结束的GPU阶段。M2最终清理仍暂缓。

## 唯一操作

只需按发布回执执行一次start，不再逐阶段手动操作；不再运行Full bootstrap或旧A0修复命令。status仅显示既有回执与进度；publish仅续传现成小证据。具体固定提交命令在发布回执及当前NEXT_EXPERIMENT提供。

本地Windows Python3.9.25/Torch2.8.0+cpu的17项检查覆盖完成/故障互斥、失效路线独立性、PID复用拒绝、无上传依赖的锁交接、忙卡停止、重复注册、真实DataLoader超时属性、模型/拟合缓存复用及释放、原内筛、首败仅停自身、部分更新不确定性与无权重导出。Linux进程组/fork、H100实际新路径及空间头首更尚待服务器，不以这些本地检查替代。

## 固定版本一次启动命令

```bash
(
set -e
ROOT=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
REL=5f2958ae8b7d3ac79901eb0261239d89e82b461e
TOOL="$ROOT/execution/a_spatial_followup_$REL.py"
mkdir -p "$ROOT/execution"

if [ ! -f "$TOOL" ]; then
  curl -fL --connect-timeout 10 --max-time 60 \
    "https://raw.githubusercontent.com/66322/remote_sensing_frequency/$REL/scripts/queue_post_m2_a_spatial_20261030.py" \
    -o "$TOOL.part"
  mv -n "$TOOL.part" "$TOOL"
fi

/home/jovyan/miniconda3/envs/remote_sensing/bin/python -u -B \
  "$TOOL" start --commit "$REL"
)
```
