/**
 * Setu Offline Storage & IndexedDB Layer (FIX 3a).
 * Zero heavy external dependencies.
 * Stores:
 * - Downloaded class content packs (with answer keys for offline grading)
 * - Student profiles with salted PBKDF2 PIN verifiers (offline authentication without plaintext PINs)
 * - Student learning state (plan, BKT mastery, open hypotheses)
 * - Recorded attempts & persistent offline sync queue (survives reload/restart)
 * - Device metadata & tombstones
 */

const DB_NAME = 'SetuOfflineDB';
const DB_VERSION = 1;

export function openDB() {
  return new Promise((resolve, reject) => {
    if (typeof indexedDB === 'undefined') {
      return reject(new Error('IndexedDB not supported in this environment'));
    }
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = (e) => {
      const db = e.target.result;
      if (!db.objectStoreNames.contains('packs')) {
        db.createObjectStore('packs', { keyPath: 'class_id' });
      }
      if (!db.objectStoreNames.contains('profiles')) {
        db.createObjectStore('profiles', { keyPath: 'student_id' });
      }
      if (!db.objectStoreNames.contains('learning_states')) {
        db.createObjectStore('learning_states', { keyPath: 'student_id' });
      }
      if (!db.objectStoreNames.contains('attempts')) {
        db.createObjectStore('attempts', { keyPath: 'attempt_id' });
      }
      if (!db.objectStoreNames.contains('sync_queue')) {
        db.createObjectStore('sync_queue', { keyPath: 'attempt_id' });
      }
      if (!db.objectStoreNames.contains('metadata')) {
        db.createObjectStore('metadata', { keyPath: 'key' });
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

function runTx(storeName, mode, fn) {
  return openDB().then((db) => {
    return new Promise((resolve, reject) => {
      const tx = db.transaction(storeName, mode);
      const store = tx.objectStore(storeName);
      let result;
      try {
        result = fn(store);
      } catch (err) {
        return reject(err);
      }
      tx.oncomplete = () => resolve(result);
      tx.onerror = () => reject(tx.error);
    });
  });
}

// ==========================================
// PBKDF2 Salted PIN Verifier (FIX 3c)
// ==========================================

export async function derivePinVerifier(pin, saltHex) {
  const enc = new TextEncoder();
  const keyMaterial = await window.crypto.subtle.importKey(
    'raw',
    enc.encode(pin),
    { name: 'PBKDF2' },
    false,
    ['deriveBits']
  );
  const salt = new Uint8Array(saltHex.match(/.{1,2}/g).map((b) => parseInt(b, 16)));
  const derivedBits = await window.crypto.subtle.deriveBits(
    {
      name: 'PBKDF2',
      salt: salt,
      iterations: 50000,
      hash: 'SHA-256'
    },
    keyMaterial,
    256
  );
  const hashArray = Array.from(new Uint8Array(derivedBits));
  return hashArray.map((b) => b.toString(16).padStart(2, '0')).join('');
}

export function generateSaltHex() {
  const bytes = new Uint8Array(16);
  window.crypto.getRandomValues(bytes);
  return Array.from(bytes).map((b) => b.toString(16).padStart(2, '0')).join('');
}

// ==========================================
// Packs Store
// ==========================================

export async function saveOfflinePack(classId, packData) {
  return runTx('packs', 'readwrite', (store) => {
    store.put({ class_id: classId, data: packData, updated_at: new Date().toISOString() });
  });
}

export async function getOfflinePack(classId) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('packs', 'readonly');
    const req = tx.objectStore('packs').get(classId);
    req.onsuccess = () => resolve(req.result ? req.result.data : null);
    req.onerror = () => reject(req.error);
  });
}

// ==========================================
// Profiles Store (Offline Sign-In)
// ==========================================

export async function saveStudentProfile(profile) {
  return runTx('profiles', 'readwrite', (store) => {
    store.put(profile);
  });
}

export async function getStudentProfile(studentId) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('profiles', 'readonly');
    const req = tx.objectStore('profiles').get(studentId);
    req.onsuccess = () => resolve(req.result || null);
    req.onerror = () => reject(req.error);
  });
}

// ==========================================
// Learning States Store
// ==========================================

export async function saveLearningState(studentId, state) {
  return runTx('learning_states', 'readwrite', (store) => {
    store.put({ student_id: studentId, state, updated_at: new Date().toISOString() });
  });
}

export async function getLearningState(studentId) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('learning_states', 'readonly');
    const req = tx.objectStore('learning_states').get(studentId);
    req.onsuccess = () => resolve(req.result ? req.result.state : null);
    req.onerror = () => reject(req.error);
  });
}

// ==========================================
// Attempts & Persistent Sync Queue
// ==========================================

export async function recordAttemptLocal(attempt) {
  return runTx('attempts', 'readwrite', (store) => {
    store.put(attempt);
  });
}

export async function enqueueSyncAttempt(attempt) {
  return runTx('sync_queue', 'readwrite', (store) => {
    store.put(attempt);
  });
}

export async function getSyncQueue() {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('sync_queue', 'readonly');
    const req = tx.objectStore('sync_queue').getAll();
    req.onsuccess = () => resolve(req.result || []);
    req.onerror = () => reject(req.error);
  });
}

export async function clearSyncQueue(attemptIds = null) {
  return runTx('sync_queue', 'readwrite', (store) => {
    if (!attemptIds) {
      store.clear();
    } else {
      attemptIds.forEach((id) => store.delete(id));
    }
  });
}

export async function getAttemptsCount() {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('attempts', 'readonly');
    const req = tx.objectStore('attempts').count();
    req.onsuccess = () => resolve(req.result || 0);
    req.onerror = () => reject(req.error);
  });
}

export async function getAllLocalAttempts() {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('attempts', 'readonly');
    const req = tx.objectStore('attempts').getAll();
    req.onsuccess = () => resolve(req.result || []);
    req.onerror = () => reject(req.error);
  });
}

// ==========================================
// Privacy & Stale Reset Wipe (FIX 4, 5)
// ==========================================

export async function wipeAllStudentData() {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(['profiles', 'learning_states', 'attempts', 'sync_queue'], 'readwrite');
    tx.objectStore('profiles').clear();
    tx.objectStore('learning_states').clear();
    tx.objectStore('attempts').clear();
    tx.objectStore('sync_queue').clear();
    tx.oncomplete = () => resolve(true);
    tx.onerror = () => reject(tx.error);
  });
}

// ==========================================
// Metadata Store
// ==========================================

export async function setMeta(key, value) {
  return runTx('metadata', 'readwrite', (store) => {
    store.put({ key, value });
  });
}

export async function getMeta(key) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('metadata', 'readonly');
    const req = tx.objectStore('metadata').get(key);
    req.onsuccess = () => resolve(req.result ? req.result.value : null);
    req.onerror = () => reject(req.error);
  });
}
