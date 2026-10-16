// Only /api/diet/config.demo may supply this context. Profile IDs and note text
// are never sufficient to identify a demo or approve a record.
export const DIET_DEMO_CONTEXT = Symbol('diet-demo-context')
export const COURSE_APPROVAL_NOTICE = '课程演示数据已获团队批准'
export function isDevelopmentDemo(demo) {
  if (!demo || typeof demo.database_path !== 'string' || !demo.database_path
      || typeof demo.notice !== 'string' || !demo.notice) return false
  if (demo.environment !== undefined) return demo.environment === 'development_demo'
  // Compatibility with the existing v2 demo factory. Approval is intentionally
  // not an environment discriminator, including when its boolean is true.
  return ['pending_final_confirmation', 'approved'].includes(demo.review_status)
}
export function isCourseApproved(demo) {
  return isDevelopmentDemo(demo) && demo.review_status === 'approved'
    && demo.course_approval?.status === 'approved'
    && demo.course_approval?.scope === 'team_course_demonstration_only'
    && /^[a-f0-9]{64}$/.test(demo.course_approval?.manifest_sha256 || '')
}
export function demoApprovalText(demo) {
  return isCourseApproved(demo) ? COURSE_APPROVAL_NOTICE
    : demo?.review_status === 'pending_final_confirmation' ? '来源数据待正式审核' : '课程演示审批状态未确认'
}
function matches(actual, expected) {
  if (Array.isArray(expected)) return Array.isArray(actual) && actual.length === expected.length
    && expected.every((item, i) => matches(actual[i], item))
  if (expected && typeof expected === 'object') return actual && typeof actual === 'object'
    && Object.entries(expected).every(([key, value]) => matches(actual[key], value))
  return actual === expected
}
export function isApprovedRecord(row, kind, demo) {
  const expected = demo?.approved_records?.[kind]?.[row.id]
  return isCourseApproved(demo) && !!expected && matches(row, expected)
}
