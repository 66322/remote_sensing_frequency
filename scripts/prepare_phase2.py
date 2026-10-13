from pathlib import Path
import argparse
from phase2_data import prepare
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);prepare(p.parse_args().directory.resolve())
