# N2双向关系条件聚合执行协议（2026-10-05）

依据[原C/N1验收与调整](../experiments/POST_C_N1_RESULTS_20261005.md)，继续用户已授权的Post-A/B条件候选池。本轮只激活N2六项；N6三项已跳过，N3/N4/N5仍待各自问题/诊断，不自动堆叠。

## 问题、基座与匹配

检验DSM相对高度关系调节RGB邻域聚合、RGB特征余弦关系调节DSM邻域聚合，是否超过同容量空间邻域控制及空间打乱。关系权重来自可得输入；RGB余弦是特征相似代理，不是真值语义关系；DSM为原tile归一化高度值，不称米制高度/nDSM/深度三维坐标。不是再次做DSM梯度重建损失或局部位移搜索。

基座固定为原规则回退的N1-2 selected，step8000，SHA256=28bc6f8ca5e1221392598b0a6f2d160e8c633a6a9cf63827067df3e7b81a144b；N1 plan SHA=be8a81b8b1c24833d5221b23dce30c949061a05923725c4126342f956c43359f。六组都载入这个完整模型state、重新创建同一AdamW与8000步调度，从相同seed42新初始化关系模块；**是匹配的新增N2阶段训练，每组另8000更新，不是N1救gate追训**。所有组同预算，N2-0也训练。N1-2是预先规定的普通适应基座，不因它此轮最高分而改规则。

保留N1-2末端特征、相同32通道固定压缩/三投影尺度/128通道合并、同一分类头、相同RGB与DSM last4/heads适应；不用失败N1-3多深度入口。固定P6/D15原始专家仍用于科学joint划分/anchor报告，不把adapted own参考变化当保护。

| ID | 物理GPU | RGB聚合关系 | DSM聚合关系 |
|---|---:|---|---|
| N2-0 | 0 | 空间距离 | 空间距离 |
| N2-1 | 1 | DSM相对高度差 | 空间距离 |
| N2-2 | 0 | 空间距离 | RGB特征余弦 |
| N2-3 | 1 | DSM相对高度差 | RGB特征余弦；固定主候选 |
| N2-4 | 0 | 高度关系场空间打乱 | 真实RGB关系 |
| N2-5 | 1 | 真实高度关系 | RGB关系场空间打乱 |

六组都有两套128→128无bias消息投影，均参与前向和反传，参数量一致。空间控制与单侧控制只替换关系权重，不删除模块。

## 一次冻结的算子

N1 stride4融合前特征固定avgpool4到stride16；3×3邻域，空间log权重为中心0、轴向−0.5、对角−1。RGB聚合添加−4×DSM归一化相对高度差；DSM聚合添加2×(RGB特征归一化余弦−1)，RGB关系detach，梯度经RGB/DSM消息与共同CE更新。无额外关系监督或超参扫描。

关系归一化float32，邻域消息投影后以固定0.1残差、nearest回stride4，再送原融合头。高度关系场用masked raw DSM nearest到stride16；不宣称该采样是真实物理几何。高层RGB代理随适应变化，其因果解释有边界。

两模态中心和邻域都有效才参与关系传播；缺失/外边界关系先填中性0，打乱为固定半网格循环移位，再按当前位置可用性屏蔽，避免填充边界成为伪信号。缺失整块传播严格0；最终像素级known missing保持剩余侧own logits精确回退，无可得输入输出0。模型forward不读取标签、退化ID、质量分数或教师完整输入。

## 数据、预算、评价和停止

Potsdam fit12/Val2 3_11、5_10，原native512/stride256/NoBoundary fg5口径，Full与6类诊断。seed42、每组8000步、batch16、无累积；六组48000新更新，GPU0/1各至多一个worker。原配对crop/退化序列不含job ID；增强、两view目标与专家own CE完全复用N1。4000/8000按clean完整/RGB-only/DSM-only平均选模，平分早选，fixed8000共同年龄保留；Test6和independent final不访问。

固定N2-3 gate：
- S_available对N2-0 ≥+0.3pp；
- DSM退化族QD对N2-1 ≥+0.2pp；RGB退化族QR对N2-2 ≥+0.2pp；
- QR对打乱高度N2-4 ≥+0.2pp；QD对打乱RGB关系N2-5 ≥+0.2pp；
- 上述每项两tile各同号正增量，fixed8000同号；
- 对N2-0的clean、dsm_missing、rgb_missing各不低于−0.1pp；primary最差condition×tile不低于−0.2pp。
真实关系对打乱的比较方向在执行前锁定。报告全部四family、逐类、双侧伤害/保留，均值不得掩盖方向。门槛只是单seed开发筛选，像素/窗口/条件不作为独立重复。

新独立目录records/research_post_ab_followup_n2_<timestamp>_<pid>；全部执行代码、日志、计数、缓存、准备报告在zzx对应目录。原N1目录只读用于基座；其19项预约旧状态不被改写，N2实际执行以新目录为准。登记先核对N1四份完成/summary与固定基座SHA、控制器/worker退出及锁释放；重复登记只显示已存在N2，不重建。nohup后台训练；异常停止新派发，已运行另卡收尾，无自动重试/种子/扩预算；单作业沿原8小时上限超时停止该worker。N2结束自动做整数与绑定检查、阶段汇总并退出，不自动启动N3。

CPU8项检查PASS（Torch2.7.1 CPU）：容量和梯度、常量关系退化为空间控制、方向性输入、掩码/空邻域、全缺失传播0、预算/基座/任务列表拒绝、打乱与缺失门槛拒绝、真实N1/N2前向接线的合成专家及checkpoint加载/回退。不是服务器真实专家精度或CUDA验证；服务器绑定Torch2.2.2重做同CPU检查，首个实际GPU作业写真实梯度与完成记录。没有额外资源探针，没有本地训练。

## 登记和交接

脚本scripts/enqueue_post_ab_n2.py，传入本次发布且回读核验的提交号。原控制器不重启，源selected.pth不覆盖，原A/B/C/N1不重训。日志输出POST_AB_N2_QUEUE_REGISTERED、POST_AB_N2_LOG后接收目录/PID；出现ALREADY_REGISTERED就查看已有目录，失败先诊断不重复注册。

查询用新目录code/scripts/status_post_ab.py；完成后用code/scripts/upload_post_ab_n2_records.py --root ROOT --directory NEW_DIR前台上传轻量原件，含n2_screen、n1_base_binding、int64矩阵和逐tile原件；权重/预测只保留索引。重要结果、交接和下一步继续同步同GitHub分支并回读。
