export enum Shift {
  MORNING = 'morning',
  AFTERNOON = 'afternoon',
  EVENING = 'evening'
}

export enum AttendanceStatus {
  PENDING = 'pending',
  PRESENT = 'present',
  ABSENT = 'absent',
  LATE = 'late',
  EARLY_LEAVE = 'early_leave',
  EXTRA = 'extra'
}

export interface Schedule {
  id: string;
  user_id: string;
  work_date: string; // YYYY-MM-DD
  shift: Shift;
  registration_type: 'manual' | 'auto';
  is_cancelled: boolean;
  cancelled_at?: string;
  cancel_reason?: string;
  created_at: string;
  updated_at: string;
}

export interface ClassSchedule {
  id: string;
  subject_name: string;
  room?: string;
  start_datetime: string;
  end_datetime: string;
  is_cancelled: boolean;
  description?: string;
}


export interface ScheduleCreate {
  work_date: string;
  shift: Shift;
}

export interface Attendance {
  id: string;
  user_id: string;
  schedule_id?: string;
  work_date: string;
  shift: Shift;
  check_in_time?: string;
  check_out_time?: string;
  status: AttendanceStatus;
  discipline_points_change: number;
  bonus_points: number;
  auto_reconciled: boolean;
  reconciled_at?: string;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface AttendanceCheckIn {
  shift: Shift;
  notes?: string;
}

export interface AttendanceCheckOut {
  notes?: string;
}

export interface AttendanceStats {
  total_scheduled: number;
  total_attended: number;
  total_absent: number;
  total_late: number;
  total_extra: number;
  attendance_rate: number;
  discipline_points_total: number;
  bonus_points_total: number;
}

export interface WeekScheduleRequest {
  schedules: ScheduleCreate[];
}

export interface WeekScheduleResponse {
  week_start: string;
  week_end: string;
  schedules: Schedule[];
  class_schedules: ClassSchedule[];
  attendances: Attendance[];
  stats: AttendanceStats | null;
}

export interface ForceSyncFailedUser {
  user_id: string;
  email: string;
  student_id: string;
  error: string;
}

export interface ForceSyncAllUsersResponse {
  success: boolean;
  message: string;
  week_start?: string;
  total_users?: number;
  success_count?: number;
  error_count?: number;
  failed_users?: ForceSyncFailedUser[];
  error?: string;
}

export const SHIFT_LABELS: Record<Shift, string> = {
  [Shift.MORNING]: 'Sáng (8h-12h)',
  [Shift.AFTERNOON]: 'Chiều (13h-17h)',
  [Shift.EVENING]: 'Tối (18h-22h)'
};

export const ATTENDANCE_STATUS_LABELS: Record<AttendanceStatus, string> = {
  [AttendanceStatus.PENDING]: 'Chờ xác nhận',
  [AttendanceStatus.PRESENT]: 'Có mặt',
  [AttendanceStatus.ABSENT]: 'Vắng mặt',
  [AttendanceStatus.LATE]: 'Đi muộn',
  [AttendanceStatus.EARLY_LEAVE]: 'Về sớm',
  [AttendanceStatus.EXTRA]: 'Làm thêm'
};

export const ATTENDANCE_STATUS_COLORS: Record<AttendanceStatus, string> = {
  [AttendanceStatus.PENDING]: 'bg-gray-100 text-gray-800',
  [AttendanceStatus.PRESENT]: 'bg-green-100 text-green-800',
  [AttendanceStatus.ABSENT]: 'bg-red-100 text-red-800',
  [AttendanceStatus.LATE]: 'bg-yellow-100 text-yellow-800',
  [AttendanceStatus.EARLY_LEAVE]: 'bg-orange-100 text-orange-800',
  [AttendanceStatus.EXTRA]: 'bg-purple-100 text-purple-800'
};
