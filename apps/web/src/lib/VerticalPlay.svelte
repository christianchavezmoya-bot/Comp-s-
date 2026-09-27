<!--
	VerticalPlay — the dance-practice visualization.

	Layout:
	  - Time flows from BOTTOM to TOP.
	  - Each instrument has a horizontal LANE.
	  - The PLAYHEAD is a horizontal line near the BOTTOM of the panel.
	  - Gems scroll UPWARD as time advances.
	  - When a gem reaches the playhead, it "lights up" (glow + scale pulse + flash).

	Why this is the killer dance practice tool:
	  - Your eye sees "what's coming" (gems approaching the line) and "what just hit" (lit gems just above the line).
	  - The 8-count grid lines scroll past, so you can feel the rhythm visually.
	  - Dancers can practice "step on the beat" by watching when a gem lights up.

	Use:
	  <VerticalPlay
	    data={visualizerData}
	    playheadSec={playhead}
	    onSeek={setPlayhead}
	    visibleStems={['requinto','bongo','bass','guira']}
	  />
-->
<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import * as PIXI from 'pixi.js';
	import type { Gem, Section, StemKind, GemGridData, MusicalityCurves } from '@compas/shared-types';

	interface Props {
		data: GemGridData;
		playheadSec: number;
		visibleStems: StemKind[];
		/** Time window shown above the playhead (in seconds) */
		lookahead?: number;
		/** Pixels per second — controls the scroll speed feel */
		pxPerSec?: number;
		onSeek?: (sec: number) => void;
	}

	let {
		data,
		playheadSec,
		visibleStems,
		lookahead = 4.0,
		pxPerSec = 120,
		onSeek
	}: Props = $props();

	let containerEl: HTMLDivElement;
	let app: PIXI.Application | null = null;
	let gemLayer: PIXI.Container | null = null;
	let gridLayer: PIXI.Container | null = null;
	let playheadLayer: PIXI.Container | null = null;
	let glowLayer: PIXI.Container | null = null;
	let resizeObs: ResizeObserver | null = null;

	// Lane configuration
	const HEADER_HEIGHT = 36;          // top section ribbon
	const TRANSPORT_RESERVE = 0;        // playhead anchored to bottom
	const PLAYHEAD_OFFSET_FROM_BOTTOM = 90; // px above bottom edge
	const LANE_GAP = 4;

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

	// Build the gem list filtered to visible stems
	type GemWithPos = Gem & { _lit: number };
	let allGems: GemWithPos[] = $derived(
		data.gems
			.filter((g) => visibleStems.includes(g.stem))
			.map((g) => ({ ...g, _lit: 0 }))
	);

	// Find which gems are "near" the playhead (for lighting effect)
	function litGemsAt(playhead: number, nowMs: number): Set<number> {
		// A gem is "lit" when its time is within ±0.1s of the playhead
		const ids = new Set<number>();
		for (let i = 0; i < allGems.length; i++) {
			const g = allGems[i];
			if (Math.abs(g.time_sec - playhead) < 0.12) {
				ids.add(i);
			}
		}
		return ids;
	}

	function yForTime(t: number, currentPlayhead: number, h: number, ppsec: number): number {
		// Time t in seconds, with currentPlayhead at the playhead line
		// Playhead is at h - PLAYHEAD_OFFSET_FROM_BOTTOM
		const playheadY = h - PLAYHEAD_OFFSET_FROM_BOTTOM;
		const dt = t - currentPlayhead; // negative = past, positive = future
		return playheadY - dt * ppsec;
	}

	// ====== PIXI setup ======
	onMount(async () => {
		app = new PIXI.Application();
		await app.init({
			background: 0x050505,
			resizeTo: containerEl,
			antialias: true,
			autoDensity: true,
			resolution: window.devicePixelRatio || 1
		});
		containerEl.appendChild(app.canvas);

		gridLayer = new PIXI.Container();
		gemLayer = new PIXI.Container();
		glowLayer = new PIXI.Container();
		playheadLayer = new PIXI.Container();

		app.stage.addChild(gridLayer);
		app.stage.addChild(gemLayer);
		app.stage.addChild(glowLayer);
		app.stage.addChild(playheadLayer);

		// Click anywhere in the play area → seek
		app.canvas.addEventListener('click', (ev) => {
			if (!onSeek) return;
			const rect = (ev.target as HTMLElement).getBoundingClientRect();
			const y = ev.clientY - rect.top;
			const h = rect.height;
			const playheadY = h - PLAYHEAD_OFFSET_FROM_BOTTOM;
			const dtSec = (playheadY - y) / pxPerSec;
			const target = playheadSec + dtSec;
			onSeek(Math.max(0, Math.min(data.duration_sec, target)));
		});

		resizeObs = new ResizeObserver(() => {
			if (app) app.renderer.resize(containerEl.clientWidth, containerEl.clientHeight);
		});
		resizeObs.observe(containerEl);
	});

	onDestroy(() => {
		resizeObs?.disconnect();
		app?.destroy(true, { children: true });
	});

	// ====== Per-frame draw ======
	let lastDraw = 0;
	function drawFrame(now: number) {
		if (!app || !gemLayer) return;
		if (now - lastDraw < 16) {
			requestAnimationFrame(drawFrame);
			return;
		}
		lastDraw = now;

		const w = app.renderer.width / (window.devicePixelRatio || 1);
		const h = app.renderer.height / (window.devicePixelRatio || 1);
		const playheadY = h - PLAYHEAD_OFFSET_FROM_BOTTOM;
		const laneCount = visibleStems.length;
		const laneH = (playheadY - HEADER_HEIGHT - 4) / Math.max(1, laneCount);

		// Clear all layers (we redraw everything each frame; cheap enough for ~1000 gems)
		gridLayer.removeChildren();
		gemLayer.removeChildren();
		glowLayer.removeChildren();
		playheadLayer.removeChildren();

		// ===== Grid layer =====
		const gGrid = new PIXI.Graphics();

		// Section ribbons at the top (clipped to the visible window)
		for (const sec of data.sections) {
			// The section header ribbon
			const color = SECTION_COLORS[sec.type] ?? 0x666666;
			const ribbonH = 24;
			const ySecTop = 4;
			// Draw the section header text
			const ribbonGfx = new PIXI.Graphics();
			ribbonGfx.beginFill(color, 0.85);
			ribbonGfx.drawRoundedRect(8, ySecTop, 110, ribbonH, 4);
			ribbonGfx.endFill();
			gridLayer.addChild(ribbonGfx);
			const label = new PIXI.Text({
				text: sec.type.replace('_', ' ').toUpperCase(),
				style: {
					fontFamily: 'system-ui, -apple-system, sans-serif',
					fontSize: 10,
					fontWeight: '600',
					fill: 0x0a0a0a
				}
			});
			label.x = 16;
			label.y = ySecTop + 8;
			gridLayer.addChild(label);
		}

		// Lane separators
		for (let i = 0; i <= laneCount; i++) {
			const y = HEADER_HEIGHT + i * laneH;
			gGrid.lineStyle(1, 0x1a1a1a, 1);
			gGrid.moveTo(0, y);
			gGrid.lineTo(w, y);
			gGrid.stroke();
		}

		// Lane labels on the right edge
		for (let i = 0; i < laneCount; i++) {
			const stem = visibleStems[i];
			const y = HEADER_HEIGHT + i * laneH + laneH / 2;
			const lbl = new PIXI.Text({
				text: STEM_LABELS[stem] ?? stem,
				style: {
					fontFamily: 'system-ui, -apple-system, sans-serif',
					fontSize: 11,
					fontWeight: '500',
					fill: 0xaaaaaa
				}
			});
			lbl.x = w - 80;
			lbl.y = y - 6;
			lbl.alpha = 0.6;
			gridLayer.addChild(lbl);

			// Lane color stripe (left edge)
			const color = STEM_COLORS[stem] ?? 0x444444;
			const stripe = new PIXI.Graphics();
			stripe.beginFill(color, 0.4);
			stripe.drawRect(0, HEADER_HEIGHT + i * laneH + 2, 3, laneH - 4);
			stripe.endFill();
			gridLayer.addChild(stripe);
		}

		// Time grid lines (8-count lines scroll past the playhead)
		// We draw lines at every beat (8 per 8-count) from playhead - lookahead to playhead + small behind
		const secPerBeat = 60.0 / (data.bpm || 128);
		const playheadX = w / 2; // for now, center the playhead
		// Vertical lines showing beats coming up
		for (let t = -1.0; t < lookahead + 0.1; t += secPerBeat) {
			const y = yForTime(playheadSec + t, playheadSec, h, pxPerSec);
			if (y < HEADER_HEIGHT || y > h) continue;
			const isOnBeat = Math.abs(t / secPerBeat - Math.round(t / secPerBeat)) < 0.01;
			const isOnDownbeat = Math.abs((t / secPerBeat) % 4) < 0.01;
			const color = isOnDownbeat ? 0x4f9eff : isOnBeat ? 0x333333 : 0x1a1a1a;
			const alpha = isOnDownbeat ? 0.6 : isOnBeat ? 0.4 : 0.25;
			const width = isOnDownbeat ? 2 : 1;
			gGrid.lineStyle(width, color, alpha);
			gGrid.moveTo(0, y);
			gGrid.lineTo(w, y);
			gGrid.stroke();
		}

		gridLayer.addChild(gGrid);

		// ===== Gem layer =====
		// Time window: from (playhead - 0.5s) to (playhead + lookahead)
		const tStart = playheadSec - 0.5;
		const tEnd = playheadSec + lookahead + 0.5;

		// Bin by stem
		const gemsByStem: Record<number, GemWithPos[]> = {};
		for (let i = 0; i < allGems.length; i++) {
			const g = allGems[i];
			if (g.time_sec < tStart || g.time_sec > tEnd) continue;
			const stemIdx = visibleStems.indexOf(g.stem);
			if (stemIdx < 0) continue;
			(gemsByStem[stemIdx] ??= []).push({ ...g, _lit: i });
		}

		const gemsGfx = new PIXI.Graphics();
		const litIds = litGemsAt(playheadSec, performance.now());

		for (let i = 0; i < visibleStems.length; i++) {
			const stem = visibleStems[i];
			const color = STEM_COLORS[stem] ?? 0xffffff;
			const laneY = HEADER_HEIGHT + i * laneH;
			const laneMidY = laneY + laneH / 2;
			const stemGems = gemsByStem[i] ?? [];
			for (const g of stemGems) {
				const y = yForTime(g.time_sec, playheadSec, h, pxPerSec);
				// Skip if off-screen
				if (y < HEADER_HEIGHT - 20 || y > h + 20) continue;
				const isLit = litIds.has(g._lit);
				const distFromPlayhead = Math.abs(g.time_sec - playheadSec);
				// Size grows as gem approaches playhead (subtle, but reinforces the "incoming" feel)
				let size = 7;
				if (distFromPlayhead < 0.5) {
					size = 7 + (0.5 - distFromPlayhead) * 6; // 7..10
				}
				if (isLit) {
					size = 18; // big pulse on hit
				}
				const alpha = isLit ? 1.0 : 0.55 + (1.0 - distFromPlayhead / lookahead) * 0.45;
				drawDiamond(gemsGfx, w / 2, y, size, color, alpha, isLit);
			}
		}
		gemLayer.addChild(gemsGfx);

		// ===== Glow layer (radial light behind lit gems) =====
		const glowGfx = new PIXI.Graphics();
		for (let i = 0; i < visibleStems.length; i++) {
			const stemGems = gemsByStem[i] ?? [];
			for (const g of stemGems) {
				if (!litIds.has(g._lit)) continue;
				const y = yForTime(g.time_sec, playheadSec, h, pxPerSec);
				const color = STEM_COLORS[g.stem] ?? 0xffffff;
				// Radial glow (concentric circles, decreasing alpha)
				for (let r = 18; r > 4; r -= 3) {
					const alpha = 0.04 * (1 - (r - 4) / 14);
					glowGfx.beginFill(color, alpha);
					glowGfx.drawCircle(w / 2, y, r);
					glowGfx.endFill();
				}
			}
		}
		glowLayer.addChild(glowGfx);

		// ===== Playhead layer =====
		const phGfx = new PIXI.Graphics();
		// Main line
		phGfx.lineStyle(3, 0xffffff, 0.9);
		phGfx.moveTo(0, playheadY);
		phGfx.lineTo(w, playheadY);
		phGfx.stroke();
		// Glow under the playhead (subtle)
		for (let r = 30; r > 0; r -= 3) {
			phGfx.beginFill(0xffffff, 0.02);
			phGfx.drawRect(0, playheadY - r, w, r * 2);
			phGfx.endFill();
		}
		// "NOW" label
		const nowLabel = new PIXI.Text({
			text: 'NOW',
			style: {
				fontFamily: 'system-ui, -apple-system, sans-serif',
				fontSize: 10,
				fontWeight: '700',
				fill: 0xffffff,
				letterSpacing: 2
			}
		});
		nowLabel.x = 8;
		nowLabel.y = playheadY + 4;
		playheadLayer.addChild(phGfx);
		playheadLayer.addChild(nowLabel);

		requestAnimationFrame(drawFrame);
	}

	function drawDiamond(g: PIXI.Graphics, x: number, y: number, size: number, color: number, alpha: number, lit: boolean) {
		const s = size;
		g.beginFill(color, lit ? 1.0 : alpha);
		if (lit) {
			g.lineStyle(2, 0xffffff, 0.95);
		} else {
			g.lineStyle(1, 0xffffff, alpha * 0.4);
		}
		g.moveTo(x, y - s);
		g.lineTo(x + s, y);
		g.lineTo(x, y + s);
		g.lineTo(x - s, y);
		g.closePath();
		g.endFill();
		if (lit) {
			// White core on hit
			g.beginFill(0xffffff, 0.9);
			g.drawCircle(x, y, 3);
			g.endFill();
		}
	}

	$effect(() => {
		// Kick off the rAF loop on mount
		void playheadSec; // track
		if (app) {
			requestAnimationFrame(drawFrame);
		}
	});
</script>

<div class="vp-host" bind:this={containerEl}>
	{#if visibleStems.length === 0}
		<div class="empty">No stems visible. Toggle stems below.</div>
	{/if}
</div>

<style>
	.vp-host {
		position: relative;
		width: 100%;
		height: 100%;
		min-height: 380px;
		max-height: 600px;
		background: #050505;
		border-radius: 8px;
		border: 1px solid #1a1a1a;
		overflow: hidden;
	}
	.empty {
		position: absolute;
		inset: 0;
		display: flex;
		align-items: center;
		justify-content: center;
		color: #666;
		font-size: 13px;
	}
	.vp-host :global(canvas) {
		display: block;
	}
</style>
