# 五组历史Val2预测删除协议（2026-10-13）

用户明确：“为什么要压缩，很多文件都没有必要保留，，可以都删了”，随后“继续”。本次授权按已盘点的五组历史实验预测.npy范围落实，不扩大到zzx全部文件或整jobs。此前压缩归档建议已被用户否决，不再要求压缩或多次确认。

执行工具scripts/delete_historical_val2_predictions.py固定五目录：Post-D30 mechanisms 20261004T000812_2446364、Post-N3 S1 20261007T083203_694293、Post-S1 support 20261008T234921_1890161、Post-S1 transfer 20261010T073327_2852696、D27 repair 20261003T092243758628_2001983。仅jobs/任务/evaluation或support_evaluation内部名为3_11.npy、5_10.npy、NPY头uint8且6000×6000、尺寸正确的普通非symlink文件。当前Phase2新旧目录、数据、所有pth、JSON/日志/代码/masks/shared_reference和Git worktree保留。不存在rm -rf或整目录删除。

去重占用约1365.52GiB为用户inode统计；外部硬链接可能保留空间，实际释放需按剩余link与最终df核对。不能把重复路径额外当空间，也不承诺精确释放1.33TiB。

工具先审计/proc所有进程cmdline/maps/fd，发现五旧目录正在被使用或权限不足则停止。遍历严格拒绝symlink路径/祖先，按inode去重计容量，逐文件只读NPY头，不读取Test6数据。生成不可变删除清单、脚本副本、plan和SHA，位于/home/jovyan/zzx对应records/storage_prediction_cleanup_<time>_<pid>；--execute才删除，每次核对路径、inode/大小/mtime与清单一致，记录deleted.jsonl、progress和完成/失败回执。对每历史实验另写prediction_retirement记录，明确像素原件已退役而不是篡改旧原始SHA、complete指标或宣称预测仍在。

5项本地单元检查通过：精确文件范围及硬链接去重、变化文件拒删、外部链接不计预计可释放空间、错误NPY头拒绝、越界路径拒绝。2改动Python语法通过。Linux/proc真实执行尚未发生；服务器仍由用户前台执行，不SSH。--execute属于用户已授权的具体删除操作，无自动压缩/训练停止/失败重跑。执行期间不要启动这些旧实验的分析程序，以避免进程审计后新增依赖。

删除后旧预测np.load和SHA查验不能直接运行；需要像素级复核时由保留checkpoint显式推理重新生成，并另登记新证据，不把新推理自动视为原SHA复原。原指标/原始混淆矩阵/联合计数/配置/训练轨迹仍保留，图像级预测可视化失去现成原件。没有压缩备份，不能承诺可直接恢复被删字节。

启动先提取固定Git提交的脚本和测试到records/bootstrap目录，以TMPDIR明确指向该目录执行5测试，再运行删除器--execute。若检测到活进程/数据变更/非预期格式，保留失败回执，诊断后再处理，不强行跳过保护。完成后用户返回CLEANUP_COMPLETE、complete.json和df，才将GitHub状态更新为实际完成。
