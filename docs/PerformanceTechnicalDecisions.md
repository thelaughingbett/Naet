## ⚡ Performance & Technical Decisions

### 🔍 Query Optimisation

The biggest performance win in this codebase isn't caching — it's eliminating unnecessary database round trips through `select_related` and `prefetch_related`. Every view that touches related models uses eager loading:

```python
# one query with joins instead of N+1 queries
Student.objects.select_related(
    'user',
    'class_entered__programme__department__school'
).get(user=request.user)
```

This means navigating `student.class_entered.programme.department` never triggers additional queries — everything is loaded upfront.

---

### 🗄️ Caching Strategy

The system uses **Redis** for frequently accessed, rarely changing data. This avoids hitting PostgreSQL on every request without needing Redis or Memcached.

```python

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        # Connects to the port exposed by Docker onto your local machine
        "LOCATION": "redis://127.0.0.1:6379/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
        "KEY_PREFIX": "local_django_dev",
        "TIMEOUT": 300,  # Expires keys automatically after 5 minutes

    }
}
```

**What gets cached and for how long:**

| Data               | Cache Key Pattern                       | Timeout | Reason                     |
| ------------------ | --------------------------------------- | ------- | -------------------------- |
| 🗓️ Active session  | `active_session`                        | 10 min  | Changes only on rollover   |
| 🎓 Student profile | `student:{user_pk}`                     | 5 min   | Changes occasionally       |
| 💰 Fee account     | `fee_account:{student_pk}:{session_pk}` | 2 min   | Changes on payment         |
| 📚 Enrollments     | `enrollments:{student_pk}:{session_pk}` | 5 min   | Changes at semester start  |
| 🕐 Timetable       | `timetable:{class_pk}:{session_pk}`     | 10 min  | Rarely changes mid-session |

**Invalidation rules — cache is cleared immediately after any write:**

```
payment recorded    → invalidate fee_account
student updated     → invalidate student profile
session rolled over → invalidate active_session
enrollment changed  → invalidate enrollments
```

---

<!-- ### 🤔 Why not Redis?

Redis is the industry standard for caching but adds infrastructure complexity — a separate service to run, monitor, and maintain. For a single-institution deployment serving hundreds of concurrent users (not millions), file-based caching is sufficient and removes a deployment dependency entirely.

The caching layer is abstracted behind a `utils/cache.py` module, so switching to Redis later requires changing one line in `settings.py` and nothing else.

--- -->

### 🏗️ Why Class-Based Views

All views inherit from Django's `View` with a shared `StudentContextMixin`:

```python
class StudentContextMixin:
    def get_student(self, request): ...
    def get_active_session(self): ...
```

This keeps `get_student()` and `get_active_session()` in one place — every view calls the cached version automatically without duplicating the lookup logic.

and the other over mixinised [its a word now] stuff

---

### 🔐 Why Custom AbstractBaseUser

Django's default `User` model uses username for authentication. This system uses email, which required a custom `AbstractBaseUser`. The upside is the model is fully owned — fields like `role`, `is_activated`, and `surname` live directly on the user without a separate profile model.

- Also cause i felt like it

---

### ⚡ Why Django Signals for Enrollment

Auto-enrollment of core courses on student creation could have been done inside the `RegisterService` view. Using a signal instead means:

- The view doesn't need to know about curriculum logic
- Any code path that creates a `Student` (shell, tests, admin, API) gets enrollment automatically
- Enrollment logic lives in one place and is easy to find
  The tradeoff is that signals are harder to trace — which is why they're documented explicitly in [docs/modules/enrollment](docs/modules/enrollment/index.md).

---

## 📱 Frontend Offline Strategy

> Kenya's internet infrastructure is uneven — students in rural areas, on
> mobile data, or in buildings with poor signal shouldn't lose their work
> or see blank pages because of a dropped connection.
> This system is built with that reality in mind.

---

### 🌍 The Problem

A student in a rural campus opens the portal on 2G, navigates to fee
statement, their connection drops mid-load, and they get a blank error page.
Or worse — they fill in a long reporting form and submit it, the connection
drops, and the data is lost with no feedback.

The frontend offline strategy addresses this at three layers:

```
Layer 1 — Cache Storage (Service Worker)  → pages load without internet
Layer 2 — IndexedDB                       → form data survives offline
Layer 3 — Background Sync                 → queued actions submit when back online
```

---

### 🔧 Layer 1 — Cache Storage via Service Worker

A Service Worker intercepts network requests and serves cached responses
when the network is unavailable. Critical pages are pre-cached on first load.

```javascript
// static/base/js/sw.js

const CACHE_NAME = "portal-v1";

const PRE_CACHE = [
  "/",
  "/academics/curriculum/",
  "/financials/fees/",
  "/timetable/schedule/",
  "/static/base/styles/index/index.css",
  "/static/base/js/main.js",
];

// install — pre-cache critical pages
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(PRE_CACHE)),
  );
});

// fetch — serve from cache, fall back to network
self.addEventListener("fetch", (event) => {
  event.respondWith(
    caches
      .match(event.request)
      .then((cached) => {
        return (
          cached ||
          fetch(event.request).then((response) => {
            // cache fresh responses for next time
            const clone = response.clone();
            caches
              .open(CACHE_NAME)
              .then((cache) => cache.put(event.request, clone));
            return response;
          })
        );
      })
      .catch(() => {
        // network failed and no cache — show offline page
        return caches.match("/offline.html");
      }),
  );
});
```

**What gets pre-cached:**

| Page             | Reason                                        |
| ---------------- | --------------------------------------------- |
| 🏠 Dashboard     | Most visited, needs to load instantly         |
| 📚 Curriculum    | Students check enrolled units frequently      |
| 💰 Fee Statement | Critical — students need balance info offline |
| 🕐 Timetable     | Checked daily, rarely changes                 |
| 🎨 CSS / JS      | Required for any page to render correctly     |

---

### 🗃️ Layer 2 — IndexedDB for Offline Data

`Cache Storage` caches HTML pages. `IndexedDB` stores actual data —
student profile, fee balance, enrolled units — so pages render with
real content even without a network connection.

```javascript
// static/base/js/db.js

const DB_NAME = "portal-db";
const DB_VERSION = 1;

const STORES = {
  STUDENT: "student",
  ENROLLMENTS: "enrollments",
  FEE_ACCOUNT: "fee_account",
  TIMETABLE: "timetable",
  PENDING: "pending_actions", // offline form submissions
};

function openDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onupgradeneeded = (event) => {
      const db = event.target.result;
      Object.values(STORES).forEach((store) => {
        if (!db.objectStoreNames.contains(store)) {
          db.createObjectStore(store, { keyPath: "id" });
        }
      });
    };

    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

// store fresh data from server
async function saveToStore(storeName, data) {
  const db = await openDB();
  const tx = db.transaction(storeName, "readwrite");
  tx.objectStore(storeName).put({ id: "current", ...data });
  return tx.complete;
}

// read back when offline
async function getFromStore(storeName) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(storeName, "readonly");
    const req = tx.objectStore(storeName).get("current");
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}
```

**On page load — hydrate from server, save to IndexedDB:**

```javascript
// when dashboard loads successfully
fetch("/api/student/context/")
  .then((r) => r.json())
  .then((data) => {
    saveToStore(STORES.STUDENT, data.student);
    saveToStore(STORES.FEE_ACCOUNT, data.fee_account);
    saveToStore(STORES.ENROLLMENTS, data.enrollments);
    renderDashboard(data);
  })
  .catch(async () => {
    // network failed — render from IndexedDB
    const student = await getFromStore(STORES.STUDENT);
    const feeAccount = await getFromStore(STORES.FEE_ACCOUNT);
    const enrollments = await getFromStore(STORES.ENROLLMENTS);
    renderDashboard({ student, feeAccount, enrollments });
    showOfflineBanner();
  });
```

---

### 📤 Layer 3 — Background Sync for Offline Form Submissions

When a student submits a form (reporting, payment, unit registration)
and the network is down, the submission is saved to the `pending_actions`
IndexedDB store and replayed automatically when connectivity returns.

```javascript
// queue a form submission for later
async function queueAction(action) {
  const db = await openDB();
  const tx = db.transaction(STORES.PENDING, "readwrite");
  tx.objectStore(STORES.PENDING).put({
    id: Date.now(),
    ...action,
    queued_at: new Date().toISOString(),
  });

  // register background sync if supported
  if ("serviceWorker" in navigator && "SyncManager" in window) {
    const sw = await navigator.serviceWorker.ready;
    await sw.sync.register("flush-pending");
  }
}

// in the service worker — fires when connection returns
self.addEventListener("sync", (event) => {
  if (event.tag === "flush-pending") {
    event.waitUntil(flushPendingActions());
  }
});

async function flushPendingActions() {
  const db = await openDB();
  const tx = db.transaction(STORES.PENDING, "readwrite");
  const store = tx.objectStore(STORES.PENDING);

  const all = await new Promise((resolve) => {
    const req = store.getAll();
    req.onsuccess = () => resolve(req.result);
  });

  for (const action of all) {
    try {
      await fetch(action.url, {
        method: action.method,
        body: JSON.stringify(action.data),
        headers: { "Content-Type": "application/json" },
      });
      store.delete(action.id); // remove on success
    } catch {
      // still offline — leave in queue, try again next sync
    }
  }
}
```

**Actions that get queued when offline:**

| Action                  | Store key         | Sync behaviour         |
| ----------------------- | ----------------- | ---------------------- |
| 📋 Semester reporting   | `pending_actions` | Submitted on reconnect |
| 📝 Unit registration    | `pending_actions` | Submitted on reconnect |
| 💬 Complaint submission | `pending_actions` | Submitted on reconnect |

> ⚠️ **Payments are never queued offline.** Financial transactions require
> a confirmed server response. A payment form shown offline displays a
> clear message: _"Payments require an active connection."_

---

### 🔔 Offline UX — What the Student Sees

```javascript
// detect connection state and show banner
function updateConnectionBanner() {
  const banner = document.getElementById("connection-banner");

  if (!navigator.onLine) {
    banner.textContent =
      "📶 You are offline — showing saved data. Some actions unavailable.";
    banner.classList.add("visible", "offline");
  } else {
    banner.textContent = "✅ Back online";
    banner.classList.add("visible", "online");
    setTimeout(() => banner.classList.remove("visible"), 3000);
    flushPendingActions(); // replay any queued submissions
  }
}

window.addEventListener("online", updateConnectionBanner);
window.addEventListener("offline", updateConnectionBanner);
```

**Offline state rules:**

| Feature              | Offline behaviour                                |
| -------------------- | ------------------------------------------------ |
| 🏠 Dashboard         | ✅ Loads from cache + IndexedDB                  |
| 📚 Curriculum        | ✅ Loads from cache + IndexedDB                  |
| 💰 Fee balance       | ✅ Shows last known balance with stale indicator |
| 🕐 Timetable         | ✅ Loads from cache                              |
| 📋 Reporting form    | ⏳ Queued — submits on reconnect                 |
| 📝 Unit registration | ⏳ Queued — submits on reconnect                 |
| 💳 Payment           | ❌ Disabled — requires live connection           |

---

### 🗂️ Storage Limits & Cleanup

Browser storage is not unlimited. The system manages this proactively:

```javascript
// check available storage
async function checkStorageQuota() {
  if ("storage" in navigator && "estimate" in navigator.storage) {
    const { usage, quota } = await navigator.storage.estimate();
    const pct = Math.round((usage / quota) * 100);

    if (pct > 80) {
      // evict old cache versions
      const keys = await caches.keys();
      keys.filter((k) => k !== CACHE_NAME).forEach((k) => caches.delete(k));
    }
  }
}
```

Old cache versions are deleted automatically when a new service worker
installs. IndexedDB data is refreshed on every successful network request —
stale data is overwritten, never accumulated.

---

### 📦 File Structure

```
static/base/js/
├── sw.js          ← service worker (cache + background sync)
├── db.js          ← IndexedDB wrapper (read/write/queue)
├── offline.js     ← connection banner + flush on reconnect
└── main.js        ← registers service worker on page load

templates/base/
└── offline.html   ← fallback page when cache miss + no network
```

---

### 🤔 Why Not a Full PWA Framework?

Libraries like Workbox abstract service worker complexity but add
kilobytes to the bundle — a real cost on 2G connections. The offline
layer here is written in vanilla JS with no dependencies, keeping the
initial page load as light as possible for students on limited data.

The service worker, IndexedDB wrapper, and sync logic together are
under 5KB minified — lighter than most framework boilerplate files.

---

## 🎓 Common Unit Management

Common Units (`CC`) are courses shared across multiple programmes and classes — e.g. Communication Skills taught to BSc CS, BSc Engineering, BA Literature, and BSc Biochem all in the same session.

### 🔀 Two Assignment Patterns

**Pattern 1 — One professor teaches all classes**

Use the bulk assign action on the `Common Units` admin list:

```
1. Go to Common Units
2. Select the course entries
3. Action → "Assign professor to ALL classes for this course"
4. Pick lecturer → Confirm
```

One click assigns the professor to every class taking that unit in the current session.

**Pattern 2 — Different professors per class**

Open the course record directly. All curriculum entries for the active session appear as inline rows — each independently assignable:

```
Communication Skills
├── BSc CS Year 1       → [Prof X ▾]
├── BSc Engineering Y1  → [Prof X ▾]
├── BA Literature Y1    → [Prof Y ▾]
└── BSc Biochem Y1      → [Prof Y ▾]
```

One save updates all assignments at once.

### 🏗️ How it works

- `CommonUnitCurriculum` is a **proxy model** of `Curriculum` filtered to `course__type = 'CC'` — no extra database table
- The inline is scoped to the **active session only** — past session entries don't clutter the view
- The bulk action uses `course + session` to find all sibling curriculum entries automatically — selecting one class is enough
