"""Read-only reports with traceable rules, sharing existing calculation functions."""
from collections import Counter,defaultdict
from datetime import datetime,timezone,timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo
from app.database import connect
from app.modules.diet import settings,nutrition_service,water_service
from app.modules.diet.library_service import LibraryError
from app.modules.diet.nutrition_math import NUTRIENTS,total,percent,number

LABELS={'calories_kcal':'热量','protein_g':'蛋白质','fat_g':'脂肪','carbohydrate_g':'碳水化合物'}
MEALS={'breakfast':'早餐','lunch':'午餐','dinner':'晚餐','snack':'加餐'}
def today():return datetime.now(timezone.utc).astimezone(ZoneInfo(settings.BUSINESS_TIME_ZONE)).date()
def average(value,days):return number(Decimal(str(value))/Decimal(days)) if value is not None and days else None

def report(path,selected,period):
    current=today()
    if selected>current:raise LibraryError(422,'REPORT_FUTURE_DATE','报告日期不能晚于业务时区的今天')
    start,natural_end=nutrition_service.period(selected,period)
    end=min(natural_end,current);days=(end-start).days+1
    with connect(path) as c:
        c.execute('BEGIN');nutrition_service.require_goals(c);water_service.require_water(c)
        records=[dict(r) for r in c.execute('SELECT * FROM diet_records WHERE profile_id=1 AND record_date BETWEEN ? AND ? ORDER BY record_date,id',(str(start),str(end)))]
        goals=[dict(r) for r in c.execute('SELECT * FROM diet_daily_goals WHERE profile_id=1 AND effective_from<=? ORDER BY effective_from',(str(end),))]
        waters=[dict(r) for r in c.execute('SELECT drank_at,amount_ml FROM water_records WHERE profile_id=1 AND drank_at>=? AND drank_at<? ORDER BY drank_at,id',(water_service.boundary(start),water_service.boundary(end,True)))]
    nutrition=nutrition_service.summarize_rows(records,goals,start,end,period)
    totals=nutrition['total'];daily=nutrition['daily']
    meal_counts=Counter(r['meal_type'] for r in records)
    recorded_dates=sorted({r['record_date'] for r in records})
    missing_dates=[d['actual_from'] for d in daily if not d['record_count']]
    by_water=defaultdict(list)
    for r in waters:
        local=datetime.fromisoformat(r['drank_at'].replace('Z','+00:00')).astimezone(ZoneInfo(settings.BUSINESS_TIME_ZONE)).date()
        by_water[str(local)].append(r['amount_ml'])
    water_daily=[];goal_index=0;goal=None
    for offset in range(days):
        day=start+timedelta(days=offset)
        while goal_index<len(goals) and goals[goal_index]['effective_from']<=str(day):
            goal=goals[goal_index];goal_index+=1
        w=water_service.summarize_amounts(day,by_water[str(day)],goal)
        # An empty recorded sum is mathematically zero, but actual intake is unknown.
        w['recorded_sum_ml']=w.pop('total_ml')
        w['known_sum_ml']=w['recorded_sum_ml'] if w['record_count'] else None
        if not w['record_count']:
            w.update(achievement_percent=None,progress_percent=None,goal_met=None)
        water_daily.append(w)
    water_days=sum(bool(w['record_count']) for w in water_daily)
    water_missing=[w['date'] for w in water_daily if not w['record_count']]
    water_known=sum(w['recorded_sum_ml'] for w in water_daily) if waters else None
    water_targets=[w['target_ml'] for w in water_daily if w['target_ml'] is not None]
    water_target=total(water_targets,rounded=False) if len(water_targets)==days else None
    water_ratio=percent(water_known,water_target) if water_known is not None and water_target is not None else None
    water={'record_count':len(waters),'recorded_days':water_days,'missing_days':days-water_days,'missing_dates':water_missing,
           'known_sum_ml':water_known,'data_status':'no_records' if not waters else 'partial' if water_missing else 'recorded',
           'target_ml':water_target,'target_missing_days':days-len(water_targets),'achievement_percent':water_ratio,
           'ratio_basis':'known_only' if water_ratio is not None and water_missing else 'recorded_only' if water_ratio is not None else None,
           'daily':water_daily}
    calories=totals['nutrients']['calories_kcal']['known_sum']
    averages={'known_calories_per_recorded_day':average(calories,totals['recorded_days']),
              'known_calories_per_period_day':average(calories,days),'recorded_day_denominator':totals['recorded_days'],
              'period_day_denominator':days,'basis':'known_recorded_sum_only',
              'note':'分子仅为已知热量小计；有记录天数包含营养未知的记录日。区间摊分不表示缺失日实际摄入为0，也不代表实际日均摄入。'}
    suggestions=[]
    def advice(code,text,evidence):suggestions.append({'rule_id':code,'text':text,'evidence':evidence})
    if missing_dates:advice('missing_diet_days',f'有{len(missing_dates)}天尚未记录饮食，可补充实际记录；不能据此判断没有进食。',{'path':'overview.missing_dates','dates':missing_dates})
    for key in NUTRIENTS:
        metric=totals['nutrients'][key]
        if metric['unknown_count']:
            advice('unknown_'+key,f"{LABELS[key]}有{metric['unknown_count']}条记录数值未知。请核对记录及营养来源；更新食物库不会自动改写历史快照。",{'path':'nutrition.total.nutrients.'+key,'unknown_count':metric['unknown_count']})
        ratio=metric['achievement_percent']
        if ratio is not None:
            advice('target_'+key,f"已记录的已知{LABELS[key]}相当于区间自设目标的{ratio:g}%；这是记录比例，不用于判断不足或过量。",{'path':'nutrition.total.nutrients.'+key,'known_sum':metric['known_sum'],'target':metric['target'],'achievement_percent':ratio,'data_status':metric['data_status']})
    if records:advice('meal_distribution','餐次记录分布：'+'、'.join(f'{label}{meal_counts[key]}条' for key,label in MEALS.items())+'。按食物记录条数计算，不等于实际进餐次数。',{'path':'meal_distribution','counts':{k:meal_counts[k] for k in MEALS}})
    if water_missing:advice('missing_water_days',f'有{len(water_missing)}天暂无饮水记录，不代表实际没有饮水。',{'path':'water.missing_dates','dates':water_missing})
    below=[{'date':w['date'],'recorded_ml':w['known_sum_ml'],'target_ml':w['target_ml'],'gap_ml':number(Decimal(str(w['target_ml']))-Decimal(str(w['known_sum_ml'])))} for w in water_daily if w['record_count'] and w['target_ml'] is not None and w['known_sum_ml']<w['target_ml']]
    if below:advice('recorded_water_below_target',f'有{len(below)}天的已记录饮水量低于当日自设目标；请先确认记录是否完整，不据此判断实际饮水不足。',{'path':'water.daily','days':below})
    if water_ratio is not None:advice('water_target',f'区间已记录饮水量相当于自设累计目标的{water_ratio:g}%；目标按每日实际生效版本累计。',{'path':'water','known_sum_ml':water_known,'target_ml':water_target,'achievement_percent':water_ratio,'data_status':water['data_status']})
    notes=['本报告仅基于当前档案已录入的饮食和饮水记录，不进行医学诊断。',
           '0表示已填写数值为零；NULL表示未知或无可计算数据；no_records表示当天没有记录。',
           nutrition['completeness_note'],averages['note'],
           '目标按每天生效版本累计；任何一天未设置该项目标，区间目标及达成率均不计算。']
    if totals['example_record_count']:notes.append(f"含{totals['example_record_count']}条示例来源饮食记录，不能作为真实营养依据。")
    if end==current:notes.append('当前统计周期尚未结束，今天的记录可能继续变化。')
    return {'schema_version':'diet-report-v1','period':period,'selected_date':str(selected),'time_zone':settings.BUSINESS_TIME_ZONE,
            'generated_at':settings.utc_now(),'period_from':str(start),'period_to':str(natural_end),'date_from':str(start),'date_to':str(end),
            'period_days':days,'natural_period_days':(natural_end-start).days+1,'is_partial_period':end==current or end<natural_end,
            'includes_today':end==current,'overview':{'record_count':len(records),'recorded_days':len(recorded_dates),'missing_days':len(missing_dates),'missing_dates':missing_dates,
            'recorded_meal_slots':len({(r['record_date'],r['meal_type']) for r in records}),'example_record_count':totals['example_record_count']},
            'meal_distribution':[{'meal_type':key,'label':label,'record_count':meal_counts[key]} for key,label in MEALS.items()],
            'averages':averages,'nutrition':nutrition,'water':water,'suggestions':suggestions,'completeness_notes':notes}
