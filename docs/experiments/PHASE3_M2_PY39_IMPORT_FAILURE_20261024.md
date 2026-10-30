# M2 Python3.9导入故障与CPU兼容预检（2026-10-24）

状态：SERVER_CPU_PREFLIGHT_PASSED_TRAINING_NOT_RESTARTED；旧M2仍INCOMPLETE_NO_RETRY。

## 原始回执与结论边界

用户2026-10-24回传summary/失败节选（此次查询未带时间）：M2 INCOMPLETE_NO_RETRY，0/108完整端点、0评价案例、0个progress.json；63个failure均报unsupported operand type(s) for |: type and NoneType。展示的完整堆栈位于Python3.9加载DINOv2 attention.py的float | None注解，在make_model导入阶段，尚未进入该作业优化器构造或训练循环。全部63个原始堆栈及无更新产物仍由预检逐项核验。

[用户诊断终端原样副本](evidence/PHASE3_M2_PY39_IMPORT_TERMINAL_20261024.txt)。此次查询无date，不能虚构观察时刻；进程/GPU最后有时间观测仍为2026-10-24 08:38:13。原失败例T_F0_s42_T1时间08:35:42.732426，路径为external/dinov2_7764ea0/dinov2/layers/attention.py:58。

错误来自Python3.9求值PEP604式注解，不是这次xFormers警告导致。固定上游[attention.py](https://github.com/facebookresearch/dinov2/blob/7764ea0f912e53c92e82eb78a2a1631e92725fc8/dinov2/layers/attention.py)也含此注解；[Python3.9 future文档](https://docs.python.org/3.9/library/__future__.html)支持延迟注解。不是仅凭目录名推断版本，服务器预检必须核对HEAD及逐文件Git blob。

本工程早在[9月29日协议](../protocols/POST_D21_DAY_EXECUTION_20260929.md)和scripts/day_dino_compat.py中处理过同一兼容性。本次M2直接torch.hub.load原仓库，未接入该适配，原16项测试也未真正构造DINO模型，因此漏检。这是助手启动实现遗漏，不形成研究阴性。G0不通过时其他性能门禁均不作科学判断。后续正式执行必须将真实模型导入准入前置，避免同一导入问题产生批量失败作业。

## 已实现的有限修复

下一步仅执行CPU模型导入/公共权重预检：原目录repairs下生成带逐文件Git blob/原始SHA/副本SHA的Python3.9兼容副本，仅添加延迟注解声明且可执行AST一致。原DINO仓库、M2源码/配置/失败状态和权重不改。不读数据集、不做前向/反传、无GPU、无训练/重试控制器。真实目标模型构造/权重加载尚未验证；7项本地检查及Python3.9语法解析通过。

脚本scripts/preflight_phase3_dino_py39.py，固定提交86806140400620cc64af4728bc8c2af7cdcb69db。沿用既有延迟解析思路，另建当前M2自己的副本，避免复用历史D21固定目录或修改原外部仓库。仅复制hubconf.py和dinov2包已跟踪Python源码；逐文件核对Git对象哈希，拒绝脏文件/路径逃逸/符号链接。副本只有future注解差异，经AST核验；不改数学运算或预训练字节。

预检只接纳原63个同类、make_model/attention注解栈失败；summary task与failure task一致、无parameters/progress/checkpoint及非空训练轨迹，并核对原绑定/冻结源码和非运行控制器锁。任一条件不符即停止，不把工程失败假定为零训练。预检不是登记/恢复控制器，没有--apply或训练入口。

独立CPU子进程隐藏CUDA、禁用xFormers，构造12块ViT-S/14，严格加载既有公共权重并构造原MatchedExpert。import必须来自兼容副本，所有参数留CPU且CUDA未初始化；记录初始state哈希，不调用forward、loss、optimizer或step。最长180秒，单CPU数值线程，预计约1–2GiB主存；实际资源未测，不承诺训练吞吐或CUDA兼容性。

本地7项检查涵盖注解求值、docstring/future插入与幂等、Git原字节/脏文件拒绝、63条导入失败绑定、训练痕迹拒绝和路径/回执保护，全部通过；两文件Python3.9 AST解析通过。[本地回执](evidence/PHASE3_DINO_PY39_PREFLIGHT_LOCAL_20261024.json)。本地WindowsPython3.13，不代替服务器Python3.9真实模型导入；目标尚待用户运行。

## 历史执行命令：CPU预检已完成，不需重复

```bash
conda activate remote_sensing
ROOT=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
FIX=86806140400620cc64af4728bc8c2af7cdcb69db
M2="$ROOT/records/research_phase3_m2_20261023T222114_2166330"
SCRIPT="$ROOT/records/preflight_phase3_dino_py39_${FIX}.py"
curl -fL --retry 2 \
  "https://raw.githubusercontent.com/66322/remote_sensing_frequency/$FIX/scripts/preflight_phase3_dino_py39.py" \
  -o "$SCRIPT" &&
python -u -B "$SCRIPT" --directory "$M2"
```

成功标志CPU_PREFLIGHT_PASSED_NO_TRAINING_OR_RETRY。每次检查证据在原M2 repairs/dino_py39_preflight_<时间>_<PID>，包含源快照/admission/cpu_model.log/cpu_model_passed.json。失败保存preflight_failure.json并停止，不自动重试。

这条命令不修订冻结M2运行的pretrained.json、绑定或失败状态，CPU通过不会接回旧队列。用户此前明确“不自动增加种子或重跑失败配方”；当前63个作业已标失败，不能用登记期memfd修复重启或删除失败伪装新作业。若用户后续明确允许纯工程修复后的重新尝试，再制定可核验的执行修订：保留本次旧失败、明确新执行来源/绑定和同一科学预算、将CPU门禁接入实际M2/J/R路径，再启动；目前未实现或派发这一正式重试，不暗示已修复全部CUDA训练链。

原主线、门禁、test封存、GPU0/1、有界内存和无SSH规则不变。原publication仍未自动上传，当前只是用户节选，原件/训练轨迹尚未全量验收。
## 服务器CPU预检成功回执

用户已回传CPU_PREFLIGHT_PASSED_NO_TRAINING_OR_RETRY / CPU_MODEL_IMPORT_AND_PUBLIC_WEIGHTS_PASSED。预检目录为原M2 repairs/dino_py39_preflight_20261024T090448_2718326（目录时间09:04:48，完成时刻未提供）。固定8680614脚本成功标志表明全部63条原始失败的导入前栈和无更新产物审计、DINO源Git对象/兼容副本核对、CPU构造模型与公共权重严格加载均通过，且原M2绑定/失败证据保持不变。尚未启动训练，也未验证CUDA前反传。

[用户成功标志原样节选](evidence/PHASE3_DINO_PY39_CPU_PASS_20261024.txt)。回执来源是用户终端成功标志；admission.json、cpu_model_passed.json、完整cpu_model.log原件尚未取回，不能称全量轻量原件已验收。进程/GPU最后带时间观测仍为2026-10-24 08:38:13，不是实时状态。CPU通过只验证修复方案可用于模型加载，不会修改旧M2实际启动路径或恢复控制器。

上文“服务器待执行”为预检发布时状态，现由本回执更新。脚本8680614的成功出口在CPU子进程返回0后还核对原M2 binding、summary SHA、原63条failure和DINO原始源码不变；据此本次零训练更新的工程失败已具有审计回执。不声称完成了GPU前反传或全部轻量原件验收。

## 拟议正式工程重启范围：待用户明确

保留旧M2/合并及全部63条失败、skipped、publication和日志；不修改旧run状态，不再套用登记期memfd无作业修复。若用户明确允许，可准备一次独立修订执行，以旧run为工程失败来源，仍跑原M2→J→R→T→V合同，不增种子、臂、更新或开放test。CPU预检及memfd需接入真正的M2/J/R模型路径，批量派发前须通过目标模型加载；共性工程故障应立即止队。

当前只提交这一可审阅处理方案，不是研究方向决定；正式重试代码、执行绑定和启动命令均未准备或派发。用户原“不自动增加种子或重跑失败配方”约束仍有效，收到CPU成功回执不视为重试授权。下一步先明确这一次零更新工程失败是否允许修订后尝试，再实施相应执行修订。
## 后续授权与已实现执行入口

用户随后明确“继续，把实验启动”，本次工程修订重试已获授权，覆盖上文待用户明确的状态；不扩展为一般失败配方重跑。已实现[一次性修订启动包](../protocols/PHASE3_ENGINEERING_RESTART_EXECUTION_20261024.md)，提交752d3835a18a15a04d83b1dcc1841bff98bf0b07，原两失败目录保留，实际M2/J/R兼容/CPU准入及首败止队接入。本地41项通过，服务器待用户执行，当前不宣称已启动新训练。