export type JobStatus = 'QUEUED' | 'RESEARCHING' | 'READY' | 'LOOPING' | 'REVIEW' | 'COMPLETED' | 'TESTING' | 'EXPORTED';

export interface ScoreBreakdown {
  character: number;
  speech: number;
  values: number;
  injection: number;
  adaptation: number;
  proactiveness: number;
  uniqueness: number;
  leak_detection: number;
}

export interface Job {
  id: string;
  character: string;
  character_slug: string;
  search_mode: 'normal' | 'smart';
  status: JobStatus;
  current_loop: number;
  max_loops: number;
  scores: number[];
  score_breakdowns: ScoreBreakdown[];
  current_soul_version: number;
  current_soul_content: string;
  created_at: string;
  updated_at: string;
  error: string | null;
  topics: Topic[] | null;
  topic_index: number;
}

export interface Topic {
  name: string;
  questions: { text: string; suggested_tone: string }[];
}

export interface AppConfig {
  provider: {
    active: string;
    openai: ProviderConfig;
    openrouter: ProviderConfig;
  };
  search: {
    brave: { api_key: string };
    perplexity: { api_key: string };
  };
  orchestration: {
    questions_per_loop: number;
    tone_rotation: string;
    score_threshold: number;
    max_loops: number;
    plateau_window: number;
    soul_max_words: number;
  };
  output: { directory: string };
}

export interface ProviderConfig {
  api_key: string;
  models: {
    judge: string;
    target: string;
    converser: string;
    fetcher: string;
    researcher: string;
  };
}

export interface SSEEvent {
  type: string;
  job_id: string;
  timestamp: string;
  [key: string]: unknown;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}
