import { api } from "./api.js";

// Global App State
const state = {
    currentRoute: window.location.hash || "#/",
    stats: null,
    projects: [],
    currentProject: null,
    currentClip: null,
    pollingInterval: null,
};

// Initialize Theme
function initTheme() {
    const saved = localStorage.getItem("autoclip_theme");
    const isDark = saved === "dark" || (!saved && window.matchMedia("(prefers-color-scheme: dark)").matches);
    if (isDark) {
        document.documentElement.classList.add("dark");
    } else {
        document.documentElement.classList.remove("dark");
    }

    document.getElementById("theme-toggle")?.addEventListener("click", () => {
        const currentlyDark = document.documentElement.classList.contains("dark");
        if (currentlyDark) {
            document.documentElement.classList.remove("dark");
            localStorage.setItem("autoclip_theme", "light");
        } else {
            document.documentElement.classList.add("dark");
            localStorage.setItem("autoclip_theme", "dark");
        }
        if (window.lucide) window.lucide.createIcons();
    });
}

// Router
function navigate(route) {
    window.location.hash = route;
}

window.addEventListener("hashchange", () => {
    state.currentRoute = window.location.hash || "#/";
    renderRoute();
});

// Main Route Dispatcher
async function renderRoute() {
    if (state.pollingInterval) {
        clearInterval(state.pollingInterval);
        state.pollingInterval = null;
    }

    const root = document.getElementById("app-root");
    const hash = state.currentRoute;
    const protectedRoute = hash.startsWith("#/dashboard") || hash.startsWith("#/projects/");
    if (protectedRoute && !sessionStorage.getItem("autoclip_access_token")) { navigate("#/login"); return; }

    // Update active nav links
    document.querySelectorAll(".nav-link").forEach(link => {
        const href = link.getAttribute("href");
        if ((href === "#/" && hash === "#/") || (href !== "#/" && hash.startsWith(href))) {
            link.classList.add("text-brand-600", "dark:text-brand-400", "font-semibold");
        } else {
            link.classList.remove("text-brand-600", "dark:text-brand-400", "font-semibold");
        }
    });

    try {
        if (hash === "#/login" || hash === "#/register") {
            renderAuthPage(root, hash === "#/register");
        } else if (hash === "#/" || hash === "") {
            renderLandingPage(root);
        } else if (hash === "#/dashboard") {
            await renderDashboardPage(root);
        } else if (hash === "#/projects/new") {
            renderNewProjectPage(root);
        } else if (hash.startsWith("#/projects/") && hash.includes("/analysis")) {
            const projectId = hash.split("/")[2];
            await renderAnalysisPage(root, projectId);
        } else if (hash.startsWith("#/projects/") && hash.includes("/editor/")) {
            const parts = hash.split("/");
            const projectId = parts[2];
            const clipId = parts[4];
            await renderEditorPage(root, projectId, clipId);
        } else if (hash.startsWith("#/projects/") && hash.includes("/export")) {
            const projectId = hash.split("/")[2];
            await renderExportPage(root, projectId);
        } else {
            root.innerHTML = `<div class="text-center py-20 text-slate-500">Page not found. <a href="#/" class="text-brand-600 underline">Go Home</a></div>`;
        }
    } catch (err) {
        console.error("Routing error:", err);
        root.innerHTML = `<div class="p-6 bg-red-50 dark:bg-red-950/30 text-red-600 rounded-2xl max-w-lg mx-auto text-center border border-red-200 dark:border-red-800">
            <h3 class="font-bold text-lg mb-2">Something went wrong</h3>
            <p class="text-sm">${err.message}</p>
            <button onclick="window.location.hash='#/dashboard'" class="mt-4 px-4 py-2 bg-red-600 text-white rounded-xl text-sm font-medium">Return to Dashboard</button>
        </div>`;
    }

    if (window.lucide) window.lucide.createIcons();
}

/* =========================================================================
   AUTHENTICATION
========================================================================= */
function renderAuthPage(container, register = false) {
    container.innerHTML = '<div class="max-w-md mx-auto my-12 p-8 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm">' +
        '<h1 class="text-2xl font-bold mb-2">' + (register ? "Create your AutoClip AI account" : "Welcome back") + '</h1>' +
        '<p class="text-sm text-slate-500 mb-6">' + (register ? "Create an account to manage your clips." : "Sign in to access your projects.") + '</p>' +
        '<form id="auth-form" class="space-y-4">' +
        (register ? '<label class="block text-sm">Name<input name="name" required maxlength="120" class="mt-1 w-full rounded-lg border p-3 dark:bg-slate-800"></label>' : "") +
        '<label class="block text-sm">Email<input name="email" type="email" required autocomplete="email" class="mt-1 w-full rounded-lg border p-3 dark:bg-slate-800"></label>' +
        '<label class="block text-sm">Password<input name="password" type="password" required minlength="' + (register ? "12" : "1") + '" autocomplete="' + (register ? "new-password" : "current-password") + '" class="mt-1 w-full rounded-lg border p-3 dark:bg-slate-800"></label>' +
        '<p id="auth-error" class="text-sm text-red-600" role="alert"></p><button class="w-full rounded-lg bg-brand-600 text-white font-semibold p-3" type="submit">' + (register ? "Create account" : "Sign in") + '</button></form>' +
        '<p class="text-sm text-center mt-5 text-slate-500">' + (register ? 'Already registered? <a href="#/login" class="text-brand-600 underline">Sign in</a>' : 'New here? <a href="#/register" class="text-brand-600 underline">Create an account</a>') + '</p></div>';
    container.querySelector("#auth-form").addEventListener("submit", async (event) => {
        event.preventDefault();
        const data = Object.fromEntries(new FormData(event.currentTarget).entries());
        const error = container.querySelector("#auth-error");
        error.textContent = "";
        try {
            if (register) await api.register(data); else await api.login(data);
            navigate("#/dashboard");
        } catch (err) { error.textContent = err.message || "Unable to authenticate."; }
    });
}
/* =========================================================================
   PAGE 1: LANDING PAGE
========================================================================= */
function renderLandingPage(container) {
    container.innerHTML = `
        <div class="space-y-24 py-6">
            <!-- Hero Section -->
            <div class="text-center max-w-4xl mx-auto space-y-6">
                <div class="inline-flex items-center space-x-2 px-3.5 py-1.5 rounded-full bg-brand-50 dark:bg-brand-950/50 border border-brand-200 dark:border-brand-800 text-brand-700 dark:text-brand-300 text-xs font-semibold">
                    <span class="flex h-2 w-2 rounded-full bg-brand-600 animate-ping"></span>
                    <span>AI-Powered Long-to-Short Video Engine</span>
                </div>
                <h1 class="text-4xl sm:text-6xl font-extrabold tracking-tight text-slate-900 dark:text-white leading-[1.15]">
                    Upload One Long Video.<br>
                    <span class="bg-gradient-to-r from-brand-600 via-indigo-600 to-violet-500 bg-clip-text text-transparent">Get Multiple Viral Shorts.</span>
                </h1>
                <p class="text-lg sm:text-xl text-slate-600 dark:text-slate-400 max-w-2xl mx-auto font-normal">
                    Transform hours of podcasts, webinars, and YouTube videos into captivating, professionally edited vertical clips with animated captions and explainable virality scoring.
                </p>
                <div class="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4">
                    <a href="#/projects/new" class="w-full sm:w-auto px-8 py-3.5 rounded-xl font-bold bg-brand-600 hover:bg-brand-700 text-white shadow-lg shadow-brand-600/30 transition-all hover:scale-105 flex items-center justify-center space-x-2">
                        <i data-lucide="sparkles" class="w-5 h-5"></i>
                        <span>Start Repurposing Video</span>
                    </a>
                    <a href="#/dashboard" class="w-full sm:w-auto px-6 py-3.5 rounded-xl font-semibold bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors flex items-center justify-center space-x-2">
                        <i data-lucide="layout-dashboard" class="w-5 h-5"></i>
                        <span>View Dashboard</span>
                    </a>
                </div>
            </div>

            <!-- Visual Workflow Showcase -->
            <div class="relative bg-gradient-to-b from-slate-100 to-white dark:from-slate-900 dark:to-slate-950 rounded-3xl p-8 border border-slate-200 dark:border-slate-800 shadow-xl overflow-hidden">
                <div class="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
                    <!-- Left: 16:9 Long Form Input Representation -->
                    <div class="lg:col-span-5 space-y-4">
                        <div class="flex items-center justify-between text-xs font-semibold text-slate-400">
                            <span class="flex items-center gap-1.5"><i data-lucide="video" class="w-4 h-4"></i> Original Long Video (16:9)</span>
                            <span>45:20 mins</span>
                        </div>
                        <div class="aspect-video bg-slate-800 rounded-2xl overflow-hidden relative shadow-inner flex items-center justify-center border border-slate-700">
                            <div class="absolute inset-0 bg-cover bg-center opacity-40" style="background-image: url('https://images.unsplash.com/photo-1590602847861-f357a9332bbc?auto=format&fit=crop&w=800&q=80')"></div>
                            <div class="z-10 text-center space-y-2 p-4">
                                <span class="px-2.5 py-1 bg-red-600 text-white text-[10px] font-bold rounded-md">YouTube Podcast</span>
                                <p class="text-white font-medium text-sm">Full Length High Value Discussion</p>
                            </div>
                        </div>
                        <div class="space-y-2 text-xs text-slate-500 dark:text-slate-400">
                            <div class="flex items-center gap-2">
                                <i data-lucide="check-circle" class="w-4 h-4 text-emerald-500"></i>
                                <span>Word-level timestamped transcription</span>
                            </div>
                            <div class="flex items-center gap-2">
                                <i data-lucide="check-circle" class="w-4 h-4 text-emerald-500"></i>
                                <span>Automatic speech silence detection & chunking</span>
                            </div>
                        </div>
                    </div>

                    <!-- Center Arrow -->
                    <div class="lg:col-span-2 flex flex-col items-center justify-center text-brand-600 dark:text-brand-400 space-y-1">
                        <div class="p-3 bg-brand-50 dark:bg-brand-950 rounded-full border border-brand-200 dark:border-brand-800 shadow-sm animate-pulse">
                            <i data-lucide="arrow-right" class="w-6 h-6 hidden lg:block"></i>
                            <i data-lucide="arrow-down" class="w-6 h-6 lg:hidden"></i>
                        </div>
                        <span class="text-[11px] font-bold uppercase tracking-wider">AI Engine</span>
                    </div>

                    <!-- Right: Vertical 9:16 Generated Shorts Mockup -->
                    <div class="lg:col-span-5 grid grid-cols-2 gap-4">
                        <div class="phone-mockup-frame border border-slate-800 shadow-2xl">
                            <div class="phone-mockup-notch"></div>
                            <div class="absolute inset-0 bg-slate-900 bg-cover bg-center" style="background-image: url('https://images.unsplash.com/photo-1590602847861-f357a9332bbc?auto=format&fit=crop&w=600&q=80');"></div>
                            <div class="absolute top-4 right-4 z-20">
                                <span class="score-badge-high px-2 py-0.5 rounded-full text-[11px] font-black">94%</span>
                            </div>
                            <div class="absolute inset-x-0 bottom-6 p-4 z-20 text-center">
                                <div class="caption-style-bold-viral text-sm leading-tight">
                                    THE SINGLE <span class="highlight">BIGGEST</span> MISTAKE!
                                </div>
                            </div>
                        </div>
                        <div class="phone-mockup-frame border border-slate-800 shadow-2xl hidden sm:block">
                            <div class="phone-mockup-notch"></div>
                            <div class="absolute inset-0 bg-slate-900 bg-cover bg-center" style="background-image: url('https://images.unsplash.com/photo-1516321318423-f06f85e504b3?auto=format&fit=crop&w=600&q=80');"></div>
                            <div class="absolute top-4 right-4 z-20">
                                <span class="score-badge-high px-2 py-0.5 rounded-full text-[11px] font-black">89%</span>
                            </div>
                            <div class="absolute inset-x-0 bottom-6 p-4 z-20 text-center">
                                <div class="caption-style-podcast text-xs">
                                    "When you understand <span class="highlight">retention</span>..."
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Features Grid -->
            <div class="space-y-12">
                <div class="text-center max-w-2xl mx-auto space-y-3">
                    <h2 class="text-3xl font-bold tracking-tight text-slate-900 dark:text-white">Built for High Retention & Virality</h2>
                    <p class="text-slate-500 dark:text-slate-400">Everything needed to transform raw footage into production-grade social shorts without manual video editing.</p>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <div class="p-6 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-3">
                        <div class="w-12 h-12 rounded-xl bg-indigo-50 dark:bg-indigo-950/50 text-indigo-600 dark:text-indigo-400 flex items-center justify-center">
                            <i data-lucide="brain-circuit" class="w-6 h-6"></i>
                        </div>
                        <h3 class="font-bold text-lg text-slate-900 dark:text-white">8-Factor Virality Scoring</h3>
                        <p class="text-sm text-slate-500 dark:text-slate-400 leading-relaxed">
                            Evaluates hook strength, emotional resonance, novelty, context completeness, pacing, audio clarity, and shareability on a transparent 0–100 scale.
                        </p>
                    </div>

                    <div class="p-6 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-3">
                        <div class="w-12 h-12 rounded-xl bg-emerald-50 dark:bg-emerald-950/50 text-emerald-600 dark:text-emerald-400 flex items-center justify-center">
                            <i data-lucide="scan-face" class="w-6 h-6"></i>
                        </div>
                        <h3 class="font-bold text-lg text-slate-900 dark:text-white">Smart Active Speaker Cropping</h3>
                        <p class="text-sm text-slate-500 dark:text-slate-400 leading-relaxed">
                            Detects speaker presence and motion to dynamically reframe 16:9 widescreen videos into vertical 9:16 format with optional podcast split-screen.
                        </p>
                    </div>

                    <div class="p-6 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-3">
                        <div class="w-12 h-12 rounded-xl bg-amber-50 dark:bg-amber-950/50 text-amber-600 dark:text-amber-400 flex items-center justify-center">
                            <i data-lucide="subtitles" class="w-6 h-6"></i>
                        </div>
                        <h3 class="font-bold text-lg text-slate-900 dark:text-white">5 Animated Subtitle Presets</h3>
                        <p class="text-sm text-slate-500 dark:text-slate-400 leading-relaxed">
                            Generate karaoke-style captions (Bold Viral, Minimal, Podcast, Cinematic, Highlighted) with synchronized word highlighting and emojis.
                        </p>
                    </div>

                    <div class="p-6 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-3">
                        <div class="w-12 h-12 rounded-xl bg-violet-50 dark:bg-violet-950/50 text-violet-600 dark:text-violet-400 flex items-center justify-center">
                            <i data-lucide="music" class="w-6 h-6"></i>
                        </div>
                        <h3 class="font-bold text-lg text-slate-900 dark:text-white">Audio Normalization & BGM</h3>
                        <p class="text-sm text-slate-500 dark:text-slate-400 leading-relaxed">
                            Automatic broadcast-standard loudness leveling with curated royalty-free background music tracks seamlessly ducked under spoken speech.
                        </p>
                    </div>

                    <div class="p-6 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-3">
                        <div class="w-12 h-12 rounded-xl bg-rose-50 dark:bg-rose-950/50 text-rose-600 dark:text-rose-400 flex items-center justify-center">
                            <i data-lucide="share-2" class="w-6 h-6"></i>
                        </div>
                        <h3 class="font-bold text-lg text-slate-900 dark:text-white">Social Media Kit Generator</h3>
                        <p class="text-sm text-slate-500 dark:text-slate-400 leading-relaxed">
                            Get 3 viral title variants, ready-to-copy Instagram captions, YouTube Shorts descriptions, and trending hashtags for every clip.
                        </p>
                    </div>

                    <div class="p-6 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-3">
                        <div class="w-12 h-12 rounded-xl bg-cyan-50 dark:bg-cyan-950/50 text-cyan-600 dark:text-cyan-400 flex items-center justify-center">
                            <i data-lucide="archive" class="w-6 h-6"></i>
                        </div>
                        <h3 class="font-bold text-lg text-slate-900 dark:text-white">One-Click Batch ZIP Export</h3>
                        <p class="text-sm text-slate-500 dark:text-slate-400 leading-relaxed">
                            Download all finished 1080x1920 MP4 clips, SRT subtitle files, and social media text kits neatly organized into a single archive.
                        </p>
                    </div>
                </div>
            </div>

            <!-- Pricing Section Placeholder -->
            <div class="border-t border-slate-200 dark:border-slate-800 pt-16">
                <div class="text-center max-w-xl mx-auto mb-10 space-y-2">
                    <h3 class="text-2xl font-bold text-slate-900 dark:text-white">Simple, Transparent Pricing</h3>
                    <p class="text-sm text-slate-500">Pick the plan that suits your content workflow.</p>
                </div>
                <div class="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-5xl mx-auto">
                    <div class="p-6 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-4">
                        <h4 class="font-bold text-slate-900 dark:text-white">Free Starter</h4>
                        <div class="text-3xl font-extrabold text-slate-900 dark:text-white">$0 <span class="text-xs font-normal text-slate-400">/mo</span></div>
                        <p class="text-xs text-slate-500">60 mins processing / month, 720p export, community support.</p>
                        <a href="#/projects/new" class="block text-center py-2 px-4 rounded-xl text-sm font-semibold border border-slate-300 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800">Get Started</a>
                    </div>
                    <div class="p-6 rounded-2xl bg-brand-50/50 dark:bg-brand-950/30 border-2 border-brand-600 space-y-4 relative">
                        <span class="absolute -top-3 right-4 px-2.5 py-0.5 bg-brand-600 text-white rounded-full text-[10px] font-bold uppercase">Popular</span>
                        <h4 class="font-bold text-brand-900 dark:text-brand-100">Creator Pro</h4>
                        <div class="text-3xl font-extrabold text-slate-900 dark:text-white">$29 <span class="text-xs font-normal text-slate-400">/mo</span></div>
                        <p class="text-xs text-slate-500">300 mins processing, 1080p vertical export, all subtitle presets & BGM.</p>
                        <a href="#/projects/new" class="block text-center py-2 px-4 rounded-xl text-sm font-semibold bg-brand-600 text-white hover:bg-brand-700 shadow-md shadow-brand-600/30">Upgrade to Pro</a>
                    </div>
                    <div class="p-6 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-4">
                        <h4 class="font-bold text-slate-900 dark:text-white">Agency</h4>
                        <div class="text-3xl font-extrabold text-slate-900 dark:text-white">$79 <span class="text-xs font-normal text-slate-400">/mo</span></div>
                        <p class="text-xs text-slate-500">Unlimited processing, multi-user seats, custom fonts, API access.</p>
                        <a href="#/projects/new" class="block text-center py-2 px-4 rounded-xl text-sm font-semibold border border-slate-300 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800">Contact Sales</a>
                    </div>
                </div>
            </div>
        </div>
    `;
}

/* =========================================================================
   PAGE 2: DASHBOARD
========================================================================= */
async function renderDashboardPage(container) {
    container.innerHTML = `
        <div class="flex items-center justify-center min-h-[40vh]">
            <div class="animate-spin rounded-full h-8 w-8 border-4 border-brand-500 border-t-transparent"></div>
        </div>
    `;

    const stats = await api.getDashboardStats();
    state.stats = stats;

    const projectsHtml = stats.recent_projects.length === 0 
        ? `<div class="text-center py-16 bg-white dark:bg-slate-900 rounded-2xl border border-dashed border-slate-300 dark:border-slate-800 p-8 space-y-4">
            <div class="w-12 h-12 mx-auto rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-400">
                <i data-lucide="video" class="w-6 h-6"></i>
            </div>
            <h4 class="font-semibold text-slate-800 dark:text-slate-200">No Video Projects Yet</h4>
            <p class="text-sm text-slate-500 max-w-sm mx-auto">Upload a long-form video or provide an authorized video source to automatically generate your first clips.</p>
            <a href="#/projects/new" class="inline-flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-brand-600 text-white font-medium text-sm shadow-md hover:bg-brand-700">
                <i data-lucide="plus" class="w-4 h-4"></i>
                <span>Create New Project</span>
            </a>
        </div>`
        : `<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            ${stats.recent_projects.map(p => renderProjectCard(p)).join("")}
        </div>`;

    container.innerHTML = `
        <div class="space-y-8">
            <!-- Header -->
            <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div>
                    <h1 class="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">Creator Dashboard</h1>
                    <p class="text-sm text-slate-500">Monitor processing workflows and access your repurposed clips.</p>
                </div>
                <a href="#/projects/new" class="inline-flex items-center justify-center space-x-2 px-5 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-700 text-white font-semibold text-sm shadow-sm shadow-brand-600/30 transition-all">
                    <i data-lucide="upload-cloud" class="w-4 h-4"></i>
                    <span>New Video Project</span>
                </a>
            </div>

            <!-- Stats Metrics -->
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-5">
                <div class="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm flex items-center space-x-4">
                    <div class="w-12 h-12 rounded-xl bg-indigo-50 dark:bg-indigo-950/50 text-indigo-600 dark:text-indigo-400 flex items-center justify-center">
                        <i data-lucide="folder-kanban" class="w-6 h-6"></i>
                    </div>
                    <div>
                        <div class="text-2xl font-black text-slate-900 dark:text-white">${stats.total_projects}</div>
                        <div class="text-xs font-medium text-slate-500 uppercase tracking-wider">Total Projects</div>
                    </div>
                </div>

                <div class="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm flex items-center space-x-4">
                    <div class="w-12 h-12 rounded-xl bg-emerald-50 dark:bg-emerald-950/50 text-emerald-600 dark:text-emerald-400 flex items-center justify-center">
                        <i data-lucide="check-circle-2" class="w-6 h-6"></i>
                    </div>
                    <div>
                        <div class="text-2xl font-black text-slate-900 dark:text-white">${stats.total_videos_processed}</div>
                        <div class="text-xs font-medium text-slate-500 uppercase tracking-wider">Videos Processed</div>
                    </div>
                </div>

                <div class="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm flex items-center space-x-4">
                    <div class="w-12 h-12 rounded-xl bg-violet-50 dark:bg-violet-950/50 text-violet-600 dark:text-violet-400 flex items-center justify-center">
                        <i data-lucide="film" class="w-6 h-6"></i>
                    </div>
                    <div>
                        <div class="text-2xl font-black text-slate-900 dark:text-white">${stats.total_clips_generated}</div>
                        <div class="text-xs font-medium text-slate-500 uppercase tracking-wider">Clips Generated</div>
                    </div>
                </div>
            </div>

            <!-- Recent Projects Section -->
            <div class="space-y-4">
                <div class="flex items-center justify-between">
                    <h3 class="font-bold text-lg text-slate-900 dark:text-white">Recent Projects</h3>
                    <span class="text-xs text-slate-400 font-medium">${stats.recent_projects.length} loaded</span>
                </div>
                ${projectsHtml}
            </div>
        </div>
    `;

    // Attach delete button listeners
    container.querySelectorAll(".btn-delete-project").forEach(btn => {
        btn.addEventListener("click", async (e) => {
            e.stopPropagation();
            const id = btn.getAttribute("data-id");
            if (confirm("Are you sure you want to delete this project and all its clips?")) {
                await api.deleteProject(id);
                renderDashboardPage(container);
            }
        });
    });
}

function renderProjectCard(project) {
    const isCompleted = project.processing_status === "completed";
    const isFailed = project.processing_status === "failed";
    const isProcessing = !isCompleted && !isFailed;

    const statusBadge = isCompleted 
        ? `<span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
            <span class="h-1.5 w-1.5 rounded-full bg-emerald-500"></span> Completed
           </span>`
        : isFailed
        ? `<span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300">
            <span class="h-1.5 w-1.5 rounded-full bg-red-500"></span> Failed
           </span>`
        : `<span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-brand-100 text-brand-800 dark:bg-brand-950 dark:text-brand-300">
            <span class="h-1.5 w-1.5 rounded-full bg-brand-500 animate-ping"></span> ${project.processing_status.replace("_", " ")} (${project.progress}%)
           </span>`;

    const targetUrl = isCompleted ? `#/projects/${project.id}/analysis` : `#/projects/${project.id}/analysis`;

    return `
        <div class="group rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm hover:shadow-md transition-all overflow-hidden flex flex-col">
            <!-- Thumbnail / Preview Area -->
            <div class="aspect-video bg-slate-900 relative overflow-hidden cursor-pointer" onclick="window.location.hash='${targetUrl}'">
                ${project.video_duration > 0
                    ? `<img src="/api/projects/${project.id}/thumbnail" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" alt="Thumbnail">`
                    : `<div class="w-full h-full flex items-center justify-center text-slate-600"><i data-lucide="video" class="w-8 h-8"></i></div>`
                }
                <div class="absolute top-3 left-3">${statusBadge}</div>
                <div class="absolute bottom-3 right-3 px-2 py-0.5 rounded bg-black/75 text-white text-[11px] font-mono">
                    ${project.video_duration ? Math.floor(project.video_duration / 60) + ":" + String(Math.floor(project.video_duration % 60)).padStart(2, '0') : "0:00"}
                </div>
            </div>

            <!-- Card Body -->
            <div class="p-5 flex-1 flex flex-col justify-between space-y-4">
                <div>
                    <h4 class="font-bold text-slate-900 dark:text-white line-clamp-1 group-hover:text-brand-600 transition-colors" title="${project.project_name}">
                        ${project.project_name}
                    </h4>
                    <p class="text-xs text-slate-500 mt-1 flex items-center gap-2">
                        <span>${new Date(project.created_at).toLocaleDateString()}</span>
                        <span>•</span>
                        <span>${project.clip_count} clips ready</span>
                    </p>
                </div>

                ${isProcessing ? `
                    <div class="space-y-1">
                        <div class="w-full bg-slate-100 dark:bg-slate-800 h-2 rounded-full overflow-hidden">
                            <div class="bg-brand-600 h-full rounded-full transition-all duration-500" style="width: ${project.progress}%"></div>
                        </div>
                        <div class="flex justify-between text-[11px] text-slate-400">
                            <span>Processing...</span>
                            <span>${project.progress}%</span>
                        </div>
                    </div>
                ` : ""}

                <div class="pt-2 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between">
                    <a href="${targetUrl}" class="text-xs font-semibold text-brand-600 dark:text-brand-400 hover:underline flex items-center gap-1">
                        <span>View Clips</span>
                        <i data-lucide="arrow-right" class="w-3.5 h-3.5"></i>
                    </a>
                    <button class="btn-delete-project text-slate-400 hover:text-red-500 p-1.5 rounded-lg transition-colors" data-id="${project.id}" title="Delete Project">
                        <i data-lucide="trash-2" class="w-4 h-4"></i>
                    </button>
                </div>
            </div>
        </div>
    `;
}

/* =========================================================================
   PAGE 3: NEW VIDEO PROJECT
========================================================================= */
function renderNewProjectPage(container) {
    container.innerHTML = `
        <div class="max-w-3xl mx-auto space-y-8">
            <!-- Header -->
            <div class="text-center space-y-2">
                <h1 class="text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white">Create New Video Project</h1>
                <p class="text-sm text-slate-500">Upload your source video or provide an authorized link to begin AI repurposing.</p>
            </div>

            <!-- Form Container -->
            <div class="bg-white dark:bg-slate-900 rounded-3xl p-6 sm:p-8 border border-slate-200 dark:border-slate-800 shadow-sm space-y-6">
                <!-- Source Input Tabs -->
                <div class="flex border-b border-slate-200 dark:border-slate-800">
                    <button id="tab-upload" class="tab-btn px-6 py-3 font-semibold text-sm border-b-2 border-brand-600 text-brand-600 dark:text-brand-400 flex items-center gap-2">
                        <i data-lucide="upload" class="w-4 h-4"></i> Video Upload
                    </button>
                    <button id="tab-youtube" class="tab-btn px-6 py-3 font-medium text-sm text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 flex items-center gap-2">
                        <i data-lucide="youtube" class="w-4 h-4"></i> YouTube Source
                    </button>
                </div>

                <!-- Section A: File Upload Zone -->
                <div id="section-upload" class="space-y-4">
                    <div id="drop-zone" class="border-2 border-dashed border-slate-300 dark:border-slate-700 hover:border-brand-500 dark:hover:border-brand-500 rounded-2xl p-8 text-center cursor-pointer transition-colors bg-slate-50/50 dark:bg-slate-950/30">
                        <input type="file" id="video-file-input" class="hidden" accept=".mp4,.mov,.webm,.mkv">
                        <div class="space-y-3">
                            <div class="w-14 h-14 mx-auto rounded-2xl bg-brand-50 dark:bg-brand-950 text-brand-600 dark:text-brand-400 flex items-center justify-center">
                                <i data-lucide="cloud-upload" class="w-7 h-7"></i>
                            </div>
                            <div>
                                <p class="text-sm font-semibold text-slate-700 dark:text-slate-300">
                                    <span class="text-brand-600 underline">Click to upload</span> or drag and drop video
                                </p>
                                <p class="text-xs text-slate-400 mt-1">MP4, MOV, WebM (up to 1 GB)</p>
                            </div>
                            <div id="selected-file-name" class="hidden text-xs font-semibold text-emerald-600 bg-emerald-50 dark:bg-emerald-950/50 py-1 px-3 rounded-full inline-block"></div>
                        </div>
                    </div>
                </div>

                <!-- Section B: YouTube URL Input -->
                <div id="section-youtube" class="hidden space-y-4">
                    <div>
                        <label class="block text-xs font-bold uppercase tracking-wider text-slate-600 dark:text-slate-400 mb-2">Authorized YouTube URL</label>
                        <div class="relative">
                            <i data-lucide="link" class="w-4 h-4 absolute left-3.5 top-3.5 text-slate-400"></i>
                            <input type="url" id="youtube-url-input" placeholder="https://www.youtube.com/watch?v=..." class="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500">
                        </div>
                    </div>
                    <div class="p-3.5 rounded-xl bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800/50 text-xs text-amber-800 dark:text-amber-300 flex items-start gap-2.5">
                        <i data-lucide="alert-triangle" class="w-4 h-4 shrink-0 mt-0.5"></i>
                        <span>
                            <strong>Platform Policy Notice:</strong> Only authorized, publicly accessible YouTube sources are supported. If platform permissions restrict media stream access, please upload your original video file directly.
                        </span>
                    </div>
                </div>

                <!-- Project Configuration Settings -->
                <div class="space-y-5 pt-4 border-t border-slate-100 dark:border-slate-800">
                    <div>
                        <label class="block text-xs font-bold uppercase tracking-wider text-slate-600 dark:text-slate-400 mb-2">Project Name (Optional)</label>
                        <input type="text" id="project-name-input" placeholder="E.g. Podcast Episode #42 Highlights" class="w-full px-4 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500">
                    </div>

                    <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
                        <div>
                            <label class="block text-xs font-bold uppercase tracking-wider text-slate-600 dark:text-slate-400 mb-2">Clip Duration</label>
                            <select id="duration-pref-input" class="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500">
                                <option value="30-60" selected>30 – 60s (Recommended)</option>
                                <option value="20-40">20 – 40s (Fast Paced)</option>
                                <option value="60-90">60 – 90s (Extended Story)</option>
                                <option value="auto">Auto (AI Decides)</option>
                            </select>
                        </div>

                        <div>
                            <label class="block text-xs font-bold uppercase tracking-wider text-slate-600 dark:text-slate-400 mb-2">Target Clips</label>
                            <select id="clip-count-input" class="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500">
                                <option value="3">Top 3 Clips</option>
                                <option value="5" selected>Top 5 Clips (Best)</option>
                                <option value="8">Top 8 Clips</option>
                                <option value="10">Top 10 Clips</option>
                            </select>
                        </div>

                        <div>
                            <label class="block text-xs font-bold uppercase tracking-wider text-slate-600 dark:text-slate-400 mb-2">Spoken Language</label>
                            <select id="language-input" class="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500">
                                <option value="en" selected>English</option>
                                <option value="bn">Bengali (বাংলা)</option>
                                <option value="hi">Hindi (हिन्दी)</option>
                            </select>
                        </div>
                    </div>

                    <!-- Subtitle Style Presets -->
                    <div>
                        <label class="block text-xs font-bold uppercase tracking-wider text-slate-600 dark:text-slate-400 mb-2">Subtitle Preset Style</label>
                        <div class="grid grid-cols-2 sm:grid-cols-5 gap-3" id="style-presets-picker">
                            <label class="cursor-pointer border-2 border-brand-600 bg-brand-50/50 dark:bg-brand-950/40 rounded-xl p-3 text-center space-y-1 block">
                                <input type="radio" name="subtitle-style" value="bold_viral" checked class="hidden style-radio">
                                <span class="caption-style-bold-viral text-xs block text-slate-900 dark:text-white">VIRAL</span>
                                <span class="text-[10px] text-slate-500 block font-semibold">Bold Viral</span>
                            </label>
                            <label class="cursor-pointer border border-slate-200 dark:border-slate-800 rounded-xl p-3 text-center space-y-1 block hover:border-brand-500">
                                <input type="radio" name="subtitle-style" value="clean_minimal" class="hidden style-radio">
                                <span class="caption-style-clean-minimal text-xs block text-slate-900 dark:text-white">Minimal</span>
                                <span class="text-[10px] text-slate-500 block font-semibold">Clean</span>
                            </label>
                            <label class="cursor-pointer border border-slate-200 dark:border-slate-800 rounded-xl p-3 text-center space-y-1 block hover:border-brand-500">
                                <input type="radio" name="subtitle-style" value="podcast" class="hidden style-radio">
                                <span class="caption-style-podcast text-[10px] block text-slate-900 dark:text-white">Podcast</span>
                                <span class="text-[10px] text-slate-500 block font-semibold">Framed</span>
                            </label>
                            <label class="cursor-pointer border border-slate-200 dark:border-slate-800 rounded-xl p-3 text-center space-y-1 block hover:border-brand-500">
                                <input type="radio" name="subtitle-style" value="cinematic" class="hidden style-radio">
                                <span class="caption-style-cinematic text-xs block text-slate-900 dark:text-white">Story</span>
                                <span class="text-[10px] text-slate-500 block font-semibold">Cinematic</span>
                            </label>
                            <label class="cursor-pointer border border-slate-200 dark:border-slate-800 rounded-xl p-3 text-center space-y-1 block hover:border-brand-500">
                                <input type="radio" name="subtitle-style" value="highlight_keyword" class="hidden style-radio">
                                <span class="caption-style-highlight-keyword text-xs block text-slate-900 dark:text-white">ENERGY</span>
                                <span class="text-[10px] text-slate-500 block font-semibold">Highlight</span>
                            </label>
                        </div>
                    </div>
                </div>

                <!-- Upload Progress Indicator -->
                <div id="upload-progress-container" class="hidden space-y-2 pt-2">
                    <div class="flex justify-between text-xs font-semibold text-slate-600 dark:text-slate-400">
                        <span>Uploading Video File...</span>
                        <span id="upload-progress-percent">0%</span>
                    </div>
                    <div class="w-full bg-slate-100 dark:bg-slate-800 h-2.5 rounded-full overflow-hidden">
                        <div id="upload-progress-bar" class="bg-brand-600 h-full rounded-full transition-all duration-300" style="width: 0%"></div>
                    </div>
                </div>

                <!-- Submit Button -->
                <button id="btn-submit-project" class="w-full py-4 rounded-xl font-bold bg-brand-600 hover:bg-brand-700 text-white shadow-lg shadow-brand-600/30 transition-all flex items-center justify-center space-x-2 text-base">
                    <i data-lucide="sparkles" class="w-5 h-5"></i>
                    <span>Start AI Analysis & Repurposing</span>
                </button>
            </div>
        </div>
    `;

    let activeTab = "upload";
    let selectedFile = null;

    // Tab Switcher
    const tabUpload = document.getElementById("tab-upload");
    const tabYouTube = document.getElementById("tab-youtube");
    const secUpload = document.getElementById("section-upload");
    const secYouTube = document.getElementById("section-youtube");

    tabUpload.addEventListener("click", () => {
        activeTab = "upload";
        tabUpload.classList.add("border-b-2", "border-brand-600", "text-brand-600", "dark:text-brand-400");
        tabYouTube.classList.remove("border-b-2", "border-brand-600", "text-brand-600", "dark:text-brand-400");
        secUpload.classList.remove("hidden");
        secYouTube.classList.add("hidden");
    });

    tabYouTube.addEventListener("click", () => {
        activeTab = "youtube";
        tabYouTube.classList.add("border-b-2", "border-brand-600", "text-brand-600", "dark:text-brand-400");
        tabUpload.classList.remove("border-b-2", "border-brand-600", "text-brand-600", "dark:text-brand-400");
        secYouTube.classList.remove("hidden");
        secUpload.classList.add("hidden");
    });

    // File Drag & Drop
    const dropZone = document.getElementById("drop-zone");
    const fileInput = document.getElementById("video-file-input");
    const fileNameDisplay = document.getElementById("selected-file-name");

    dropZone.addEventListener("click", () => fileInput.click());
    dropZone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropZone.classList.add("border-brand-500", "bg-brand-50/20");
    });
    dropZone.addEventListener("dragleave", () => {
        dropZone.classList.remove("border-brand-500", "bg-brand-50/20");
    });
    dropZone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropZone.classList.remove("border-brand-500", "bg-brand-50/20");
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            handleFileSelection(e.dataTransfer.files[0]);
        }
    });
    fileInput.addEventListener("change", (e) => {
        if (e.target.files && e.target.files[0]) {
            handleFileSelection(e.target.files[0]);
        }
    });

    function handleFileSelection(file) {
        selectedFile = file;
        fileNameDisplay.textContent = `Selected: ${file.name} (${(file.size / (1024*1024)).toFixed(1)} MB)`;
        fileNameDisplay.classList.remove("hidden");
        const nameInput = document.getElementById("project-name-input");
        if (!nameInput.value) {
            nameInput.value = file.name.replace(/\.[^/.]+$/, "");
        }
    }

    // Style Picker Highlighting
    container.querySelectorAll(".style-radio").forEach(radio => {
        radio.addEventListener("change", () => {
            container.querySelectorAll("#style-presets-picker label").forEach(l => {
                l.classList.remove("border-2", "border-brand-600", "bg-brand-50/50", "dark:bg-brand-950/40");
                l.classList.add("border-slate-200", "dark:border-slate-800");
            });
            const parent = radio.closest("label");
            parent.classList.add("border-2", "border-brand-600", "bg-brand-50/50", "dark:bg-brand-950/40");
            parent.classList.remove("border-slate-200", "dark:border-slate-800");
        });
    });

    // Submit Project
    const submitBtn = document.getElementById("btn-submit-project");
    submitBtn.addEventListener("click", async () => {
        const projectName = document.getElementById("project-name-input").value;
        const durationPref = document.getElementById("duration-pref-input").value;
        const clipCount = parseInt(document.getElementById("clip-count-input").value);
        const language = document.getElementById("language-input").value;
        const defaultStyle = document.querySelector("input[name='subtitle-style']:checked")?.value || "bold_viral";

        submitBtn.disabled = true;
        submitBtn.innerHTML = `<div class="animate-spin rounded-full h-5 w-5 border-2 border-white border-t-transparent mr-2"></div> Starting Pipeline...`;

        try {
            if (activeTab === "upload") {
                if (!selectedFile) {
                    alert("Please select or drop a video file first.");
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = `<i data-lucide="sparkles" class="w-5 h-5 mr-2"></i> Start AI Analysis & Repurposing`;
                    if (window.lucide) window.lucide.createIcons();
                    return;
                }

                const progressContainer = document.getElementById("upload-progress-container");
                const progressBar = document.getElementById("upload-progress-bar");
                const progressText = document.getElementById("upload-progress-percent");
                progressContainer.classList.remove("hidden");

                const formData = new FormData();
                formData.append("file", selectedFile);
                if (projectName) formData.append("project_name", projectName);
                formData.append("target_clip_count", clipCount);
                formData.append("duration_preference", durationPref);
                formData.append("language", language);
                formData.append("default_style", defaultStyle);

                const project = await api.uploadVideo(formData, (percent) => {
                    progressBar.style.width = `${percent}%`;
                    progressText.textContent = `${percent}%`;
                });

                navigate(`#/projects/${project.id}/analysis`);
            } else {
                const youtubeUrl = document.getElementById("youtube-url-input").value.trim();
                if (!youtubeUrl) {
                    alert("Please enter a valid YouTube URL.");
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = `<i data-lucide="sparkles" class="w-5 h-5 mr-2"></i> Start AI Analysis & Repurposing`;
                    if (window.lucide) window.lucide.createIcons();
                    return;
                }

                const project = await api.importYouTube({
                    youtube_url: youtubeUrl,
                    project_name: projectName || "YouTube Video",
                    target_clip_count: clipCount,
                    duration_preference: durationPref,
                    language: language,
                    default_style: defaultStyle
                });

                navigate(`#/projects/${project.id}/analysis`);
            }
        } catch (err) {
            alert(err.message);
            submitBtn.disabled = false;
            submitBtn.innerHTML = `<i data-lucide="sparkles" class="w-5 h-5 mr-2"></i> Start AI Analysis & Repurposing`;
            if (window.lucide) window.lucide.createIcons();
        }
    });
}

/* =========================================================================
   PAGE 4: AI ANALYSIS RESULTS
========================================================================= */
async function renderAnalysisPage(container, projectId) {
    container.innerHTML = `
        <div class="flex items-center justify-center min-h-[40vh]">
            <div class="animate-spin rounded-full h-8 w-8 border-4 border-brand-500 border-t-transparent"></div>
        </div>
    `;

    const project = await api.getProject(projectId);
    state.currentProject = project;

    const isProcessing = project.processing_status !== "completed" && project.processing_status !== "failed";

    if (isProcessing) {
        container.innerHTML = `
            <div class="max-w-2xl mx-auto py-12 text-center space-y-6">
                <div class="relative w-24 h-24 mx-auto">
                    <div class="absolute inset-0 rounded-full border-4 border-brand-200 dark:border-brand-900"></div>
                    <div class="absolute inset-0 rounded-full border-4 border-brand-600 border-t-transparent animate-spin"></div>
                    <div class="absolute inset-0 flex items-center justify-center text-brand-600 dark:text-brand-400 font-bold text-lg">
                        ${project.progress}%
                    </div>
                </div>
                <div class="space-y-2">
                    <h2 class="text-2xl font-bold text-slate-900 dark:text-white capitalize">
                        ${project.processing_status.replace("_", " ")}
                    </h2>
                    <p class="text-sm text-slate-500">
                        AI is transcribing speech, detecting high-retention hooks, and rendering 9:16 vertical clips.
                    </p>
                </div>
                <div class="w-full bg-slate-100 dark:bg-slate-800 h-2.5 rounded-full overflow-hidden max-w-md mx-auto">
                    <div class="bg-brand-600 h-full rounded-full transition-all duration-500" style="width: ${project.progress}%"></div>
                </div>
            </div>
        `;

        // Start polling status
        state.pollingInterval = setInterval(async () => {
            const updated = await api.getProject(projectId);
            if (updated.processing_status === "completed" || updated.processing_status === "failed") {
                clearInterval(state.pollingInterval);
                state.pollingInterval = null;
                renderAnalysisPage(container, projectId);
            } else {
                renderAnalysisPage(container, projectId);
            }
        }, 2500);
        return;
    }

    if (project.processing_status === "failed") {
        container.innerHTML = `
            <div class="max-w-md mx-auto py-12 text-center space-y-4">
                <div class="w-16 h-16 mx-auto rounded-full bg-red-100 dark:bg-red-950 text-red-600 flex items-center justify-center">
                    <i data-lucide="alert-circle" class="w-8 h-8"></i>
                </div>
                <h3 class="text-xl font-bold text-slate-900 dark:text-white">Analysis Failed</h3>
                <p class="text-sm text-slate-500">${project.error_message || "An unexpected error occurred during processing."}</p>
                <a href="#/dashboard" class="inline-block px-5 py-2.5 rounded-xl bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900 font-medium text-sm">Return to Dashboard</a>
            </div>
        `;
        return;
    }

    // Render Full Analysis Results
    const clips = project.clips || [];

    container.innerHTML = `
        <div class="space-y-8">
            <!-- Header Bar -->
            <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-slate-200 dark:border-slate-800">
                <div class="space-y-1">
                    <div class="flex items-center gap-2">
                        <span class="px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
                            Analysis Complete
                        </span>
                        <span class="text-xs text-slate-400 font-mono">${project.video_duration ? (project.video_duration/60).toFixed(1) : 0} mins</span>
                    </div>
                    <h1 class="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">${project.project_name}</h1>
                </div>

                <div class="flex items-center space-x-3">
                    <a href="#/projects/${projectId}/export" class="px-5 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-700 text-white font-semibold text-sm shadow-sm shadow-brand-600/30 flex items-center gap-2">
                        <i data-lucide="download" class="w-4 h-4"></i>
                        <span>Export Center</span>
                    </a>
                </div>
            </div>

            <!-- Video Timeline Heatmap Visualizer -->
            <div class="bg-white dark:bg-slate-900 p-6 rounded-3xl border border-slate-200 dark:border-slate-800 space-y-4 shadow-sm">
                <div class="flex items-center justify-between text-xs font-semibold text-slate-500">
                    <span class="flex items-center gap-1.5"><i data-lucide="bar-chart-3" class="w-4 h-4"></i> Video Virality Map</span>
                    <span>${clips.length} Viral Moments Identified</span>
                </div>

                <!-- Timeline Bar -->
                <div class="relative w-full h-8 bg-slate-100 dark:bg-slate-800 rounded-xl overflow-hidden flex items-center">
                    ${clips.map((c, i) => {
                        const total = project.video_duration || 100;
                        const leftPct = ((c.start_time / total) * 100).toFixed(1);
                        const widthPct = (((c.end_time - c.start_time) / total) * 100).toFixed(1);
                        return `
                            <div class="absolute h-full rounded cursor-pointer group flex items-center justify-center ${c.potential_score >= 80 ? 'bg-emerald-500/80 hover:bg-emerald-500' : 'bg-amber-500/80 hover:bg-amber-500'}"
                                 style="left: ${leftPct}%; width: ${Math.max(2, widthPct)}%;"
                                 title="Clip ${i+1}: ${c.potential_score}% Potential (${c.start_time}s - ${c.end_time}s)">
                            </div>
                        `;
                    }).join("")}
                </div>
                <div class="flex justify-between text-[11px] text-slate-400 font-mono">
                    <span>0:00</span>
                    <span>${project.video_duration ? Math.floor(project.video_duration / 60) + ":" + String(Math.floor(project.video_duration % 60)).padStart(2, '0') : "0:00"}</span>
                </div>
            </div>

            <!-- Clips Grid -->
            <div class="space-y-4">
                <h3 class="font-bold text-lg text-slate-900 dark:text-white">Detected Viral Moments (${clips.length})</h3>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                    ${clips.map((clip, idx) => renderClipAnalysisCard(clip, idx, projectId)).join("")}
                </div>
            </div>
        </div>
    `;

    // Hook up open in editor buttons
    container.querySelectorAll(".btn-open-editor").forEach(btn => {
        btn.addEventListener("click", () => {
            const clipId = btn.getAttribute("data-clip-id");
            navigate(`#/projects/${projectId}/editor/${clipId}`);
        });
    });
}

function renderClipAnalysisCard(clip, idx, projectId) {
    const isHigh = clip.potential_category === "High";
    const isMed = clip.potential_category === "Medium";
    const badgeClass = isHigh ? "score-badge-high" : isMed ? "score-badge-medium" : "score-badge-low";

    const breakdown = clip.scoring_breakdown || {};

    return `
        <div class="rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-6 shadow-sm space-y-5 hover:border-brand-500 transition-colors">
            <!-- Top Card Row -->
            <div class="flex items-start justify-between gap-4">
                <div class="space-y-1">
                    <span class="text-xs font-semibold text-slate-400">Clip #${idx + 1}</span>
                    <h4 class="font-bold text-base text-slate-900 dark:text-white line-clamp-1">${clip.title}</h4>
                    <p class="text-xs text-slate-500 font-mono">
                        ${Math.floor(clip.start_time)}s – ${Math.floor(clip.end_time)}s (${clip.duration.toFixed(1)}s duration)
                    </p>
                </div>
                <!-- Viral Potential Score Badge -->
                <div class="text-center">
                    <div class="${badgeClass} px-3 py-1.5 rounded-2xl flex items-center gap-1.5 shadow-md">
                        <i data-lucide="flame" class="w-4 h-4"></i>
                        <span class="text-base font-black">${clip.potential_score}</span>
                    </div>
                    <span class="block text-[10px] font-bold uppercase tracking-wider text-slate-400 mt-1">${clip.potential_category} Potential</span>
                </div>
            </div>

            <!-- Opening Hook Quote -->
            ${clip.suggested_hook ? `
                <div class="p-3.5 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800 text-xs">
                    <span class="font-bold text-slate-700 dark:text-slate-300 block mb-1">Opening Hook:</span>
                    <p class="text-slate-600 dark:text-slate-400 italic">"${clip.suggested_hook}"</p>
                </div>
            ` : ""}

            <!-- 8-Factor Score Breakdown Accordion -->
            <div class="space-y-2 pt-2 border-t border-slate-100 dark:border-slate-800 text-xs">
                <span class="font-semibold text-slate-500 uppercase tracking-wider text-[10px]">8-Factor Virality Evaluation</span>
                <div class="grid grid-cols-2 gap-x-4 gap-y-2">
                    <div>
                        <div class="flex justify-between text-[11px] text-slate-600 dark:text-slate-400 mb-0.5">
                            <span>Hook (20%)</span>
                            <span class="font-semibold">${breakdown.hook_strength || 75}%</span>
                        </div>
                        <div class="h-1.5 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                            <div class="bg-indigo-500 h-full rounded-full" style="width: ${breakdown.hook_strength || 75}%"></div>
                        </div>
                    </div>
                    <div>
                        <div class="flex justify-between text-[11px] text-slate-600 dark:text-slate-400 mb-0.5">
                            <span>Emotion (15%)</span>
                            <span class="font-semibold">${breakdown.emotional_impact || 70}%</span>
                        </div>
                        <div class="h-1.5 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                            <div class="bg-violet-500 h-full rounded-full" style="width: ${breakdown.emotional_impact || 70}%"></div>
                        </div>
                    </div>
                    <div>
                        <div class="flex justify-between text-[11px] text-slate-600 dark:text-slate-400 mb-0.5">
                            <span>Novelty (15%)</span>
                            <span class="font-semibold">${breakdown.information_value || 70}%</span>
                        </div>
                        <div class="h-1.5 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                            <div class="bg-emerald-500 h-full rounded-full" style="width: ${breakdown.information_value || 70}%"></div>
                        </div>
                    </div>
                    <div>
                        <div class="flex justify-between text-[11px] text-slate-600 dark:text-slate-400 mb-0.5">
                            <span>Context (15%)</span>
                            <span class="font-semibold">${breakdown.context_completeness || 80}%</span>
                        </div>
                        <div class="h-1.5 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                            <div class="bg-teal-500 h-full rounded-full" style="width: ${breakdown.context_completeness || 80}%"></div>
                        </div>
                    </div>
                    <div>
                        <div class="flex justify-between text-[11px] text-slate-600 dark:text-slate-400 mb-0.5">
                            <span>Shareability (10%)</span>
                            <span class="font-semibold">${breakdown.shareability || 75}%</span>
                        </div>
                        <div class="h-1.5 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                            <div class="bg-rose-500 h-full rounded-full" style="width: ${breakdown.shareability || 75}%"></div>
                        </div>
                    </div>
                    <div>
                        <div class="flex justify-between text-[11px] text-slate-600 dark:text-slate-400 mb-0.5">
                            <span>Pacing (10%)</span>
                            <span class="font-semibold">${breakdown.content_pacing || 80}%</span>
                        </div>
                        <div class="h-1.5 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                            <div class="bg-amber-500 h-full rounded-full" style="width: ${breakdown.content_pacing || 80}%"></div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- AI Reason -->
            <p class="text-xs text-slate-500 leading-relaxed">
                <strong>Why Selected:</strong> ${clip.selection_reason}
            </p>

            <!-- Card Actions -->
            <div class="pt-3 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between">
                <button class="btn-open-editor px-4 py-2 rounded-xl text-xs font-semibold bg-brand-50 dark:bg-brand-950/60 text-brand-600 dark:text-brand-300 hover:bg-brand-100 transition-colors flex items-center gap-1.5" data-clip-id="${clip.id}">
                    <i data-lucide="sliders" class="w-3.5 h-3.5"></i>
                    <span>Open in Video Editor</span>
                </button>
                <a href="/api/clips/${clip.id}/download" target="_blank" class="text-xs font-medium text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white flex items-center gap-1">
                    <i data-lucide="download" class="w-3.5 h-3.5"></i> Download MP4
                </a>
            </div>
        </div>
    `;
}

/* =========================================================================
   PAGE 5: VIDEO EDITOR
========================================================================= */
async function renderEditorPage(container, projectId, clipId) {
    container.innerHTML = `
        <div class="flex items-center justify-center min-h-[40vh]">
            <div class="animate-spin rounded-full h-8 w-8 border-4 border-brand-500 border-t-transparent"></div>
        </div>
    `;

    const clip = await api.getClip(clipId);
    state.currentClip = clip;

    const videoSrc = clip.clip_status === "ready"
        ? `/api/clips/${clip.id}/media`
        : "";

    container.innerHTML = `
        <div class="space-y-6">
            <!-- Header Bar -->
            <div class="flex items-center justify-between pb-4 border-b border-slate-200 dark:border-slate-800">
                <div class="flex items-center space-x-3">
                    <a href="#/projects/${projectId}/analysis" class="p-2 rounded-xl text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800">
                        <i data-lucide="arrow-left" class="w-5 h-5"></i>
                    </a>
                    <div>
                        <h1 class="text-xl font-bold text-slate-900 dark:text-white">Video Editor: ${clip.title}</h1>
                        <p class="text-xs text-slate-500">Trim start/end, adjust crop positioning, change subtitle presets & BGM.</p>
                    </div>
                </div>
                <div class="flex items-center space-x-3">
                    <button id="btn-re-render" class="px-5 py-2.5 rounded-xl font-bold bg-brand-600 hover:bg-brand-700 text-white shadow-sm flex items-center space-x-2 text-xs">
                        <i data-lucide="sparkles" class="w-4 h-4"></i>
                        <span>Re-Render 9:16 Video</span>
                    </button>
                </div>
            </div>

            <!-- Two-Column Studio Layout -->
            <div class="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
                <!-- Left: 9:16 Video Player Preview Phone Mockup -->
                <div class="lg:col-span-5 flex flex-col items-center">
                    <div class="phone-mockup-frame w-full max-w-[320px] shadow-2xl relative">
                        <div class="phone-mockup-notch"></div>
                        <video id="editor-video-player" src="${videoSrc}" controls class="w-full h-full object-cover rounded-[24px]" playsinline></video>
                    </div>
                    <div class="mt-3 text-center text-xs text-slate-400">
                        Rendered in 1080 × 1920 (9:16 Vertical Format)
                    </div>
                </div>

                <!-- Right: Editing Controls Pane -->
                <div class="lg:col-span-7 space-y-6 bg-white dark:bg-slate-900 p-6 rounded-3xl border border-slate-200 dark:border-slate-800 shadow-sm">
                    <!-- Control 1: Trimming Controls -->
                    <div class="space-y-3 pb-5 border-b border-slate-100 dark:border-slate-800">
                        <div class="flex items-center justify-between">
                            <span class="font-bold text-sm text-slate-900 dark:text-white flex items-center gap-1.5">
                                <i data-lucide="scissors" class="w-4 h-4 text-brand-600"></i> Clip Trim Range
                            </span>
                            <span id="trim-duration-badge" class="px-2 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800 text-xs font-mono">
                                Duration: ${clip.duration.toFixed(1)}s
                            </span>
                        </div>
                        <div class="grid grid-cols-2 gap-4">
                            <div>
                                <label class="text-[11px] font-semibold text-slate-500 uppercase">Start Time (sec)</label>
                                <input type="number" step="0.5" id="input-start-time" value="${clip.start_time}" class="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-sm mt-1">
                            </div>
                            <div>
                                <label class="text-[11px] font-semibold text-slate-500 uppercase">End Time (sec)</label>
                                <input type="number" step="0.5" id="input-end-time" value="${clip.end_time}" class="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-sm mt-1">
                            </div>
                        </div>
                    </div>

                    <!-- Control 2: Smart Cropping & Framing Mode -->
                    <div class="space-y-3 pb-5 border-b border-slate-100 dark:border-slate-800">
                        <span class="font-bold text-sm text-slate-900 dark:text-white flex items-center gap-1.5">
                            <i data-lucide="crop" class="w-4 h-4 text-emerald-600"></i> Framing & Cropping Mode
                        </span>
                        <div class="grid grid-cols-2 sm:grid-cols-5 gap-2" id="crop-mode-buttons">
                            <button class="crop-btn p-2 rounded-xl border text-xs font-semibold ${clip.crop_mode === 'auto_face' ? 'border-brand-600 bg-brand-50 text-brand-600' : 'border-slate-200 text-slate-600'}" data-mode="auto_face">
                                Auto Face
                            </button>
                            <button class="crop-btn p-2 rounded-xl border text-xs font-semibold ${clip.crop_mode === 'center' ? 'border-brand-600 bg-brand-50 text-brand-600' : 'border-slate-200 text-slate-600'}" data-mode="center">
                                Center
                            </button>
                            <button class="crop-btn p-2 rounded-xl border text-xs font-semibold ${clip.crop_mode === 'left' ? 'border-brand-600 bg-brand-50 text-brand-600' : 'border-slate-200 text-slate-600'}" data-mode="left">
                                Left Focus
                            </button>
                            <button class="crop-btn p-2 rounded-xl border text-xs font-semibold ${clip.crop_mode === 'right' ? 'border-brand-600 bg-brand-50 text-brand-600' : 'border-slate-200 text-slate-600'}" data-mode="right">
                                Right Focus
                            </button>
                            <button class="crop-btn p-2 rounded-xl border text-xs font-semibold ${clip.crop_mode === 'split_screen' ? 'border-brand-600 bg-brand-50 text-brand-600' : 'border-slate-200 text-slate-600'}" data-mode="split_screen">
                                Split Screen
                            </button>
                        </div>
                    </div>

                    <!-- Control 3: Subtitle Presets -->
                    <div class="space-y-3 pb-5 border-b border-slate-100 dark:border-slate-800">
                        <div class="flex items-center justify-between">
                            <span class="font-bold text-sm text-slate-900 dark:text-white flex items-center gap-1.5">
                                <i data-lucide="subtitles" class="w-4 h-4 text-amber-600"></i> Subtitle Style Preset
                            </span>
                            <label class="flex items-center space-x-2 text-xs cursor-pointer">
                                <input type="checkbox" id="check-enable-subtitles" ${clip.enable_subtitles ? 'checked' : ''} class="rounded text-brand-600">
                                <span>Enable Captions</span>
                            </label>
                        </div>
                        <div class="grid grid-cols-2 sm:grid-cols-5 gap-2" id="sub-style-buttons">
                            <button class="sub-btn p-2 rounded-xl border text-xs font-semibold ${clip.subtitle_style === 'bold_viral' ? 'border-brand-600 bg-brand-50 text-brand-600' : 'border-slate-200 text-slate-600'}" data-style="bold_viral">
                                Bold Viral
                            </button>
                            <button class="sub-btn p-2 rounded-xl border text-xs font-semibold ${clip.subtitle_style === 'clean_minimal' ? 'border-brand-600 bg-brand-50 text-brand-600' : 'border-slate-200 text-slate-600'}" data-style="clean_minimal">
                                Clean
                            </button>
                            <button class="sub-btn p-2 rounded-xl border text-xs font-semibold ${clip.subtitle_style === 'podcast' ? 'border-brand-600 bg-brand-50 text-brand-600' : 'border-slate-200 text-slate-600'}" data-style="podcast">
                                Podcast
                            </button>
                            <button class="sub-btn p-2 rounded-xl border text-xs font-semibold ${clip.subtitle_style === 'cinematic' ? 'border-brand-600 bg-brand-50 text-brand-600' : 'border-slate-200 text-slate-600'}" data-style="cinematic">
                                Cinematic
                            </button>
                            <button class="sub-btn p-2 rounded-xl border text-xs font-semibold ${clip.subtitle_style === 'highlight_keyword' ? 'border-brand-600 bg-brand-50 text-brand-600' : 'border-slate-200 text-slate-600'}" data-style="highlight_keyword">
                                Highlight
                            </button>
                        </div>
                    </div>

                    <!-- Control 4: Audio & Background Music -->
                    <div class="space-y-3">
                        <span class="font-bold text-sm text-slate-900 dark:text-white flex items-center gap-1.5">
                            <i data-lucide="music" class="w-4 h-4 text-violet-600"></i> Audio Enhancements & BGM
                        </span>
                        <div class="space-y-3">
                            <label class="flex items-center space-x-2 text-xs cursor-pointer">
                                <input type="checkbox" id="check-normalize-audio" ${clip.normalize_audio ? 'checked' : ''} class="rounded text-brand-600">
                                <span>Broadcast Audio Normalization (EBU R128)</span>
                            </label>
                            <label class="flex items-center space-x-2 text-xs cursor-pointer">
                                <input type="checkbox" id="check-enable-bgm" ${clip.enable_music ? 'checked' : ''} class="rounded text-brand-600">
                                <span>Add Royalty-Free Background Music</span>
                            </label>
                            <div id="bgm-options-container" class="${clip.enable_music ? '' : 'hidden'} space-y-2 pl-5 pt-1">
                                <select id="select-bgm-track" class="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-xs">
                                    <option value="lofi_chill">Lo-Fi Midnight Chill (Relaxed)</option>
                                    <option value="upbeat_energy">Dynamic Tech Pulse (High Energy)</option>
                                    <option value="cinematic_ambient">Cinematic Storyteller (Emotional)</option>
                                </select>
                                <div class="flex items-center gap-3">
                                    <span class="text-[11px] text-slate-400">BGM Volume:</span>
                                    <input type="range" id="range-bgm-vol" min="0.05" max="0.4" step="0.02" value="${clip.bgm_volume}" class="flex-1">
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;

    // State bindings
    let currentCropMode = clip.crop_mode;
    let currentSubStyle = clip.subtitle_style;

    // Crop mode buttons
    container.querySelectorAll(".crop-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            currentCropMode = btn.getAttribute("data-mode");
            container.querySelectorAll(".crop-btn").forEach(b => {
                b.classList.remove("border-brand-600", "bg-brand-50", "text-brand-600");
                b.classList.add("border-slate-200", "text-slate-600");
            });
            btn.classList.add("border-brand-600", "bg-brand-50", "text-brand-600");
            btn.classList.remove("border-slate-200", "text-slate-600");
        });
    });

    // Subtitle style buttons
    container.querySelectorAll(".sub-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            currentSubStyle = btn.getAttribute("data-style");
            container.querySelectorAll(".sub-btn").forEach(b => {
                b.classList.remove("border-brand-600", "bg-brand-50", "text-brand-600");
                b.classList.add("border-slate-200", "text-slate-600");
            });
            btn.classList.add("border-brand-600", "bg-brand-50", "text-brand-600");
            btn.classList.remove("border-slate-200", "text-slate-600");
        });
    });

    // BGM Checkbox toggle
    const checkBgm = document.getElementById("check-enable-bgm");
    const bgmOptions = document.getElementById("bgm-options-container");
    checkBgm.addEventListener("change", () => {
        if (checkBgm.checked) {
            bgmOptions.classList.remove("hidden");
        } else {
            bgmOptions.classList.add("hidden");
        }
    });

    // Re-Render Trigger
    const reRenderBtn = document.getElementById("btn-re-render");
    reRenderBtn.addEventListener("click", async () => {
        const startTime = parseFloat(document.getElementById("input-start-time").value);
        const endTime = parseFloat(document.getElementById("input-end-time").value);
        const enableSubs = document.getElementById("check-enable-subtitles").checked;
        const normalize = document.getElementById("check-normalize-audio").checked;
        const enableMusic = document.getElementById("check-enable-bgm").checked;
        const bgmTrack = document.getElementById("select-bgm-track").value;
        const bgmVol = parseFloat(document.getElementById("range-bgm-vol").value);

        reRenderBtn.disabled = true;
        reRenderBtn.innerHTML = `<div class="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent mr-2"></div> Rendering...`;

        try {
            // 1. Save settings
            await api.updateClip(clipId, {
                start_time: startTime,
                end_time: endTime,
                crop_mode: currentCropMode,
                subtitle_style: currentSubStyle,
                enable_subtitles: enableSubs,
                normalize_audio: normalize,
                enable_music: enableMusic,
                bgm_track: bgmTrack,
                bgm_volume: bgmVol
            });

            // 2. Trigger FFmpeg re-render
            const updated = await api.reRenderClip(clipId);
            
            // Reload player source with cache-buster
            const player = document.getElementById("editor-video-player");
            const newSrc = `/api/clips/${updated.id}/media?t=${Date.now()}`;
            player.src = newSrc;
            player.load();
            player.play().catch(() => {});

            alert("Clip re-rendered successfully!");
        } catch (err) {
            alert(`Rendering failed: ${err.message}`);
        } finally {
            reRenderBtn.disabled = false;
            reRenderBtn.innerHTML = `<i data-lucide="sparkles" class="w-4 h-4 mr-2"></i> Re-Render 9:16 Video`;
            if (window.lucide) window.lucide.createIcons();
        }
    });
}

/* =========================================================================
   PAGE 6: EXPORT CENTER
========================================================================= */
async function renderExportPage(container, projectId) {
    container.innerHTML = `
        <div class="flex items-center justify-center min-h-[40vh]">
            <div class="animate-spin rounded-full h-8 w-8 border-4 border-brand-500 border-t-transparent"></div>
        </div>
    `;

    const project = await api.getProject(projectId);
    const clips = project.clips || [];

    container.innerHTML = `
        <div class="space-y-8">
            <!-- Header Bar -->
            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-slate-200 dark:border-slate-800">
                <div class="space-y-1">
                    <div class="flex items-center gap-2">
                        <a href="#/projects/${projectId}/analysis" class="text-xs text-brand-600 hover:underline">← Back to Analysis</a>
                    </div>
                    <h1 class="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">Export Center</h1>
                    <p class="text-xs text-slate-500">Download individual clips or package all video assets and captions in a ZIP bundle.</p>
                </div>

                <div class="flex items-center space-x-3">
                    <button id="btn-batch-export-zip" class="px-6 py-3 rounded-xl font-bold bg-brand-600 hover:bg-brand-700 text-white shadow-lg shadow-brand-600/30 flex items-center space-x-2 text-sm">
                        <i data-lucide="archive" class="w-4 h-4"></i>
                        <span>Download All as ZIP</span>
                    </button>
                </div>
            </div>

            <!-- ZIP Export Progress Modal / Banner -->
            <div id="zip-progress-banner" class="hidden p-5 rounded-2xl bg-brand-50 dark:bg-brand-950/40 border border-brand-200 dark:border-brand-800 space-y-2">
                <div class="flex justify-between text-xs font-semibold text-brand-900 dark:text-brand-200">
                    <span>Packaging clips, SRT subtitles, and metadata into ZIP...</span>
                    <span id="zip-progress-pct">0%</span>
                </div>
                <div class="w-full bg-brand-200 dark:bg-brand-900 h-2 rounded-full overflow-hidden">
                    <div id="zip-progress-bar" class="bg-brand-600 h-full rounded-full transition-all duration-300" style="width: 0%"></div>
                </div>
            </div>

            <!-- Export Clips List -->
            <div class="space-y-6">
                ${clips.map((clip, idx) => renderExportClipItem(clip, idx)).join("")}
            </div>
        </div>
    `;

    // Copy helper buttons
    container.querySelectorAll(".btn-copy").forEach(btn => {
        btn.addEventListener("click", () => {
            const text = btn.getAttribute("data-text");
            navigator.clipboard.writeText(text);
            const originalHtml = btn.innerHTML;
            btn.innerHTML = `<i data-lucide="check" class="w-3.5 h-3.5 mr-1 text-emerald-500"></i> Copied!`;
            if (window.lucide) window.lucide.createIcons();
            setTimeout(() => {
                btn.innerHTML = originalHtml;
                if (window.lucide) window.lucide.createIcons();
            }, 1800);
        });
    });

    // Batch ZIP export
    const zipBtn = document.getElementById("btn-batch-export-zip");
    zipBtn.addEventListener("click", async () => {
        zipBtn.disabled = true;
        const banner = document.getElementById("zip-progress-banner");
        const bar = document.getElementById("zip-progress-bar");
        const pct = document.getElementById("zip-progress-pct");
        banner.classList.remove("hidden");

        try {
            const job = await api.createExportJob(projectId, {
                resolution: "1080x1920",
                quality: "high"
            });

            // Poll job
            const poll = setInterval(async () => {
                const status = await api.getExportJobStatus(job.id);
                bar.style.width = `${status.progress}%`;
                pct.textContent = `${status.progress}%`;

                if (status.export_status === "completed") {
                    clearInterval(poll);
                    zipBtn.disabled = false;
                    window.location.href = `/api/export/${job.id}/download`;
                } else if (status.export_status === "failed") {
                    clearInterval(poll);
                    zipBtn.disabled = false;
                    alert("ZIP creation failed: " + status.error_message);
                }
            }, 1000);
        } catch (err) {
            alert(err.message);
            zipBtn.disabled = false;
        }
    });
}

function renderExportClipItem(clip, idx) {
    const meta = clip.metadata_info || {};
    const videoSrc = clip.clip_status === "ready"
        ? `/api/clips/${clip.id}/media`
        : "";

    return `
        <div class="rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-6 shadow-sm space-y-6">
            <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
                <!-- 9:16 Video Preview -->
                <div class="lg:col-span-4 flex justify-center">
                    <div class="phone-mockup-frame w-full max-w-[240px] shadow-lg">
                        <div class="phone-mockup-notch"></div>
                        <video src="${videoSrc}" controls class="w-full h-full object-cover rounded-[20px]"></video>
                    </div>
                </div>

                <!-- Metadata & Downloads -->
                <div class="lg:col-span-8 space-y-5">
                    <div class="flex items-start justify-between">
                        <div>
                            <span class="text-xs font-semibold text-slate-400">Clip #${idx + 1}</span>
                            <h3 class="font-bold text-lg text-slate-900 dark:text-white">${clip.title}</h3>
                            <p class="text-xs text-slate-500 font-mono">1080 × 1920 • ${clip.duration.toFixed(1)}s</p>
                        </div>
                        <div class="flex items-center space-x-2">
                            <a href="/api/clips/${clip.id}/download" target="_blank" class="px-4 py-2 rounded-xl text-xs font-semibold bg-brand-600 text-white hover:bg-brand-700 flex items-center gap-1.5 shadow-sm">
                                <i data-lucide="download" class="w-3.5 h-3.5"></i> Download MP4
                            </a>
                            <a href="/api/clips/${clip.id}/subtitles" target="_blank" class="px-3 py-2 rounded-xl text-xs font-semibold bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 flex items-center gap-1.5">
                                <i data-lucide="file-text" class="w-3.5 h-3.5"></i> Subtitles (.SRT)
                            </a>
                        </div>
                    </div>

                    <!-- Suggested Titles -->
                    ${meta.suggested_titles && meta.suggested_titles.length ? `
                        <div class="space-y-2">
                            <span class="text-xs font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider block">Suggested Viral Titles</span>
                            <div class="space-y-1.5">
                                ${meta.suggested_titles.map(t => `
                                    <div class="flex items-center justify-between p-2.5 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800 text-xs">
                                        <span class="font-medium text-slate-800 dark:text-slate-200">${t}</span>
                                        <button class="btn-copy text-brand-600 hover:underline flex items-center gap-1" data-text="${t}">
                                            <i data-lucide="copy" class="w-3 h-3"></i> Copy
                                        </button>
                                    </div>
                                `).join("")}
                            </div>
                        </div>
                    ` : ""}

                    <!-- Captions & Hashtags -->
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                        <div class="p-3.5 rounded-2xl bg-slate-50 dark:bg-slate-800/50 border border-slate-100 dark:border-slate-800 space-y-2">
                            <div class="flex justify-between items-center font-bold text-slate-700 dark:text-slate-300">
                                <span>Instagram & TikTok Caption</span>
                                <button class="btn-copy text-brand-600 hover:underline flex items-center gap-1" data-text="${meta.instagram_caption || ''}">
                                    <i data-lucide="copy" class="w-3 h-3"></i> Copy
                                </button>
                            </div>
                            <p class="text-slate-600 dark:text-slate-400 whitespace-pre-line text-[11px] line-clamp-4">
                                ${meta.instagram_caption || "Watch till the end! 🔥"}
                            </p>
                        </div>

                        <div class="p-3.5 rounded-2xl bg-slate-50 dark:bg-slate-800/50 border border-slate-100 dark:border-slate-800 space-y-2">
                            <div class="flex justify-between items-center font-bold text-slate-700 dark:text-slate-300">
                                <span>Trending Hashtags</span>
                                <button class="btn-copy text-brand-600 hover:underline flex items-center gap-1" data-text="${meta.hashtags ? meta.hashtags.join(' ') : ''}">
                                    <i data-lucide="copy" class="w-3 h-3"></i> Copy
                                </button>
                            </div>
                            <p class="text-slate-600 dark:text-slate-400 font-mono text-[11px]">
                                ${meta.hashtags ? meta.hashtags.join(' ') : "#shorts #viral #reels"}
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
}

// App Initialization
document.addEventListener("DOMContentLoaded", () => {
    initTheme();
    renderRoute();
});
