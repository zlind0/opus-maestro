import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { AudioSegment, Movement, Work } from '@/types'
import { getMovementSegments, getAudioStreamUrl, getRecommendations } from '@/api'

export const usePlayerStore = defineStore('player', () => {
  const currentWork = ref<Work | null>(null)
  const currentMovement = ref<Movement | null>(null)
  const currentSegment = ref<AudioSegment | null>(null)
  const isPlaying = ref(false)
  const progress = ref(0)
  const duration = ref(0)
  const volume = ref(0.8)
  const queue = ref<Movement[]>([])
  const queueIndex = ref(-1)
  const recommendations = ref<Work[]>([])

  const audio = ref<HTMLAudioElement | null>(null)

  function initAudio() {
    if (!audio.value) {
      audio.value = new Audio()
      audio.value.addEventListener('timeupdate', () => {
        progress.value = audio.value!.currentTime * 1000
      })
      audio.value.addEventListener('loadedmetadata', () => {
        duration.value = audio.value!.duration * 1000
      })
      audio.value.addEventListener('ended', () => {
        isPlaying.value = false
        playNext()
      })
      audio.value.addEventListener('play', () => { isPlaying.value = true })
      audio.value.addEventListener('pause', () => { isPlaying.value = false })
    }
    return audio.value
  }

  async function playMovement(work: Work, movement: Movement) {
    const el = initAudio()
    currentWork.value = work
    currentMovement.value = movement

    const segments = await getMovementSegments(movement.id)
    if (segments.length === 0) return

    currentSegment.value = segments[0]
    el.src = getAudioStreamUrl(segments[0].id, 'mp3')
    el.volume = volume.value
    await el.play()

    updateMediaSession()

    // Fetch recommendations in background
    getRecommendations(movement.id).then(recs => {
      recommendations.value = recs
    }).catch(() => {})
  }

  function togglePlay() {
    const el = initAudio()
    if (isPlaying.value) {
      el.pause()
    } else {
      el.play()
    }
  }

  function seek(ms: number) {
    const el = initAudio()
    el.currentTime = ms / 1000
  }

  function setVolume(v: number) {
    volume.value = v
    if (audio.value) {
      audio.value.volume = v
    }
  }

  function setQueue(movements: Movement[], startIndex: number = 0) {
    queue.value = movements
    queueIndex.value = startIndex
  }

  async function playNext() {
    if (queueIndex.value < queue.value.length - 1 && currentWork.value) {
      queueIndex.value++
      await playMovement(currentWork.value, queue.value[queueIndex.value])
    }
  }

  async function playPrevious() {
    if (queueIndex.value > 0 && currentWork.value) {
      queueIndex.value--
      await playMovement(currentWork.value, queue.value[queueIndex.value])
    }
  }

  function updateMediaSession() {
    if ('mediaSession' in navigator && currentWork.value) {
      navigator.mediaSession.metadata = new MediaMetadata({
        title: currentMovement.value?.title || currentWork.value.title,
        artist: currentWork.value.composer,
        album: currentWork.value.title,
      })
      navigator.mediaSession.setActionHandler('play', () => togglePlay())
      navigator.mediaSession.setActionHandler('pause', () => togglePlay())
      navigator.mediaSession.setActionHandler('previoustrack', () => playPrevious())
      navigator.mediaSession.setActionHandler('nexttrack', () => playNext())
    }
  }

  function formatTime(ms: number): string {
    const totalSeconds = Math.floor(ms / 1000)
    const minutes = Math.floor(totalSeconds / 60)
    const seconds = totalSeconds % 60
    return `${minutes}:${seconds.toString().padStart(2, '0')}`
  }

  return {
    currentWork,
    currentMovement,
    currentSegment,
    isPlaying,
    progress,
    duration,
    volume,
    queue,
    queueIndex,
    recommendations,
    playMovement,
    togglePlay,
    seek,
    setVolume,
    setQueue,
    playNext,
    playPrevious,
    formatTime,
  }
})
