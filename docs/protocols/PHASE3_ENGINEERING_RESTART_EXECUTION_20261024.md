# Phase3零训练更新工程失败的一次性修订执行（2026-10-24）

状态：AUTHORIZED_IMPLEMENTED_LOCAL_CHECKED_NOT_SERVER_LAUNCHED。用户在CPU兼容预检通过后明确回复“继续，把实验启动”，授权本次工程修复后的一次正式重新尝试；不是开放自动重跑失败配方。服务器由用户执行，无SSH。

执行代码：752d3835a18a15a04d83b1dcc1841bff98bf0b07。科学来源M2 ac325cdbb403ebb95b5eb0acbf17fffa5441dcfd、合并e65c6cb0830985461b3cd30e2f43158dd3d858cb；运行期修订、科学源和上游DINO 7764ea0分别记录，不能把包装修改冒充冻结源字节。此版本未在目标CUDA完成首次训练，目标检查通过才派发，首个正式更新执行CUDA准入，无额外训练probe。

## 原件与已知事实

原M2 records/research_phase3_m2_20261023T222114_2166330、原合并records/research_phase3_combined_20261023T222112_2164225完整保留。0/108端点、0评价案例、63条DINO Python3.9导入失败；成功CPU检查位于原M2 repairs/dino_py39_preflight_20261024T090448_2718326。固定8680614回执表明全部失败在模型导入前且无更新产物、兼容模型CPU构造/公共权重加载通过。详见[诊断与回执](../experiments/PHASE3_M2_PY39_IMPORT_FAILURE_20261024.md)。GPU/控制器最后有时间的查询仍是08:38:13，不能当作当前资源状态。

## 科学合同保持

M2→J→R→T→V，最多228作业/5,088,000更新。M2仍108×32k，原种子、Fit12地理fold、公开初始化、配对样本流、优化器、增强、目标、端点选择、计数和科学门禁保持。J42/R18/T30/V30及原条件保持，B/C不自动开放，不追加种子/失败配方。旧零更新尝试只保留为工程失败证据，不计为科学复现结果。

仅物理GPU0/1、无24小时硬截止。Val2/Test6/held4/final和公开test封存；所有快照/日志在/home/jovyan/zzx。中间量按冻结执行器有界内存处理，不恢复整轮磁盘数组缓存。M2未COMPLETE_SERVER_CHECKED且G0不真则后段不放行；J/R及T/V按原合同，不以单一正结果自动换主线。

## 接入方式与启动门禁

bootstrap_phase3_engineering_restart.py只接纳这两个确定的旧目录、固定旧绑定/全部源文件、原63条导入前失败与完整CPU回执。核对原控制器锁、公共权重SHA、原预训练来源、精确Torch2.2.2+cu121和CPU检查Python版本；任一不符停止。GPU0/1必须可用且UUID一致，磁盘保留40GiB。检查源码包使用同一完整Git提交及逐文件SHA。

新执行目录为records/research_phase3_m2_revision_<时间>_<PID>和records/research_phase3_combined_revision_<时间>_<PID>，不是在旧失败目录清理重跑。原M2源/代码清单/folds按字节复制；新plan标明previous_failed_attempt和engineering_revision_commit，科学源execution_commit仍ac325cd。新pretrained.json明确指向本次拥有的延迟注解副本，并保留原仓库/权重来源；runtime_revision.json另外绑定新执行代码、输入前史、CPU回执、DINO副本和实际路径。两处registration均绑定该修订回执SHA。

实际模型路径已接入M2/J/R：源repo不改，兼容副本由固定Git blob生成，仅增加future annotations且可执行AST一致；每次make_model再核验源/兼容副本。真实新目录CPU模型初始化SHA必须与已通过CPU预检相同。memfd在控制器进程内安装同语义绑定并实测，fork继承，没有磁盘回退。

目标机检查：新执行保护14项、真实新路径CPU模型/公共权重检查、原M2全16项（实际Linux FD不可跳过）、合并3套共11项。新M2数据准备还须与原prepared input_index逐项一致（文件SHA、大小、mtime、数组形状/类型和归一化），不一致在GPU worker创建前停止。首次正式更新后才有CUDA反传实证。

原控制器每项失败后继续独立根作业的行为被显式运行期适配为首次FAILED→WORKER_FAILED，走原拥有子进程清理分支并停止全M2，不再批量产生同类失败；这是调度故障保护，不改成功作业数学。合并监督器使用明确的新M2路径，绝不按glob误选旧run或另行bootstrap。缺公开catalog的返回形状另行适配为两数据集未就绪，后段保持WAIT_PUBLIC_DATA；不跳过新任务或放宽catalog合同。

两个新入口先校验修订并写ready回执，bootstrap核对双方PID/修订、再次检查GPU后写launch_release才放行；任一未就绪时不进入训练。只终止本启动器新建、尚在等待放行的入口，不按PID/进程名搜索或影响其他任务。放行后失败不自动恢复。

全局单次回执records/phase3_engineering_restart_20261024_once.json在登记前置写入。重复命令只打印EXISTING_ENGINEERING_RESTART_NO_DUPLICATE，无第二次登记或派发；任何登记/检查/部分启动失败保留回执和新目录，不自动重试，也不能删回执绕过。

## 用户执行一次

沿用remote_sensing，不安装新环境或继续改包。启动器会下载小型修订源码、核验、建新目录、执行CPU检查，再派发；几分钟内GPU暂时空闲可能仍在准备。

```bash
conda activate remote_sensing
ROOT=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
FIX=752d3835a18a15a04d83b1dcc1841bff98bf0b07
SCRIPT="$ROOT/records/bootstrap_phase3_engineering_restart_${FIX}.py"
curl -fL --retry 2 \
  "https://raw.githubusercontent.com/66322/remote_sensing_frequency/$FIX/scripts/bootstrap_phase3_engineering_restart.py" \
  -o "$SCRIPT" &&
{
  RESTART_LOG="$ROOT/records/phase3_engineering_restart_$(date +%Y%m%dT%H%M%S).log"
  nohup python -u -B "$SCRIPT" --commit "$FIX" --apply </dev/null >"$RESTART_LOG" 2>&1 &
  echo "$!" > "${RESTART_LOG%.log}.pid"
  echo "$RESTART_LOG"
  sleep 10
  tail -n 100 "$RESTART_LOG"
}
```

实际派发标志ENGINEERING_RESTART_LAUNCHED及STATUS_RECEIPT；只有CHECK_PASSED或启动器Done不证明训练已更新。首次M2_TRAIN ... 1及jobs/*/progress.json step≥1才证明已更新。只查询新目录，不看旧失败nohup。

```bash
tail -n 100 "$RESTART_LOG"
python -B "$ROOT/records/phase3_engineering_restart_package_${FIX}/scripts/status_phase3_engineering_restart.py" --tail 40
```

状态助手按全局回执明确读取新M2/合并状态、准备进度、最新两作业progress、前两失败栈、两日志末尾、PID状态及GPU0/1，只读且不自动启动。若尚无全局回执则NOT_REGISTERED_OR_BOOTSTRAP_STILL_CHECKING，先读RESTART_LOG。缺数据后段WAIT_PUBLIC_DATA正常；若NO_RETRY/FAILED/STOPPED先读新错误，禁止重跑启动命令试运气。

## 验证与验收边界

本地41项通过：运行期修订14、Python3.9兼容7、memfd9、原合并合同/头/公开队列11；七文件Python3.9语法解析通过。独立无.git源码包重跑修订14项通过；[回执](../experiments/evidence/PHASE3_ENGINEERING_RESTART_LOCAL_20261024.json)。本地为Windows/Python3.13，不代替目标CUDA测试。原CPU检查已经成功，本次新目录CPU检查/原16项/合并11项及训练派发均待用户实际执行。

结束后额外验收runtime_revision.json、两registration、runtime/admission/cpu_model_passed/previous_input_index/execution_manifest/launch_release、目标检查日志/回执、全局单次回执及所有训练/计数轨迹。原M2上传器不保证自动包含修订材料，不能声称这些服务器原件已在GitHub；训练失败只整理证据，不自动重算。