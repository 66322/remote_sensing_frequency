# D23长任务后台运行与断点接续

用户明确要求：GPU0/1可用，两张H10080GB，服务器内存/磁盘充足；长实验必须用nohup防终端断线。此要求为后续默认执行规则，不再因资源充足增加独立probe前置。

本次上一入口已前台启动TSF(pid739666)/T0(pid739667)，用户回传0.5分钟日志，仅证明进程已启动、尚无4000步完成证据。回传没有观测时钟，不能作为实时状态。

旧进程不能通过重新敲nohup直接获得可靠的终端I/O重定向。迁移步骤：在原终端按一次Ctrl+C，让旧controller停止并清理它创建的worker；随后以nohup、stdin=/dev/null、stdout/stderr到本次实验目录日志运行新controller --resume-queue。启动前拒绝本目录仍活着的旧worker，防止重复占GPU。

接续保持旧plan、runtime_lock和执行模型源码绑定不改。已formal_complete4000的组跳过；未完成的组复制最近100步周期保存的checkpoint/optimizer及绑定到本次目录jobs/<arm>_resume_<timestamp>，SHA验证复制，使用已有runner --resume恢复。没有checkpoint的初始化阶段从该组开头开始。旧缓存、权重、日志、部分评价保持原状，新评价在新job目录执行，不覆盖旧预测。正式checkpoint特征不含输出目录，因此相同源/锁/设备可用于新目录接续；每组重新缓存的I/O会增加少量耗时。

controller新源码快照放本次目录code_resume_<timestamp>，resume_event记录前次状态与controller提交，worker的模型/损失/4000步协议不变。新增接续复制/旧部分评价保留检查通过，既有5项队列模拟检查及语法通过。实际服务器接续尚待用户执行。

后台没有TTY，不能交互输入GitHub认证；新controller完成计算后输出D23_UPLOAD_PENDING与D23_UPLOAD_SCRIPT路径，退出并保留完整轻量记录。之后在前台运行所打印的上传脚本 --root <项目root> --directory <本次目录>，输入认证，原件上GitHub后用户只回传提交号。不存储凭据、不把nohup计算结果未上传写成GitHub已更新。

全部log、PID、快照、接续checkpoint和Git上传工作树仍在/home/jovyan/zzx对应实验目录。资源与研究阈值保持已有协议；不要另外启动第二个八组队列。
