import test from 'node:test'
import assert from 'node:assert/strict'
import { isDevelopmentDemo, isCourseApproved, isApprovedRecord, demoApprovalText } from './demoContext.js'
import { foodSource } from './foodPresentation.js'
import { recipeSource } from './recipeSource.js'
import { demoReportNotice } from './reportCopy.js'

const food = {id: 1, name:'米饭', source_type:'referenced', source_url:'https://fdc.nal.usda.gov/food-details/1/nutrients',
  source_note:'食品来源已技术核验\nHAIMPORT1:{"key":"usda:fdc:1"}', calories_per_100g:130}
const recipe = {id: 2, name:'演示食谱', source_note:'项目团队自编，AI辅助草案，未经实际试做。\nHAIMPORT1:{"key":"recipe:1"}',
  ingredients:[{food_id:1,amount_g:100}], servings:1, steps:['示例步骤'], revision:1}
const context = {environment:'development_demo', database_path:'test/demo.db', notice:'课程演示数据已获团队批准',
  approved:true, review_status:'approved', course_approval:{status:'approved',scope:'team_course_demonstration_only',manifest_sha256:'a'.repeat(64)},
  approved_records:{food:{1:food}, recipe:{2:recipe}}}

test('course approval, source verification and allergen review remain distinct', () => {
  assert.ok(isCourseApproved(context))
  assert.match(foodSource(food, context).review, /课程演示数据已获团队批准/)
  assert.match(foodSource(food, context).review, /食品来源已技术核验/)
  assert.match(foodSource(food, context).review, /过敏原未完整核验/)
  const source=recipeSource(recipe, context)
  assert.match(source.label,/AI辅助草案/)
  assert.equal(source.trial,'未经实际试做')
  assert.match(source.review,/课程演示数据已获团队批准/)
  assert.doesNotMatch(source.review,/待团队|pending/)
})
test('edited, new and marker-only rows cannot inherit package approval', () => {
  assert.ok(isApprovedRecord({...food, extra:'API metadata'},'food',context))
  for(const changed of [{...food,calories_per_100g:999}, {...food,id:99}, {...food,source_note:'approved'}])
    assert.equal(isApprovedRecord(changed,'food',context),false)
  for(const changed of [{...recipe,servings:2}, {...recipe,ingredients:[{food_id:1,amount_g:101}]}, {...recipe,steps:['changed']}, {...recipe,revision:2}])
    assert.equal(isApprovedRecord(changed,'recipe',context),false)
  assert.doesNotMatch(foodSource(food).review,/已获团队批准/)
  assert.doesNotMatch(recipeSource(recipe).review,/已获团队批准/)
})
test('legacy v2 stays pending; course approval never suppresses demo marking', () => {
  const v2={database_path:'test/demo.db',notice:'来源数据已技术核验，尚未获得团队正式批准',review_status:'pending_final_confirmation',approved:false}
  assert.equal(isCourseApproved(v2),false)
  assert.equal(demoApprovalText(v2),'来源数据待正式审核')
  assert.match(demoReportNotice(v2),/开发演示.*非真实健康记录.*待正式审核/)
  for(const approved of [true,false,undefined]) assert.match(demoReportNotice({...context,approved}),/开发演示.*非真实健康记录.*已获团队批准/)
  assert.match(recipeSource({...recipe,source_note:'项目团队自编，AI辅助草案，待审核；未经实际试做'}).review,/待团队正式审核/)
})
test('ordinary environment and unrelated flags do not acquire a demo watermark', () => {
  for(const input of [null,{}, {approved:false}, {profile_id:1}, {...context,environment:'production'}]) {
    assert.equal(isDevelopmentDemo(input),false)
    assert.equal(demoReportNotice(input),'')
  }
  assert.equal(isCourseApproved({...context,course_approval:{status:'approved',scope:'medical'}}),false)
})
