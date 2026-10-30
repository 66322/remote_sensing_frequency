# 第二批历史 Val2 预测删除（2026-10-13）
用户明确授权清理无用历史实验文件，拒绝压缩。仅处理首轮 receipt 的 skipped_paths 中、五个原定历史 jobs 下第一层评估目录为 fixed8000/support_fixed8000/initial_evaluation/stress_evaluation 的 3_11.npy 或 5_10.npy。按用户分类预计21216路径，其余660嵌套路径只输出样例，暂不删除。实际缺失数、inode去重和完整断链预计字节由执行核算；不保证可回收固定容量。
源receipt固定为 records/storage_prediction_cleanup_20261013T192501_1424574，要求前轮31956/31956完成且21876跳过记录。只读现有清单，不重新遍历五实验。每200项记录并显示进度，进程检查有起止提示。先审计路径、uint8 6000×6000 NPY头、尺寸及硬链接，再写manifest，删除前检查进程依赖，逐文件核对dev/inode/size/mtime后unlink。异常停止，无自动重试。
保持所有权重、JSON/JSONL/日志、源码、masks/shared_reference、当前Phase2和其他实验文件。已删历史预测不可再按原路径读取；保留权重允许日后另行授权重推理。不会自动重算。
核对历史执行脚本的fixed8000及support_fixed8000/initial/stress评估调用；当前phase2_data使用源数据、独立输入、Phase1.5 masks和预训练权重，phase2_legacy只读取Phase1.5 JSON计数，不依赖此次旧预测。运行中打开/映射五旧实验文件仍会阻止删除。
本地11项检查通过；Linux进程审计与真实服务器删除未在本地验证。服务器由用户执行，bootstrap、测试临时文件及回执均在/home/jovyan/zzx。
当前Phase2约461.4GiB的val_cache/head_cache仍保留，19:36观测处于B0评估，后续用毕及结果核验后再制定独立缓存清单。
