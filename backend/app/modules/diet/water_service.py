import json
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo
from app.database import connect
from app.modules.diet import settings
from app.modules.diet.service import require_profile
from app.modules.diet.library_service import LibraryError
from app.modules.diet.migration_003 import ready
from app.modules.diet.nutrition_service import effective
from app.modules.diet.nutrition_math import percent
from app.modules.diet.water_schemas import ReminderInput

def require_water(c):
    require_profile(c)
    if not ready(c):
        raise LibraryError(503,'WATER_MIGRATION_REQUIRED','饮水功能尚未启用，请先备份并经授权完成 003 迁移')

def utc(value):
    return value.astimezone(timezone.utc).isoformat(timespec='microseconds').replace('+00:00','Z')

def boundary(day, next_day=False):
    try:
        if next_day:
            day += timedelta(days=1)
        return utc(datetime.combine(day,time.min,tzinfo=ZoneInfo(settings.BUSINESS_TIME_ZONE)))
    except (OverflowError,ValueError):
        raise LibraryError(422,'INVALID_RANGE','日期超出可支持范围')

def row(c,id):
    result=c.execute('SELECT * FROM water_records WHERE id=? AND profile_id=1',(id,)).fetchone()
    if result is None:
        raise LibraryError(404,'WATER_NOT_FOUND','饮水记录不存在')
    return dict(result)

def get(path,id):
    with connect(path) as c:
        require_water(c)
        return row(c,id)

def records(path,start=None,end=None):
    if start and end and start>end:
        raise LibraryError(422,'INVALID_RANGE','开始日期不能晚于结束日期')
    with connect(path) as c:
        require_water(c)
        sql='SELECT * FROM water_records WHERE profile_id=1'; params=[]
        if start:
            sql+=' AND drank_at>=?';params.append(boundary(start))
        if end:
            sql+=' AND drank_at<?';params.append(boundary(end,True))
        return {'items':[dict(r) for r in c.execute(sql+' ORDER BY drank_at DESC,id DESC',params)]}

def save(path,data,id=None):
    with connect(path) as c:
        c.execute('BEGIN IMMEDIATE');require_water(c)
        values=(utc(data.drank_at),data.amount_ml,data.notes,settings.utc_now())
        if id is None:
            id=c.execute('INSERT INTO water_records(profile_id,drank_at,amount_ml,notes,updated_at,created_at) VALUES(1,?,?,?,?,?)',values+(values[-1],)).lastrowid
        else:
            row(c,id)
            c.execute('UPDATE water_records SET drank_at=?,amount_ml=?,notes=?,updated_at=? WHERE id=? AND profile_id=1',values+(id,))
        return row(c,id)

def delete(path,id):
    with connect(path) as c:
        c.execute('BEGIN IMMEDIATE');require_water(c);row(c,id)
        c.execute('DELETE FROM water_records WHERE id=? AND profile_id=1',(id,))

def summary(path,day):
    with connect(path) as c:
        c.execute('BEGIN');require_water(c)
        amounts=[r[0] for r in c.execute('SELECT amount_ml FROM water_records WHERE profile_id=1 AND drank_at>=? AND drank_at<?',(boundary(day),boundary(day,True)))]
        goal=effective(c,day)
        return summarize_amounts(day,amounts,goal)


def summarize_amounts(day,amounts,goal):
    """Preserve existing water API semantics; reports additionally expose missing status."""
    target=goal['water_ml'] if goal else None
    total=sum(amounts)
    ratio=percent(total,target) if target is not None else None
    return {'date':str(day),'time_zone':settings.BUSINESS_TIME_ZONE,'record_count':len(amounts),'total_ml':total,
            'data_status':'recorded' if amounts else 'no_records','target_ml':target,'goal_effective_from':goal['effective_from'] if goal else None,
            'achievement_percent':ratio,'progress_percent':min(100,ratio) if ratio is not None else None,
            'goal_met':target is not None and total>=target}

def reminder_row(c):
    r=c.execute('SELECT * FROM water_reminder_settings WHERE profile_id=1').fetchone()
    if r is None:
        return ReminderInput().model_dump() | {'profile_id':1,'created_at':None,'updated_at':None}
    result=dict(r);result['fixed_times']=json.loads(result.pop('fixed_times_json'))
    for field in ('enabled','pause_when_goal_met'):
        result[field]=bool(result[field])
    return result

def get_reminder(path):
    with connect(path) as c:
        require_water(c);return reminder_row(c)

def save_reminder(path,data):
    values=data.model_dump();values['fixed_times_json']=json.dumps(values.pop('fixed_times'))
    values['updated_at']=settings.utc_now()
    with connect(path) as c:
        c.execute('BEGIN IMMEDIATE');require_water(c)
        if c.execute('SELECT 1 FROM water_reminder_settings WHERE profile_id=1').fetchone():
            c.execute('UPDATE water_reminder_settings SET '+','.join(k+'=:'+k for k in values)+' WHERE profile_id=1',values)
        else:
            values['created_at']=values['updated_at']
            c.execute('INSERT INTO water_reminder_settings(profile_id,'+','.join(values)+') VALUES(1,'+','.join(':'+k for k in values)+')',values)
        return reminder_row(c)
