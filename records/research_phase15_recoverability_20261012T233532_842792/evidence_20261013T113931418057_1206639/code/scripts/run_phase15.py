import argparse
from pathlib import Path
from phase15_common import *


def main(base,job_id,gpu):
    import fcntl
    p = validate(base)
    job = next(j for j in p['jobs'] if j['id'] == job_id)
    out = base/'jobs'/job_id
    out.mkdir(parents=True,exist_ok=False)
    lock = (out/'worker.lock').open('a')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    from phase15_inference import Runner
    def progress(**kw):
        write(out/'progress.json',dict(job=job_id,observed_at=now(),optimizer_updates=0,**kw))
    runner = Runner(base,gpu,progress)
    records = {}
    for c in job['cases']:
        runner.run(c)
        records[case_id(c)] = sha(base/'cases'/(case_id(c)+'.json'))
    runner.finish()
    write(out/'complete.json',dict(binding=binding(base),cases=[case_id(c) for c in job['cases']],
        records=records,optimizer_updates=0,completed_at=now()))
    progress(phase='complete',physical_gpu=gpu)


if __name__ == '__main__':
    a = argparse.ArgumentParser()
    a.add_argument('--directory',type=Path,required=True)
    a.add_argument('--job',required=True)
    a.add_argument('--gpu',type=int,choices=(0,1),required=True)
    x = a.parse_args()
    main(x.directory.resolve(),x.job,x.gpu)
