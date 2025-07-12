const foodDiaryUtils = {
  dbName: "FoodDiaryDB",
  dbVersion: 1,
  storeName: "entries",
  apiBase: "/api/entries",

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

  async deleteEntryFromDB(entryId) {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(this.dbName, this.dbVersion);

      request.onsuccess = (event) => {
        const db = event.target.result;
        const transaction = db.transaction(this.storeName, "readwrite");
        const store = transaction.objectStore(this.storeName);

        const deleteRequest = store.delete(entryId);

        deleteRequest.onsuccess = () => {
          resolve();
        };

        deleteRequest.onerror = (error) => {
          reject(error);
        };
      };

      request.onerror = (event) => {
        reject(event.target.error);
      };
    });
  },

  // Network/sync functions
  async isOnline() {
    return navigator.onLine;
  },

  async syncWithServer() {
    if (!(await this.isOnline())) {
      console.log("Offline - skipping sync");
      return;
    }

    try {
      // Get all unsynced entries from IndexedDB
      const unsyncedEntries = await this.getUnsyncedEntries();

      // Upload unsynced entries to server
      for (const entry of unsyncedEntries) {
        await this.uploadEntryToServer(entry);
        await this.markEntryAsSyncedInDB(entry.id);
      }

      // Download entries from server and update local storage
      await this.downloadEntriesFromServer();

      console.log("Sync completed successfully");
    } catch (error) {
      console.error("Sync failed:", error);
      throw error;
    }
  },

  async getUnsyncedEntries() {
    const allEntries = await this.readAllEntriesFromDB();
    return allEntries.filter((entry) => !entry.synced);
  },

  async uploadEntryToServer(entry) {
    const response = await fetch(this.apiBase, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        timestamp: entry.timestamp,
        text: entry.text,
        photo: entry.photo,
      }),
    });

    if (!response.ok) {
      throw new Error(`Failed to upload entry: ${response.statusText}`);
    }

    return await response.json();
  },

  async downloadEntriesFromServer() {
    const response = await fetch(this.apiBase);

    if (!response.ok) {
      throw new Error(`Failed to fetch entries: ${response.statusText}`);
    }

    const serverEntries = await response.json();

    // Update local storage with server entries
    // Note: This is a simple implementation - in production you'd want
    // more sophisticated conflict resolution
    for (const serverEntry of serverEntries) {
      await this.saveServerEntryToDB(serverEntry);
    }
  },

  async saveServerEntryToDB(serverEntry) {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(this.dbName, this.dbVersion);

      request.onsuccess = (event) => {
        const db = event.target.result;
        const transaction = db.transaction(this.storeName, "readwrite");
        const store = transaction.objectStore(this.storeName);

        // Check if entry already exists
        const getRequest = store.get(serverEntry.id);

        getRequest.onsuccess = () => {
          const existingEntry = getRequest.result;

          if (!existingEntry) {
            // Entry doesn't exist locally, add it
            const entry = {
              id: serverEntry.id,
              timestamp: serverEntry.timestamp,
              text: serverEntry.text || "",
              photo: serverEntry.photo || null,
              synced: true,
            };

            const addRequest = store.put(entry);

            addRequest.onsuccess = () => {
              resolve();
            };

            addRequest.onerror = (error) => {
              reject(error);
            };
          } else {
            // Entry exists, update it if server version is newer
            existingEntry.synced = true;
            const updateRequest = store.put(existingEntry);

            updateRequest.onsuccess = () => {
              resolve();
            };

            updateRequest.onerror = (error) => {
              reject(error);
            };
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

  async deleteEntryOnServer(entryId) {
    if (!(await this.isOnline())) {
      console.log("Offline - will delete from server when online");
      return;
    }

    try {
      const response = await fetch(`${this.apiBase}/${entryId}`, {
        method: "DELETE",
      });

      if (!response.ok) {
        throw new Error(
          `Failed to delete entry on server: ${response.statusText}`,
        );
      }
    } catch (error) {
      console.error("Failed to delete entry on server:", error);
      // Don't throw - allow local deletion to proceed
    }
  },
};
