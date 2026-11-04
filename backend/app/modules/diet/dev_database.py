"""Create a NEW disposable acceptance database. Never accepts an existing path."""
import argparse
import json
import tempfile
from pathlib import Path
from app.database import init_database, connect
from app.modules.diet.migrations import migrate_diet
from app.modules.diet.migration_002 import migrate_goals
from app.modules.diet.migration_003 import migrate_water
from app.modules.diet.migration_004 import migrate_recipes

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--without-profile',action='store_true')
    parser.add_argument('--demo',action='store_true',help='仅在新临时库加入明确标记的示例食物')
    args=parser.parse_args()
    path=Path(tempfile.mkdtemp(prefix='health-diet-recipes-'))/'health.db'
    init_database(path);migrate_diet(path);migrate_goals(path);migrate_water(path);migrate_recipes(path)
    if not args.without_profile:
        with connect(path) as c:c.execute("INSERT INTO profiles(id,display_name) VALUES(1,'食谱临时验收档案')")
        if args.demo:
            from app.modules.diet.library_schemas import FoodInput
            from app.modules.diet.library_service import save_food
            save_food(path,FoodInput(name='联动验收示例（非真实营养）',source_type='example',source_note='仅用于验收的虚构数值',calories_per_100g=100,protein_g_per_100g=10,fat_g_per_100g=0))
    print(json.dumps({'database_path':str(path),'temporary':True,'profile_created':not args.without_profile},ensure_ascii=False))
if __name__=='__main__':main()
