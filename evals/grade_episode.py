"""Grade a saved fixture episode without treating manual metadata as model proof."""
import argparse
import json
from pathlib import Path
from .grader import grade


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--episode',type=Path,required=True)
    args=parser.parse_args();episode=json.loads(args.episode.read_text())
    cases=json.loads((Path(__file__).parent/'fixtures/cases.json').read_text())['cases']
    case=next(c for c in cases if c['id']==episode['task_id']);outcome=grade(case,episode)
    print(json.dumps({'outcome':outcome,'model_provenance':'not_authenticated_by_this_harness','eligible_for_automated_model_comparison':False},indent=2))
    return 0 if outcome['goal_success']else 2


if __name__=='__main__':raise SystemExit(main())
