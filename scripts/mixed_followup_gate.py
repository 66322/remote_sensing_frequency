"""Pure completion gate for starting the post-D21 mixed-degradation queue."""


def require_original_complete(summary, analysis):
    if (summary.get('status') != 'COMPLETE' or summary.get('completed') != 42 or
            summary.get('planned') != 42 or summary.get('failures') or
            summary.get('test6_loaded') is not False):
        raise RuntimeError('original 42-job queue is incomplete; follow-up not started')
    if analysis is None or (analysis.get('completed') != 42 or
                            analysis.get('selected') != 42 or
                            analysis.get('integer_count_audit') != 'PASS' or
                            analysis.get('test6_loaded') is not False):
        raise RuntimeError('original 42-job integer audit is incomplete; follow-up not started')
    needed = {
        (dataset, comparison)
        for dataset in ('potsdam', 'vaihingen')
        for comparison in ('D_recovery_x_DSM_interaction', 'D_DSM_minus_gray_capacity')
    }
    observed = {(row.get('dataset'), row.get('comparison'))
                for row in analysis.get('comparisons', ())}
    if not needed.issubset(observed):
        raise RuntimeError('original D interaction comparisons are missing; follow-up not started')
