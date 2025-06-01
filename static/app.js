const foodDiaryUtils = {
  dbName: "FoodDiaryDB",
  dbVersion: 1,
  storeName: "entries",

  async initDB() {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(this.dbName, this.dbVersion);

      request.onupgradeneeded = (event) => {
        const db = event.target.result;
        if (!db.objectStoreNames.contains(this.storeName)) {
          const store = db.createObjectStore(this.storeName, {
            keyPath: "id",
            autoIncrement: true,
          });
          store.createIndex("timestamp", "timestamp", { unique: false });
          store.createIndex("synced", "synced", { unique: false });
        }
      };

      request.onsuccess = () => {
        console.log("Database initialized successfully");
        resolve();
      };

      request.onerror = (event) => {
        console.error("Database error:", event.target.error);
        reject(event.target.error);
      };
    });
  },

  async saveEntryToDB(entryData) {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(this.dbName, this.dbVersion);

      request.onsuccess = (event) => {
        const db = event.target.result;
        const transaction = db.transaction(this.storeName, "readwrite");
        const store = transaction.objectStore(this.storeName);

        const entry = {
          timestamp: entryData.timestamp || new Date().toISOString(),
          text: entryData.text || "",
          photo: entryData.photo || null,
          synced: false,
        };

        const addRequest = store.add(entry);

        addRequest.onsuccess = () => {
          resolve(addRequest.result); // Returns the auto-incremented ID
        };

        addRequest.onerror = (error) => {
          reject(error);
        };
      };

      request.onerror = (event) => {
        reject(event.target.error);
      };
    });
  },

  async readAllEntriesFromDB() {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(this.dbName, this.dbVersion);

      request.onsuccess = (event) => {
        const db = event.target.result;
        const transaction = db.transaction(this.storeName, "readonly");
        const store = transaction.objectStore(this.storeName);
        const getAllRequest = store.getAll();

        getAllRequest.onsuccess = () => {
          resolve(getAllRequest.result);
        };

        getAllRequest.onerror = (error) => {
          reject(error);
        };
      };

      request.onerror = (event) => {
        reject(event.target.error);
      };
    });
  },

  async markEntryAsSyncedInDB(entryId) {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(this.dbName, this.dbVersion);

      request.onsuccess = (event) => {
        const db = event.target.result;
        const transaction = db.transaction(this.storeName, "readwrite");
        const store = transaction.objectStore(this.storeName);

        const getRequest = store.get(entryId);

        getRequest.onsuccess = () => {
          const entry = getRequest.result;
          if (entry) {
            entry.synced = true;
            const updateRequest = store.put(entry);

            updateRequest.onsuccess = () => {
              resolve();
            };

            updateRequest.onerror = (error) => {
              reject(error);
            };
          } else {
            reject(new Error("Entry not found"));
          }
        };

        getRequest.onerror = (error) => {
          reject(error);
        };
      };

      request.onerror = (event) => {
        reject(event.target.error);
      };
    });
  },
};
