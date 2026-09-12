"""Opt-in movement report checks; shares the cumulative capped test ledger.

Requires the dev dependencies. Synthetic trajectories come from the same analytic
fixtures as the offline phase-comparison tests, not from the demonstration athlete.
"""
import argparse
from pathlib import Path
import json
import runpy
from types import SimpleNamespace
from unittest.mock import patch

from evaluate_coaching import ROOT, OUT, BudgetedResponses
from track_sprint.coaching import generate_report, report_markdown, DEFAULT_MODEL, PROMPT_VERSION
from track_sprint.movement import movement_evidence
from track_sprint.schemas import AthleteProfile


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live',action='store_true')
    args=parser.parse_args()
    if not args.live:
        print('No API calls made. Pass --live to use the shared capped testing ledger.')
        return
    from dotenv import dotenv_values
    from openai import OpenAI
    api=OpenAI(api_key=dotenv_values(ROOT/'.env')['OPENAI_API_KEY'],max_retries=0,timeout=45,
               base_url='https://api.openai.com/v1')
    meter=BudgetedResponses(api)
    client=SimpleNamespace(responses=meter)
    fixture=runpy.run_path(str(ROOT/'tests/test_movement.py'))['synthetic_movement']
    for name in ('synthetic_movement','demo_movement','reversed_movement'):
        directory=ROOT/'artifacts/demo' if name=='demo_movement' else OUT/name
        directory.mkdir(parents=True,exist_ok=True)
        profile=AthleteProfile()
        if name=='demo_movement':
            summary=json.loads((directory/'summary.json').read_text())
            from contextlib import nullcontext
            patcher=nullcontext()
        else:
            data,summary,review=fixture()
            if name=='reversed_movement':
                data['sides']['left'],data['sides']['right']=data['sides']['right'],data['sides']['left']
            evidence=movement_evidence(data,summary,review)
            profile=AthleteProfile(goal='Compare left and right forward thigh motion and arm action. What might explain differences and what should I practice?')
            patcher=patch('track_sprint.movement.load_movement_evidence',return_value=evidence)
        meter.case=f'{name}:{DEFAULT_MODEL}:v{PROMPT_VERSION}'
        before=len(meter.entries)
        try:
            with patcher:
                saved,cached=generate_report(summary,profile,'configured privately',directory,client=client)
                count=len(meter.entries)
                repeated,hit=generate_report(summary,profile,'',directory,client=client)
                assert hit and len(meter.entries)==count and repeated==saved
            dest=OUT/f'{name}-{DEFAULT_MODEL}-v{PROMPT_VERSION}'
            Path(str(dest)+'.json').write_text(json.dumps(saved,indent=2))
            Path(str(dest)+'.md').write_text(report_markdown(saved))
            print(json.dumps({'case':name,'accepted':True,'requests':len(meter.entries)-before,'cached':cached,'cache_verified':True}),flush=True)
        except Exception as exc:
            print(json.dumps({'case':name,'accepted':False,'error_class':type(exc).__name__}),flush=True)
            break
    print(json.dumps({'requests_total':len(meter.entries),'budget_accounted_usd':sum(e['budget_charge_usd'] for e in meter.entries)}),flush=True)


if __name__=='__main__':
    main()
