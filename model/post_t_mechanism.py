"""Complete module-package swaps; intentionally no learned alignment or optimizer."""
HEADS=('project_rgb','project_dsm','merge_rgb','merge_dsm','fusion')
def group(name):
    if name.startswith('rgb_expert.'):return 'rgb'
    if name.startswith('dsm_expert.'):return 'dsm'
    if name.split('.')[0] in HEADS:return 'head'
    raise ValueError('unclassified state key '+name)
def compose(a,b,card):
    if set(a)!=set(b):raise ValueError('state schema mismatch')
    out={}
    for n,v in a.items():
        w=b[n]
        if v.shape!=w.shape or v.dtype!=w.dtype:raise ValueError('state shape/dtype mismatch '+n)
        out[n]=v if card[group(n)]==0 else w
    return out
