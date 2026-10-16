import { localParts } from './waterTime.js'
const minutes=t=>Number(t.slice(0,2))*60+Number(t.slice(3))
const clock=m=>`${String(Math.floor(m/60)).padStart(2,'0')}:${String(m%60).padStart(2,'0')}`
export function dueSlot(settings,now,zone) {
  if(!settings?.enabled) return null
  const p=localParts(now,zone),current=minutes(p.clock),start=minutes(settings.active_start),end=minutes(settings.active_end)
  if(current<start||current>end) return null
  const slots=settings.mode==='fixed_times'?settings.fixed_times.map(minutes):Array.from({length:Math.floor((end-start)/settings.interval_minutes)+1},(_,i)=>start+i*settings.interval_minutes)
  const due=slots.filter(m=>m<=current).at(-1)
  // Only the current minute is eligible. Never replay missed reminders in a burst.
  return due===current?`${p.day}T${clock(due)}`:null
}
export function notifyIfAllowed(NotificationAPI, text) {
  if(!NotificationAPI||NotificationAPI.permission!=='granted') return false
  try {new NotificationAPI('饮水提醒',{body:text,tag:'diet-water'});return true} catch {return false}
}
// State contains no health data. Storage failure stops scheduling rather than
// silently losing refresh deduplication. A persistent snooze is checked first.
export function takeReminder(settings,summary,now,zone,storage) {
  if(!settings?.enabled) return null
  const p=localParts(now,zone)
  if(settings.pause_when_goal_met && (!summary||summary.date!==p.day)) return null
  const key='health-diet-water-reminder-v1'
  let state=JSON.parse(storage.getItem(key)||'null')
  if(!state||state.day!==p.day) state={day:p.day,seen:[],snooze:null}
  if(settings.pause_when_goal_met&&summary.goal_met) {state.snooze=null;storage.setItem(key,JSON.stringify(state));return null}
  if(p.clock<settings.active_start||p.clock>settings.active_end) return null
  let slot=dueSlot(settings,now,zone),kind='scheduled'
  if(state.snooze) {
    if(now.getTime()<state.snooze) return null
    const late=now.getTime()-state.snooze
    slot=late<=60000?'snooze:'+state.snooze:null;kind='snooze';state.snooze=null
    storage.setItem(key,JSON.stringify(state))
  }
  if(!slot||state.seen.includes(slot)) return null
  state.seen.push(slot)
  if(kind==='snooze') {
    const scheduled=dueSlot(settings,now,zone)
    if(scheduled&&!state.seen.includes(scheduled))state.seen.push(scheduled)
  }
  storage.setItem(key,JSON.stringify(state))
  return {slot,kind}
}
export function snoozeReminder(now,zone,storage) {
  const key='health-diet-water-reminder-v1',day=localParts(now,zone).day
  const state=JSON.parse(storage.getItem(key)||'null')||{day,seen:[]}
  state.snooze=now.getTime()+10*60000
  storage.setItem(key,JSON.stringify(state))
}
export function clearSnooze(storage) {
  const key='health-diet-water-reminder-v1',state=JSON.parse(storage.getItem(key)||'null')
  if(state){state.snooze=null;storage.setItem(key,JSON.stringify(state))}
}

export function startReminderChecks(check,{document:doc,setInterval:setTimer,clearInterval:clearTimer}) {
  let active=true
  const run=()=>{if(active&&doc.visibilityState==='visible') check()}
  const timer=setTimer(run,15000)
  doc.addEventListener('visibilitychange',run);run()
  return ()=>{active=false;clearTimer(timer);doc.removeEventListener('visibilitychange',run)}
}
