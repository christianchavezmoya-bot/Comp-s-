<script lang="ts">
	import GemGrid from '$lib/GemGrid.svelte';
	import { MOCK_DATA } from '$lib/mockData';

	let playhead = $state(0);
	let playing = $state(false);
	let rafId: number | null = null;
	let lastT = 0;

	function tick(t: number) {
		if (!playing) return;
		const dt = (t - lastT) / 1000;
		lastT = t;
		playhead = (playhead + dt) % MOCK_DATA.duration_sec;
		rafId = requestAnimationFrame(tick);
	}

	function togglePlay() {
		if (playing) {
			playing = false;
			if (rafId) cancelAnimationFrame(rafId);
		} else {
			playing = true;
			lastT = performance.now();
			rafId = requestAnimationFrame(tick);
		}
	}

	function jumpTo(t: number) {
		playhead = Math.max(0, Math.min(MOCK_DATA.duration_sec, t));
	}
</script>

<svelte:head>
	<title>Compás — Visualizer Prototype</title>
</svelte:head>

<main>
	<header>
		<div class="logo">
			<span class="logo-mark">◐</span>
			<span>Compás</span>
		</div>
		<div class="tagline">Visualize the music · v0.1 prototype</div>
	</header>

	<section class="hero">
		<h1>See the music. <span class="accent">Feel the rhythm.</span></h1>
		<p>
			Below: a fully working prototype of the Compás gem-grid — the same idea as Dentro,
			but with section detection, pitch-aware gem positioning, musicality curves, and
			ready for <strong>{MOCK_DATA.sections.length} sections</strong> ·
			<strong>{MOCK_DATA.gems.length} instrument onsets</strong> ·
			<strong>{MOCK_DATA.bpm} BPM</strong>.
		</p>
		<p class="muted">
			This is mock data. Real analysis (Demucs + Beat-Transformer + Whisper) lands in Phase 1
			of the roadmap.
		</p>
	</section>

	<section class="visualizer">
		<div class="controls">
			<button class="play" onclick={togglePlay} aria-label={playing ? 'Pause' : 'Play'}>
				{playing ? '❚❚' : '▶'}
			</button>
			<input
				type="range"
				min="0"
				max={MOCK_DATA.duration_sec}
				step="0.1"
				bind:value={playhead}
				aria-label="Seek"
			/>
			<span class="time">{playhead.toFixed(1)}s / {MOCK_DATA.duration_sec.toFixed(0)}s</span>
		</div>
		<GemGrid data={MOCK_DATA} {playheadSec} />
		<div class="section-jumps">
			{#each MOCK_DATA.sections as sec}
				<button class="section-btn" onclick={() => jumpTo(sec.start_sec)} title={sec.notes ?? ''}>
					{sec.type.replace('_', ' ')}
				</button>
			{/each}
		</div>
	</section>

	<section class="status">
		<h2>What works in v0.1</h2>
		<ul>
			<li>✅ SvelteKit 2 + Svelte 5 + Vite 5 + Tailwind-ready</li>
			<li>✅ Pixi.js v8 gem grid with pitch-aware positioning</li>
			<li>✅ Mock data for a 195s bachata at 128 BPM (mambo, majae, soneo, puente, breakdown)</li>
			<li>✅ Section chips above the grid (clickable to jump)</li>
			<li>✅ Musicality curves below (energy, onset density, bass RMS, vocal activity)</li>
			<li>✅ Playhead + transport controls</li>
			<li>⏳ Phase 1: real Demucs stem separation + Beat-Transformer + Whisper pipeline</li>
			<li>⏳ Phase 1: replace mock data with <code>fetch('/api/songs/:id/analysis')</code></li>
		</ul>
	</section>
</main>

<style>
	main {
		max-width: 1200px;
		margin: 0 auto;
		padding: 24px 20px 80px;
		display: flex;
		flex-direction: column;
		gap: 32px;
	}
	header {
		display: flex;
		justify-content: space-between;
		align-items: center;
	}
	.logo {
		display: flex;
		gap: 8px;
		align-items: center;
		font-size: 20px;
		font-weight: 600;
	}
	.logo-mark {
		font-size: 24px;
		color: var(--accent);
	}
	.tagline {
		color: var(--muted);
		font-size: 13px;
	}
	.hero h1 {
		font-size: 44px;
		line-height: 1.1;
		margin: 0 0 12px;
		font-weight: 700;
		letter-spacing: -0.02em;
	}
	.hero h1 .accent { color: var(--accent); }
	.hero p {
		font-size: 16px;
		line-height: 1.5;
		max-width: 720px;
		color: #d0d0d0;
	}
	.muted { color: var(--muted); }
	.visualizer {
		display: flex;
		flex-direction: column;
		gap: 12px;
	}
	.controls {
		display: flex;
		align-items: center;
		gap: 12px;
	}
	.play {
		width: 44px;
		height: 44px;
		border-radius: 50%;
		border: none;
		background: var(--accent);
		color: white;
		font-size: 16px;
		cursor: pointer;
	}
	.play:hover { filter: brightness(1.1); }
	.controls input[type=range] {
		flex: 1;
		accent-color: var(--accent);
	}
	.time { color: var(--muted); font-variant-numeric: tabular-nums; font-size: 13px; min-width: 90px; }
	.section-jumps {
		display: flex;
		flex-wrap: wrap;
		gap: 6px;
	}
	.section-btn {
		background: #1a1a1a;
		border: 1px solid #2a2a2a;
		color: #ccc;
		padding: 6px 12px;
		border-radius: 4px;
		font-size: 12px;
		cursor: pointer;
		text-transform: capitalize;
	}
	.section-btn:hover { background: #2a2a2a; color: white; }
	.status {
		background: #0f0f0f;
		border: 1px solid #1a1a1a;
		border-radius: 8px;
		padding: 20px 24px;
	}
	.status h2 { margin-top: 0; font-size: 18px; }
	.status ul { padding-left: 20px; }
	.status li { margin: 4px 0; font-size: 14px; color: #d0d0d0; }
	code { background: #1a1a1a; padding: 1px 6px; border-radius: 3px; font-size: 12px; }
</style>
