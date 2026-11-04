// Generated sounds are local Web Audio synthesis; no remote media dependencies.
export class SoundPlayer {
  constructor(onEnd = () => {}) { this.onEnd = onEnd; this.volume = 0.3; this.nodes = [] }
  async unlock() {
    const AudioContext = window.AudioContext || window.webkitAudioContext
    if (!AudioContext) throw new Error('此浏览器不支持音频播放')
    this.context ||= new AudioContext()
    await this.context.resume()
  }
  async play(item, url) {
    this.stop()
    if (item.source_type !== 'generated') {
      this.media = new Audio(url)
      this.media.volume = this.volume
      this.media.onended = () => { this.stop(); this.onEnd() }
      this.media.onerror = () => { this.stop(); this.onEnd('音频无法加载，请检查文件格式或链接') }
      await this.media.play()
      return
    }
    await this.unlock()
    const context = this.context
    this.gain = context.createGain()
    this.gain.gain.setValueAtTime(0, context.currentTime)
    this.gain.gain.linearRampToValueAtTime(this.volume * 0.35, context.currentTime + 1)
    this.gain.connect(context.destination)
    if (item.source === 'meditation') {
      for (const frequency of [174.61, 220, 261.63]) {
        const tone = context.createOscillator(), level = context.createGain(), pulse = context.createOscillator(), depth = context.createGain()
        tone.frequency.value = frequency; level.gain.value = 0.17
        pulse.frequency.value = 0.1; depth.gain.value = 0.05
        pulse.connect(depth); depth.connect(level.gain); tone.connect(level); level.connect(this.gain)
        tone.start(); pulse.start(); this.nodes.push(tone, pulse, level, depth)
      }
    } else {
      const buffer = context.createBuffer(1, context.sampleRate * 4, context.sampleRate)
      const data = buffer.getChannelData(0)
      let last = 0
      for (let index = 0; index < data.length; index++) {
        const white = Math.random() * 2 - 1
        last = (last + 0.02 * white) / 1.02
        data[index] = item.source === 'brown' ? last * 3.5 : white * 0.55
      }
      const source = context.createBufferSource(); source.buffer = buffer; source.loop = true
      source.connect(this.gain); source.start(); this.nodes.push(source)
    }
  }
  setVolume(value) {
    this.volume = Number(value)
    if (this.media) this.media.volume = this.volume
    if (this.gain) this.gain.gain.setTargetAtTime(this.volume * 0.35, this.context.currentTime, 0.1)
  }
  stop() {
    if (this.media) { this.media.onended = null; this.media.onerror = null; this.media.pause(); this.media.removeAttribute('src'); this.media.load(); this.media = null }
    for (const node of this.nodes) { try { node.stop?.() } catch { /* Already stopped. */ } node.disconnect() }
    this.nodes = []; this.gain?.disconnect(); this.gain = null
  }
  dispose() { this.stop(); this.context?.close() }
}
