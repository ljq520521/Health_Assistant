"""Entirely synthetic importer fixtures, NOT real USDA nutrient records.

No values/IDs in this module may be promoted into a production package.
"""
import csv
import io
import json
import zipfile
from pathlib import Path
from app.modules.diet.source_mapping import sha, SOURCE_URLS

STAMP='2026-10-14T00:00:00+00:00'

def write_json(path,value):
    Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')

def fixture(root, *, fmt='json', foundation=False):
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    kind='Foundation' if foundation else 'SR Legacy';release='2026-04-30' if foundation else '2018-04'
    energy={'id':2048,'name':'Energy (Atwater Specific Factors)','unitName':'kcal'} if foundation else {'id':1008,'name':'Energy','unitName':'kcal'}
    source={'fdcId':900000001,'dataType':kind,'description':'SYNTHETIC TEST FIXTURE NOT USDA DATA',
            'foodNutrients':[{'nutrient':energy,'amount':120},
                             {'nutrient':{'id':1003,'name':'Protein','unitName':'g'},'amount':8},
                             {'nutrient':{'id':1004,'name':'Total lipid (fat)','unitName':'g'},'amount':0}]}
    with zipfile.ZipFile(root/'source.zip','w') as z:
        z.writestr('test-only.json',json.dumps({'FoundationFoods' if foundation else 'SRLegacyFoods':[source]}))
    food={'source_key':'usda:fdc:900000001','fdc_id':900000001,'source_archive':'source.zip',
          'original_english_name':source['description'],'name_zh':'临时夹具食物，非真实营养','category':'测试分类',
          'food_state':'测试状态','edible_part':'测试可食部分','match_evidence':'仅验证导入机制，不代表官方条目',
          'basis_g':100,'energy_unit':'kcal','nutrient_unit':'g','calories_per_100g':120,
          'protein_g_per_100g':8,'fat_g_per_100g':0,'carbohydrate_g_per_100g':None,
          'source_url':'https://fdc.nal.usda.gov/food-details/900000001/nutrients','review_status':'approved'}
    recipe={'recipe_key':'health-assistant:recipe:test-only','recipe_version':1,'name':'临时夹具食谱',
            'category':'测试午餐','description':'自动化夹具，不可导入正式数据库','servings':2,
            'preparation_minutes':None,'time_evidence':None,'source_note':'项目团队自编，AI辅助草案，待审核（仅测试）',
            'ingredients':[{'food_source_key':food['source_key'],'amount_g':200}],
            'steps':['仅测试步骤，不是实际配方'],'review_status':'approved'}
    if fmt=='json':
        write_json(root/'foods.json',[food]);write_json(root/'recipes.json',[recipe])
        filenames={'foods':'foods.json','recipes':'recipes.json'}
    else:
        def csv_write(filename,rows,fields=None):
            with (root/filename).open('w',encoding='utf-8-sig',newline='') as out:
                w=csv.DictWriter(out,fieldnames=fields or list(rows[0]));w.writeheader();w.writerows(rows)
        csv_write('foods.csv',[food])
        csv_write('recipes.csv',[{k:v for k,v in recipe.items() if k not in ('ingredients','steps')}])
        csv_write('ingredients.csv',[{'recipe_key':recipe['recipe_key'],'position':1,**recipe['ingredients'][0]}])
        csv_write('steps.csv',[{'recipe_key':recipe['recipe_key'],'position':1,'instruction':recipe['steps'][0]}])
        filenames={k:k+'.csv' for k in ('foods','recipes','ingredients','steps')}
    manifest={'schema_version':1,'package_id':'synthetic-test-only','package_version':1,'purpose':'test_fixture',
              'review_status':'approved','reviewer':'Automated fixture NOT source approval','reviewed_at':STAMP,
              'mapping_policy':'usda-per100-v1','format':fmt,
              'files':{k:{'path':v,'sha256':sha((root/v).read_bytes())} for k,v in filenames.items()},
              'sources':[{'path':'source.zip','sha256':sha((root/'source.zip').read_bytes()),
                          'url':SOURCE_URLS[kind,release],'data_type':kind,'release':release,'retrieved_at':STAMP}]}
    write_json(root/'manifest.json',manifest)
    return food,recipe,source

def rehash(root):
    root=Path(root);m=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
    for ref in [*m['files'].values(),*m['sources']]: ref['sha256']=sha((root/ref['path']).read_bytes())
    write_json(root/'manifest.json',m)
