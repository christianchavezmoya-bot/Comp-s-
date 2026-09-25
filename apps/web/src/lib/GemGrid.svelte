<!--
	GemGrid — the core visualization.
	Renders one vertical lane per stem, with each instrument onset as a gem
	diamond positioned by (time, pitch). Section ribbons above, musicality
	curves below. Bars are aligned to the 8-count.
-->
<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import * as PIXI from 'pixi.js';
	import type { Gem, GemGridData, Section, StemKind } from '@compas/shared-types';

	interface Props {
		data: GemGridData;
		playheadSec?: number;
		loopA?: number | null;
		loopB?: number | null;
		onSeek?: (sec: number) => void;
	}

	let { data, playheadSec = 0, loopA = null, loopB = null, onSeek }: Props = $props();

	let containerEl: HTMLDivElement;
	let app: PIXI.Application | null = null;
	let gemLayer: PIXI.Container | null = null;
	let sectionLayer: PIXI.Container | null = null;
	let playheadLayer: PIXI.Container | null = null;
	let resizeObs: ResizeObserver | null = null;

	const STEM_COLORS: Record<StemKind, number> = {
		vocals_lead: 0xec4899,
		vocals_back: 0xf472b6,
		requinto: 0x2dd4bf,
		segunda: 0x38bdf8,
		bass: 0xfb923c,
		bongo: 0xa3e635,
		guira: 0xfacc15,
		clave: 0xa78bfa,
		palmas: 0x94a3b8,
		tambora: 0x84cc16,
		synth: 0x818cf8,
		horns: 0xf87171,
		piano: 0x60a5fa,
		congas: 0xfbbf24,
		timbales: 0xfde047,
		cowbell: 0xfb923c,
		maracas: 0xd4d4d8,
		guiro: 0xe5e7eb
	};

	const STEM_LABELS: Record<StemKind, string> = {
		vocals_lead: 'Vocals',
		vocals_back: 'Backing',
		requinto: 'Requinto',
		segunda: 'Segunda',
		bass: 'Bass',
		bongo: 'Bongó',
		guira: 'Güira',
		clave: 'Clave',
		palmas: 'Palmas',
		tambora: 'Tambora',
		synth: 'Synth',
		horns: 'Horns',
		piano: 'Piano',
		congas: 'Congas',
		timbales: 'Timbales',
		cowbell: 'Cowbell',
		maracas: 'Maracas',
		guiro: 'Güiro'
	};

	const SECTION_COLORS: Record<string, number> = {
		intro: 0x4b5563,
		verso: 0x6366f1,
		pre_coro: 0x818cf8,
		coro: 0xec4899,
		mambo: 0xf97316,
		majae: 0xeab308,
		soneo: 0x22c55e,
		puente: 0x06b6d4,
		breakdown: 0xef4444,
		outro: 0x6b7280,
		coro_pregon: 0x818cf8,
		montuno: 0x10b981,
		mambo_sub: 0xf97316,
		diablo_sub: 0xdc2626,
		mona_sub: 0xeab308,
		especial_sub: 0x8b5cf6,
		coda: 0x6b7280
	};

	// Layout constants
	const SEC_PER_8COUNT = (60 / data.bpm) * 8;
	const LANE_HEIGHT = 70;
	const LANE_GAP = 4;
	const SECTION_HEADER = 28;
	const MUSICALITY_HEIGHT = 70;
	const HEADER_HEIGHT = 40;
	const TIME_PX_PER_SEC = 12; // zoom level; user can adjust

	let layout = $derived({
		width: 0,
		height: 0,
		laneCount: data.stems.length,
		laneHeight: LANE_HEIGHT,
		laneGap: LANE_GAP,
		timePxPerSec: TIME_PX_PER_SEC,
		totalWidth: data.duration_sec * TIME_PX_PER_SEC
	});

	function timeToX(t: number): number {
		return t * layout.timePxPerSec;
	}

	function pitchToY(stemIdx: number, pitchMidi?: number): number {
		// Default: center of the lane. If pitch is given, offset from center
		const baseY = HEADER_HEIGHT + SECTION_HEADER + stemIdx * (LANE_HEIGHT + LANE_GAP) + LANE_HEIGHT / 2;
		if (pitchMidi === undefined) return baseY;
		// Map pitch deviation from a per-stem base
		const baseMap: Partial<Record<StemKind, number>> = {
			bass: 36,
			requinto: 60,
			segunda: 48,
			bongo: 56,
			guira: 76,
			clave: 70,
			vocals_lead: 65,
			vocals_back: 60
		};
		const base = baseMap[data.stems[stemIdx] as StemKind] ?? 60;
		const deviation = (pitchMidi - base) / 12; // octaves
		return baseY - deviation * (LANE_HEIGHT / 4);
	}

	function drawGem(g: PIXI.Graphics, x: number, y: number, size: number, color: number, strength: number, isHit: boolean) {
		// Diamond shape
		const s = size * (0.6 + strength * 0.4);
		g.clear();
		g.beginFill(color, isHit ? 1.0 : 0.6 + strength * 0.4);
		if (isHit) {
			g.lineStyle(2, 0xffffff, 0.9);
		}
		g.moveTo(x, y - s);
		g.lineTo(x + s, y);
		g.lineTo(x, y + s);
		g.lineTo(x - s, y);
		g.closePath();
		g.endFill();
	}

	function drawSections() {
		if (!sectionLayer) return;
		sectionLayer.removeChildren();
		for (const sec of data.sections) {
			const x = timeToX(sec.start_sec);
			const w = Math.max(2, timeToX(sec.end_sec) - x);
			const color = SECTION_COLORS[sec.type] ?? 0x666666;

			// Background band across all lanes
			const band = new PIXI.Graphics();
			band.beginFill(color, 0.06);
			band.drawRect(x, HEADER_HEIGHT, w, layout.laneCount * (LANE_HEIGHT + LANE_GAP) + SECTION_HEADER);
			band.endFill();
			sectionLayer.addChild(band);

			// Header chip
			const chip = new PIXI.Graphics();
			chip.beginFill(color, 0.85);
			chip.drawRoundedRect(x + 2, HEADER_HEIGHT + 4, Math.max(20, Math.min(w - 4, 110)), SECTION_HEADER - 8, 4);
			chip.endFill();
			sectionLayer.addChild(chip);

			const label = new PIXI.Text({
				text: sec.type.replace('_', ' ').toUpperCase(),
				style: { fontFamily: 'system-ui, -apple-system, sans-serif', fontSize: 10, fontWeight: '600', fill: 0x0a0a0a }
			});
			label.x = x + 8;
			label.y = HEADER_HEIGHT + 8;
			sectionLayer.addChild(label);
		}
	}

	function drawGems() {
		if (!gemLayer) return;
		gemLayer.removeChildren();
		// Pre-allocate a single Graphics and re-use
		const g = new PIXI.Graphics();
		for (const gem of data.gems) {
			const stemIdx = data.stems.indexOf(gem.stem);
			if (stemIdx < 0) continue;
			const x = timeToX(gem.time_sec);
			const y = pitchToY(stemIdx, gem.pitch_midi);
			const color = STEM_COLORS[gem.stem] ?? 0xffffff;
			drawGem(g, x, y, 4, color, gem.strength, gem.is_hit);
		}
		gemLayer.addChild(g);
	}

	function drawLaneLabels() {
		if (!gemLayer) return;
		for (let i = 0; i < data.stems.length; i++) {
			const stem = data.stems[i];
			const y = HEADER_HEIGHT + SECTION_HEADER + i * (LANE_HEIGHT + LANE_GAP) + LANE_HEIGHT / 2;
			const label = new PIXI.Text({
				text: STEM_LABELS[stem] ?? stem,
				style: { fontFamily: 'system-ui, -apple-system, sans-serif', fontSize: 11, fontWeight: '500', fill: 0xcccccc }
			});
			label.x = 8;
			label.y = y - 6;
			// Anchor on a non-scrolling layer via parent
			(app as any)._labelLayer.addChild(label);
		}
	}

	function drawLaneBackgrounds() {
		if (!gemLayer) return;
		for (let i = 0; i < data.stems.length; i++) {
			const y = HEADER_HEIGHT + SECTION_HEADER + i * (LANE_HEIGHT + LANE_GAP);
			const bg = new PIXI.Graphics();
			const color = STEM_COLORS[data.stems[i] as StemKind] ?? 0x333333;
			bg.beginFill(color, 0.04);
			bg.drawRect(0, y, layout.totalWidth, LANE_HEIGHT);
			bg.endFill();
			bg.lineStyle(1, 0x1a1a1a, 1);
			bg.moveTo(0, y + LANE_HEIGHT);
			bg.lineTo(layout.totalWidth, y + LANE_HEIGHT);
			bg.stroke();
			gemLayer.addChild(bg);
		}
	}

	function drawBarGrid() {
		if (!gemLayer) return;
		const g = new PIXI.Graphics();
		g.lineStyle(1, 0x222222, 1);
		// 8-count boundaries (heavy), 4-count (medium), beats (light)
		for (let t = data.first_8count_sec; t <= data.duration_sec; t += SEC_PER_8COUNT) {
			const x = timeToX(t);
			g.moveTo(x, HEADER_HEIGHT);
			g.lineTo(x, HEADER_HEIGHT + layout.laneCount * (LANE_HEIGHT + LANE_GAP) + MUSICALITY_HEIGHT);
		}
		g.stroke({ width: 1, color: 0x2a2a2a, alpha: 0.6 });
		gemLayer.addChild(g);
	}

	function drawPlayhead() {
		if (!playheadLayer) return;
		playheadLayer.removeChildren();
		const g = new PIXI.Graphics();
		const x = timeToX(playheadSec);
		g.lineStyle(2, 0xffffff, 0.9);
		g.moveTo(x, HEADER_HEIGHT);
		g.lineTo(x, HEADER_HEIGHT + layout.laneCount * (LANE_HEIGHT + LANE_GAP) + MUSICALITY_HEIGHT);
		g.stroke();
		// Top indicator triangle
		g.beginFill(0xffffff, 1);
		g.moveTo(x - 6, HEADER_HEIGHT - 2);
		g.lineTo(x + 6, HEADER_HEIGHT - 2);
		g.lineTo(x, HEADER_HEIGHT + 6);
		g.closePath();
		g.endFill();
		playheadLayer.addChild(g);
	}

	function drawMusicalityStrip() {
		if (!gemLayer) return;
		const yBase = HEADER_HEIGHT + SECTION_HEADER + layout.laneCount * (LANE_HEIGHT + LANE_GAP);
		const g = new PIXI.Graphics();
		// Background
		g.beginFill(0x0f0f0f, 1);
		g.drawRect(0, yBase, layout.totalWidth, MUSICALITY_HEIGHT);
		g.endFill();

		const curves = [
			{ key: 'energy', color: 0xffffff, alpha: 0.6 },
			{ key: 'onset_density', color: 0x4f9eff, alpha: 0.7 },
			{ key: 'bass_rms', color: 0xfb923c, alpha: 0.7 },
			{ key: 'vocal_activity', color: 0xec4899, alpha: 0.7 }
		] as const;

		for (const curve of curves) {
			const data_arr = (data.musicality as any)[curve.key] as number[];
			if (!data_arr) continue;
			g.lineStyle(1.5, curve.color, curve.alpha);
			for (let i = 0; i < data_arr.length - 1; i++) {
				const x1 = timeToX(i * SEC_PER_8COUNT);
				const x2 = timeToX((i + 1) * SEC_PER_8COUNT);
				const y1 = yBase + MUSICALITY_HEIGHT - data_arr[i] * MUSICALITY_HEIGHT;
				const y2 = yBase + MUSICALITY_HEIGHT - data_arr[i + 1] * MUSICALITY_HEIGHT;
				g.moveTo(x1, y1);
				g.lineTo(x2, y2);
			}
			g.stroke();
		}
		gemLayer.addChild(g);
	}

	function drawLoop() {
		if (!gemLayer) return;
		// Remove old loop markers
		const toRemove: any[] = [];
		(gemLayer.children as any[]).forEach((c) => {
			if (c._isLoopMarker) toRemove.push(c);
		});
		toRemove.forEach((c) => gemLayer!.removeChild(c));
		if (loopA === null && loopB === null) return;
		const g = new PIXI.Graphics();
		;(g as any)._isLoopMarker = true;
		if (loopA !== null) {
			const x = timeToX(loopA);
			g.lineStyle(2, 0xfbbf24, 0.9);
			g.moveTo(x, HEADER_HEIGHT);
			g.lineTo(x, HEADER_HEIGHT + layout.laneCount * (LANE_HEIGHT + LANE_GAP) + MUSICALITY_HEIGHT);
			g.stroke();
		}
		if (loopB !== null) {
			const x = timeToX(loopB);
			g.lineStyle(2, 0xfbbf24, 0.9);
			g.moveTo(x, HEADER_HEIGHT);
			g.lineTo(x, HEADER_HEIGHT + layout.laneCount * (LANE_HEIGHT + LANE_GAP) + MUSICALITY_HEIGHT);
			g.stroke();
		}
		if (loopA !== null && loopB !== null && loopB > loopA) {
			const x1 = timeToX(loopA);
			const x2 = timeToX(loopB);
			g.beginFill(0xfbbf24, 0.07);
			g.drawRect(
				x1,
				HEADER_HEIGHT,
				x2 - x1,
				layout.laneCount * (LANE_HEIGHT + LANE_GAP) + MUSICALITY_HEIGHT
			);
			g.endFill();
		}
		gemLayer.addChild(g);
	}

	function redraw() {
		if (!app) return;
		drawLaneBackgrounds();
		drawBarGrid();
		drawSections();
		drawGems();
		drawMusicalityStrip();
		drawLaneLabels();
		drawPlayhead();
		drawLoop();
	}

	onMount(async () => {
		app = new PIXI.Application();
		await app.init({
			background: 0x0a0a0a,
			resizeTo: containerEl,
			antialias: true,
			autoDensity: true,
			resolution: window.devicePixelRatio || 1
		});
		containerEl.appendChild(app.canvas);

		gemLayer = new PIXI.Container();
		sectionLayer = new PIXI.Container();
		playheadLayer = new PIXI.Container();
		(app as any)._labelLayer = new PIXI.Container();

		app.stage.addChild(gemLayer);
		app.stage.addChild(sectionLayer);
		app.stage.addChild((app as any)._labelLayer);
		app.stage.addChild(playheadLayer);

		// click-to-seek on the canvas
		app.canvas.addEventListener('click', (ev) => {
			if (!onSeek) return;
			const rect = (ev.target as HTMLElement).getBoundingClientRect();
			const scrollLeft = containerEl.scrollLeft;
			const x = ev.clientX - rect.left + scrollLeft;
			const t = x / layout.timePxPerSec;
			onSeek(Math.max(0, Math.min(data.duration_sec, t)));
		});

		redraw();

		resizeObs = new ResizeObserver(() => {
			if (app) app.renderer.resize(containerEl.clientWidth, containerEl.clientHeight);
		});
		resizeObs.observe(containerEl);
	});

	onDestroy(() => {
		resizeObs?.disconnect();
		app?.destroy(true, { children: true });
	});

	$effect(() => {
		// re-draw on playhead change
		void playheadSec;
		drawPlayhead();
	});

	$effect(() => {
		// re-draw on loop change
		void loopA;
		void loopB;
		drawLoop();
	});
</script>

<div class="grid-wrap">
	<div class="meta">
		<div class="title">Volar <span class="muted">· sP Polanco · demo</span></div>
		<div class="stats">
			<span class="pill">{data.bpm} BPM</span>
			<span class="pill">{data.duration_sec.toFixed(0)}s</span>
			<span class="pill muted">bachata · 8-count</span>
		</div>
	</div>
	<div class="canvas-host" bind:this={containerEl}></div>
	<div class="legend">
		{#each data.stems as stem}
			<span class="legend-item">
				<span class="dot" style="background: #{STEM_COLORS[stem].toString(16).padStart(6, '0')}"></span>
				{STEM_LABELS[stem] ?? stem}
			</span>
		{/each}
	</div>
</div>

<style>
	.grid-wrap {
		display: flex;
		flex-direction: column;
		gap: 8px;
		padding: 16px;
		background: #0a0a0a;
		border-radius: 8px;
		border: 1px solid #1f1f1f;
	}
	.meta {
		display: flex;
		justify-content: space-between;
		align-items: center;
	}
	.title {
		font-size: 20px;
		font-weight: 600;
	}
	.muted { color: var(--muted); font-weight: 400; }
	.stats { display: flex; gap: 6px; }
	.pill {
		background: #1a1a1a;
		border: 1px solid #2a2a2a;
		border-radius: 999px;
		padding: 4px 10px;
		font-size: 12px;
		font-weight: 500;
	}
	.canvas-host {
		width: 100%;
		height: 380px;
		background: #050505;
		border-radius: 6px;
		overflow-x: auto;
		overflow-y: hidden;
		border: 1px solid #1a1a1a;
	}
	.legend {
		display: flex;
		flex-wrap: wrap;
		gap: 12px;
		font-size: 12px;
		color: #ccc;
	}
	.legend-item { display: inline-flex; align-items: center; gap: 6px; }
	.dot { display: inline-block; width: 10px; height: 10px; border-radius: 2px; transform: rotate(45deg); }
</style>
