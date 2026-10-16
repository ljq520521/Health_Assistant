"""Build source-verified TEMPORARY REVIEW packages from an explicit ID mapping.

Does not approve a production package, touch a database, infer aliases/allergens,
or generate any nutrient values. All amounts are extracted from source archives.
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from app.modules.diet.source_mapping import SOURCE_URLS, archive_records, mapped_nutrients, sha, digest
from app.modules.diet.import_service import load_package

def write(path, value):
    with Path(path).open('x',encoding='utf-8') as out:
        json.dump(value,out,ensure_ascii=False,indent=2,allow_nan=False)

def build(source_dir, preparation_dir, output):
    source_dir=Path(source_dir);preparation_dir=Path(preparation_dir);output=Path(output)
    output.mkdir(parents=True,exist_ok=False);(output/'sources').mkdir()
    now=datetime.now(timezone.utc).isoformat()
    sources=[];records={};archive_by_type={}
    for (kind,release),url in SOURCE_URLS.items():
        filename=url.rsplit('/',1)[1];data=(source_dir/filename).read_bytes()
        items=archive_records(data,kind)
        if set(records)&set(items):raise ValueError('不同来源包存在相同FDC ID，须明确版本后再合并')
        records.update(items)
        local='sources/'+filename;(output/local).write_bytes(data);archive_by_type[kind]=local
        sources.append({'path':local,'sha256':sha(data),'url':url,'release':release,'data_type':kind,'retrieved_at':now})
    doc_name='Download_Field_Descriptions_Oct2020.pdf';doc=(source_dir/doc_name).read_bytes()
    if not doc.startswith(b'%PDF-'):raise ValueError('说明文件不是PDF')
    (output/'sources'/doc_name).write_bytes(doc)
    candidates=json.loads((preparation_dir/'food_candidates_150.json').read_text(encoding='utf-8'))['items']
    candidates={c['candidate_key']:c for c in candidates}
    matches=json.loads((preparation_dir/'food_matches.json').read_text(encoding='utf-8'))['items']
    if len(matches)!=len(candidates) or {r['candidate_key'] for r in matches}!=set(candidates):
        raise ValueError('候选映射必须唯一且覆盖原候选清单')
    foods=[];pending=[];candidate_sources={};raw_provenance={}
    for match in matches:
        if match['match_status']!='source_matched':pending.append(match);continue
        raw=records[match['fdc_id']]
        if raw['description']!=match['original_english_name'] or raw['dataType']!=match['data_type']:
            raise ValueError('已核验映射与源文件英文描述/类型不符')
        values,evidence=mapped_nutrients(raw);candidate=candidates[match['candidate_key']]
        key='usda:fdc:'+str(raw['fdcId']);candidate_sources[match['candidate_key']]=key
        foods.append({'source_key':key,'fdc_id':raw['fdcId'],'source_archive':archive_by_type[raw['dataType']],
                      'original_english_name':raw['description'],'name_zh':match['name_zh'],'category':candidate['category'],
                      'food_state':raw['description'],'edible_part':'对应USDA条目的可食部分；按克称重，非带骨/带壳整重或毫升',
                      'match_evidence':match['review_note'],'basis_g':100,'energy_unit':'kcal','nutrient_unit':'g',
                      **values,'source_url':f"https://fdc.nal.usda.gov/food-details/{raw['fdcId']}/nutrients",'review_status':'approved'})
        raw_provenance[key]={'record_sha256':digest(raw),'candidate_key':match['candidate_key'],**evidence}
    drafts=json.loads((preparation_dir/'recipe_drafts_30.json').read_text(encoding='utf-8'))['items']
    recipes=[];pending_recipes=[]
    for r in drafts:
        missing=[i['food_candidate_key'] for i in r['ingredients'] if i['food_candidate_key'] not in candidate_sources]
        if missing:
            pending_recipes.append({'recipe_key':r['recipe_key'],'name':r['name'],'missing_candidate_keys':missing});continue
        recipes.append({'recipe_key':r['recipe_key'],'recipe_version':r['recipe_version'],'name':r['name'],'category':r['category'],
                        'description':'临时审核配方，待团队确认。营养按对应可食状态的投料估算，非成品实测；加工配料与过敏原未完整核对。',
                        'servings':r['servings'],'preparation_minutes':None,'time_evidence':None,
                        'source_note':'项目团队自编，AI辅助草案，待审核；仅在临时数据库验证，营养按食材投料估算，非成品实测。',
                        'ingredients':[{'food_source_key':candidate_sources[i['food_candidate_key']],'amount_g':i['amount_g']} for i in r['ingredients']],
                        'steps':r['steps'],'review_status':'approved'})
    write(output/'foods.json',foods);write(output/'recipes.json',recipes)
    manifest={'schema_version':1,'package_id':'common-food-cn-preview','package_version':1,'purpose':'temporary_review',
              'review_status':'approved','reviewer':'Codex：仅来源映射与临时库技术核对，非用户正式审批','reviewed_at':now,
              'mapping_policy':'usda-per100-v1','format':'json','sources':sources,
              'documentation':[{'path':'sources/'+doc_name,'sha256':sha(doc)}],
              'files':{name:{'path':name+'.json','sha256':sha((output/(name+'.json')).read_bytes())} for name in ('foods','recipes')}}
    write(output/'manifest.json',manifest)
    report={'source_files':'运行时从用户指定本地目录读取；直接联网下载曾被Windows10013阻止；不把文件哈希宣称为官方签名',
            'verified_food_count':len(foods),'pending_foods':pending,'temporary_recipe_count':len(recipes),
            'team_approved_recipe_count':0,'pending_recipes':pending_recipes,'formal_import_approved':False,
            'nutrition_incomplete_foods':[f['source_key'] for f in foods if any(f[k] is None for k in ('calories_per_100g','protein_g_per_100g','fat_g_per_100g','carbohydrate_g_per_100g'))],
            'sources':sources,'documentation_sha256':sha(doc),'manifest_sha256':sha((output/'manifest.json').read_bytes())}
    write(output/'review_report.json',report);write(output/'nutrient_provenance.json',raw_provenance)
    load_package(output,allow_temporary_review=True)  # Full independent import validation.
    return report

def main():
    p=argparse.ArgumentParser(description='从明确审核映射生成只供临时库使用的数据包；不写数据库')
    p.add_argument('--source-dir',type=Path,required=True)
    p.add_argument('--preparation-dir',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();r=build(args.source_dir,args.preparation_dir,args.output)
    print(json.dumps({k:r[k] for k in ('verified_food_count','temporary_recipe_count','team_approved_recipe_count','manifest_sha256')},ensure_ascii=False))

if __name__=='__main__':main()
