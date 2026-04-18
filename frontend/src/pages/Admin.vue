<template>
  <div class="admin-container">
    <h1>Admin Panel</h1>
    <div class="admin-sections">
      <section class="admin-card">
        <h2>User Management</h2>
        <p>Create, edit, and manage user accounts</p>
        <button>Manage Users</button>
      </section>
      <section class="admin-card">
        <h2>Audio Import</h2>
        <p>Import and process audio files from NAS</p>
        <button>Scan Directory</button>
      </section>
      <section class="admin-card">
        <h2>System Settings</h2>
        <p>Configure backend properties and language</p>
        <button>Settings</button>
      </section>
      <section class="admin-card">
        <h2>Indexing Status</h2>
        <p>Monitor background indexing progress</p>
        <button>View Status</button>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
// Admin logic
</script>

<style scoped>
.admin-container {
  max-width: 1000px;
  margin: 0 auto;
}

h1 {
  color: #333;
  margin-bottom: 30px;
}

.admin-sections {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
}

.admin-card {
  background: white;
  padding: 25px;
  border-radius: 10px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  text-align: center;
}

.admin-card h2 {
  margin: 0 0 10px 0;
  color: #333;
  font-size: 18px;
}

.admin-card p {
  color: #666;
  font-size: 14px;
  margin: 0 0 20px 0;
}

.admin-card button {
  padding: 10px 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: opacity 0.2s;
}

.admin-card button:hover {
  opacity: 0.9;
}
</style>
