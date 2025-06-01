const DB_NAME = "foodDiaryDB";
const DB_VERSION = 1;
const STORE_NAME = "entries";
let db;

window.foodDiaryUtils = {
  initDB: function () {
    return new Promise((resolve, reject) => {
      if (db) {
      resolve(db);
      return;
    }
    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onupgradeneeded = (event) => {
      const dbInstance = event.target.result;
      if (!dbInstance.objectStoreNames.contains(STORE_NAME)) {
        const store = dbInstance.createObjectStore(STORE_NAME, {
          keyPath: "id",
          autoIncrement: true,
        });
        store.createIndex("timestamp", "timestamp", { unique: false });
        store.createIndex("synced", "synced", { unique: false });
        console.log(`Object store '${STORE_NAME}' created.`);
      }
    };

    request.onsuccess = (event) => {
      db = event.target.result;
      console.log("Database initialized successfully (static/app.js).");
      resolve(db);
    };

    request.onerror = (event) => {
      console.error(
        "Database error (static/app.js): ",
        event.target.error || event.target.errorCode,
      );
      reject(event.target.error || event.target.errorCode);
      };
    });
  },

  saveEntryToDB: function (entryData) {
    return new Promise((resolve, reject) => {
      if (!db) {
      console.error("Database not initialized. Call initDB first.");
      return reject("Database not initialized.");
    }
    const transaction = db.transaction([STORE_NAME], "readwrite");
    const store = transaction.objectStore(STORE_NAME);

    // Ensure all required fields are present
    const entry = {
      timestamp: entryData.timestamp || new Date().toISOString(),
      text: entryData.text || "",
      photo: entryData.photo || null, // base64 string or null
      synced: false, // New entries are not synced
    };

    const requestAdd = store.add(entry);

    requestAdd.onsuccess = (event) => {
      console.log("Entry saved to DB. ID:", event.target.result);
      resolve(event.target.result); // Returns the ID of the newly added entry
    };

    requestAdd.onerror = (event) => {
      console.error(
        "Error saving entry to DB (static/app.js): ",
        event.target.errorCode,
      );
      reject(event.target.errorCode);
      };
    });
  },

  readAllEntriesFromDB: function () {
    return new Promise((resolve, reject) => {
      if (!db) {
      console.error("Database not initialized. Call initDB first.");
      return reject("Database not initialized.");
    }
    const transaction = db.transaction([STORE_NAME], "readonly");
    const store = transaction.objectStore(STORE_NAME);
    const requestGetAll = store.getAll();

    requestGetAll.onsuccess = (event) => {
      console.log("Entries retrieved successfully from DB (static/app.js).");
      resolve(event.target.result);
    };

    requestGetAll.onerror = (event) => {
      console.error(
        "Error reading entries from DB (static/app.js): ",
        event.target.errorCode,
      );
      reject(event.target.errorCode);
      };
    });
  },

  markEntryAsSyncedInDB: function (id) {
    return new Promise((resolve, reject) => {
      if (!db) {
      console.error("Database not initialized. Call initDB first.");
      return reject("Database not initialized.");
    }
    const transaction = db.transaction([STORE_NAME], "readwrite");
    const store = transaction.objectStore(STORE_NAME);
    const getRequest = store.get(id);

    getRequest.onsuccess = (event) => {
      const entry = event.target.result;
      if (entry) {
        entry.synced = true;
        const updateRequest = store.put(entry);
        updateRequest.onsuccess = () => {
          console.log(`Entry ${id} marked as synced in DB (static/app.js).`);
          resolve();
        };
        updateRequest.onerror = (event) => {
          console.error(
            `Error updating entry ${id} to synced (static/app.js): `,
            event.target.errorCode,
          );
          reject(event.target.errorCode);
        };
      } else {
        console.error(`Entry ${id} not found for syncing (static/app.js).`);
        reject(`Entry ${id} not found.`);
      }
    };
    getRequest.onerror = (event) => {
      console.error(
        `Error fetching entry ${id} for update (static/app.js): `,
        event.target.errorCode,
      );
      reject(event.target.errorCode);
    };
  });
  },
};
