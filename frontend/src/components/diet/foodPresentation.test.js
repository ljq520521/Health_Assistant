import test from 'node:test'
import assert from 'node:assert/strict'
import { foodSource, httpsSourceUrl, nutrientDisplay } from './foodPresentation.js'

test('0 remains a known quantity, NULL and missing values remain unknown', () => {
  assert.deepEqual(nutrientDisplay(0), { known: true, text: '0' })
  for (const value of [null, undefined, '', NaN, Infinity]) assert.deepEqual(nutrientDisplay(value), { known: false, text: '未知' })
  assert.equal(nutrientDisplay(30.2).text, '30.2')
})
test('only absolute HTTPS links without credentials or malformed whitespace are clickable', () => {
  for (const url of ['', null, '/relative', 'http://example.com', 'javascript:alert(1)', 'data:text/html,test', 'https://', 'https://user:pass@example.com', 'https://exa mple.com', 'https://example.com\\fake']) assert.equal(httpsSourceUrl(url), '')
  assert.equal(httpsSourceUrl('https://fdc.nal.usda.gov/food-details/170556/nutrients'), 'https://fdc.nal.usda.gov/food-details/170556/nutrients')
})
test('verified pending USDA imports have concise source and pending notice, without mutation', () => {
  const food = Object.freeze({ source_type: 'referenced', source_url: 'https://fdc.nal.usda.gov/food-details/170556/nutrients', source_note: '来源数据已技术核验，尚未获得团队正式批准；仅限开发演示。\nUSDA FoodData Central | FDC 170556\nHAIMPORT1:{"content_sha256":"hash","key":"usda:fdc:170556","run_id":"run"}' })
  const before = JSON.stringify(food), source = foodSource(food)
  assert.equal(source.label, '数据来源：USDA FoodData Central')
  assert.equal(source.review, '已核验来源，待团队正式审核')
  assert.doesNotMatch(JSON.stringify(source), /HAIMPORT1|content_sha256|run_id|"key"/)
  assert.equal(JSON.stringify(food), before)
})
test('an import marker alone does not prove USDA identity, verification or approval', () => {
  const result = foodSource({ source_type: 'referenced', source_note: 'HAIMPORT1:{"key":"usda:fdc:1","approved":true}' })
  assert.equal(result.label, '来源未填写')
  assert.equal(result.review, '审核状态未确认，请核对来源')
})
test('manual, reference and example sources keep their original types', () => {
  for (const [type, label] of [['user_entered', '用户录入'], ['referenced', '参考资料'], ['example', '示例数据']]) {
    assert.equal(foodSource({ source_type: type, source_note: '包装标签' }).label, `数据来源：${label}`)
  }
  assert.equal(foodSource({ source_type: 'user_entered' }).label, '来源未填写')
})
test('unknown or JSON-only source is not displayed as a real citation', () => {
  for (const note of ['', '{"content_sha256":"hash","run_id":"run","key":"foo"}', '[{"key":"foo"}]']) {
    assert.equal(foodSource({ source_type: 'referenced', source_note: note }).label, '来源未填写')
  }
})
test('long source notes and malicious markup never enter card text', () => {
  const result = foodSource({ source_type: 'user_entered', source_note: '<script>alert(1)</script>' + '很长的备注'.repeat(200) })
  assert.equal(result.label, '数据来源：用户录入')
  assert.equal(result.href, '')
})
test('USDA cannot be inferred from an impersonating domain or metadata tail', () => {
  for (const url of ['https://fdc.nal.usda.gov.example.com', 'https://example.com/fdc.nal.usda.gov']) {
    assert.equal(foodSource({ source_type: 'referenced', source_url: url }).label, '数据来源：参考资料')
  }
  assert.equal(foodSource({ source_type: 'referenced', source_note: '包装标签\nHAIMPORT1:{"name":"USDA FoodData Central"}' }).label, '数据来源：参考资料')
})
test('explicit USDA citation can be shown without a source URL', () => {
  const result = foodSource({ source_type: 'referenced', source_note: 'USDA FoodData Central | FDC 170556' })
  assert.equal(result.label, '数据来源：USDA FoodData Central')
  assert.equal(result.href, '')
  assert.equal(result.review, '')
})
