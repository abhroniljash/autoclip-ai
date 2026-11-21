// AutoClip AI - Frontend API Client

const API_BASE = "/api";

export const api = {
    async getDashboardStats() {
        const res = await fetch(`${API_BASE}/dashboard/stats`);
        if (!res.ok) throw new Error("Failed to load dashboard stats");
        return res.json();
    },

    async getProjects() {
        const res = await fetch(`${API_BASE}/projects`);
        if (!res.ok) throw new Error("Failed to load projects");
        return res.json();
    },

    async getProject(projectId) {
        const res = await fetch(`${API_BASE}/projects/${projectId}`);
        if (!res.ok) throw new Error("Failed to load project details");
        return res.json();
    },

    async uploadVideo(formData, onProgress = null) {
        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();
            xhr.open("POST", `${API_BASE}/projects/upload`);

            if (xhr.upload && onProgress) {
                xhr.upload.onprogress = (e) => {
                    if (e.lengthComputable) {
                        const percent = Math.round((e.loaded / e.total) * 100);
                        onProgress(percent);
                    }
                };
            }

            xhr.onload = () => {
                if (xhr.status >= 200 && xhr.status < 300) {
                    try {
                        resolve(JSON.parse(xhr.responseText));
                    } catch (e) {
                        resolve(xhr.responseText);
                    }
                } else {
                    let errMsg = "Upload failed";
                    try {
                        const err = JSON.parse(xhr.responseText);
                        errMsg = err.detail || errMsg;
                    } catch (_) {}
                    reject(new Error(errMsg));
                }
            };

            xhr.onerror = () => reject(new Error("Network error during upload"));
            xhr.send(formData);
        });
    },

    async importYouTube(data) {
        const res = await fetch(`${API_BASE}/projects/youtube`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data)
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || "YouTube import failed");
        }
        return res.json();
    },

    async deleteProject(projectId) {
        const res = await fetch(`${API_BASE}/projects/${projectId}`, {
            method: "DELETE"
        });
        if (!res.ok) throw new Error("Failed to delete project");
        return res.json();
    },

    async getClip(clipId) {
        const res = await fetch(`${API_BASE}/clips/${clipId}`);
        if (!res.ok) throw new Error("Failed to fetch clip");
        return res.json();
    },

    async updateClip(clipId, data) {
        const res = await fetch(`${API_BASE}/clips/${clipId}`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data)
        });
        if (!res.ok) throw new Error("Failed to update clip");
        return res.json();
    },

    async reRenderClip(clipId) {
        const res = await fetch(`${API_BASE}/clips/${clipId}/render`, {
            method: "POST"
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || "Failed to render clip");
        }
        return res.json();
    },

    async getBgmTracks() {
        const res = await fetch(`${API_BASE}/clips/bgm/tracks`);
        if (!res.ok) return [];
        return res.json();
    },

    async createExportJob(projectId, data) {
        const res = await fetch(`${API_BASE}/projects/${projectId}/export`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data)
        });
        if (!res.ok) throw new Error("Failed to start export job");
        return res.json();
    },

    async getExportJobStatus(jobId) {
        const res = await fetch(`${API_BASE}/export/${jobId}/status`);
        if (!res.ok) throw new Error("Failed to check export status");
        return res.json();
    }
};
