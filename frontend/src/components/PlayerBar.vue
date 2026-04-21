<template>
  <div class="player-bar" v-if="player.currentWork">
    <div class="player-bar-inner leather-bar">
      <!-- Track info -->
      <div class="player-info">
        <div class="player-vinyl" :class="{ spinning: false }">♫</div>
        <!-- don't spin, save battery.  spinning: player.isPlaying -->
        <div class="player-text">
          <div class="player-title">{{ player.currentMovement?.title || player.currentWork.title }}</div>
          <div class="player-artist">{{ player.currentWork.composer }}</div>
        </div>
      </div>

      <!-- Controls -->
      <div class="player-controls">
        <button class="btn-metal medium" @click="player.playPrevious()" title="上一曲">⏮</button>
        <button class="btn-metal large" @click="player.togglePlay()" :title="player.isPlaying ? '暂停' : '播放'">
          {{ player.isPlaying ? '⏸' : '▶' }}
        </button>
        <button class="btn-metal medium" @click="player.playNext()" title="下一曲">⏭</button>
      </div>

      <!-- Progress -->
      <div class="player-progress">
        <span class="time-label">{{ player.formatTime(player.progress) }}</span>
        <input
          type="range"
          class="skeuo-slider"
          min="0"
          :max="player.duration || 100"
          :value="player.progress"
          @input="onSeek"
        />
        <span class="time-label">{{ player.formatTime(player.duration) }}</span>
      </div>

      <!-- Volume -->
      <div class="player-volume">
        <span class="volume-icon">🔊</span>
        <input
          type="range"
          class="skeuo-slider volume-slider"
          min="0"
          max="100"
          :value="player.volume * 100"
          @input="onVolume"
        />
      </div>
    </div>
  </div>

  <!-- Placeholder when nothing is playing -->
  <div class="player-bar" v-else>
    <div class="player-bar-inner leather-bar">
      <div class="player-info">
        <div class="player-vinyl">♫</div>
        <div class="player-text">
          <div class="player-title">未在播放</div>
          <div class="player-artist">古典音乐播放器</div>
        </div>
      </div>
      <div class="player-controls">
        <button class="btn-metal medium" disabled>⏮</button>
        <button class="btn-metal large" disabled>▶</button>
        <button class="btn-metal medium" disabled>⏭</button>
      </div>
      <div class="player-progress">
        <span class="time-label">0:00</span>
        <input type="range" class="skeuo-slider" min="0" max="100" value="0" disabled />
        <span class="time-label">0:00</span>
      </div>
      <div class="player-volume">
        <span class="volume-icon">🔊</span>
        <input type="range" class="skeuo-slider volume-slider" min="0" max="100" value="80" disabled />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { usePlayerStore } from '@/stores/player'

const player = usePlayerStore()

function onSeek(e: Event) {
  const target = e.target as HTMLInputElement
  player.seek(Number(target.value))
}

function onVolume(e: Event) {
  const target = e.target as HTMLInputElement
  player.setVolume(Number(target.value) / 100)
}
</script>

<style scoped>
.player-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 1000;
}

.player-bar-inner {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.5rem 1rem;
}

.player-info {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  min-width: 180px;
}

.player-vinyl {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: radial-gradient(circle at 50% 50%, #2a2a2a 30%, #1a1a1a 60%, #333 100%);
  border: 2px solid var(--border-groove);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1rem;
  color: var(--accent-gold);
  flex-shrink: 0;
}

.player-vinyl.spinning {
  animation: spin 3s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.player-text {
  overflow: hidden;
}

.player-title {
  font-size: 0.85rem;
  font-weight: 600;
  white-space: nowrap;
  text-overflow: ellipsis;
  overflow: hidden;
  color: var(--text-primary);
}

.player-artist {
  font-size: 0.72rem;
  color: var(--text-muted);
  white-space: nowrap;
  text-overflow: ellipsis;
  overflow: hidden;
}

.player-controls {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-shrink: 0;
}

.player-progress {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 0;
}

.time-label {
  font-size: 0.7rem;
  color: var(--text-muted);
  font-family: var(--font-sans);
  min-width: 32px;
  text-align: center;
}

.player-volume {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  flex-shrink: 0;
}

.volume-icon {
  font-size: 0.8rem;
}

.volume-slider {
  width: 80px;
}

@media (max-width: 700px) {
  .player-bar-inner {
    flex-wrap: wrap;
    gap: 0.4rem;
    padding: 0.4rem 0.75rem;
  }
  .player-info { min-width: 120px; flex: 1; }
  .player-progress { order: 10; flex-basis: 100%; }
  .player-volume { display: none; }
}
</style>
