/**
 * Mock data for the gem-grid prototype.
 * Synthesizes a realistic-looking 128 BPM bachata analysis so the
 * visualization is testable before we have the real ML pipeline.
 *
 * This is a development-only file. The real flow will:
 *   fetch('/api/songs/{id}/analysis') → SongAnalysis → GemGridData
 */

import type { Gem, GemGridData, Section, StemKind, MusicalityCurves } from '@compas/shared-types';

const BPM = 128;
const SEC_PER_BEAT = 60 / BPM; // ~0.469s
const SEC_PER_8COUNT = SEC_PER_BEAT * 8; // ~3.75s
const DURATION = 195; // 3:15

const STEMS_ORDER: StemKind[] = [
	'vocals_lead',
	'vocals_back',
	'requinto',
	'segunda',
	'bass',
	'bongo',
	'guira',
	'clave'
];

// Mock sections following the locked bachata taxonomy (§1.2)
const SECTIONS: Section[] = [
	{ start_sec: 0, end_sec: 7.5, type: 'intro', confidence: 'high' },
	{ start_sec: 7.5, end_sec: 30, type: 'verso', confidence: 'high' },
	{ start_sec: 30, end_sec: 41.25, type: 'pre_coro', confidence: 'med' },
	{ start_sec: 41.25, end_sec: 63.75, type: 'coro', confidence: 'high' },
	{ start_sec: 63.75, end_sec: 67.5, type: 'mambo', confidence: 'high', notes: 'vocal break + bass fill' },
	{ start_sec: 67.5, end_sec: 90, type: 'coro', confidence: 'high' },
	{ start_sec: 90, end_sec: 101.25, type: 'majae', confidence: 'high', notes: 'open position section' },
	{ start_sec: 101.25, end_sec: 135, type: 'soneo', confidence: 'high', notes: 'vocal improv' },
	{ start_sec: 135, end_sec: 143, type: 'puente', confidence: 'med', notes: 'chord change' },
	{ start_sec: 143, end_sec: 146, type: 'breakdown', confidence: 'high' },
	{ start_sec: 146, end_sec: 183.75, type: 'coro', confidence: 'high' },
	{ start_sec: 183.75, end_sec: 195, type: 'outro', confidence: 'high' }
];

function rand(seed: number): () => number {
	let s = seed;
	return () => {
		s = (s * 9301 + 49297) % 233280;
		return s / 233280;
	};
}

function generateGems(): Gem[] {
	const r = rand(42);
	const gems: Gem[] = [];
	const stemDensity: Partial<Record<StemKind, { perBeat: number; pitchBase: number; pitchRange: number }>> = {
		requinto: { perBeat: 1, pitchBase: 60, pitchRange: 12 },
		segunda: { perBeat: 0.5, pitchBase: 48, pitchRange: 8 },
		bass: { perBeat: 0.25, pitchBase: 36, pitchRange: 4 }, // on 1 and 5
		bongo: { perBeat: 1, pitchBase: 56, pitchRange: 6 }, // martillo
		guira: { perBeat: 2, pitchBase: 76, pitchRange: 3 }, // 8th notes
		clave: { perBeat: 0.125, pitchBase: 70, pitchRange: 2 },
		vocals_lead: { perBeat: 0.6, pitchBase: 65, pitchRange: 12 },
		vocals_back: { perBeat: 0.4, pitchBase: 60, pitchRange: 8 }
	};

	let t = SEC_PER_BEAT;
	while (t < DURATION - 1) {
		// Find which section we're in to modulate density
		const sec = SECTIONS.find((s) => t >= s.start_sec && t < s.end_sec);
		const secMod = sec?.type === 'mambo' || sec?.type === 'majae' ? 1.4 : sec?.type === 'breakdown' ? 0.3 : sec?.type === 'outro' ? 0.7 : 1.0;

		for (const stem of STEMS_ORDER) {
			const cfg = stemDensity[stem];
			if (!cfg) continue;
			if (r() < cfg.perBeat * secMod * 0.5) {
				gems.push({
					time_sec: t + (r() - 0.5) * 0.04, // small jitter
					stem,
					pitch_midi: Math.round(cfg.pitchBase + r() * cfg.pitchRange),
					strength: 0.3 + r() * 0.7,
					is_hit: r() < 0.05
				});
			}
		}
		t += SEC_PER_BEAT / 2; // 8th-note grid
	}
	return gems;
}

function generateCurves(): MusicalityCurves {
	const bars = Math.ceil(DURATION / SEC_PER_8COUNT);
	const energy: number[] = [];
	const onset_density: number[] = [];
	const bass_rms: number[] = [];
	const vocal_activity: number[] = [];
	for (let i = 0; i < bars; i++) {
		const sec = SECTIONS.find((s) => i * SEC_PER_8COUNT >= s.start_sec && i * SEC_PER_8COUNT < s.end_sec);
		const baseE = sec?.type === 'coro' ? 0.85 : sec?.type === 'mambo' || sec?.type === 'majae' ? 0.9 : sec?.type === 'breakdown' ? 0.3 : 0.65;
		energy.push(baseE + (Math.sin(i * 1.7) * 0.1));
		onset_density.push((sec?.type === 'majae' ? 0.95 : 0.7) + (Math.cos(i * 2.3) * 0.1));
		bass_rms.push((sec?.type === 'mambo' ? 0.95 : 0.75) + (Math.sin(i * 0.9) * 0.1));
		vocal_activity.push((sec?.type === 'soneo' || sec?.type === 'verso' ? 0.9 : sec?.type === 'mambo' || sec?.type === 'breakdown' ? 0.2 : 0.7));
	}
	const r = rand(7);
	return {
		energy,
		onset_density,
		spectral_flux: energy.map((e) => e * 0.9 + r() * 0.1),
		bass_rms,
		vocal_activity,
		percussion_density: onset_density.map((d) => d * 0.95),
		hits: SECTIONS.flatMap((s) => [
			{ time_sec: s.start_sec, strength: 0.9, type: 'downbeat' as const },
			{ time_sec: s.start_sec + SEC_PER_8COUNT, strength: 0.6, type: 'accent' as const }
		])
	};
}

export const MOCK_DATA: GemGridData = {
	song_id: 'mock-bachata-001',
	duration_sec: DURATION,
	bpm: BPM,
	first_8count_sec: 0,
	gems: generateGems(),
	stems: STEMS_ORDER,
	sections: SECTIONS,
	musicality: generateCurves()
};
