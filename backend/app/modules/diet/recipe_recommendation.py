"""Read-only deterministic product ranking; never a medical or allergy-safety score."""
from typing import Annotated
from pydantic import Field
from app.database import connect
from app.modules.diet.recipe_schemas import Input,ID
from app.modules.diet.schemas import CalendarDate
from app.modules.diet.recipe_service import require_recipes,detail,nutrition
from app.modules.diet.recipe_preference_service import composition_row
from app.modules.diet.nutrition_service import effective
from app.modules.diet.nutrition_math import NUTRIENTS,scale
from app.modules.diet.settings import utc_now

BASE_WEIGHTS={'nutrition':.5,'inventory':.3,'preference':.2}
ALGORITHM_VERSION='local-rules-v1'
class RecommendationInput(Input):
    date: CalendarDate
    portions: Annotated[float,Field(strict=True,ge=.0001,le=10000,allow_inf_nan=False)]=1
    target_ratio: Annotated[float,Field(strict=True,ge=.0001,le=1,allow_inf_nan=False)] | None=None
    category_id: ID | None=None
    max_preparation_minutes: Annotated[int,Field(strict=True,ge=0,le=100000)] | None=None
    include_examples: bool=False
    limit: Annotated[int,Field(strict=True,ge=1,le=50)]=10

def matches(rule,ingredient,composition,include_possible=True):
    if rule['food_id'] is not None:return rule['food_id']==ingredient['food_id']
    return any(t['term_id']==rule['term_id'] and (include_possible or t['relation']=='contains') for t in composition['terms'])

def recommend(path,data):
    with connect(path) as c:
        c.execute('BEGIN');require_recipes(c)
        goal=effective(c,data.date)
        rules=[dict(r) for r in c.execute('SELECT * FROM diet_food_preferences WHERE profile_id=1 ORDER BY id')]
        hard=[r for r in rules if r['rule_type'] in ('allergy','forbidden')]
        soft=[r for r in rules if r['rule_type'] in ('like','dislike')]
        stock={r['food_id']:r['quantity_g'] for r in c.execute('SELECT * FROM diet_inventory_items WHERE profile_id=1')}
        ids=[r[0] for r in c.execute('SELECT id FROM diet_recipes WHERE profile_id=1 AND archived_at IS NULL ORDER BY id')]
        compositions={};results=[];excluded=[]
        for id in ids:
            recipe=detail(c,id);reason=None
            if data.category_id is not None and recipe['category_id']!=data.category_id:reason='不符合所选食谱分类'
            if data.max_preparation_minutes is not None and (recipe['preparation_minutes'] is None or recipe['preparation_minutes']>data.max_preparation_minutes):reason='制作时间未知或超过筛选上限'
            if recipe['is_example'] and not data.include_examples:reason='示例食谱默认不参与推荐'
            if any(i['food_archived_at'] for i in recipe['ingredients']):reason='食材已归档，需先维护食谱'
            if reason:
                excluded.append({'recipe_id':id,'name':recipe['name'],'reason':reason});continue
            for i in recipe['ingredients']:
                if i['food_id'] not in compositions:compositions[i['food_id']]=composition_row(c,i['food_id'])
            # Every hard rule is checked before computing any ranking dimension.
            for i in recipe['ingredients']:
                comp=compositions[i['food_id']]
                hits=[r for r in hard if matches(r,i,comp)]
                if hits:
                    reason=f"{i['food_name_snapshot']} 命中过敏/禁用规则（含有或可能含有；规则ID：{','.join(str(r['id']) for r in hits)}）";break
            if not reason and hard:
                for i in recipe['ingredients']:
                    comp=compositions[i['food_id']]
                    if comp['outdated'] or comp['ingredient_status']!='declared_complete' or comp['allergen_status']!='declared_complete':
                        reason=f"{i['food_name_snapshot']} 的成分/过敏原信息未知、不完整或核对已过期，按已有硬禁忌保守排除";break
            if reason:
                excluded.append({'recipe_id':id,'name':recipe['name'],'reason':reason});continue

            values=nutrition(recipe,data.portions);metrics={};scores=[];targeted=0;known_targeted=0
            for nutrient in NUTRIENTS:
                daily=goal[nutrient] if goal else None
                target=daily*data.target_ratio if daily is not None and data.target_ratio is not None else None
                actual=values[nutrient]['total'];score=None
                status='target_unset' if daily is None else 'ratio_unset' if data.target_ratio is None else 'target_not_computable' if not target else 'nutrition_unknown' if actual is None else 'computed'
                if target:
                    targeted+=1
                    if actual is not None:
                        known_targeted+=1;score=100*max(0,1-abs(actual-target)/target);scores.append(score)
                metrics[nutrient]={'actual':actual,'target':target if target else None,'score':score,'status':status}
            ingredients=[];coverages=[];preferences=[]
            for i in recipe['ingredients']:
                need=i['amount_g']*data.portions/recipe['servings'];available=stock.get(i['food_id'],0)
                shortage=max(0,need-available)
                ingredients.append({'food_id':i['food_id'],'name':i['food_name_snapshot'],'required_g':need,'available_g':available,'shortage_g':shortage,'registered':i['food_id'] in stock})
                coverages.append(min(1,available/need))
                comp=compositions[i['food_id']]
                # Known contains only for likes; may_contain cannot earn a liking bonus.
                matched=[r['rule_type'] for r in soft if matches(r,i,comp,False)]
                preferences.append(-1 if 'dislike' in matched else 1 if 'like' in matched else 0)
            subscores={'nutrition':sum(scores)/len(scores) if scores else None,
                       'inventory':100*sum(coverages)/len(coverages) if stock else None,
                       'preference':50+50*sum(preferences)/len(preferences) if soft else None}
            weight_sum=sum(BASE_WEIGHTS[k] for k,v in subscores.items() if v is not None)
            weights={k:BASE_WEIGHTS[k]/weight_sum if v is not None else 0 for k,v in subscores.items()}
            base=sum(weights[k]*v for k,v in subscores.items() if v is not None) if weight_sum else None
            completeness=sum(v['complete'] for v in values.values())/len(NUTRIENTS)
            target_completeness=known_targeted/targeted if targeted else None
            # Separate data-confidence deduction, never substituted for a nutrient value.
            penalty=20*(1-target_completeness) if target_completeness is not None else 0
            reasons=[]
            for k,label in (('nutrition','营养匹配'),('inventory','库存匹配'),('preference','喜好匹配')):
                if subscores[k] is None:reasons.append(label+'条件不足，未参与评分')
                else:reasons.append(f'{label} {subscores[k]:.1f} 分，实际权重 {weights[k]*100:.1f}%')
            if penalty:reasons.append(f'目标相关营养数据不完整：独立排序扣分 {penalty:.1f}，不表示营养不足')
            if base is None:reasons.append('无有效评分维度，按缺料种类数、食谱ID稳定展示')
            if recipe['snapshot_outdated']:reasons.append('营养使用保存的历史快照；食物库已更新，可在食谱库主动刷新')
            results.append({'recipe':recipe,'portions':data.portions,'nutrition':values,'ingredients':ingredients,'missing_ingredients':[i for i in ingredients if i['shortage_g']>0],
                'scores':subscores,'weights':weights,'base_score':base,'data_penalty':penalty,'score':max(0,base-penalty) if base is not None else None,
                'nutrition_completeness':completeness,'target_nutrition_completeness':target_completeness,'metrics':metrics,'reasons':reasons,
                'composition_verified':all(not compositions[i['food_id']]['outdated'] and compositions[i['food_id']]['ingredient_status']=='declared_complete' and compositions[i['food_id']]['allergen_status']=='declared_complete' for i in recipe['ingredients'])})
        results.sort(key=lambda r:(r['score'] is None,-r['score'] if r['score'] is not None else 0,len(r['missing_ingredients']),r['recipe']['id']))
        warnings=['排序分仅用于产品推荐，不是医学健康评分；成分资料可能不完整，不能保证绝对过敏安全。']
        if not hard:warnings.append('尚未设置饮食禁忌，推荐结果未进行个人禁忌匹配')
        if not stock:warnings.append('尚未登记库存，库存维度未参与评分；缺料清单表示尚未登记可用量。')
        if data.include_examples:warnings.append('本次包含明确标记的示例数据，请勿作为真实营养依据。')
        return {'algorithm_version':ALGORITHM_VERSION,'generated_at':utc_now(),'conditions':data.model_dump(mode='json'),'goal':goal,'base_weights':BASE_WEIGHTS,
                'hard_rule_count':len(hard),'inventory_registered':bool(stock),'warnings':warnings,'eligible_count':len(results),'items':results[:data.limit],'excluded':excluded}
