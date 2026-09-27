<!--
	LyricsPanel — auto-scrolling lyrics with karaoke-style highlighting,
	translation, and tap-to-jump.
-->
<script lang="ts">
	import type { LyricSegment } from '@compas/shared-types';

	interface LyricAnalysis {
		language: string;
		segments: LyricSegment[];
	}

	interface Props {
		lyrics: LyricAnalysis | null | undefined;
		playheadSec: number;
		primaryTranslation?: string; // "en" or another lang code
		onSeek?: (sec: number) => void;
	}

	let { lyrics, playheadSec, primaryTranslation = 'en', onSeek }: Props = $props();

	let containerEl: HTMLDivElement;

	// Find the current line (the one the playhead is inside)
	let currentIdx = $derived.by(() => {
		if (!lyrics?.segments?.length) return -1;
		// Find the segment whose [start, end) contains the playhead
		for (let i = 0; i < lyrics.segments.length; i++) {
			const s = lyrics.segments[i];
			if (playheadSec >= s.start_sec && playheadSec < s.end_sec) {
				return i;
			}
		}
		// If past the last segment, use the last
		if (playheadSec >= (lyrics.segments[lyrics.segments.length - 1]?.end_sec ?? Infinity)) {
			return lyrics.segments.length - 1;
		}
		// Before the first, use the first
		return 0;
	});

	// Auto-scroll to keep current line visible
	$effect(() => {
		if (!containerEl) return;
		if (currentIdx < 0) return;
		const el = containerEl.querySelector(`[data-lyric-idx="${currentIdx}"]`) as HTMLElement | null;
		if (!el) return;
		const containerRect = containerEl.getBoundingClientRect();
		const elRect = el.getBoundingClientRect();
		// Only scroll if not in view
		if (elRect.top < containerRect.top || elRect.bottom > containerRect.bottom) {
			el.scrollIntoView({ behavior: 'smooth', block: 'center' });
		}
	});

	function jumpTo(seg: LyricSegment) {
		onSeek?.(seg.start_sec);
		(window as any).compasHaptic?.(8);
	}

	function colorForVocalType(t: string): string {
		switch (t) {
			case 'lead': return '#fce7f3';
			case 'backing': return '#fbcfe8';
			case 'coro': return '#f9a8d4';
			case 'soneo': return '#a7f3d0';
			case 'ad_lib': return '#fef3c7';
			case 'spoken': return '#e0e7ff';
			default: return '#fff';
		}
	}
</script>

<div class="lp" bind:this={containerEl}>
	{#if !lyrics || !lyrics.segments || lyrics.segments.length === 0}
		<div class="empty">
			<div>
				<div class="empty-title">No lyrics yet</div>
				<div class="empty-sub">Set <code>COMPAS_TRANSCRIBE=true</code> and re-analyze to get word-level lyrics with translation.</div>
			</div>
		</div>
	{:else}
		<div class="lang-bar">
			<span class="lang-label">Source: <strong>{lyrics.language.toUpperCase()}</strong></span>
			{#if lyrics.segments[0]?.translation}
				<span class="lang-label">Translation: <strong>{primaryTranslation.toUpperCase()}</strong></span>
			{/if}
		</div>
		<ol class="lines">
			{#each lyrics.segments as seg, i (i)}
				<li
					data-lyric-idx={i}
					class="line"
					class:current={i === currentIdx}
					class:past={i < currentIdx}
				>
					<button class="line-btn" onclick={() => jumpTo(seg)}>
						<div class="line-time">{formatTime(seg.start_sec)}</div>
						<div class="line-text" style="color: {colorForVocalType(seg.vocal_type)}">
							{seg.text}
							<span class="vocal-type">· {seg.vocal_type}</span>
						</div>
						{#if seg.translation && seg.translation[primaryTranslation]}
							<div class="line-translation">{seg.translation[primaryTranslation]}</div>
						{/if}
					</button>
				</li>
			{/each}
		</ol>
	{/if}
</div>

<script lang="ts" module>
	function formatTime(t: number): string {
		const m = Math.floor(t / 60);
		const s = Math.floor(t % 60);
		return `${m}:${s.toString().padStart(2, '0')}`;
	}
</script>

<style>
	.lp {
		display: flex;
		flex-direction: column;
		background: #0a0a0a;
		border-radius: 8px;
		border: 1px solid #1a1a1a;
		overflow: hidden;
		height: 100%;
	}
	.lang-bar {
		display: flex;
		justify-content: space-between;
		padding: 8px 14px;
		background: #0f0f0f;
		border-bottom: 1px solid #1a1a1a;
		font-size: 10px;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: #888;
	}
	.lang-label strong { color: #ccc; }
	.lines {
		list-style: none;
		padding: 12px 0;
		margin: 0;
		overflow-y: auto;
		scroll-behavior: smooth;
		flex: 1;
		max-height: 380px;
	}
	.line {
		padding: 0;
	}
	.line-btn {
		display: block;
		width: 100%;
		text-align: left;
		background: transparent;
		border: none;
		padding: 8px 16px;
		cursor: pointer;
		transition: background 0.15s ease;
	}
	.line-btn:hover { background: #0f0f0f; }
	.line-time {
		font-size: 10px;
		color: #666;
		font-variant-numeric: tabular-nums;
		margin-bottom: 2px;
	}
	.line-text {
		font-size: 16px;
		font-weight: 500;
		line-height: 1.3;
		color: #888;
	}
	.line.past .line-text { color: #666; }
	.line.current .line-text { color: #fff; font-weight: 600; }
	.line.current .line-btn {
		background: linear-gradient(90deg, rgba(236, 72, 153, 0.1) 0%, transparent 100%);
		border-left: 3px solid #ec4899;
		padding-left: 13px;
	}
	.vocal-type {
		font-size: 10px;
		color: #666;
		font-weight: 400;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		margin-left: 4px;
	}
	.line-translation {
		font-size: 13px;
		color: #888;
		font-style: italic;
		margin-top: 3px;
		line-height: 1.3;
	}
	.empty {
		flex: 1;
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 24px;
		text-align: center;
	}
	.empty-title {
		font-size: 14px;
		color: #888;
		margin-bottom: 6px;
	}
	.empty-sub {
		font-size: 12px;
		color: #555;
		max-width: 300px;
	}
	code { background: #1a1a1a; padding: 1px 4px; border-radius: 2px; font-size: 11px; }
</style>
