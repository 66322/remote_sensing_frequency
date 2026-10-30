# Post-T离线审计

原件57ef5ad9，634个Git blob及全部633载荷取得/核验；原计数复算范围见audit.json。receive.py从固定提交的sparse Git工作副本github/读取同一证据路径，校正checkout换行后以manifest SHA和Git blob SHA重新检验，输出received/decoded/，不写Git或访问服务器。需Python/NumPy；audit.py已内嵌实际使用的metric/joint/check，prior_full_t_audit.json为之前已验收T的计数/4000绑定审计原文副本。运行receive.py后audit.py即可复算本轮；预测/权重本体留服务器，无GPU重现。
