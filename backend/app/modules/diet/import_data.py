"""python -m app.modules.diet.import_data --help (default: read-only)."""
import argparse
import json
from pathlib import Path
from app.modules.diet.import_service import load_package, dry_run, apply_package

def main(argv=None):
    parser=argparse.ArgumentParser(description='离线审核数据导入；默认dry-run，不初始化数据库，不建档，不执行迁移')
    parser.add_argument('--package',type=Path,required=True)
    parser.add_argument('--database',type=Path,required=True)
    parser.add_argument('--expected-manifest-sha256')
    parser.add_argument('--expected-plan-sha256')
    parser.add_argument('--audit-dir',type=Path)
    parser.add_argument('--apply',action='store_true')
    parser.add_argument('--confirm-database',type=Path)
    args=parser.parse_args(argv)
    try:
        package=load_package(args.package,expected_manifest_sha256=args.expected_manifest_sha256)
        if args.apply:
            if not all((args.expected_manifest_sha256,args.expected_plan_sha256,args.audit_dir,args.confirm_database)):
                parser.error('--apply须指定审核manifest/plan摘要、audit-dir及confirm-database')
            if args.database.resolve(strict=True)!=args.confirm_database.resolve(strict=True):
                parser.error('确认数据库路径与目标不一致')
            result=apply_package(args.database,package,args.audit_dir,expected_plan_sha256=args.expected_plan_sha256)
        else:
            result={'status':'dry_run','read_only':True,**dry_run(args.database,package,args.audit_dir)}
        print(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False))
        return 2 if result.get('counts',{}).get('conflict') else 0
    except Exception as error:
        print(json.dumps({'status':'rejected','error_type':type(error).__name__,'error':str(error),
                          'code':getattr(error,'code',None),'http_status':getattr(error,'status',None)},ensure_ascii=False))
        return 2

if __name__=='__main__':
    raise SystemExit(main())
