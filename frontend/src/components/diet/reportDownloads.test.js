import test from 'node:test'
import assert from 'node:assert/strict'
import {useReportDownloads,attemptDownload,DOWNLOAD_NOTICE} from './reportDownloads.js'

const file = (name, value, type='application/pdf') => ({name,blob:new Blob([value],{type})})
test('download URLs resolve to the exact generated PDF and PNG blobs',async()=>{
  const d=useReportDownloads()
  try {
    const pdf=d.replace('pdf',file('报告.pdf','%PDF-1.4\nreal-payload'))
    const png=d.replace('png',file('图表.png',new Uint8Array([137,80,78,71,13,10,26,10]),'image/png'))
    const pdfResponse=await fetch(pdf.url),pngResponse=await fetch(png.url)
    assert.equal(pdfResponse.headers.get('content-type'),'application/pdf')
    assert.equal(await pdfResponse.text(),'%PDF-1.4\nreal-payload')
    assert.equal(pngResponse.headers.get('content-type'),'image/png')
    assert.deepEqual([...new Uint8Array(await pngResponse.arrayBuffer())],[137,80,78,71,13,10,26,10])
  } finally { d.dispose() }
})
test('a new file releases only the preceding file of the same type',async()=>{
  const d=useReportDownloads()
  try {
    const old=d.replace('pdf',file('旧报告.pdf','old')),png=d.replace('png',file('图表.png','png','image/png'))
    const next=d.replace('pdf',file('新报告.pdf','new'))
    await assert.rejects(fetch(old.url));assert.equal(await (await fetch(next.url)).text(),'new')
    assert.equal(await (await fetch(png.url)).text(),'png')
    assert.equal(d.files.value.pdf.name,'新报告.pdf')
    const newPNG=d.replace('png',file('新图表.png','new-png','image/png'))
    await assert.rejects(fetch(png.url));assert.equal(await (await fetch(newPNG.url)).text(),'new-png')
    assert.equal(await (await fetch(next.url)).text(),'new')
  } finally { d.dispose() }
})
test('failed file preparation preserves the previous usable link',async()=>{
  const d=useReportDownloads()
  try {
    const old=d.replace('pdf',file('报告.pdf','preserved'))
    assert.throws(()=>d.replace('pdf',{name:'bad',blob:null}),/无效/)
    assert.equal(d.files.value.pdf.url,old.url)
    assert.equal(await (await fetch(old.url)).text(),'preserved')
  } finally { d.dispose() }
})
test('unmount cleanup releases both URLs, is idempotent, and ignores late generation',async()=>{
  const d=useReportDownloads(),a=d.replace('pdf',file('a.pdf','a')),b=d.replace('png',file('b.png','b','image/png'))
  d.dispose();d.dispose()
  await assert.rejects(fetch(a.url));await assert.rejects(fetch(b.url))
  assert.deepEqual(d.files.value,{pdf:null,png:null})
  assert.equal(d.replace('pdf',file('late.pdf','late')),null)
})
test('repeated download requests use the same live Blob without a release timer',async t=>{
  const old=globalThis.document,clicks=[]
  globalThis.document={body:{append(){}},createElement(){return {click(){clicks.push([this.href,this.download])},remove(){}}}}
  t.mock.method(globalThis,'setTimeout',()=>{throw Error('不得提前定时释放')})
  const d=useReportDownloads()
  try {
    const entry=d.replace('pdf',file('重试.pdf','retry'))
    assert.equal(attemptDownload(entry),true);assert.equal(attemptDownload(entry),true)
    assert.deepEqual(clicks,[[entry.url,'重试.pdf'],[entry.url,'重试.pdf']])
    assert.equal(await (await fetch(entry.url)).text(),'retry')
    assert.equal(d.files.value.pdf.url,entry.url)
  } finally { d.dispose();if(old===undefined)delete globalThis.document;else globalThis.document=old }
})
test('an automatic trigger error still leaves the generated file available for manual retry',async()=>{
  const old=globalThis.document;let removed=0
  globalThis.document={body:{append(){}},createElement(){return {click(){throw Error('浏览器拒绝')},remove(){removed++}}}}
  const d=useReportDownloads()
  try {
    const entry=d.replace('png',file('重试.png','preserved','image/png'))
    assert.equal(attemptDownload(entry),false);assert.equal(removed,1)
    assert.equal(await (await fetch(d.files.value.png.url)).text(),'preserved')
    assert.doesNotMatch(DOWNLOAD_NOTICE,/保存成功/)
  } finally { d.dispose();if(old===undefined)delete globalThis.document;else globalThis.document=old }
})
