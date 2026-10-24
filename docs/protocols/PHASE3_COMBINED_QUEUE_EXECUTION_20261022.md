# Phase3 M2＋后续机制与新数据合并队列（M2执行不完整，已停止）

2026-10-24最新诊断：Python3.9导入DINO的float | None注解失败，63条同类错误、0/108完整端点、无进度。见[CPU兼容预检](../experiments/PHASE3_M2_PY39_IMPORT_FAILURE_20261024.md)。原队列已停止，仅CPU验证，不再次登记、memfd --apply或重跑失败作业。当前实际M2/J/R正式重试尚未准备或派发，下方为原合同和历史启动方法。

2026-10-23启动前修复：执行代码改用 `e65c6cb0830985461b3cd30e2f43158dd3d858cb`。90b9bbe的下载包遗漏执行清单，用户目标检查在队列登记前失败；新入口保存并绑定清单，提前检查冻结Torch版本。见[故障及证据](../experiments/PHASE3_COMBINED_BOOTSTRAP_FIX_20261023.md)。M2冻结提交、作业数、模型及科学门禁均不变。

2026-10-23 22:21:12登记回执：用户已沿用remote_sensing并升级到2.2.2+cu121，合并队列已登记，见[登记记录](../experiments/PHASE3_COMBINED_REGISTRATION_20261023.md)。后续停止原因已由2026-10-24修复协议更新。下方登记仅为历史参考；独立环境是隔离选项，不是强制条件。

## 目的与边界

本队列已由用户在原目录派发控制器，首次训练状态仍待核验；派发回执不代表实验结果。主线仍是 RGB–DSM 双向条件互补与退化/缺失分割；恢复只作为历史旁支。执行顺序是 M2→J→R→T→V，总计最多 228 个训练作业、5,088,000 次优化器更新。M2 原 108×32k 作业及其科学门禁不改；M2-B/C 仍为独立未开放合同。GPU 仅使用物理 0/1，无 24 小时截止。任何阶段失败即停止，不自动重跑失败配方、不补种子。

M2 来自冻结提交 `ac325cdbb403ebb95b5eb0acbf17fffa5441dcfd`。J/R 只有在 M2 `publication/summary.json` 为 `COMPLETE_SERVER_CHECKED` 且 `gates.json` 的 G0 为真时执行；它们不以 M2 的正向假设门禁作为筛选条件。J 完整性通过后执行 R，J6 的性能不控制 R 的去留。T/V 有独立数据合同；不得将公开数据的开发结果写成 M2 同城结果。所有 Test6、历史 held4/final、Val2 和新数据公开 test 均封存。

## 五段固定比较

| 阶段 | 固定规模 | 开发问题 | 主要输出 |
|---|---:|---|---|
| M2 | 108×32k | 原 RGB–DSM 条件实验 | 原执行协议的轨迹、混淆矩阵、门禁 |
| J | 7 臂×3 外折×2 种子×8k=42 | 冻结专家后，几何对应关系/条件头是否解释提升 | 逐 tile int64 6×6、J0 固定概率基线、J6 对七个对照的逐块差 |
| R | 3 臂×3 外折×2 种子×32k=18 | 端到端表征训练与 DSM 辅助 CE 的区别 | 相同输入流的联合训练、外层四 tile 开发评估 |
| T | 5 臂×3 地理组×2 种子×12k=30 | DSM 时间差是否被基准偏置/配准误差混淆 | 3DCD 开发组变化混淆矩阵与已变化区域高度误差 |
| V | 5 臂×3 国家组×2 种子×12k=30 | 几何是否帮助建筑对象拆分而非仅像素分数 | P³ 开发组建筑像素矩阵、对象 TP/FP/FN、并合/拆分 |

J 为冻结专家头部测试。J0 固定 0.9 RGB＋0.1 DSM 概率融合；J1 为可学 logit 融合，J2 为特征拼接，J3 为 RGB-only，J4 为另一真实 RGB 专家替代 DSM，J5 将 DSM 特征固定错开半个窗口，J6 为 RGB 条件调制 DSM，J7 为 DSM 自条件。J5/J6 使用相同头部架构与初始种子。J 在训练 tile 上读取同一 train8 训练的 M2 专家，只对 outer-held4 评估；这限制了训练阶段的解释边界。J6 的预登记开发判据写入 `publication/J/gates.json`；即使为阴性也保留所有臂结果。

R 从同一公开 DINO 权重初始化，不加载 M2 微调端点；`concat_joint`、`conditional_joint`、`conditional_joint_aux` 使用相同 crop 流、32k 更新、batch16/微批4。两个 conditional 臂只相差 DSM 辅助 CE（权重 0.5），三臂都使 DSM logit 参与主损失。这是独立的端到端比较，不把 J 冻结头的正结果反推为表征因果结论。

T/V 是**探索性方法迁移**，共同采用小型编码解码器与匹配预算；目前尚没有官方强基线复现实验，不能凭这些结果宣布优于已有变化检测或建筑矢量化方法。T 分离普通输入、训练期扰动、稳健偏置校正、硬对应、软对应＋无匹配信号。V 分离 RGB-only、普通 RGB＋高度、RGB 关系监督、RGB＋高度关系监督及错位高度对照。若进入论文主张，须再锁定对应任务的成熟基线和独立测试协议。

## 数据合同与内存

公开数据应从 [3DCD 官方页面](https://sites.google.com/uniroma1.it/3dchangedetection/download)、[3DCD 官方代码](https://github.com/VMarsocci/3DCD) 与 [P³ 官方数据卡](https://huggingface.co/datasets/rsi/PixelsPointsPolygons)、[P³ 官方代码](https://github.com/raphaelsulzer/PixelsPointsPolygons) 获取，保留原始来源、许可、版本、下载日期、文件大小及 SHA-256 索引。**本代码不下载数据**。训练与评估只读 catalog 的 `development` 行；3DCD 必须在标签盲条件下先按空间位置冻结三个互不重叠的地理组，P³ 必须使用 CH/NY/NZ 三个开发国家组。不得把官方公开 test 路径列入 catalog。P³ 的 163 GB 原集只按需读当前 tile；LiDAR 在内存里投影为每 tile 高度，tile 缓存每 worker 最多 3 GiB，用完释放，不建立整轮磁盘派生缓存。

轻量 catalog 建议放在 `/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/phase3_combined_public_catalog.json`，最小结构见 [`configs/phase3_public_catalog.template.json`](../../configs/phase3_public_catalog.template.json)。模板中的占位路径不能作为可运行数据。每条源文件路径必须是 `/home/jovyan/zzx` 内的绝对路径，不能经过 test/Val2/Test6/held4/final 或 symlink。3DCD 必须明确原 DSM 单位换算、2D 变化正负值编码、3D 高度标签缩放/偏移和 ignore 值，并人工确认不同分辨率栅格在同一地面范围对齐后将 `pixel_grid_alignment_verified` 设为 true；这些数值须通过原始数据说明与抽样人工核对后填写，代码不猜。P³ `image_id` 必须与原 COCO `images` 条目匹配，RGB 与 `.copc.laz` 要同 CRS；标注多边形须可解码。任何不符停止且不自动降级。

## 登记与观察

必须使用Torch `2.2.2+cu121`，不能只以CUDA可用为准。可升级现有环境，也可按下面示例准备独立环境。用户已在原环境完成升级；以下仅为历史启动参考，当前不必执行：

```bash
conda create -y -n remote_sensing_phase3 python=3.9 pip &&
conda activate remote_sensing_phase3 &&
python -m pip install torch==2.2.2 torchvision==0.17.2 torchaudio==2.2.2 --index-url https://download.pytorch.org/whl/cu121 &&
python -m pip install 'numpy<2' scipy Pillow tifffile PyYAML rasterio 'laspy[lazrs]' pyproj &&
python -c 'import sys,torch; print(sys.executable,torch.__version__,torch.cuda.is_available()); assert torch.__version__=="2.2.2+cu121" and torch.cuda.is_available()'
```

PyTorch组合依据[官方历史版本说明](https://pytorch.org/get-started/previous-versions/#v222)。其他依赖实际安装版本应随服务器环境记录保留；本地CPU检查不替代目标Linux/CUDA验收。

在服务器终端、数据准备后或准备中，使用最终提交的完整 40 位 SHA（见本次交接中的提交链接）：

```bash
COMMIT='e65c6cb0830985461b3cd30e2f43158dd3d858cb'
CATALOG='/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/phase3_combined_public_catalog.json'
curl -fsSL "https://raw.githubusercontent.com/66322/remote_sensing_frequency/${COMMIT}/scripts/bootstrap_phase3_combined.py" | python - --root /home/jovyan/zzx/paper_rebuild/08_thesis_full_repro --commit "$COMMIT" --catalog "$CATALOG" --inspect
```

`--inspect` 只列出已有 M2/合并运行和 catalog 存在状态，不登记或启动。核对无已有合并队列后，删除命令末尾的 `--inspect` 才登记单一队列。完整队列只从固定 GitHub 提交下载经过 SHA 核对的轻量源码包；新的服务器运行目录为 `records/research_phase3_combined_<时间>_<PID>`。控制器先沿原 M2 登记入口启动原 108 作业，等待其门禁；M2 已存在则复用其唯一原运行目录，不重复创建。队列报告为 `queue_status.json`，过程日志为 `nohup.log`；每段 `publication/<阶段>/summary.json` 和 `jobs/<ID>/` 保留完整端点、轨迹、样本哈希、逐 tile 指标。

公开 catalog 尚未存在或不完整时，M2/J/R 结束后状态为 `WAIT_PUBLIC_DATA`，不自动跳过 T/V。待源 catalog 合同完整后，控制器冻结一份到队列 `catalog.json`，随后执行 T 和 V；若已经冻结而源数据改变，训练阶段按本地固定 catalog 复核。原 M2 或任何后续作业报错时状态停止；用户先核验原始错误和科学门禁，再另行决定是否修复，不自动续跑已有失败作业。

新数据阶段要求在 M2 所用 Python 环境中可导入 `rasterio`、`laspy`（含 LAZ/COPC 解码后端）、`pyproj`、`Pillow`、`scipy`、`numpy` 和目标 `torch`。下载后可用本提交的 `scripts/check_phase3_public_catalog.py --catalog "$CATALOG" --sample-headers` 对每个开发地理组抽一张原始样本做只读栅格/标注/点云预检；若缺依赖、地理对齐或标签编码不清，不应把模板改为“就绪”。

## 证据与去留

每段完成后先核验作业数、训练步数、轻量 receipt、端点 SHA、样本流哈希、逐 tile 混淆矩阵及完整轨迹，再分析跨折×种子的方向和退化/健康区域差异。J 的配对单位是 fold×seed 六块，tile 和随机遮挡像素不得当独立重复。T/V 的地理组是外层单位，不能把相邻 tile 当独立城市。若新数据对标现有成熟方法后仍无法形成清晰问题和机制，保留负结果并重新讨论论文切入点。重要结论和交接写回 GitHub 当前研究分支并回读核验。
