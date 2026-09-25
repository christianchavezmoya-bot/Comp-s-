<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import * as PIXI from 'pixi.js';
	import type { Song, SongAnalysis, Section, StemKind, Gem } from '@compas/shared-types';
	import {
		listSongs,
		uploadSong,
		deleteSong,
		triggerAnalysis,
		getAnalysis,
		audioUrl,
		stemUrl
	} from '$lib/api';

	// ====== State ======
	let songs = $state<Song[]>([]);
	let selectedSong = $state<Song | null>(null);
	let analysis = $state<SongAnalysis | null>(null);
	let analysisLoading = $state(false);
	let analysisError = $state<string | null>(null);
	let uploadBusy = $state(false);
	let uploadError = $state<string | null>(null);

	// Audio
	let audio: HTMLAudioElement;
	let playing = $state(false);
	let playhead = $state(0);
	let rafId: number | null = null;
	let lastT = 0;
	let duration = $state(0);

	// Loop
	let loopA = $state<number | null>(null);
	let loopB = $state<number | null>(null);

	// Speed (0.5–1.5) and pitch
	let playbackRate = $state(1.0);
	let preservePitch = $state(true);

	// Stem mixer: per-stem volume + mute
	let stemVolumes = $state<Record<string, number>>({});
	let stemMutes = $state<Record<string, boolean>>({});

	// UI
	let showUpload = $state(false);
	let showHelp = $state(false);

	const STEMS_DISPLAY: { key: StemKind; label: string; color: string; audioGroup: string }[] = [
		{ key: 'vocals_lead', label: 'Vocals', color: '#ec4899', audioGroup: 'vocals' },
		{ key: 'vocals_back', label: 'Backing', color: '#f472b6', audioGroup: 'vocals' },
		{ key: 'requinto', label: 'Requinto', color: '#2dd4bf', audioGroup: 'other' },
		{ key: 'segunda', label: 'Segunda', color: '#38bdf8', audioGroup: 'other' },
		{ key: 'bass', label: 'Bass', color: '#fb923c', audioGroup: 'bass' },
		{ key: 'bongo', label: 'Bongó', color: '#a3e635', audioGroup: 'drums' },
		{ key: 'guira', label: 'Güira', color: '#facc15', audioGroup: 'drums' },
		{ key: 'tambora', label: 'Tambora', color: '#84cc16', audioGroup: 'drums' },
		{ key: 'clave', label: 'Clave', color: '#a78bfa', audioGroup: 'other' },
		{ key: 'palmas', label: 'Palmas', color: '#94a3b8', audioGroup: 'other' },
		{ key: 'synth', label: 'Synth', color: '#818cf8', audioGroup: 'other' },
		{ key: 'horns', label: 'Horns', color: '#f87171', audioGroup: 'other' },
		{ key: 'piano', label: 'Piano', color: '#60a5fa', audioGroup: 'other' },
		{ key: 'congas', label: 'Congas', color: '#fbbf24', audioGroup: 'drums' },
		{ key: 'timbales', label: 'Timbales', color: '#fde047', audioGroup: 'drums' },
		{ key: 'cowbell', label: 'Cowbell', color: '#fb923c', audioGroup: 'drums' },
		{ key: 'maracas', label: 'Maracas', color: '#d4d4d8', audioGroup: 'drums' },
		{ key: 'guiro', label: 'Güiro', color: '#e5e7eb', audioGroup: 'drums' }
	];

	const SECTION_COLORS: Record<string, string> = {
		intro: '#4b5563',
		verso: '#6366f1',
		pre_coro: '#818cf8',
		coro: '#ec4899',
		mambo: '#f97316',
		majae: '#eab308',
		soneo: '#22c55e',
		puente: '#06b6d4',
		breakdown: '#ef4444',
		outro: '#6b7280',
		coro_pregon: '#818cf8',
		montuno: '#10b981',
		mambo_sub: '#f97316',
		diablo_sub: '#dc2626',
		mona_sub: '#eab308',
		especial_sub: '#8b5cf6',
		coda: '#6b7280'
	};

	// ====== Effects ======
	$effect(() => {
		if (audio) {
			audio.playbackRate = playbackRate;
			audio.preservesPitch = preservePitch;
		}
	});

	$effect(() => {
		// reset state when song changes
		void selectedSong;
		loopA = null;
		loopB = null;
		playhead = 0;
		playing = false;
		stemVolumes = {};
		stemMutes = {};
		analysis = null;
		analysisError = null;
	});

	// ====== Lifecycle ======
	onMount(async () => {
		await loadLibrary();
	});

	onDestroy(() => {
		if (rafId) cancelAnimationFrame(rafId);
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
		duration = song.duration_sec;
		// try to fetch existing analysis
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
			const result = await triggerAnalysis(selectedSong.id);
			console.log('analyze triggered:', result);
			// In v0.1 with run_ml_inline=true, the result is { status: "done" } already
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

	// ====== Audio transport ======
	function togglePlay() {
		if (!audio) return;
		if (audio.paused) {
			audio.play();
			(window as any).compasHaptic?.(10);
		} else {
			audio.pause();
			(window as any).compasHaptic?.(5);
		}
	}

	function onTimeUpdate() {
		if (!audio) return;
		playhead = audio.currentTime;
		duration = audio.duration || duration;
		// Loop
		if (loopA !== null && loopB !== null && loopB > loopA) {
			if (audio.currentTime >= loopB) {
				audio.currentTime = loopA;
			}
		}
	}

	function tick(t: number) {
		if (!audio) return;
		const dt = (t - lastT) / 1000;
		lastT = t;
		// playhead is set by onTimeUpdate; we just keep rAF alive
		rafId = requestAnimationFrame(tick);
	}

	function setPlayhead(t: number) {
		if (!audio) return;
		audio.currentTime = Math.max(0, Math.min(duration, t));
		playhead = audio.currentTime;
		(window as any).compasHaptic?.(8);
	}

	function setLoopA() {
		loopA = playhead;
		if (loopB !== null && loopB <= loopA) loopB = null;
	}

	function setLoopB() {
		loopB = playhead;
		if (loopA !== null && loopA >= loopB) loopA = null;
	}

	function clearLoop() {
		loopA = null;
		loopB = null;
	}

	// ====== Derived ======
	let visibleStems = $derived(
		analysis
			? STEMS_DISPLAY.filter((s) => analysis!.stems_present[s.key])
			: []
	);

	let visibleSections = $derived(analysis?.sections ?? []);

	let visibleGems = $derived(analysis?.gems ?? []);

	let bpm = $derived(analysis?.global.bpm ?? null);

	// Current section (whichever section contains the playhead)
	let currentSection = $derived(
		visibleSections.find((s) => playhead >= s.start_sec && playhead < s.end_sec) ?? null
	);

	// Pattern coach: section → move suggestion (locked §4.6)
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

	// Format helpers
	function fmtTime(t: number) {
		const m = Math.floor(t / 60);
		const s = Math.floor(t % 60);
		return `${m}:${s.toString().padStart(2, '0')}`;
	}
</script>

<svelte:head>
	<title>Compás · {selectedSong ? selectedSong.title : 'Visualizer'}</title>
</svelte:head>

<main>
	<!-- Header -->
	<header>
		<div class="logo">
			<span class="logo-mark">◐</span>
			<span>Compás</span>
			<span class="version">v0.2</span>
		</div>
		<div class="tagline">Get inside the music</div>
	</header>

	<div class="layout">
		<!-- Library sidebar -->
		<aside>
			<div class="aside-head">
				<h2>Library</h2>
				<label class="upload-btn" class:busy={uploadBusy}>
					{uploadBusy ? 'Uploading…' : '+ Upload'}
					<input type="file" accept="audio/*" onchange={handleUpload} disabled={uploadBusy} />
				</label>
			</div>
			{#if uploadError}
				<div class="error">{uploadError}</div>
			{/if}
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
					<li class="empty">No songs yet. Upload a bachata or salsa track to start.</li>
				{/if}
			</ul>
		</aside>

		<!-- Main view -->
		<section class="main">
			{#if !selectedSong}
				<div class="placeholder">
					<h1>Welcome to Compás</h1>
					<p>Upload a song, click <strong>Analyze</strong>, and explore the music.</p>
				</div>
			{:else}
				<div class="song-head">
					<div>
						<h1>{selectedSong.title}</h1>
						<div class="sub">
							<span class="genre-pill genre-{selectedSong.genre}">{selectedSong.genre}</span>
							{#if bpm}<span><strong>{Math.round(bpm)}</strong> BPM</span>{/if}
							{#if analysis?.global.clave_direction}
								<span class="clave-pill">Clave: {analysis.global.clave_direction}</span>
							{/if}
							<span>{fmtTime(duration)}</span>
						</div>
					</div>
					<div class="actions">
						{#if !analysis}
							<button class="primary" onclick={handleAnalyze} disabled={analysisLoading}>
								{analysisLoading ? 'Analyzing…' : '▶ Analyze'}
							</button>
						{:else}
							<button class="secondary" onclick={handleAnalyze} disabled={analysisLoading}>
								{analysisLoading ? 'Re-analyzing…' : '↻ Re-analyze'}
							</button>
						{/if}
					</div>
				</div>

				{#if analysisError}
					<div class="error">{analysisError}</div>
				{/if}

				{#if analysis}
					<div class="confidence">
						Confidence: <strong>{Math.round(analysis.confidence_overall * 100)}%</strong>
						<span class="muted">· {analysis.sections.length} sections · {analysis.gems.length} gems · {Object.values(analysis.stems_present).filter(Boolean).length} stems</span>
					</div>
				{/if}

				<!-- Audio element -->
				<audio
					bind:this={audio}
					src={selectedSong ? audioUrl(selectedSong.id) : ''}
					onplay={() => { playing = true; lastT = performance.now(); if (!rafId) rafId = requestAnimationFrame(tick); }}
					onpause={() => { playing = false; if (rafId) { cancelAnimationFrame(rafId); rafId = null; } }}
					ontimeupdate={onTimeUpdate}
					onended={() => { playing = false; if (rafId) { cancelAnimationFrame(rafId); rafId = null; } }}
					preload="auto"
					crossorigin="anonymous"
				></audio>

				<!-- Transport controls -->
				<div class="controls">
					<button class="play-btn" onclick={togglePlay} disabled={!audio?.src}>
						{playing ? '❚❚' : '▶'}
					</button>
					<input
						type="range"
						min="0"
						max={duration || 0}
						step="0.01"
						value={playhead}
						oninput={(e) => setPlayhead(parseFloat((e.target as HTMLInputElement).value))}
						class="seek"
					/>
					<span class="time">{fmtTime(playhead)} / {fmtTime(duration)}</span>
					<div class="control-group">
						<label>Speed
							<input type="range" min="0.5" max="1.5" step="0.05" bind:value={playbackRate} />
							<span class="val">{playbackRate.toFixed(2)}×</span>
						</label>
						<label class="checkbox">
							<input type="checkbox" bind:checked={preservePitch} />
							Keep pitch
						</label>
					</div>
					<div class="control-group">
						<button class="loop-btn" onclick={setLoopA} title="Set loop start at playhead">Set A</button>
						<button class="loop-btn" onclick={setLoopB} title="Set loop end at playhead">Set B</button>
						<button class="loop-btn" onclick={clearLoop} title="Clear loop">Clear</button>
						{#if loopA !== null && loopB !== null}
							<span class="val">A={fmtTime(loopA)} B={fmtTime(loopB)}</span>
						{/if}
					</div>
				</div>

				<!-- Gem grid -->
				{#if analysis}
					<GemGrid
						data={{
							song_id: analysis.song_id,
							duration_sec: duration,
							bpm: bpm ?? 128,
							first_8count_sec: analysis.global.first_8count_start_sec,
							gems: visibleGems,
							stems: visibleStems.map(s => s.key),
							sections: visibleSections,
							musicality: analysis.musicality
						}}
						{playheadSec}
						{loopA}
						{loopB}
						onSeek={setPlayhead}
					/>
				{:else}
					<div class="placeholder-card">
						<p>Click <strong>Analyze</strong> to compute BPM, sections, stems, and gems for this song.</p>
						<p class="muted">First analysis takes ~3 min for a 3-min song on CPU. Results are saved to the song.</p>
					</div>
				{/if}

				<!-- Stem mixer -->
				{#if analysis && Object.values(analysis.stems_present).filter(Boolean).length > 0}
					<div class="mixer">
						<h3>Stems</h3>
						<div class="mixer-grid">
							{#each visibleStems as stem}
								<div class="stem-cell">
									<div class="stem-name" style="color: {stem.color}">{stem.label}</div>
									<input
										type="range"
										min="0"
										max="1"
										step="0.01"
										value={stemVolumes[stem.key] ?? 0}
										oninput={(e) => stemVolumes = { ...stemVolumes, [stem.key]: parseFloat((e.target as HTMLInputElement).value) }}
									/>
									<button
										class="mute-btn"
										class:active={stemMutes[stem.key]}
										onclick={() => stemMutes = { ...stemMutes, [stem.key]: !stemMutes[stem.key] }}
									>{stemMutes[stem.key] ? '🔇' : '🔊'}</button>
								</div>
							{/each}
						</div>
					</div>
				{/if}

				<!-- Section jumps -->
				{#if analysis}
					<div class="section-jumps">
						{#each visibleSections as sec}
							<button class="section-btn" onclick={() => setPlayhead(sec.start_sec)}>
								<span class="dot" style="background: {SECTION_COLORS[sec.type] ?? '#666'}"></span>
								{sec.type.replace('_', ' ')}
								<span class="muted"> {fmtTime(sec.start_sec)}</span>
							</button>
						{/each}
					</div>
				{/if}

				<!-- Pattern Coach (locked §4.6) -->
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
			{/if}
		</section>
	</div>
</main>

<style>
	:global(body) { background: #0a0a0a; }
	main {
		display: flex;
		flex-direction: column;
		min-height: 100vh;
		max-width: 1400px;
		margin: 0 auto;
	}
	header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 16px 24px;
		border-bottom: 1px solid #1a1a1a;
	}
	.logo {
		display: flex;
		gap: 10px;
		align-items: center;
		font-size: 20px;
		font-weight: 600;
	}
	.logo-mark { color: var(--accent); font-size: 24px; }
	.version {
		font-size: 10px;
		background: #1a1a1a;
		padding: 2px 6px;
		border-radius: 3px;
		color: #888;
		margin-left: 4px;
	}
	.tagline { color: var(--muted); font-size: 13px; }
	.layout {
		display: grid;
		grid-template-columns: 280px 1fr;
		gap: 0;
		flex: 1;
		min-height: 0;
	}
	aside {
		background: #0f0f0f;
		border-right: 1px solid #1a1a1a;
		padding: 16px;
		overflow-y: auto;
	}
	.aside-head {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 12px;
	}
	.aside-head h2 { font-size: 14px; margin: 0; text-transform: uppercase; letter-spacing: 0.05em; color: #888; }
	.upload-btn {
		background: var(--accent);
		color: white;
		padding: 6px 12px;
		border-radius: 4px;
		font-size: 12px;
		cursor: pointer;
	}
	.upload-btn.busy { opacity: 0.6; cursor: wait; }
	.upload-btn input { display: none; }
	.song-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 4px; }
	.song-list li {
		display: flex;
		align-items: stretch;
		border-radius: 4px;
		overflow: hidden;
	}
	.song-list li.active { background: #1a1a1a; }
	.song-list li:hover { background: #141414; }
	.song-btn {
		flex: 1;
		text-align: left;
		background: transparent;
		border: none;
		color: #ddd;
		padding: 10px 12px;
		cursor: pointer;
		font-size: 13px;
	}
	.song-title {
		font-weight: 500;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.song-meta {
		display: flex;
		gap: 6px;
		margin-top: 4px;
		font-size: 11px;
		color: #888;
	}
	.del-btn {
		background: transparent;
		border: none;
		color: #555;
		font-size: 18px;
		padding: 0 10px;
		cursor: pointer;
	}
	.del-btn:hover { color: #ef4444; }
	.empty {
		color: #666;
		font-size: 12px;
		padding: 12px;
		text-align: center;
	}
	.genre-pill {
		padding: 2px 6px;
		border-radius: 3px;
		font-size: 10px;
		text-transform: uppercase;
	}
	.genre-bachata { background: #1e3a5f; color: #93c5fd; }
	.genre-salsa { background: #5f1e1e; color: #fca5a5; }
	.status {
		padding: 1px 5px;
		border-radius: 3px;
		font-size: 9px;
		text-transform: uppercase;
	}
	.status-none { background: #2a2a2a; color: #888; }
	.status-running, .status-queued { background: #4a3a00; color: #fbbf24; }
	.status-done { background: #1e4a1e; color: #86efac; }
	.status-failed { background: #5f1e1e; color: #fca5a5; }
	.main {
		padding: 24px;
		overflow-y: auto;
	}
	.placeholder {
		padding: 60px 20px;
		text-align: center;
	}
	.placeholder h1 { font-size: 32px; margin-bottom: 12px; }
	.placeholder p { color: #888; }
	.song-head {
		display: flex;
		justify-content: space-between;
		align-items: flex-end;
		gap: 16px;
		margin-bottom: 16px;
	}
	.song-head h1 { margin: 0 0 6px; font-size: 28px; }
	.sub {
		display: flex;
		gap: 12px;
		font-size: 13px;
		color: #aaa;
		align-items: center;
	}
	.clave-pill {
		background: #2d1a4a;
		color: #c4b5fd;
		padding: 2px 8px;
		border-radius: 3px;
		font-size: 11px;
	}
	button.primary {
		background: var(--accent);
		color: white;
		border: none;
		padding: 10px 20px;
		border-radius: 4px;
		font-size: 14px;
		font-weight: 500;
		cursor: pointer;
	}
	button.primary:disabled { opacity: 0.6; cursor: wait; }
	button.secondary {
		background: #1a1a1a;
		color: #ccc;
		border: 1px solid #2a2a2a;
		padding: 8px 14px;
		border-radius: 4px;
		font-size: 13px;
		cursor: pointer;
	}
	button.secondary:disabled { opacity: 0.5; cursor: wait; }
	.confidence {
		margin-bottom: 12px;
		font-size: 13px;
		color: #aaa;
	}
	.confidence strong { color: #86efac; }
	.muted { color: #888; }
	.error {
		background: #5f1e1e;
		color: #fca5a5;
		padding: 8px 12px;
		border-radius: 4px;
		font-size: 13px;
		margin-bottom: 12px;
	}
	.controls {
		display: flex;
		align-items: center;
		gap: 12px;
		margin-bottom: 16px;
		flex-wrap: wrap;
	}
	.play-btn {
		width: 44px;
		height: 44px;
		border-radius: 50%;
		border: none;
		background: var(--accent);
		color: white;
		font-size: 16px;
		cursor: pointer;
	}
	.play-btn:disabled { opacity: 0.4; cursor: not-allowed; }
	.seek {
		flex: 1;
		min-width: 200px;
		accent-color: var(--accent);
	}
	.time {
		font-variant-numeric: tabular-nums;
		font-size: 12px;
		color: #888;
		min-width: 110px;
	}
	.control-group {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 6px 10px;
		background: #0f0f0f;
		border-radius: 4px;
		border: 1px solid #1a1a1a;
	}
	.control-group label {
		display: flex;
		align-items: center;
		gap: 6px;
		font-size: 11px;
		color: #888;
	}
	.control-group input[type=range] {
		width: 80px;
		accent-color: var(--accent);
	}
	.val { font-size: 11px; color: #ccc; min-width: 30px; }
	.checkbox { cursor: pointer; }
	.checkbox input { accent-color: var(--accent); }
	.loop-btn {
		background: #1a1a1a;
		border: 1px solid #2a2a2a;
		color: #ccc;
		padding: 4px 8px;
		border-radius: 3px;
		font-size: 11px;
		cursor: pointer;
	}
	.loop-btn:hover { background: #2a2a2a; }
	.mixer {
		margin-top: 16px;
		padding: 12px;
		background: #0f0f0f;
		border-radius: 6px;
		border: 1px solid #1a1a1a;
	}
	.mixer h3 {
		margin: 0 0 8px;
		font-size: 12px;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: #888;
	}
	.mixer-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
		gap: 8px;
	}
	.stem-cell {
		display: flex;
		align-items: center;
		gap: 6px;
		background: #050505;
		padding: 6px 8px;
		border-radius: 4px;
		border: 1px solid #1a1a1a;
	}
	.stem-name {
		font-size: 11px;
		min-width: 60px;
		font-weight: 500;
	}
	.stem-cell input[type=range] {
		flex: 1;
		accent-color: var(--accent);
	}
	.mute-btn {
		background: transparent;
		border: none;
		font-size: 14px;
		cursor: pointer;
		opacity: 0.5;
	}
	.mute-btn.active { opacity: 1; }
	.section-jumps {
		display: flex;
		flex-wrap: wrap;
		gap: 6px;
		margin-top: 12px;
	}
	.section-btn {
		background: #1a1a1a;
		border: 1px solid #2a2a2a;
		color: #ccc;
		padding: 6px 10px;
		border-radius: 4px;
		font-size: 12px;
		cursor: pointer;
		display: inline-flex;
		align-items: center;
		gap: 6px;
		text-transform: capitalize;
	}
	.section-btn:hover { background: #2a2a2a; }
	.section-btn .dot {
		display: inline-block;
		width: 8px;
		height: 8px;
		border-radius: 2px;
	}
	.placeholder-card {
		padding: 24px;
		background: #0f0f0f;
		border: 1px dashed #2a2a2a;
		border-radius: 6px;
		color: #aaa;
		text-align: center;
	}
	.placeholder-card p { margin: 6px 0; }
	.coach {
		margin-top: 12px;
		padding: 14px 18px;
		background: linear-gradient(135deg, #1a1a2e 0%, #0f0f1a 100%);
		border: 1px solid #2a2a4a;
		border-radius: 6px;
		border-left: 3px solid var(--accent);
	}
	.coach-head {
		display: flex;
		gap: 12px;
		align-items: center;
		margin-bottom: 6px;
	}
	.coach-label {
		font-size: 11px;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: #aaa;
	}
	.coach-section {
		font-size: 11px;
		font-weight: 600;
		letter-spacing: 0.05em;
	}
	.coach-diff {
		font-size: 10px;
		padding: 1px 6px;
		border-radius: 3px;
		text-transform: uppercase;
		margin-left: auto;
	}
	.coach-diff-beginner { background: #1e3a1e; color: #86efac; }
	.coach-diff-intermediate { background: #3a3a1e; color: #fde047; }
	.coach-diff-advanced { background: #3a1e1e; color: #fca5a5; }
	.coach-move {
		font-size: 16px;
		font-weight: 600;
		color: #fff;
		margin-bottom: 4px;
	}
	.coach-detail {
		font-size: 13px;
		color: #aaa;
		line-height: 1.4;
	}
</style>
