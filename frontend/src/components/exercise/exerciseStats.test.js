import test from 'node:test'
import assert from 'node:assert/strict'
import {
  buildTrend,
  formatMinutes,
  groupByDate,
  shiftDate,
  shortDate,
  summarize,
  todayInZone,
  validDate,
  weekdayLabel,
} from './exerciseStats.js'

const record = (id, record_date, duration_minutes, intensity = 'medium', notes = '') => ({
  id,
  record_date,
  duration_minutes,
  intensity,
  notes,
})

test('汇总总时长、活跃天数、单次均值与强度分布', () => {
  const summary = summarize([
    record(1, '2026-10-19', 30, 'low'),
    record(2, '2026-10-19', 20, 'high'),
    record(3, '2026-10-20', 40, 'medium'),
    record(4, '2026-10-20', 0, 'medium'),
  ])
  assert.equal(summary.count, 4)
  assert.equal(summary.totalMinutes, 90)
  assert.equal(summary.activeDays, 2)
  assert.equal(summary.averageSession, 23)
  assert.equal(summary.averagePerActiveDay, 45)
  assert.equal(summary.longest, 40)
  assert.deepEqual(summary.intensityMinutes, { low: 30, medium: 40, high: 20 })
  assert.deepEqual(summarize([]), {
    count: 0,
    totalMinutes: 0,
    activeDays: 0,
    averageSession: 0,
    averagePerActiveDay: 0,
    longest: 0,
    intensityMinutes: { low: 0, medium: 0, high: 0 },
  })
})

test('按日期分组倒序，同日合计并保持新记录在前', () => {
  const groups = groupByDate([
    record(1, '2026-10-18', 20),
    record(3, '2026-10-20', 40),
    record(2, '2026-10-18', 10),
    record(4, '2026-10-20', 25),
  ])
  assert.deepEqual(groups.map((group) => group.date), ['2026-10-20', '2026-10-18'])
  assert.equal(groups[0].totalMinutes, 65)
  assert.equal(groups[0].count, 2)
  assert.deepEqual(groups[0].items.map((item) => item.id), [4, 3])
  assert.equal(groups[1].totalMinutes, 30)
  assert.deepEqual(groups[1].items.map((item) => item.id), [2, 1])
})

test('趋势序列零填充固定天数并只统计窗口内日期', () => {
  const points = buildTrend(
    [
      record(1, '2026-10-20', 30),
      record(2, '2026-10-20', 15),
      record(3, '2026-10-06', 60),
      record(4, '2026-10-21', 20),
    ],
    { days: 7, endDate: '2026-10-20' },
  )
  assert.equal(points.length, 7)
  assert.equal(points[0].date, '2026-10-14')
  assert.equal(points.at(-1).date, '2026-10-20')
  assert.equal(points.at(-1).minutes, 45)
  assert.equal(points[0].minutes, 0)
  assert.equal(
    points.reduce((sum, point) => sum + point.minutes, 0),
    45,
    '窗口外的 2026-10-06 与未来日期不进入序列',
  )
})

test('日期工具拒绝不存在的日期并正确跨月跨年', () => {
  assert.equal(validDate('2026-10-20'), true)
  assert.equal(validDate('2024-02-29'), true)
  assert.equal(validDate('2026-02-30'), false)
  assert.equal(validDate('2026-1-1'), false)
  assert.equal(validDate('0000-01-01'), false)
  assert.equal(validDate(''), false)
  assert.equal(validDate(undefined), false)
  assert.equal(shiftDate('2026-01-01', -1), '2025-12-31')
  assert.equal(shiftDate('2026-02-28', 1), '2026-03-01')
  assert.match(todayInZone('Asia/Shanghai'), /^\d{4}-\d{2}-\d{2}$/)
  assert.equal(shortDate('2026-10-20'), '10-20')
  assert.ok(['周一', '周二', '周三', '周四', '周五', '周六', '周日'].includes(weekdayLabel('2026-10-20')))
  assert.equal(weekdayLabel('2026-02-30'), '')
})

test('时长格式化覆盖分钟、整点与小时加分钟', () => {
  assert.equal(formatMinutes(0), '0 分钟')
  assert.equal(formatMinutes(45), '45 分钟')
  assert.equal(formatMinutes(60), '1 小时')
  assert.equal(formatMinutes(75), '1 小时 15 分钟')
  assert.equal(formatMinutes(-5), '0 分钟')
  assert.equal(formatMinutes('90'), '1 小时 30 分钟')
})
