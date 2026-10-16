"""Real-source preview acceptance. Always creates and deletes its own temp DB."""
import argparse
from pathlib import Path
import tempfile
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.config import Settings
from app.database import init_database
from app.main import create_app
from app.modules.diet import migrations as m1,migration_002 as m2,migration_003 as m3,migration_004 as m4
from app.modules.diet.import_service import load_package,database,dry_run,apply_package,snapshot,write_audit

def verify(package_dir, report_path):
    package=load_package(package_dir,allow_temporary_review=True)
    if package['manifest'].purpose!='temporary_review':raise ValueError('此验收入口只接受temporary_review包')
    checks=[];report={}
    with tempfile.TemporaryDirectory(prefix='diet-source-acceptance-') as folder:
        path=Path(folder)/'acceptance.db'
        init_database(path);m1.migrate_diet(path);m2.migrate_goals(path);m3.migrate_water(path);m4.migrate_recipes(path)
        with database(path,write=True) as c:
            c.execute("INSERT INTO profiles(id,display_name) VALUES(1,'独立临时库技术验收档案')")
        initial=dry_run(path,package)
        # Force failure after food/category insertion to demonstrate full rollback on real data.
        with database(path) as c:before=snapshot(c)
        with patch('app.modules.diet.recipe_service.save_in_connection',side_effect=RuntimeError('acceptance rollback probe')):
            try:apply_package(path,package,Path(folder)/'audit',expected_plan_sha256=initial['plan_sha256'])
            except RuntimeError as e:
                if str(e)!='acceptance rollback probe':raise
            else:raise AssertionError('failure injection did not run')
        with database(path) as c:assert before==snapshot(c)
        checks.append('真实来源包中途失败后分类、食物、食谱整批回滚')
        result=apply_package(path,package,Path(folder)/'audit',expected_plan_sha256=initial['plan_sha256'])
        repeat=dry_run(path,package);assert repeat['counts']['add']==repeat['counts']['conflict']==0
        with database(path) as c:before=snapshot(c)
        apply_package(path,package,Path(folder)/'audit',expected_plan_sha256=repeat['plan_sha256'])
        with database(path) as c:assert before==snapshot(c)
        checks.append('重复导入全部跳过，所有业务数据一致')
        with TestClient(create_app(Settings('USDA temporary acceptance',path,()))) as client:
            def get(url,params=None):
                response=client.get(url,params=params);assert response.status_code==200,response.text
                return response.json()
            def post(url,payload,status=201):
                response=client.post(url,json=payload);assert response.status_code==status,response.text
                return response.json()
            foods=get('/api/diet/foods')['items'];recipes=get('/api/diet/recipes')['items']
            assert len(foods)==len(package['foods']);assert len(recipes)==len(package['recipes'])
            searches={q:len(get('/api/diet/foods',{'q':q})['items']) for q in ('米饭','鸡蛋','牛奶')}
            assert all(searches.values())
            cat=foods[0]['category_id'];filtered=get('/api/diet/foods',{'category_id':cat})['items']
            assert filtered and all(f['category_id']==cat for f in filtered)
            checks.append('食物中文搜索、分类筛选、食谱列表与详情真实API可读')
            for r in recipes:
                assert get('/api/diet/recipes/'+str(r['id']))['nutrition']==r['nutrition']
            def recommend(**conditions):
                return post('/api/diet/recipe-recommendations/preview',{'date':'2026-10-14','limit':50,**conditions},200)
            normal=recommend();assert normal['eligible_count']==len(recipes)
            assert all(r['score'] is None and r['scores']['inventory'] is None for r in normal['items'])
            chosen=normal['items'][0];ingredient=chosen['ingredients'][0]
            post('/api/diet/inventory-items',{'food_id':ingredient['food_id'],'quantity_g':ingredient['required_g']/2})
            response=client.put('/api/diet/goals',json={'effective_from':'2026-10-01','calories_kcal':2000,'protein_g':80})
            assert response.status_code==200,response.text
            targeted=recommend(target_ratio=.3)
            assert any(r['scores']['nutrition'] is not None for r in targeted['items'])
            assert all(abs(sum(r['weights'].values())-1)<1e-10 for r in targeted['items'])
            assert any(r['missing_ingredients'] for r in targeted['items'])
            checks.append('无目标/库存时NULL评分；设置临时目标与部分库存后归一化评分、缺料、理由正常')
            rule=post('/api/diet/food-preferences',{'food_id':ingredient['food_id'],'rule_type':'allergy'})
            excluded=recommend(target_ratio=.3)
            assert not excluded['items'] and len(excluded['excluded'])==len(recipes)
            assert any('命中' in r['reason'] for r in excluded['excluded'])
            # Other recipes remain excluded due to unverified compositions, never relaxed for more results.
            checks.append('真实食材禁忌命中硬过滤；其他未核对成分食谱保守排除')
            client.delete('/api/diet/food-preferences/'+str(rule['id']))
            assert len(recommend()['items'])==len(recipes)
            report={'status':'passed','database_scope':'独立TemporaryDirectory，已清理后交付',
                    'manifest_sha256':package['manifest_sha256'],'dry_run':initial,'repeat_dry_run':repeat,
                    'imported_foods':len(foods),'imported_recipes':len(recipes),'search_results':searches,
                    'ordinary_recommendation_count':normal['eligible_count'],'hard_filter_excluded':len(excluded['excluded']),
                    'checks':checks,'normal_recommendation':normal,'targeted_recommendation':targeted,
                    'import_audit':result,'formal_database_used':False}
        with database(path) as c:
            report['integrity_check']=c.execute('PRAGMA integrity_check').fetchone()[0]
            report['foreign_key_violations']=[list(r) for r in c.execute('PRAGMA foreign_key_check')]
        # Keep audit evidence in the report; remove all DBs/clients before TemporaryDirectory exits.
        report['audits']=[__import__('json').loads(p.read_text(encoding='utf-8')) for p in (Path(folder)/'audit').glob('*.json')]
    report['temporary_directory_removed']=not Path(folder).exists()
    assert report['temporary_directory_removed']
    write_audit(report_path,report)
    return {k:report[k] for k in ('status','imported_foods','imported_recipes','ordinary_recommendation_count','integrity_check','temporary_directory_removed')}

def main():
    p=argparse.ArgumentParser(description='USDA包临时库验收；不接收正式数据库路径')
    p.add_argument('--package',type=Path,required=True);p.add_argument('--report',type=Path,required=True)
    args=p.parse_args();print(__import__('json').dumps(verify(args.package,args.report),ensure_ascii=False))

if __name__=='__main__':main()
