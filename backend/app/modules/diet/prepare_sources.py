"""Inspect manually downloaded archives and suggest matches, never approve them.

Uses official JSON ZIPs (no extraction); output stays pending until a reviewer
checks cooking state, edible portion and original description.
"""
import argparse
from difflib import SequenceMatcher
import json
from pathlib import Path
from app.modules.diet.source_mapping import SOURCE_URLS, archive_records, mapped_nutrients, sha

def prepare(source_dir, candidate_file, recipe_file):
    candidates=json.loads(Path(candidate_file).read_text(encoding='utf-8'))['items']
    recipes=json.loads(Path(recipe_file).read_text(encoding='utf-8'))['items']
    records=[];sources=[];missing=[]
    for (kind,release),url in SOURCE_URLS.items():
        path=Path(source_dir)/url.rsplit('/',1)[1]
        if not path.is_file():
            missing.append({'filename':path.name,'official_url':url,'place_at':str(path.resolve())});continue
        data=path.read_bytes();found=archive_records(data,kind)
        sources.append({'filename':path.name,'data_type':kind,'release':release,'sha256':sha(data),'record_count':len(found),'official_url':url})
        records.extend(found.values())
    report=[]
    for candidate in candidates:
        hint=candidate['english_match_hint'].lower()
        ranked=sorted(records,key=lambda r:SequenceMatcher(None,hint,r['description'].lower()).ratio(),reverse=True)[:5]
        suggestions=[]
        for record in ranked:
            try:
                nutrients,evidence=mapped_nutrients(record)
                error=None
            except ValueError as exc:
                nutrients=None;evidence=None;error=str(exc)
            suggestions.append({'fdc_id':record['fdcId'],'description':record['description'],'data_type':record['dataType'],
                                'nutrients_per_100g':nutrients,'mapping_evidence':evidence,'mapping_error':error})
        report.append({**candidate,'review_status':'pending_official_match','suggestions':suggestions,
                       'pending_reason':'官方原始文件未取得' if not records else '候选匹配建议不等于审核通过，须核对生熟/加工/可食部分'})
    keys={r['candidate_key'] for r in report}
    recipe_report=[]
    for r in recipes:
        ingredients=r['ingredients']
        errors=[]
        if any(i['food_candidate_key'] not in keys or i['amount_g']<=0 for i in ingredients): errors.append('配料键或重量非法')
        if not r['steps'] or r['servings']<=0: errors.append('步骤或份数缺失')
        recipe_report.append({'recipe_key':r['recipe_key'],'name':r['name'],'status':'pending',
                              'structural_errors':errors,'missing_verified_foods':[i['food_candidate_key'] for i in ingredients],
                              'review_note':'结构检查完成；真实食材身份、烹饪可操作性及团队配方审批尚待人工核对'})
    return {'status':'pending_not_importable','sources':sources,'missing_downloads':missing,
            'verified_food_count':0,'approved_recipe_count':0,'food_reviews':report,'recipe_reviews':recipe_report,
            'note':'模糊检索仅提供候选，不会自动生成approved数据或写数据库。'}

def main():
    p=argparse.ArgumentParser(description='USDA离线来源检查与待审核候选报告；无数据库操作')
    p.add_argument('--source-dir',required=True,type=Path)
    p.add_argument('--candidates',required=True,type=Path)
    p.add_argument('--recipes',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path)
    args=p.parse_args()
    result=prepare(args.source_dir,args.candidates,args.recipes)
    with args.output.open('x',encoding='utf-8') as out: json.dump(result,out,ensure_ascii=False,indent=2,allow_nan=False)
    print(json.dumps({'verified_food_count':0,'approved_recipe_count':0,'missing_files':len(result['missing_downloads']),'output':str(args.output)},ensure_ascii=False))

if __name__=='__main__': main()
