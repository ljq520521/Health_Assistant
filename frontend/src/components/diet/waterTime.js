export function localParts(date, timeZone) {
  const parts = Object.fromEntries(new Intl.DateTimeFormat('en-CA', {timeZone,year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit',hourCycle:'h23'}).formatToParts(date).map(p=>[p.type,p.value]))
  return {day:`${parts.year}-${parts.month}-${parts.day}`,clock:`${parts.hour}:${parts.minute}`,second:Number(parts.second)}
}
export const localInput = (date,zone) => {const p=localParts(date,zone);return `${p.day}T${p.clock}`}
// Interpret datetime-local in the configured business zone, not the browser zone.
export function toUTC(value,zone) {
  if(!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(value)) throw new Error('请输入完整饮水时间')
  const nominal=Date.parse(value+':00Z'); let epoch=nominal
  for(let i=0;i<4;i++) {
    const p=localParts(new Date(epoch),zone)
    epoch+=nominal-Date.parse(`${p.day}T${p.clock}:${String(p.second).padStart(2,'0')}Z`)
  }
  if(localInput(new Date(epoch),zone)!==value) throw new Error('该时间在业务时区中不存在，请重新选择')
  return new Date(epoch).toISOString()
}
