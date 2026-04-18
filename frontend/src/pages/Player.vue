<template>
  <div class="player-container">
    <div class="player-card">
      <div class="album-art">
        <div class="placeholder">♪</div>
      </div>

      <div class="track-info">
        <h2>{{ currentTrack?.title || 'Select a track' }}</h2>
        <p>{{ currentTrack?.composer || 'Classical Music Player' }}</p>
        <p class="meta">{{ currentTrack?.catalog_number || '' }}</p>
      </div>

      <div class="controls">
        <button @click="previousTrack" :disabled="!canPlayPrevious">⏮ Previous</button>
        <button @click="togglePlay" class="play-btn">
          {{ isPlaying ? '⏸ Pause' : '▶ Play' }}
        </button>
        <button @click="nextTrack" :disabled="!canPlayNext">Next ⏭</button>
      </div>

      <audio ref="audioElement" @ended="nextTrack" @timeupdate="updateTime" />

      <div class="progress">
        <span>{{ formatTime(currentTime) }}</span>
        <div class="progress-bar">
          <input
            v-model="currentTime"
            type="range"
            min="0"
            :max="duration"
            @input="seek"
            class="slider"
          />
        </div>
        <span>{{ formatTime(duration) }}</span>
      </div>

      <div class="movements" v-if="currentTrack && movements.length > 0">
        <h3>Movements:</h3>
        <div class="movement-list">
          <div
            v-for="(movement, index) in movements"
            :key="movement.movement_id"
            class="movement-item"
            :class="{ active: index === currentMovementIndex }"
          >
            <strong>{{ movement.movement_number }}. {{ movement.movement_title }}</strong>
            <p v-if="movement.emotion">{{ movement.emotion }}</p>
          </div>
        </div>
      </div>

      <div class="recommendations" v-if="recommendations.length > 0">
        <h3>Recommended:</h3>
        <div class="rec-list">
          <div
            v-for="rec in recommendations.slice(0, 3)"
            :key="rec.work_id"
            class="rec-item"
            @click="loadTrack(rec)"
          >
            <p><strong>{{ rec.title }}</strong></p>
            <p class="artist">{{ rec.composer }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { MusicAPI, Work, Movement } from '../api/music';

const audioElement = ref<HTMLAudioElement>();
const currentTrack = ref<Work | null>(null);
const currentMovementIndex = ref(0);
const movements = ref<Movement[]>([]);
const recommendations = ref<Work[]>([]);
const isPlaying = ref(false);
const currentTime = ref(0);
const duration = ref(0);
const canPlayPrevious = ref(false);
const canPlayNext = ref(false);
const playlist = ref<Work[]>([]);
const currentTrackIndex = ref(0);

onMounted(async () => {
  await loadPlaylist();
});

async function loadPlaylist() {
  try {
    playlist.value = await MusicAPI.listWorks(20);
    if (playlist.value.length > 0) {
      await loadTrack(playlist.value[0]);
    }
  } catch (err) {
    console.error('Failed to load playlist:', err);
  }
}

async function loadTrack(track: Work) {
  try {
    currentTrack.value = track;
    movements.value = await MusicAPI.getMovements(track.work_id);
    recommendations.value = await MusicAPI.getRecommendations(track.work_id);
    currentMovementIndex.value = 0;
    currentTime.value = 0;

    // For now, create a dummy stream URL
    // In real implementation, you'd get the actual audio segment URL
    if (audioElement.value) {
      audioElement.value.src = '/sample.m4a'; // Placeholder
    }

    updateNavButtons();
  } catch (err) {
    console.error('Failed to load track:', err);
  }
}

function togglePlay() {
  if (!audioElement.value || !currentTrack.value) return;

  if (isPlaying.value) {
    audioElement.value.pause();
  } else {
    audioElement.value.play();
  }
  isPlaying.value = !isPlaying.value;
}

function seek(e: Event) {
  const input = e.target as HTMLInputElement;
  if (audioElement.value) {
    audioElement.value.currentTime = parseFloat(input.value);
  }
}

function updateTime() {
  if (audioElement.value) {
    currentTime.value = audioElement.value.currentTime;
    duration.value = audioElement.value.duration || 0;
  }
}

function previousTrack() {
  if (currentTrackIndex.value > 0) {
    currentTrackIndex.value--;
    loadTrack(playlist.value[currentTrackIndex.value]);
  }
}

function nextTrack() {
  if (currentTrackIndex.value < playlist.value.length - 1) {
    currentTrackIndex.value++;
    loadTrack(playlist.value[currentTrackIndex.value]);
  }
}

function updateNavButtons() {
  canPlayPrevious.value = currentTrackIndex.value > 0;
  canPlayNext.value = currentTrackIndex.value < playlist.value.length - 1;
}

function formatTime(seconds: number): string {
  if (!seconds || isNaN(seconds)) return '0:00';
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}
</script>

<style scoped>
.player-container {
  display: flex;
  justify-content: center;
  padding: 20px;
}

.player-card {
  background: white;
  border-radius: 15px;
  padding: 40px;
  max-width: 500px;
  width: 100%;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
}

.album-art {
  width: 100%;
  aspect-ratio: 1;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 30px;
}

.placeholder {
  font-size: 100px;
  color: white;
  opacity: 0.5;
}

.track-info {
  text-align: center;
  margin-bottom: 30px;
}

.track-info h2 {
  margin: 0 0 10px 0;
  color: #333;
  font-size: 22px;
}

.track-info p {
  margin: 5px 0;
  color: #666;
  font-size: 14px;
}

.meta {
  color: #999 !important;
  font-size: 12px !important;
}

.controls {
  display: flex;
  gap: 10px;
  margin-bottom: 30px;
  justify-content: center;
}

button {
  padding: 10px 20px;
  border: none;
  border-radius: 5px;
  background: #f0f0f0;
  color: #333;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: background 0.2s;
}

button:hover:not(:disabled) {
  background: #e0e0e0;
}

button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.play-btn {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 12px 30px;
  font-size: 16px;
}

.play-btn:hover {
  opacity: 0.9;
}

.progress {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 30px;
  font-size: 12px;
  color: #666;
}

.progress-bar {
  flex: 1;
}

.slider {
  width: 100%;
  cursor: pointer;
}

.movements {
  margin-bottom: 30px;
  padding: 20px;
  background: #f9f9f9;
  border-radius: 10px;
}

.movements h3 {
  margin: 0 0 15px 0;
  font-size: 14px;
  color: #333;
}

.movement-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.movement-item {
  padding: 10px;
  background: white;
  border-radius: 5px;
  border-left: 3px solid #ddd;
  cursor: pointer;
  font-size: 12px;
}

.movement-item.active {
  border-left-color: #667eea;
  background: #f0f4ff;
}

.movement-item p {
  margin: 5px 0 0 0;
  color: #999;
  font-size: 11px;
}

.recommendations {
  padding: 20px;
  background: #f9f9f9;
  border-radius: 10px;
}

.recommendations h3 {
  margin: 0 0 15px 0;
  font-size: 14px;
  color: #333;
}

.rec-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.rec-item {
  padding: 10px;
  background: white;
  border-radius: 5px;
  cursor: pointer;
  transition: background 0.2s;
  font-size: 12px;
}

.rec-item:hover {
  background: #f0f4ff;
}

.rec-item p {
  margin: 5px 0;
}

.rec-item .artist {
  color: #999;
  font-size: 11px;
}
</style>
