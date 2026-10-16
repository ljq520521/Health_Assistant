import {shallowRef} from 'vue'

export const DOWNLOAD_NOTICE = '文件已生成，已尝试发起下载，请检查浏览器下载列表'

// Keep only the most recently generated file of each type. The component owns
// these URLs; neither automatic nor manual download releases them on a timer.
export function useReportDownloads() {
  const files = shallowRef({pdf:null, png:null})
  let disposed = false
  function replace(kind, file) {
    if (disposed) return null // Generation may finish after the panel unmounts.
    if (!['pdf','png'].includes(kind) || !(file.blob instanceof Blob)) throw Error('导出文件无效')
    const next = {url:URL.createObjectURL(file.blob), name:file.name, kind}
    const previous = files.value[kind]
    files.value = {...files.value, [kind]:next}
    if (previous) URL.revokeObjectURL(previous.url)
    return next
  }
  function dispose() {
    disposed = true
    for (const file of Object.values(files.value)) if (file) URL.revokeObjectURL(file.url)
    files.value = {pdf:null, png:null}
  }
  return {files, replace, dispose}
}

export function attemptDownload(file) {
  let anchor
  try {
    anchor = document.createElement('a')
    anchor.href = file.url; anchor.download = file.name
    document.body.append(anchor)
    anchor.click()
    return true // Only a request was dispatched, not confirmation of saving.
  } catch { return false } finally { anchor?.remove() }
}
