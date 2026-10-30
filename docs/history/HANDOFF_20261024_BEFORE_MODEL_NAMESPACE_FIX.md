# 当前交接：一次工程修订已授权，启动包就绪待用户执行（2026-10-24）

用户已明确“继续，把实验启动”，允许本次零训练更新工程失败的一次修订重试。实际M2/J/R兼容路径、memfd、明确源选择、首败止队和重复启动拦截已实现；本地41项及七文件Python3.9语法检查通过。当前只完成代码/协议，服务器尚未执行新启动命令，没有新PID或新run回执。

唯一新启动入口：[执行协议](../protocols/PHASE3_ENGINEERING_RESTART_EXECUTION_20261024.md)，修订代码[752d3835a18a15a04d83b1dcc1841bff98bf0b07](https://github.com/66322/remote_sensing_frequency/commit/752d3835a18a15a04d83b1dcc1841bff98bf0b07)。沿用remote_sensing/Torch2.2.2+cu121，不改包。用户在服务器执行bootstrap_phase3_engineering_restart.py --commit <修订SHA> --apply一次，先现场准入/源码/新CPU模型/原16项/合并11项，双方入口就绪后才放行训练。无SSH，当前无新服务器启动回执。

旧M2 /home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_phase3_m2_20261023T222114_2166330与旧合并research_phase3_combined_20261023T222112_2164225保留。旧63条失败/0更新已由CPU预检审计；09:04:48目录CPU模型构造/公共权重通过。原进程/GPU最后带时间查询08:38:13，不是实时状态。

新目录在启动时生成research_phase3_m2_revision_<时间>_<PID>及research_phase3_combined_revision_<时间>_<PID>；全局回执records/phase3_engineering_restart_20261024_once.json保护任何登记/部分启动不重复派发。失败后不删除回执绕过。新状态助手status_phase3_engineering_restart.py按回执明确查新目录/进度/PID/日志/GPU，不再拿旧失败日志判断新状态。

科学源M2 ac325cd/合并e65c6cb按原字节复制，运行期修订SHA及兼容副本另绑runtime_revision/registration；新pretrained指向独立拥有的延迟注解副本，M2/J/R实际加载已接入。准备输入索引必须与旧准备一致；首个作业失败走原owned-worker清理立即止队；缺catalog保持WAIT_PUBLIC_DATA。原16项不是CUDA训练，首个M2_TRAIN step1/progress才证明实际更新。

M2→J→R→T→V最多228作业/5,088,000更新，原种子/预算/门禁不变，B/C不开放；主线/独立候选角色不变。test封存、GPU0/1、有界内存和用户服务器执行约束保持。结束时额外验收修订/CPU/launch原件与训练轨迹；原上传器不保证包含修订材料。前一交接见[归档](../history/HANDOFF_20261024_BEFORE_AUTHORIZED_RESTART.md)。