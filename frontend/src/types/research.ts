export type ResearchConsentStatus =
  | 'NOT_REQUESTED'
  | 'PENDING'
  | 'GRANTED'
  | 'DECLINED'
  | 'WITHDRAWN';

export interface ResearchParticipantProgress {
  study_code: string;
  study_name?: string | null;
  participant_code: string;
  experiment_group: 'ADAPTIVE' | 'FIXED';
  consent_status: ResearchConsentStatus;
  data_origin: 'REAL' | 'TEST' | 'DEMO' | 'SEED';
  pre_exam_id?: string | null;
  post_exam_id?: string | null;
  pre_completed: boolean;
  train_completed: number;
  train_required: number;
  post_completed: boolean;
  survey_completed: boolean;
  completed_at?: string | null;
}

export interface ResearchSurveySubmit {
  likert_answers: number[];
  useful_feedback?: string;
  improvement_feedback?: string;
}

export interface ResearchSurveyResponse extends ResearchSurveySubmit {
  id: string;
  study_code: string;
  submitted_at: string;
}
