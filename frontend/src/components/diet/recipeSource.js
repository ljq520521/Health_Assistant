import { httpsSourceUrl, sourceLabels } from './foodPresentation.js'
import { isApprovedRecord, COURSE_APPROVAL_NOTICE } from './demoContext.js'

export function recipeSource(recipe, demo = null) {
  const note = typeof recipe.source_note === 'string' ? recipe.source_note : ''
  const human = note.split(/HAIMPORT1\s*:/i)[0].split(/[\r\n]/)
    .filter(line => !/[{}\[\]]|content_sha256|run_id|\bkey\s*[:=]|\bSHA256\b/i.test(line)).join(' ').trim()
  const draft = /待审核|待团队|尚未获得团队正式批准/.test(human)
  const imported = /HAIMPORT1\s*:/i.test(note)
  return {
    label: /项目团队自编/.test(human) ? `配方来源：项目团队自编${/AI辅助草案/.test(human) ? '，AI辅助草案' : ''}` : `配方来源：${human ? sourceLabels[recipe.source_type] || '其他参考资料' : '来源未填写'}`,
    description: human,
    review: isApprovedRecord(recipe, 'recipe', demo) ? `${COURSE_APPROVAL_NOTICE}；不代表实际试做或过敏原安全核验。`
      : draft ? '待团队正式审核；来源技术核验不代表配方已获批准。' : imported ? '团队审核状态未确认。' : '',
    trial: /未经实际试做/.test(human) ? '未经实际试做' : '实际试做情况未提供',
    href: httpsSourceUrl(recipe.source_url),
  }
}
