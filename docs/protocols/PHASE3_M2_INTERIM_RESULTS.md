# 读取已有M2中间评价：不必等完整阶段报告（2026-10-24）

本文先记录工具交付时的证据边界，后续实际回执见文末。用户询问“没有得出一些实验结果吗”。澄清：尚无publication阶段汇总不等于没有中间定量评价原件。当前收到的22:49终端仅有17/108训练完成与loss，没有展示这些作业的评价计数，因此本轮不能填入任何实际mIoU或宣称某臂优胜。服务器由用户执行，未直接取回原件。

## 已有可读材料及边界

实际M2执行链在8k/16k/24k/32k对外层四tile做单模态clean评价，primary_task输出中央内缩512区域的nb/full两份6×6整数混淆矩阵；Sink把它们写入trajectory_counts/<job>/<step>_<tile>.json。该分支不增加完整故障面板cases，所以counted_cases=0不能用来断言“没有任何评价”。控制器报告作业完成，按实现已发出这些年龄评价；实际文件覆盖与绑定仍须读取核对，不只凭17完成推断原件齐全。

现在可以先看：同一fold、系统seed、固定32k年龄下，DSM各臂的clean单模态NoBoundary fg5 mIoU及相对D0差值，以及RGB参考/教师的相应诊断。教师train6与部署RGB train8角色不同，不能混在一起当同一基线。年龄8k/16k/24k可作学习轨迹诊断，不从中反选最好checkpoint。

现在不能据此判断：RGB-down4困难位置的补救/损伤、实际融合收益、保护条件或未见退化迁移、科学G1–G4是否通过。这些需完整面板/配对计数。单fold/单seed、clean指标也不能当确认性结论；不能用中间结果裁剪失败臂、改变样本流/预算、补seed或放宽门禁。

## 独立只读汇总器

入口：[report_phase3_m2_interim.py](../../scripts/report_phase3_m2_interim.py)，Python标准库，无torch/项目模型导入，不读原始影像/标签/权重，不训练或重新推理，不改运行目录内任何原件。只读取登记、folds、parameters/complete和少量JSON轨迹计数；默认只写标准输出。下载脚本及用户选择的输出重定向均须在zzx对应目录，不放进或修改冻结code快照。

- 先合并四tile整数矩阵，再算前五类IoU平均；不能平均各tile的mIoU。计分域为中央512内缩，full_GT表示使用full标签，不是全tile；不能误标为mIoU(fulltile)。
- 要求四个预登记评价tile齐全、6×6非负整数矩阵、作业/年龄/参数绑定一致；32k还须有同绑定完整端点回执。缺失显示eligible=False与NA，不用三tile冒充四tile。
- 只对同fold×seed×固定年龄×同四tile的DSM学生计算相对D0百分点差，GT支持数、端点回执中的初始化SHA和完整训练采样流SHA必须一致；年龄8k/16k/24k只列单模态分数，不据32k完整流回执反证该年龄前缀配对。RGB参考/OOF教师不参加DSM差值；没有已就绪D0不补零或换seed。
- 模型实际字节SHA不重读；输出引用complete.json端点SHA，不声称重新校验全部端点。计数JSON小文件保留路径/内容SHA供--json溯源。
- 默认只列已出现parameters的作业，未启动的其余作业尚无行，不能把未列出当作失败或被删除。age为请求的评价年龄，不是当前训练步数。读取是瞬时快照，原子写完前的新文件稍后才能看到。

执行时FIX取本次代码提交的完整40位SHA（见最终回复），不以动态分支文件覆盖同名版本：

```bash
ROOT=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
M2="$ROOT/records/research_phase3_m2_revision_20261024T092814_2738345"
FIX='<本次代码提交的完整40位SHA>'
SCRIPT="$ROOT/records/report_phase3_m2_interim_${FIX}.py"
curl -fL --retry 2 \
  "https://raw.githubusercontent.com/66322/remote_sensing_frequency/$FIX/scripts/report_phase3_m2_interim.py" \
  -o "$SCRIPT" &&
python -B "$SCRIPT" --directory "$M2" --step 32000
```

输出nb_fg5_%为主开发指标，full_GT_fg5_%为同计分域full标签诊断，delta_D0_nb_pp为同块相对D0的百分点差；eligible=True表示这一行满足该读取工具的计数覆盖/回执条件，不是整个M2 G0或科学门禁通过。NA须结合eligible/coverage及角色理解，不自行当零分。

需要保存结构化原件索引时可用--json并重定向到M2目录下新的带时间戳轻量文件；不得覆盖既有publication、gates、summary、端点或训练日志。终端默认表为少量行，可以回传；更长JSON按轻量清单上传GitHub，不要求粘全量日志。此工具不提供新的训练/恢复入口。

## 实现发布时的本地验证与目标边界

8项针对性检查通过：四tile先池化后计分、缺/多tile、缺类别不补零、整数矩阵合同、同seed/年龄/角色配对、不一致GT支持拒绝、初始化/样本流回执不一致拒绝，以及实际记录目录布局下完整读取/缺一tile不比较/不改文件的集成检查。两文件Python3.9语法解析及隔离路径下独立脚本--help通过；只依赖标准库，不借用完整仓库模块。

测试为本地受控合成计数，不是服务器真实指标。本轮未运行服务器汇总器，仍以22:49:33为最后服务器观测。下一步由用户只读汇总现有计数后，再依据真实表讨论clean单模态表现；完整故障面板与108作业finalize继续原计划。研究角色、资源、预算和test封存保持。

## 后续目标回执：2026-10-24 23:39:19

用户已使用624194105b3b018bb1e1e66d80cada2a405e7758版本成功读取当前修订M2目录。输出19行、17行eligible；F0 seed42七DSM臂32k四tile齐全，D0=62.9713%，DF=62.3730%（-0.5983pp），全部改动臂未超过D0。见[真实表格、原始输出转录与分析](../experiments/PHASE3_M2_INTERIM_F0_S42_20261024T233919.md)。先前未运行/无分数的表述仅描述工具交付当时；本次目标回执更新了该边界。未回传完整JSON/矩阵/权重字节，未刷新进程/GPU状态，不据此判完整科学门禁或修改队列。
