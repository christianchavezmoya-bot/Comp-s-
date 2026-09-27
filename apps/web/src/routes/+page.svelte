<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import type { Song, SongAnalysis, Section, StemKind, Gem } from '@compas/shared-types';
	import GemGrid from '$lib/GemGrid.svelte';
	import VerticalPlay from '$lib/VerticalPlay.svelte';
	import LyricsPanel from '$lib/LyricsPanel.svelte';
	import { AudioEngine } from '$lib/audio-engine';
	import {
		listSongs,
		uploadSong,
		deleteSong,
		triggerAnalysis,
		getAnalysis,
		stemUrl
	} from '$lib/api';

	type View = 'grid' | 'play' | 'lyrics';

	// ====== State ======
	let songs = $state<Song[]>([]);
	let selectedSong = $state<Song | null>(null);
	let analysis = $state<SongAnalysis | null>(null);
	let analysisLoading = $state(false);
	let analysisError = $state<string | null>(null);
	let uploadBusy = $state(false);
	let uploadError = $state<string | null>(null);

	// UI
	let view = $state<View>('play');
	let sidebarOpen = $state(true);
	let downloadBusy = $state<Record<string, boolean>>({});
	let presets = $state<Array<{ name: string; volumes: Record<string, number>; mutes: Record<string, boolean>; solos: Record<string, boolean> }>>([]);
	let showPresets = $state(false);

	// Audio engine
	const engine = new AudioEngine();
	let engineLoaded = $state(false);
	let engineLoading = $state(false);
	let engineError = $state<string | null>(null);
	let playhead = $state(0);
	let playing = $state(false);
	let duration = $state(0);

	// Loop + speed
	let loopA = $state<number | null>(null);
	let loopB = $state<number | null>(null);
	let playbackRate = $state(1.0);

	// Stem state
	type StemState = { volume: number; muted: boolean; solo: boolean };
	let stemState = $state<Record<string, StemState>>({});

	// ====== STEMS catalog ======
	const STEMS_DISPLAY: { key: StemKind; label: string; color: string }[] = [
		{ key: 'vocals_lead', label: 'Vocals',  color: '#ec4899' },
		{ key: 'vocals_back', label: 'Backing', color: '#f472b6' },
		{ key: 'requinto',   label: 'Requinto',color: '#2dd4bf' },
		{ key: 'segunda',    label: 'Segunda', color: '#38bdf8' },
		{ key: 'bass',       label: 'Bass',    color: '#fb923c' },
		{ key: 'bongo',      label: 'Bongó',   color: '#a3e635' },
		{ key: 'guira',      label: 'Güira',   color: '#facc15' },
		{ key: 'tambora',    label: 'Tambora', color: '#84cc16' },
		{ key: 'clave',      label: 'Clave',   color: '#a78bfa' },
		{ key: 'palmas',     label: 'Palmas',  color: '#94a3b8' },
		{ key: 'synth',      label: 'Synth',   color: '#818cf8' },
		{ key: 'horns',      label: 'Horns',   color: '#f87171' },
		{ key: 'piano',      label: 'Piano',   color: '#60a5fa' },
		{ key: 'congas',     label: 'Congas',  color: '#fbbf24' },
		{ key: 'timbales',   label: 'Timbales',color: '#fde047' },
		{ key: 'cowbell',    label: 'Cowbell', color: '#fb923c' },
		{ key: 'maracas',    label: 'Maracas', color: '#d4d4d8' },
		{ key: 'guiro',      label: 'Güiro',   color: '#e5e7eb' }
	];

	const SECTION_COLORS: Record<string, string> = {
		intro: '#4b5563', verso: '#6366f1', pre_coro: '#818cf8', coro: '#ec4899',
		mambo: '#f97316', majae: '#eab308', soneo: '#22c55e', puente: '#06b6d4',
		breakdown: '#ef4444', outro: '#6b7280',
		coro_pregon: '#818cf8', montuno: '#10b981',
		mambo_sub: '#f97316', diablo_sub: '#dc2626', mona_sub: '#eab308', especial_sub: '#8b5cf6',
		coda: '#6b7280'
	};

	// ====== Derived ======
	let visibleStems = $derived(
		analysis
			? STEMS_DISPLAY.filter((s) => analysis!.stems_present[s.key])
			: []
	);
	let visibleSections = $derived(analysis?.sections ?? []);
	let visibleGems = $derived(analysis?.gems ?? []);
	let bpm = $derived(analysis?.global.bpm ?? null);

	let currentSection = $derived(
		visibleSections.find((s) => playhead >= s.start_sec && playhead < s.end_sec) ?? null
	);

	// Coach (locked §4.6)
	const COACH_BACHATA: Record<string, { move: string; detail: string; difficulty: 'beginner' | 'intermediate' | 'advanced' }> = {
		intro: { move: 'Get into position', detail: 'Connect with partner, find your frame, breathe.', difficulty: 'beginner' },
		verso: { move: 'Basic step with body movement', detail: 'Hip check on counts 4 and 8, weight shifts with the melody.', difficulty: 'beginner' },
		pre_coro: { move: 'Anticipate the turn', detail: 'Slight weight shift, eye contact, prepare for the coro.', difficulty: 'beginner' },
		coro: { move: 'Same footwork, more hip', detail: 'More pronounced hip motion. Stay in close position.', difficulty: 'beginner' },
		mambo: { move: 'Cross-body lead with 1 turn', detail: 'Vocal break + bass hit = your moment. Use it.', difficulty: 'intermediate' },
		majae: { move: 'Open-position footwork', detail: 'Vocal drops, percussion leads. Shine in shadow position.', difficulty: 'intermediate' },
		soneo: { move: 'Shines and freestyle', detail: 'Singer is improvising — the music is open. Separate or add partner tricks.', difficulty: 'advanced' },
		puente: { move: 'Dips and body isolations', detail: 'Chord change = emotional shift. Romantic moment.', difficulty: 'intermediate' },
		breakdown: { move: 'Stop, dip, body roll', detail: 'Instrumentation drops. Dramatic pause = dramatic move.', difficulty: 'advanced' },
		outro: { move: 'Wind down, final pose', detail: 'Match the energy ramp-down. End with intention.', difficulty: 'beginner' }
	};
	const COACH_SALSA: Record<string, { move: string; detail: string; difficulty: 'beginner' | 'intermediate' | 'advanced' }> = {
		intro: { move: 'Find the 1 (or 2)', detail: 'On1 = break on count 1. On2 = break on count 2. Locate your foot.', difficulty: 'beginner' },
		verso: { move: 'Partner work, basic step', detail: 'Stay connected, listen for the coro. Don\'t pre-plan turns.', difficulty: 'beginner' },
		coro_pregon: { move: 'Anticipate the coro', detail: 'Call to chorus — get ready to sing along and start the footwork pattern.', difficulty: 'beginner' },
		coro: { move: 'Basic step, sing along', detail: 'Same footwork, more groove. Sing if you know it.', difficulty: 'beginner' },
		montuno: { move: 'Continuous partner work + turn patterns', detail: 'Piano montuno + bass tumbao = the main 8-count. All your patterns live here.', difficulty: 'intermediate' },
		mambo_sub: { move: 'Shines! Partner separates', detail: 'Horns drive the mambo. Both dancers shine — solo footwork.', difficulty: 'intermediate' },
		diablo_sub: { move: 'Fast footwork shines', detail: 'Highest energy. Complex shines. Show your best.', difficulty: 'advanced' },
		mona_sub: { move: 'Climax — biggest move', detail: 'Peak of the song. Your signature trick, dip, or lift.', difficulty: 'advanced' },
		especial_sub: { move: 'Special arrangement, big trick', detail: 'Key change or new vamp. Time your biggest move.', difficulty: 'advanced' },
		soneo: { move: 'Shines, freestyle, partner tricks', detail: 'Singer improvising over the montuno. Open for anything.', difficulty: 'intermediate' },
		coda: { move: 'Big finish, dramatic pose', detail: 'Final vamp, often with a hit. End with confidence.', difficulty: 'beginner' }
	};
	let coachSuggestion = $derived.by(() => {
		if (!currentSection || !selectedSong) return null;
		const table = selectedSong.genre === 'bachata' ? COACH_BACHATA : COACH_SALSA;
		return table[currentSection.type] ?? null;
	});

	// ====== Stem state effects ======
	$effect(() => {
		// Push stem state changes to the engine
		if (!engineLoaded) return;
		for (const [k, v] of Object.entries(stemState)) {
			engine.setStemVolume(k as any, v.volume);
			engine.setStemMute(k as any, v.muted);
			engine.setStemSolo(k as any, v.solo);
		}
	});

	// ====== Lifecycle ======
	$effect(() => {
		void selectedSong;
		// Reset state on song change
		engineLoaded = false;
		engineLoading = false;
		engineError = null;
		playhead = 0;
		playing = false;
		loopA = null;
		loopB = null;
		stemState = {};
		analysis = null;
		analysisError = null;
	});

	onMount(async () => {
		engine.onTimeUpdate = (t: number) => {
			playhead = t;
		};
		engine.onEnded = () => {
			playing = false;
		};
		await loadLibrary();
	});

	onDestroy(() => {
		engine.dispose();
	});

	async function loadLibrary() {
		try {
			songs = await listSongs();
			if (!selectedSong && songs.length > 0) {
				await selectSong(songs[0]);
			}
		} catch (e) {
			console.error('Failed to load library:', e);
		}
	}

	async function selectSong(song: Song) {
		selectedSong = song;
		analysis = null;
		analysisError = null;
		engineLoaded = false;
		duration = song.duration_sec;
		try {
			const data = await getAnalysis(song.id);
			analysis = data.result;
		} catch {
			analysis = null;
		}
	}

	async function handleUpload(e: Event) {
		const f = (e.target as HTMLInputElement).files?.[0];
		if (!f) return;
		uploadBusy = true;
		uploadError = null;
		try {
			const title = f.name.replace(/\.[^.]+$/, '');
			const song = await uploadSong(title, 'Unknown', 'bachata', f);
			songs = [song, ...songs];
			await selectSong(song);
		} catch (err: any) {
			uploadError = err.message || 'Upload failed';
		} finally {
			uploadBusy = false;
		}
	}

	async function handleAnalyze() {
		if (!selectedSong) return;
		analysisLoading = true;
		analysisError = null;
		try {
			await triggerAnalysis(selectedSong.id);
			const data = await getAnalysis(selectedSong.id);
			analysis = data.result;
		} catch (err: any) {
			analysisError = err.message || 'Analysis failed';
		} finally {
			analysisLoading = false;
		}
	}

	async function handleDelete(song: Song) {
		if (!confirm(`Delete "${song.title}"?`)) return;
		try {
			await deleteSong(song.id);
			songs = songs.filter((s) => s.id !== song.id);
			if (selectedSong?.id === song.id) {
				selectedSong = songs[0] ?? null;
				if (selectedSong) await selectSong(selectedSong);
				else analysis = null;
			}
		} catch (e) {
			console.error(e);
		}
	}

	// ====== Engine loading ======
	async function loadEngine() {
		if (!selectedSong || !analysis) return;
		if (engineLoaded || engineLoading) return;
		engineLoading = true;
		engineError = null;
		try {
			// Load the original mix + every available split stem
			const stemsToLoad: StemKind[] = visibleStems.map((s) => s.key);
			await engine.load(selectedSong.id, stemsToLoad);
			duration = engine.duration || duration;
			engineLoaded = true;
			// Initialize stem state for all loaded stems
			const newState: Record<string, StemState> = { mix: { volume: 1, muted: false, solo: false } };
			for (const s of stemsToLoad) {
				newState[s] = stemState[s] ?? { volume: 1, muted: false, solo: false };
			}
			stemState = newState;
		} catch (e: any) {
			engineError = e.message || 'Audio engine failed to load';
		} finally {
			engineLoading = false;
		}
	}

	// Auto-load engine when analysis + song are ready
	$effect(() => {
		if (selectedSong && analysis && !engineLoaded && !engineLoading) {
			loadEngine();
		}
	});

	// ====== Transport ======
	function togglePlay() {
		if (!engineLoaded) {
			loadEngine().then(() => engine.play());
			return;
		}
		if (playing) {
			engine.pause();
			playing = false;
			(window as any).compasHaptic?.(5);
		} else {
			engine.play();
			playing = true;
			(window as any).compasHaptic?.(10);
		}
	}

	function setPlayhead(t: number) {
		if (engineLoaded) {
			engine.seek(t);
			playhead = engine.currentTime;
		} else {
			playhead = t;
		}
		(window as any).compasHaptic?.(8);
	}

	function setLoopA() { loopA = playhead; if (loopB !== null && loopB <= loopA) loopB = null; if (engineLoaded) engine.setLoop(loopA, loopB); }
	function setLoopB() { loopB = playhead; if (loopA !== null && loopA >= loopB) loopA = null; if (engineLoaded) engine.setLoop(loopA, loopB); }
	function clearLoop() { loopA = null; loopB = null; if (engineLoaded) engine.setLoop(null, null); }

	$effect(() => {
		if (engineLoaded) engine.setLoop(loopA, loopB);
	});
	$effect(() => {
		if (engineLoaded) engine.setRate(playbackRate);
	});

	// ====== Stem mixer actions ======
	function getState(stem: string): StemState {
		return stemState[stem] ?? { volume: 1, muted: false, solo: false };
	}
	function setState(stem: string, s: Partial<StemState>) {
		stemState = { ...stemState, [stem]: { ...getState(stem), ...s } };
	}
	function setVolume(stem: string, vol: number) { setState(stem, { volume: vol }); }
	function toggleMute(stem: string) { setState(stem, { muted: !getState(stem).muted }); }
	function toggleSolo(stem: string) { setState(stem, { solo: !getState(stem).solo }); }
	function clearAllMutesAndSolos() {
		const newState: Record<string, StemState> = {};
		for (const [k, v] of Object.entries(stemState)) {
			newState[k] = { ...v, muted: false, solo: false };
		}
		stemState = newState;
	}

	// ====== Mix presets ======
	function savePreset(name: string) {
		presets = [...presets, { name, volumes: Object.fromEntries(Object.entries(stemState).map(([k, v]) => [k, v.volume])), mutes: Object.fromEntries(Object.entries(stemState).map(([k, v]) => [k, v.muted])), solos: Object.fromEntries(Object.entries(stemState).map(([k, v]) => [k, v.solo])) }];
		try { localStorage.setItem('compas.presets', JSON.stringify(presets)); } catch {}
	}
	function loadPreset(idx: number) {
		const p = presets[idx];
		if (!p) return;
		const newState: Record<string, StemState> = {};
		for (const [k, v] of Object.entries(stemState)) {
			newState[k] = {
				volume: p.volumes[k] ?? 1,
				muted: p.mutes[k] ?? false,
				solo: p.solos[k] ?? false
			};
		}
		stemState = newState;
	}
	function deletePreset(idx: number) {
		presets = presets.filter((_, i) => i !== idx);
		try { localStorage.setItem('compas.presets', JSON.stringify(presets)); } catch {}
	}

	onMount(() => {
		try {
			const stored = localStorage.getItem('compas.presets');
			if (stored) presets = JSON.parse(stored);
		} catch {}
	});

	// ====== Stem download ======
	async function downloadStem(stem: StemKind) {
		if (!selectedSong) return;
		downloadBusy = { ...downloadBusy, [stem]: true };
		try {
			// Use the proxy URL on dev, but the API is also exposed
			const a = document.createElement('a');
			a.href = stemUrl(selectedSong.id, stem);
			a.download = `${selectedSong.title.replace(/[^\w]+/g, '_')}_${stem}.flac`;
			document.body.appendChild(a);
			a.click();
			a.remove();
		} catch (e) {
			console.error('Download failed', e);
		} finally {
			downloadBusy = { ...downloadBusy, [stem]: false };
		}
	}

	function fmtTime(t: number) {
		if (!isFinite(t)) return '0:00';
		const m = Math.floor(t / 60);
		const s = Math.floor(t % 60);
		return `${m}:${s.toString().padStart(2, '0')}`;
	}

	function isStemActive(stem: StemKind): boolean {
		if (!analysis) return false;
		if (!analysis.stems_present[stem]) return false;
		const st = getState(stem);
		if (st.muted) return false;
		const anySolo = Object.values(stemState).some((s) => s.solo);
		if (anySolo) return st.solo;
		return true;
	}
</script>

<svelte:head>
	<title>Compás · {selectedSong ? selectedSong.title : 'Visualizer'}</title>
</svelte:head>

<main class:sidebar-open={sidebarOpen}>
	<header>
		<button class="icon-btn" onclick={() => (sidebarOpen = !sidebarOpen)} aria-label="Toggle library">☰</button>
		<div class="logo">
			<span class="logo-mark">◐</span>
			<span>Compás</span>
			<span class="version">v0.5</span>
		</div>
		<div class="tagline">Get inside the music</div>
		<nav class="header-nav">
			<a href="https://github.com/christianchavezmoya-bot/Comp-s-" target="_blank" rel="noopener">GitHub</a>
		</nav>
	</header>

	<div class="layout">
		<aside class:open={sidebarOpen}>
			<div class="aside-head">
				<h2>Library</h2>
				<label class="upload-btn" class:busy={uploadBusy}>
					{uploadBusy ? 'Uploading…' : '+ Upload'}
					<input type="file" accept="audio/*" onchange={handleUpload} disabled={uploadBusy} />
				</label>
			</div>
			{#if uploadError}<div class="error">{uploadError}</div>{/if}
			<ul class="song-list">
				{#each songs as song (song.id)}
					<li class:active={selectedSong?.id === song.id}>
						<button class="song-btn" onclick={() => selectSong(song)}>
							<div class="song-title">{song.title}</div>
							<div class="song-meta">
								<span class="genre-pill genre-{song.genre}">{song.genre}</span>
								{#if song.bpm}<span>{Math.round(song.bpm)} BPM</span>{/if}
								<span class="status status-{song.analysis_status}">{song.analysis_status}</span>
							</div>
						</button>
						<button class="del-btn" onclick={() => handleDelete(song)} title="Delete">×</button>
					</li>
				{/each}
				{#if songs.length === 0}
					<li class="empty">No songs yet. Click <strong>+ Upload</strong> to add one.</li>
				{/if}
			</ul>
		</aside>

		<section class="main">
			{#if !selectedSong}
				<div class="placeholder">
					<div class="placeholder-art">◐</div>
					<h1>Compás</h1>
					<p>Visualize, analyze, and dance to your favorite bachata and salsa tracks.</p>
					<p class="muted">Click <strong>+ Upload</strong> in the sidebar to get started.</p>
				</div>
			{:else}
				<div class="song-head">
					<div class="song-info">
						<h1>{selectedSong.title}</h1>
						<div class="sub">
							<span class="genre-pill genre-{selectedSong.genre}">{selectedSong.genre}</span>
							{#if bpm}<span class="bpm"><strong>{Math.round(bpm)}</strong> BPM</span>{/if}
							{#if analysis?.global.clave_direction}
								<span class="clave-pill">Clave: {analysis.global.clave_direction.replace('son_', '').replace('_', '-')}</span>
							{/if}
							<span class="muted">{fmtTime(duration)}</span>
							{#if engineLoading}<span class="engine-status">⏳ Loading audio…</span>{/if}
							{#if engineError}<span class="engine-status error">⚠ {engineError}</span>{/if}
						</div>
					</div>
					<div class="head-actions">
						{#if !analysis}
							<button class="primary" onclick={handleAnalyze} disabled={analysisLoading}>
								{analysisLoading ? '⏳ Analyzing…' : '▶ Analyze'}
							</button>
						{:else}
							<button class="secondary" onclick={handleAnalyze} disabled={analysisLoading}>
								{analysisLoading ? '⏳' : '↻ Re-analyze'}
							</button>
						{/if}
					</div>
				</div>

				{#if analysisError}<div class="error">{analysisError}</div>{/if}
				{#if analysis}
					<div class="confidence-bar">
						<span>Confidence: <strong>{Math.round(analysis.confidence_overall * 100)}%</strong></span>
						<span class="muted">· {analysis.sections.length} sections · {analysis.gems.length} gems · {Object.values(analysis.stems_present).filter(Boolean).length} stems</span>
						{#if engineLoaded}<span class="muted">· audio engine ready ✓</span>{/if}
					</div>
				{/if}

				<div class="tabs">
					<button class="tab" class:active={view === 'play'} onclick={() => (view = 'play')}>▶ Play</button>
					<button class="tab" class:active={view === 'grid'} onclick={() => (view = 'grid')}>◇ Grid</button>
					<button class="tab" class:active={view === 'lyrics'} onclick={() => (view = 'lyrics')}>¶ Lyrics</button>
				</div>

				<div class="viz-host">
					{#if analysis && view === 'play'}
						<VerticalPlay
							data={{
								song_id: analysis.song_id,
								duration_sec: duration,
								bpm: bpm ?? 128,
								first_8count_sec: analysis.global.first_8count_start_sec,
								gems: visibleGems,
								stems: visibleStems.map((s) => s.key),
								sections: visibleSections,
								musicality: analysis.musicality
							}}
							{playhead}
							visibleStems={visibleStems.filter((s) => isStemActive(s.key)).map((s) => s.key)}
							onSeek={setPlayhead}
						/>
					{:else if analysis && view === 'grid'}
						<GemGrid
							data={{
								song_id: analysis.song_id,
								duration_sec: duration,
								bpm: bpm ?? 128,
								first_8count_sec: analysis.global.first_8count_start_sec,
								gems: visibleGems,
								stems: visibleStems.map((s) => s.key),
								sections: visibleSections,
								musicality: analysis.musicality
							}}
							playheadSec={playhead}
							{loopA}
							{loopB}
							onSeek={setPlayhead}
						/>
					{:else if view === 'lyrics'}
						<LyricsPanel lyrics={analysis?.lyrics} {playhead} onSeek={setPlayhead} />
					{:else}
						<div class="placeholder-card">
							<p>Click <strong>Analyze</strong> to compute BPM, sections, stems, and gems for this song.</p>
							<p class="muted">First analysis takes ~3 min for a 3-min song on CPU.</p>
						</div>
					{/if}
				</div>

				{#if coachSuggestion && currentSection}
					<div class="coach">
						<div class="coach-head">
							<span class="coach-label">🎯 Pattern Coach</span>
							<span class="coach-section" style="color: {SECTION_COLORS[currentSection.type] ?? '#888'}">
								{currentSection.type.replace('_', ' ').toUpperCase()}
							</span>
							<span class="coach-diff coach-diff-{coachSuggestion.difficulty}">{coachSuggestion.difficulty}</span>
						</div>
						<div class="coach-move">{coachSuggestion.move}</div>
						<div class="coach-detail">{coachSuggestion.detail}</div>
					</div>
				{/if}

				<!-- Transport -->
				<div class="transport">
					<button class="play-btn" onclick={togglePlay} disabled={engineLoading} aria-label={playing ? 'Pause' : 'Play'}>
						{playing ? '❚❚' : '▶'}
					</button>
					<button class="ctrl-btn" onclick={() => setPlayhead(playhead - 5)} title="Back 5s">«</button>
					<button class="ctrl-btn" onclick={() => setPlayhead(playhead + 5)} title="Forward 5s">»</button>
					<input
						type="range"
						class="seek"
						min="0"
						max={duration || 0}
						step="0.01"
						value={playhead}
						oninput={(e) => setPlayhead(parseFloat((e.target as HTMLInputElement).value))}
					/>
					<span class="time">{fmtTime(playhead)} / {fmtTime(duration)}</span>
				</div>

				<div class="control-row">
					<div class="control-group">
						<span class="lbl">Speed</span>
						<input type="range" min="0.5" max="1.5" step="0.05" bind:value={playbackRate} />
						<span class="val">{playbackRate.toFixed(2)}×</span>
					</div>
					<div class="control-group">
						<span class="lbl">Loop</span>
						<button class="ctrl-btn small" onclick={setLoopA} title="Set A at playhead">A</button>
						<button class="ctrl-btn small" onclick={setLoopB} title="Set B at playhead">B</button>
						<button class="ctrl-btn small" onclick={clearLoop} title="Clear loop">×</button>
						{#if loopA !== null && loopB !== null}
							<span class="val">{fmtTime(loopA)}–{fmtTime(loopB)}</span>
						{:else if loopA !== null}
							<span class="val">A={fmtTime(loopA)}</span>
						{:else}
							<span class="val muted">—</span>
						{/if}
					</div>
					<button class="ctrl-btn small" onclick={clearAllMutesAndSolos} title="Reset all mutes and solos">Reset mix</button>
				</div>

				<!-- Stem mixer (REAL AUDIO) -->
				{#if analysis && visibleStems.length > 0}
					<div class="mixer">
						<div class="mixer-head">
							<h3>Stems <span class="muted">(multi-track playback)</span></h3>
							<div class="mixer-actions">
								<button class="ctrl-btn small" onclick={() => (showPresets = !showPresets)}>
									{showPresets ? '▾' : '▸'} Presets ({presets.length})
								</button>
							</div>
						</div>
						{#if showPresets}
							<div class="presets-bar">
								<input
									type="text"
									placeholder="Preset name"
									id="preset-name"
									class="preset-name-input"
									onkeydown={(e) => {
										if (e.key === 'Enter') {
											const inp = e.target as HTMLInputElement;
											if (inp.value.trim()) { savePreset(inp.value.trim()); inp.value = ''; }
										}
									}}
								/>
								<button class="ctrl-btn small" onclick={() => {
									const inp = document.getElementById('preset-name') as HTMLInputElement;
									if (inp.value.trim()) { savePreset(inp.value.trim()); inp.value = ''; }
								}}>Save current</button>
								{#if presets.length > 0}
									<div class="preset-chips">
										{#each presets as p, i}
											<span class="preset-chip">
												<button class="preset-load" onclick={() => loadPreset(i)} title="Load">{p.name}</button>
												<button class="preset-del" onclick={() => deletePreset(i)} title="Delete">×</button>
											</span>
										{/each}
									</div>
								{/if}
							</div>
						{/if}
						<div class="mixer-grid">
							{#each visibleStems as stem}
								{@const st = getState(stem.key)}
								<div class="stem-cell" class:solo={st.solo} class:muted={st.muted}>
									<div class="stem-name" style="color: {stem.color}">{stem.label}</div>
									<input
										type="range"
										class="stem-vol"
										min="0" max="1" step="0.01"
										value={st.volume}
										oninput={(e) => setVolume(stem.key, parseFloat((e.target as HTMLInputElement).value))}
									/>
									<div class="stem-actions">
										<button
											class="act-btn"
											class:active={st.solo}
											onclick={() => toggleSolo(stem.key)}
											title="Solo (S)"
										>S</button>
										<button
											class="act-btn"
											class:active={st.muted}
											onclick={() => toggleMute(stem.key)}
											title="Mute (M)"
										>M</button>
										<button
											class="act-btn"
											class:busy={downloadBusy[stem.key]}
											onclick={() => downloadStem(stem.key)}
											title="Download this stem (FLAC)"
										>↓</button>
									</div>
								</div>
							{/each}
						</div>
					</div>
				{/if}

				{#if analysis}
					<div class="section-jumps">
						{#each visibleSections as sec}
							<button
								class="section-btn"
								class:active={currentSection?.type === sec.type}
								onclick={() => setPlayhead(sec.start_sec)}
							>
								<span class="dot" style="background: {SECTION_COLORS[sec.type] ?? '#666'}"></span>
								{sec.type.replace('_', ' ')}
								<span class="muted"> {fmtTime(sec.start_sec)}</span>
							</button>
						{/each}
					</div>
				{/if}
			{/if}
		</section>
	</div>
</main>

<style>
	:global(body) { background: #0a0a0a; margin: 0; }
	main { display: flex; flex-direction: column; min-height: 100vh; }
	header {
		display: grid;
		grid-template-columns: auto 1fr auto auto;
		align-items: center;
		gap: 16px;
		padding: 14px 20px;
		border-bottom: 1px solid #1a1a1a;
		background: #0a0a0a;
		position: sticky;
		top: 0;
		z-index: 10;
	}
	.icon-btn {
		background: transparent;
		border: 1px solid #1a1a1a;
		color: #ccc;
		width: 36px;
		height: 36px;
		border-radius: 4px;
		cursor: pointer;
		font-size: 16px;
	}
	.icon-btn:hover { background: #1a1a1a; }
	.logo { display: flex; gap: 8px; align-items: center; font-size: 20px; font-weight: 700; letter-spacing: -0.02em; }
	.logo-mark { color: var(--accent); font-size: 24px; }
	.version {
		font-size: 10px;
		background: #1a1a1a;
		padding: 2px 6px;
		border-radius: 3px;
		color: #666;
		margin-left: 4px;
		font-weight: 400;
	}
	.tagline { color: #888; font-size: 13px; }
	.header-nav a {
		color: #888;
		text-decoration: none;
		font-size: 12px;
		padding: 6px 10px;
		border: 1px solid #1a1a1a;
		border-radius: 4px;
	}
	.header-nav a:hover { color: #fff; border-color: #2a2a2a; }
	.layout { display: grid; grid-template-columns: 280px 1fr; flex: 1; min-height: 0; }
	main.sidebar-open .layout { grid-template-columns: 0 1fr; }
	aside {
		background: #0f0f0f;
		border-right: 1px solid #1a1a1a;
		padding: 16px;
		overflow-y: auto;
		transition: margin-left 0.2s ease;
	}
	main:not(.sidebar-open) aside { margin-left: -280px; }
	.aside-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
	.aside-head h2 { font-size: 12px; margin: 0; text-transform: uppercase; letter-spacing: 0.08em; color: #888; font-weight: 600; }
	.upload-btn {
		background: var(--accent);
		color: white;
		padding: 6px 12px;
		border-radius: 4px;
		font-size: 12px;
		cursor: pointer;
		font-weight: 500;
	}
	.upload-btn.busy { opacity: 0.6; cursor: wait; }
	.upload-btn input { display: none; }
	.song-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 4px; }
	.song-list li { display: flex; align-items: stretch; border-radius: 4px; overflow: hidden; }
	.song-list li.active { background: #1a1a1a; }
	.song-list li:hover { background: #141414; }
	.song-btn {
		flex: 1; text-align: left; background: transparent; border: none; color: #ddd;
		padding: 10px 12px; cursor: pointer; font-size: 13px;
	}
	.song-title {
		font-weight: 500;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		margin-bottom: 4px;
	}
	.song-meta { display: flex; gap: 6px; font-size: 10px; color: #888; align-items: center; }
	.del-btn {
		background: transparent; border: none; color: #555;
		font-size: 18px; padding: 0 10px; cursor: pointer;
	}
	.del-btn:hover { color: #ef4444; }
	.empty { color: #555; font-size: 12px; padding: 16px; text-align: center; }

	.main {
		padding: 20px 24px 40px;
		overflow-y: auto;
		display: flex; flex-direction: column; gap: 14px;
	}
	.placeholder { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 60px 20px; text-align: center; }
	.placeholder-art { font-size: 96px; color: var(--accent); opacity: 0.5; margin-bottom: 16px; }
	.placeholder h1 { font-size: 36px; margin: 0 0 12px; font-weight: 700; letter-spacing: -0.02em; }
	.placeholder p { color: #aaa; margin: 4px 0; max-width: 480px; }

	.song-head { display: flex; justify-content: space-between; align-items: flex-end; gap: 16px; flex-wrap: wrap; }
	.song-info h1 { margin: 0 0 6px; font-size: 26px; font-weight: 700; letter-spacing: -0.02em; }
	.sub { display: flex; gap: 10px; font-size: 13px; color: #aaa; align-items: center; flex-wrap: wrap; }
	.bpm { color: #fff; }
	.bpm strong { color: var(--accent); font-size: 16px; }
	.clave-pill { background: #2d1a4a; color: #c4b5fd; padding: 2px 8px; border-radius: 3px; font-size: 11px; font-weight: 500; }
	.genre-pill { padding: 2px 8px; border-radius: 3px; font-size: 10px; text-transform: uppercase; letter-spacing: 0.05em; font-weight: 600; }
	.genre-bachata { background: #1e3a5f; color: #93c5fd; }
	.genre-salsa { background: #5f1e1e; color: #fca5a5; }
	.status { padding: 1px 5px; border-radius: 3px; font-size: 9px; text-transform: uppercase; letter-spacing: 0.05em; }
	.status-none { background: #2a2a2a; color: #888; }
	.status-running, .status-queued { background: #4a3a00; color: #fbbf24; }
	.status-done { background: #1e4a1e; color: #86efac; }
	.status-failed { background: #5f1e1e; color: #fca5a5; }
	.muted { color: #666; }
	.head-actions { display: flex; gap: 8px; }
	button.primary {
		background: var(--accent); color: white; border: none;
		padding: 10px 18px; border-radius: 4px; font-size: 13px; font-weight: 600; cursor: pointer;
	}
	button.primary:disabled { opacity: 0.6; cursor: wait; }
	button.secondary {
		background: #1a1a1a; color: #ccc; border: 1px solid #2a2a2a;
		padding: 8px 14px; border-radius: 4px; font-size: 12px; cursor: pointer;
	}
	.engine-status { font-size: 11px; color: #fbbf24; padding: 2px 6px; background: #2a1a00; border-radius: 3px; }
	.engine-status.error { color: #fca5a5; background: #2a0a0a; }

	.confidence-bar { display: flex; gap: 8px; align-items: center; font-size: 12px; color: #aaa; padding: 8px 12px; background: #0f0f0f; border-radius: 4px; border: 1px solid #1a1a1a; flex-wrap: wrap; }
	.confidence-bar strong { color: #86efac; }
	.error { background: #5f1e1e; color: #fca5a5; padding: 8px 12px; border-radius: 4px; font-size: 13px; }

	.tabs { display: flex; gap: 0; background: #0f0f0f; border: 1px solid #1a1a1a; border-radius: 6px; padding: 4px; }
	.tab { flex: 1; background: transparent; border: none; color: #888; padding: 10px 16px; border-radius: 4px; cursor: pointer; font-size: 13px; font-weight: 500; transition: all 0.15s ease; }
	.tab:hover { color: #ccc; }
	.tab.active { background: #1a1a1a; color: #fff; }

	.viz-host { min-height: 420px; height: 50vh; max-height: 580px; }
	.placeholder-card { padding: 32px; background: #0f0f0f; border: 1px dashed #2a2a2a; border-radius: 6px; color: #aaa; text-align: center; }
	.placeholder-card p { margin: 6px 0; }

	.transport { display: flex; align-items: center; gap: 10px; padding: 10px 12px; background: #0f0f0f; border: 1px solid #1a1a1a; border-radius: 6px; }
	.play-btn { width: 44px; height: 44px; border-radius: 50%; border: none; background: var(--accent); color: white; font-size: 16px; cursor: pointer; flex-shrink: 0; }
	.play-btn:disabled { opacity: 0.4; cursor: not-allowed; }
	.play-btn:hover:not(:disabled) { filter: brightness(1.1); }
	.ctrl-btn { background: #1a1a1a; border: 1px solid #2a2a2a; color: #ccc; width: 36px; height: 36px; border-radius: 4px; cursor: pointer; font-size: 14px; }
	.ctrl-btn:hover { background: #2a2a2a; }
	.ctrl-btn.small { width: auto; height: 28px; font-size: 11px; padding: 0 10px; }
	.seek { flex: 1; accent-color: var(--accent); }
	.time { font-variant-numeric: tabular-nums; font-size: 12px; color: #888; min-width: 110px; text-align: right; }

	.control-row { display: flex; align-items: center; gap: 16px; padding: 8px 12px; background: #0f0f0f; border: 1px solid #1a1a1a; border-radius: 6px; flex-wrap: wrap; }
	.control-group { display: flex; align-items: center; gap: 8px; }
	.lbl { font-size: 10px; text-transform: uppercase; letter-spacing: 0.05em; color: #666; font-weight: 600; }
	.control-group input[type=range] { width: 100px; accent-color: var(--accent); }
	.val { font-size: 11px; color: #ccc; min-width: 32px; }

	.mixer { padding: 12px; background: #0f0f0f; border: 1px solid #1a1a1a; border-radius: 6px; }
	.mixer-head { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 8px; }
	.mixer h3 { margin: 0; font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em; color: #888; font-weight: 600; }
	.mixer-actions { display: flex; gap: 6px; }
	.presets-bar { display: flex; align-items: center; gap: 6px; padding: 8px; background: #050505; border-radius: 4px; margin-bottom: 8px; flex-wrap: wrap; }
	.preset-name-input { background: #1a1a1a; border: 1px solid #2a2a2a; color: #fff; padding: 5px 8px; border-radius: 3px; font-size: 11px; min-width: 140px; }
	.preset-chips { display: flex; gap: 6px; flex-wrap: wrap; margin-left: auto; }
	.preset-chip { display: inline-flex; align-items: center; background: #1a1a1a; border-radius: 3px; overflow: hidden; }
	.preset-load { background: transparent; border: none; color: #4f9eff; padding: 4px 8px; font-size: 11px; cursor: pointer; }
	.preset-load:hover { background: #2a2a2a; }
	.preset-del { background: transparent; border: none; color: #666; padding: 4px 8px; font-size: 12px; cursor: pointer; }
	.preset-del:hover { color: #ef4444; }

	.mixer-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 6px; }
	.stem-cell { display: flex; align-items: center; gap: 8px; padding: 8px 10px; background: #050505; border-radius: 4px; border: 1px solid #1a1a1a; transition: all 0.15s ease; }
	.stem-cell.solo { background: #1a2a1a; border-color: #2a4a2a; }
	.stem-cell.muted { opacity: 0.4; }
	.stem-name { font-size: 11px; font-weight: 600; min-width: 70px; }
	.stem-vol { flex: 1; accent-color: var(--accent); }
	.stem-actions { display: flex; gap: 3px; }
	.act-btn { width: 28px; height: 28px; background: transparent; border: 1px solid #2a2a2a; color: #666; border-radius: 3px; cursor: pointer; font-size: 10px; font-weight: 700; }
	.act-btn:hover { color: #ccc; }
	.act-btn.active { background: var(--accent); color: #fff; border-color: var(--accent); }
	.act-btn.busy { opacity: 0.5; }

	.coach { padding: 14px 18px; background: linear-gradient(135deg, #1a1a2e 0%, #0f0f1a 100%); border: 1px solid #2a2a4a; border-radius: 6px; border-left: 3px solid var(--accent); }
	.coach-head { display: flex; gap: 12px; align-items: center; margin-bottom: 6px; }
	.coach-label { font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em; color: #aaa; font-weight: 600; }
	.coach-section { font-size: 11px; font-weight: 700; letter-spacing: 0.05em; }
	.coach-diff { font-size: 10px; padding: 2px 8px; border-radius: 3px; text-transform: uppercase; letter-spacing: 0.05em; font-weight: 600; margin-left: auto; }
	.coach-diff-beginner { background: #1e3a1e; color: #86efac; }
	.coach-diff-intermediate { background: #3a3a1e; color: #fde047; }
	.coach-diff-advanced { background: #3a1e1e; color: #fca5a5; }
	.coach-move { font-size: 16px; font-weight: 600; color: #fff; margin-bottom: 4px; }
	.coach-detail { font-size: 13px; color: #aaa; line-height: 1.4; }

	.section-jumps { display: flex; flex-wrap: wrap; gap: 6px; }
	.section-btn { background: #1a1a1a; border: 1px solid #2a2a2a; color: #ccc; padding: 6px 10px; border-radius: 4px; font-size: 12px; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; text-transform: capitalize; transition: all 0.15s ease; }
	.section-btn:hover { background: #2a2a2a; }
	.section-btn.active { background: #2a2a4a; border-color: var(--accent); color: #fff; }
	.section-btn .dot { display: inline-block; width: 8px; height: 8px; border-radius: 2px; }

	@media (max-width: 720px) {
		.layout { grid-template-columns: 1fr; }
		aside { display: none; }
		.song-head { flex-direction: column; align-items: flex-start; }
		.viz-host { min-height: 320px; height: 40vh; }
		.mixer-grid { grid-template-columns: 1fr; }
	}
</style>
