from datetime import date, timedelta
from collections import defaultdict
from calendar import monthrange
from app.database import connect
from app.modules.diet.service import require_profile
from app.modules.diet.library_service import LibraryError
from app.modules.diet.migration_002 import ready
from app.modules.diet.settings import utc_now
from app.modules.diet.nutrition_math import NUTRIENTS, total, percent

GOALS = (*NUTRIENTS, 'water_ml')

def require_goals(c):
    require_profile(c)
    if not ready(c):
        raise LibraryError(503,'GOALS_MIGRATION_REQUIRED','营养分析与目标尚未启用，请先经确认完成 002 升级')

def effective(c, day):
    row = c.execute('SELECT * FROM diet_daily_goals WHERE profile_id=1 AND effective_from<=? ORDER BY effective_from DESC LIMIT 1',(str(day),)).fetchone()
    return dict(row) if row else None

def get_goal(path, day):
    with connect(path) as c:
        require_goals(c)
        return {'date':str(day),'goal':effective(c,day)}

def history(path):
    with connect(path) as c:
        require_goals(c)
        return {'items':[dict(r) for r in c.execute('SELECT * FROM diet_daily_goals WHERE profile_id=1 ORDER BY effective_from DESC')]}

def save_goal(path,data):
    changes=data.model_dump(mode='json',exclude_unset=True)
    day=changes.pop('effective_from')
    with connect(path) as c:
        c.execute('BEGIN IMMEDIATE')
        require_goals(c)
        base=effective(c,day)
        values={k:base[k] if base else None for k in GOALS}
        values.update(changes)
        values.update(effective_from=day,updated_at=utc_now())
        existing=c.execute('SELECT id FROM diet_daily_goals WHERE profile_id=1 AND effective_from=?',(day,)).fetchone()
        if existing:
            values['id']=existing[0]
            c.execute('UPDATE diet_daily_goals SET '+','.join(k+'=:'+k for k in GOALS)+',updated_at=:updated_at WHERE id=:id AND profile_id=1',values)
        else:
            values['created_at']=values['updated_at']
            c.execute('INSERT INTO diet_daily_goals(profile_id,'+','.join(values)+') VALUES(1,'+','.join(':'+k for k in values)+')',values)
        return effective(c,day)

def period(day,group):
    if group=='day': return day,day
    if group=='week':
        start=day-timedelta(days=day.weekday())
        return start,date.fromordinal(min(date.max.toordinal(),start.toordinal()+6))
    start=day.replace(day=1)
    end=day.replace(day=monthrange(day.year,day.month)[1])
    return start,end

def summary(path,start,end,group):
    if start>end or (end-start).days>365:
        raise LibraryError(422,'INVALID_RANGE','起止日期顺序需正确，查询范围最多 366 天')
    # One read transaction keeps records and goal versions in the same snapshot.
    with connect(path) as c:
        c.execute('BEGIN')
        require_goals(c)
        records=[dict(r) for r in c.execute('SELECT * FROM diet_records WHERE profile_id=1 AND record_date BETWEEN ? AND ? ORDER BY record_date,id',(str(start),str(end)))]
        goals=[dict(r) for r in c.execute('SELECT * FROM diet_daily_goals WHERE profile_id=1 AND effective_from<=? ORDER BY effective_from',(str(end),))]
    return summarize_rows(records,goals,start,end,group)


def summarize_rows(records,goals,start,end,group):
    """Shared calculation over one caller-owned database snapshot."""
    by_day=defaultdict(list)
    for r in records: by_day[r['record_date']].append(r)
    days=[]; goal_index=0; current=None
    for offset in range((end-start).days+1):
        day=start+timedelta(days=offset)
        while goal_index<len(goals) and goals[goal_index]['effective_from']<=str(day):
            current=goals[goal_index]; goal_index+=1
        rows=by_day[str(day)]
        days.append({'date':str(day),'rows':rows,'goal':current})

    def bucket(subset, natural_start,natural_end):
        rows=[r for d in subset for r in d['rows']]
        missing_days=sum(not d['rows'] for d in subset)
        metrics={}
        for key in NUTRIENTS:
            known=[r[key] for r in rows if r[key] is not None]
            unknown=len(rows)-len(known)
            value=total(known) if known else None
            status='no_records' if not rows else 'unknown' if not known else 'partial' if unknown or missing_days else 'complete'
            targets=[d['goal'][key] for d in subset if d['goal'] and d['goal'][key] is not None]
            missing_targets=len(subset)-len(targets)
            target=total(targets, rounded=False) if not missing_targets else None
            ratio=percent(value,target) if value is not None and target is not None else None
            metrics[key]={'known_sum':value,'known_count':len(known),'unknown_count':unknown,'record_count':len(rows),'data_status':status,'target':target,'target_missing_days':missing_targets,'achievement_percent':ratio,'ratio_basis':'known_only' if ratio is not None and status=='partial' else 'complete_recorded' if ratio is not None else None}
        return {'period_from':str(natural_start),'period_to':str(natural_end),'actual_from':subset[0]['date'],'actual_to':subset[-1]['date'],'is_partial_period':str(natural_start)!=subset[0]['date'] or str(natural_end)!=subset[-1]['date'],'record_count':len(rows),'recorded_days':len(subset)-missing_days,'missing_days':missing_days,'example_record_count':sum(bool(r.get('is_example')) for r in rows),'nutrients':metrics}
    daily=[bucket([d],date.fromisoformat(d['date']),date.fromisoformat(d['date'])) for d in days]
    groups=[]; subset=[]; previous=None
    for d in days:
        bounds=period(date.fromisoformat(d['date']),group)
        if previous and bounds!=previous:
            groups.append(bucket(subset,*previous)); subset=[]
        subset.append(d);previous=bounds
    groups.append(bucket(subset,*previous))
    return {'date_from':str(start),'date_to':str(end),'group_by':group,'items':groups,'daily':daily,'total':bucket(days,start,end),'completeness_note':'完整仅指已录入记录字段齐全，不表示已记录全部饮食；比例不用于健康判断。'}


def record_summary(path,date_from=None,date_to=None):
    from app.modules.diet.service import list_records
    days=defaultdict(list)
    for record in list_records(path,date_from,date_to)['items']:
        days[record['record_date']].append(record['calories_kcal'])
    return {'items':[{'date':day,'known':total([v for v in values if v is not None]) if any(v is not None for v in values) else None,'knownCount':sum(v is not None for v in values),'unknown':sum(v is None for v in values)} for day,values in sorted(days.items(),reverse=True)]}
