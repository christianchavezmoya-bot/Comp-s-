/**
 * Compás — shared types
 * Used by web (TypeScript) and a future mobile client.
 * The Python API serializes/deserializes to these shapes via Pydantic.
 *
 * Schema version: 1
 */

// ============================================================
// Genre & sections (locked per §1 of COMPAS_PLAN.md)
// ============================================================

export type Genre = 'bachata' | 'salsa';

export type BachataSectionType =
  | 'intro'
  | 'verso'
  | 'pre_coro'
  | 'coro'
  | 'mambo'
  | 'majae'
  | 'soneo'
  | 'puente'
  | 'breakdown'
  | 'outro';

export type SalsaSectionType =
  | 'intro'
  | 'verso'
  | 'coro_pregon'
  | 'coro'
  | 'montuno'
  | 'mambo_sub'
  | 'diablo_sub'
  | 'mona_sub'
  | 'especial_sub'
  | 'soneo'
  | 'coda';

export type SectionType = BachataSectionType | SalsaSectionType;

export type ClaveDirection =
  | 'son_2_3'
  | 'son_3_2'
  | 'rumba_2_3'
  | 'rumba_3_2'
  | 'none'
  | 'unclear';

export type ConfidenceLevel = 'high' | 'med' | 'low';

// ============================================================
// Song metadata
// ============================================================

export interface SongMetadata {
  title: string;
  artist: string;
  album?: string;
  year?: number;
  genre: Genre;
  subgenre?: string;
  language?: string;
}

// ============================================================
// Analysis results
// ============================================================

export interface GlobalAnalysis {
  bpm: number;
  bpm_confidence: ConfidenceLevel;
  bpm_alt?: number[];
  bpm_notes?: string;
  key?: string;
  time_signature: string;
  first_downbeat_sec: number;
  first_8count_start_sec: number;
  feel: 'single_time' | 'double_time' | 'half_time';
  clave_direction: ClaveDirection | null;
  clave_notes?: string;
}

export interface Section {
  start_sec: number;
  end_sec: number;
  type: SectionType;
  confidence: ConfidenceLevel;
  pattern_label?: string;
  danceability_score?: number;
  notes?: string;
}

export interface ClaveSegment {
  start_sec: number;
  end_sec: number;
  direction: ClaveDirection;
  confidence: ConfidenceLevel;
  notes?: string;
}

export interface LyricSegment {
  start_sec: number;
  end_sec: number;
  text: string;
  translation?: string;
  phonetic_ipa?: string;
  vocal_type: 'lead' | 'backing' | 'coro' | 'soneo' | 'ad_lib' | 'spoken';
}

export interface Hit {
  time_sec: number;
  strength: number; // 0..1
  type: 'downbeat' | 'accent' | 'syncopation' | 'break';
  notes?: string;
}

export interface StemQuality {
  sdr_db_estimate: number;
  bleed: 'low' | 'med' | 'high';
  notes?: string;
}

export interface StemsPresent {
  vocals_lead: boolean;
  vocals_back: boolean;
  requinto: boolean;
  segunda: boolean;
  bass: boolean;
  bongo: boolean;
  guira: boolean;
  tambora: boolean;
  clave: boolean;
  palmas: boolean;
  synth: boolean;
  horns: boolean;
  piano: boolean;
  congas: boolean;
  timbales: boolean;
  cowbell: boolean;
  maracas: boolean;
  guiro: boolean;
}

export type StemKind = keyof StemsPresent;

export interface MusicalityCurves {
  energy: number[]; // 0..1 per 8-count
  onset_density: number[];
  spectral_flux: number[];
  bass_rms: number[];
  vocal_activity: number[];
  percussion_density: number[];
  hits: Hit[];
  /** Per-genre extras: bachata → requinto_intensity, martillo_density, guira_subdivision; salsa → piano_montuno_density, conga_tumbao, cowbell_chordbeat, clave_direction, horn_hits */
  [extra: string]: number[] | Hit[];
}

export interface SongAnalysis {
  $schema: string;
  song_id: string;
  version: number;
  model_set: Record<string, string>;
  status: 'queued' | 'running' | 'done' | 'failed' | 'low_confidence';
  confidence_overall: number;

  metadata: SongMetadata;
  global: GlobalAnalysis;
  downbeats: number[]; // seconds
  beats: number[]; // seconds
  sections: Section[];
  stems_present: StemsPresent;
  stems_quality?: Partial<Record<StemKind, StemQuality>>;
  lyrics?: {
    language: string;
    segments: LyricSegment[];
  };
  clave_segments?: ClaveSegment[];
  musicality: MusicalityCurves;

  created_at: string; // ISO
}

// ============================================================
// Library items (DB row shape)
// ============================================================

export interface Song {
  id: string;
  owner_user_id: string | null;
  title: string;
  artist: string;
  album: string | null;
  genre: Genre;
  style: string | null;
  duration_sec: number;
  bpm: number | null;
  key_signature: string | null;
  visibility: 'private' | 'community' | 'curated';
  moderation_status: 'pending' | 'approved' | 'rejected';
  analysis_status: 'none' | 'queued' | 'running' | 'done' | 'failed';
  analysis_version: number;
  created_at: string;
  updated_at: string;
}

export interface User {
  id: string;
  email: string;
  role: 'guest' | 'user' | 'trusted' | 'mod' | 'admin';
  trust_score: number;
  created_at: string;
}

// ============================================================
// API request/response shapes
// ============================================================

export interface UploadRequest {
  title: string;
  artist: string;
  album?: string;
  genre: Genre;
  style?: string;
  visibility?: 'private' | 'community';
}

export interface UploadResponse {
  song_id: string;
  upload_url?: string; // presigned or local path
  expires_at?: string;
}

export interface AnalysisStatusResponse {
  song_id: string;
  status: SongAnalysis['status'];
  progress?: number;
  message?: string;
}

// ============================================================
// Visualization shapes (used by the gem grid)
// ============================================================

export interface Gem {
  time_sec: number;
  stem: StemKind;
  pitch_midi?: number; // for vertical positioning
  strength: number; // 0..1
  is_hit: boolean;
}

export interface GemGridData {
  song_id: string;
  duration_sec: number;
  bpm: number;
  first_8count_sec: number;
  gems: Gem[]; // all gems, pre-computed
  stems: StemKind[]; // ordered list of stem lanes to render
  sections: Section[];
  musicality: MusicalityCurves;
}
