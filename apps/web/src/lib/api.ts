/**
 * API client.
 */
import type { Song, SongAnalysis } from '@compas/shared-types';

const API_BASE = ''; // relative; the dev server proxies /api to localhost:8000

export async function listSongs(): Promise<Song[]> {
	const r = await fetch(`${API_BASE}/api/library/songs`);
	if (!r.ok) throw new Error(`listSongs failed: ${r.status}`);
	return r.json();
}

export async function uploadSong(
	title: string,
	artist: string,
	genre: 'bachata' | 'salsa',
	audio: File
): Promise<Song> {
	const fd = new FormData();
	fd.append('title', title);
	fd.append('artist', artist);
	fd.append('genre', genre);
	fd.append('audio', audio);
	const r = await fetch(`${API_BASE}/api/library/songs`, { method: 'POST', body: fd });
	if (!r.ok) {
		const t = await r.text();
		throw new Error(`upload failed: ${r.status} ${t}`);
	}
	return r.json();
}

export async function deleteSong(id: string): Promise<void> {
	const r = await fetch(`${API_BASE}/api/library/songs/${id}`, { method: 'DELETE' });
	if (!r.ok) throw new Error(`delete failed: ${r.status}`);
}

export async function triggerAnalysis(id: string): Promise<{ status: string; song_id: string; version?: number }> {
	const r = await fetch(`${API_BASE}/api/analysis/songs/${id}/analyze`, { method: 'POST' });
	if (!r.ok) {
		const t = await r.text();
		throw new Error(`analyze failed: ${r.status} ${t}`);
	}
	return r.json();
}

export async function getAnalysis(id: string): Promise<{
	song_id: string;
	version: number;
	status: string;
	confidence_overall: number;
	result: SongAnalysis;
	created_at: string;
}> {
	const r = await fetch(`${API_BASE}/api/analysis/songs/${id}/latest`);
	if (!r.ok) {
		if (r.status === 404) throw new Error('No analysis yet');
		throw new Error(`getAnalysis failed: ${r.status}`);
	}
	return r.json();
}

export function audioUrl(songId: string): string {
	return `${API_BASE}/api/library/songs/${songId}/audio`;
}

export function stemUrl(songId: string, stem: string): string {
	return `${API_BASE}/api/library/songs/${songId}/stems/${stem}`;
}
