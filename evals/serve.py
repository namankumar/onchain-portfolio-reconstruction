"""JSONL tools for a model-led investigation. No model/provider calls are made."""
import argparse
import json
import sys
from pathlib import Path
from .runtime import Session


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--case',required=True);parser.add_argument('--version',default='a81ed25',choices=['d084374','a81ed25']);parser.add_argument('--episode-out',type=Path)
    args=parser.parse_args();cases=json.loads((Path(__file__).parent/'fixtures/cases.json').read_text())['cases']
    session=Session(next(c for c in cases if c['id']==args.case),args.version)
    for line in sys.stdin:
        try:response=session.request(json.loads(line))
        except (ValueError,TypeError) as error:response={'error':str(error)}
        print(json.dumps(response),flush=True)
    if args.episode_out:
        args.episode_out.parent.mkdir(parents=True,exist_ok=True)
        args.episode_out.write_text(json.dumps(session.episode({'kind':'unbound_manual_session','model':None,'prompt':'investigator-v1'}),indent=2)+'\n')


if __name__=='__main__':main()
