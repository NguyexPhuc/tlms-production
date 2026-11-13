'use client';

import { useCallback, useEffect, useState } from 'react';
import { Award, BookOpen, ChevronDown, Clock3, Download, ExternalLink, FileCheck2, GraduationCap } from 'lucide-react';
import { useRouter } from 'next/navigation';

import { useAuth } from '@/contexts/AuthContext';
import { apiClient } from '@/lib/api';
import { Certificate, CertificationExam, Course, CourseEnrollment, CourseLesson } from '@/types/certification';

const CERTIFICATION_READ_ONLY = true;


export default function CertificationsPage() {
  const router = useRouter();
  const { user, isLoading } = useAuth();
  const [exams, setExams] = useState<CertificationExam[]>([]);
  const [certificates, setCertificates] = useState<Certificate[]>([]);
  const [courses, setCourses] = useState<Course[]>([]);
  const [enrollments, setEnrollments] = useState<CourseEnrollment[]>([]);
  const [openCourse, setOpenCourse] = useState<string | null>(null);
  const [lessons, setLessons] = useState<Record<string, CourseLesson[]>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadData = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [examRows, certificateRows, courseRows, enrollmentRows] = await Promise.all([
        apiClient.listCertificationExams(),
        apiClient.getMyCertificates(),
        apiClient.listCertificationCourses(),
        apiClient.getMyCourseEnrollments(),
      ]);
      setExams(examRows);
      setCertificates(certificateRows);
      setCourses(courseRows);
      setEnrollments(enrollmentRows);
    } catch {
      setError('Không thể tải dữ liệu thi và chứng chỉ.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!isLoading && !user) router.push('/login');
    if (user) loadData();
  }, [isLoading, user, router, loadData]);

  const enroll = async (courseId: string) => {
    try {
      const enrollment = await apiClient.enrollCertificationCourse(courseId);
      setEnrollments((current) => current.some((item) => item.id === enrollment.id) ? current : [...current, enrollment]);
    } catch {
      setError('Không thể đăng ký khóa học lúc này.');
    }
  };

  const toggleLessons = async (courseId: string) => {
    if (openCourse === courseId) { setOpenCourse(null); return; }
    setOpenCourse(courseId);
    if (!lessons[courseId]) {
      try {
        const courseLessons = await apiClient.listCourseLessons(courseId);
        setLessons((current) => ({ ...current, [courseId]: courseLessons }));
      } catch { setError('Không thể tải bài học.'); }
    }
  };

  if (isLoading || loading) {
    return <div className="flex min-h-screen items-center justify-center bg-slate-50 text-sm text-slate-500">Đang tải...</div>;
  }
  if (!user) return null;

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex min-h-16 max-w-6xl items-center justify-between gap-4 px-4 py-3">
          <div>
            <p className="text-xs font-semibold uppercase text-red-700">Năng lực số</p>
            <h1 className="text-xl font-bold text-slate-950">Bài thi & Chứng chỉ</h1>
          </div>
          <button onClick={() => router.push('/dashboard')} className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:border-red-300 hover:text-red-700">
            Quay lại
          </button>
        </div>
      </header>

      <main className="mx-auto max-w-6xl space-y-8 px-4 py-8">
        {error && <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div>}
        {CERTIFICATION_READ_ONLY && (
          <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
            <p className="font-semibold text-amber-900">Đang phát triển</p>
            <p className="mt-1 text-sm text-amber-800">
              Bạn có thể xem khóa học, nội dung và chứng chỉ hiện có. Chức năng đăng ký và làm bài thi sẽ được mở sau.
            </p>
          </div>
        )}

        <section>
          <div className="mb-4"><h2 className="text-lg font-bold text-slate-950">Khóa học</h2><p className="mt-1 text-sm text-slate-500">Xem trước nội dung các khóa học đang được hoàn thiện.</p></div>
          <div className="grid gap-4 md:grid-cols-2">
            {courses.map((course) => {
              const enrolled = enrollments.some((item) => item.course_id === course.id);
              return <article key={course.id} className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
                <div className="flex items-start justify-between gap-3"><div><p className="text-xs font-semibold uppercase text-red-700">{course.code}</p><h3 className="mt-1 text-lg font-bold text-slate-950">{course.title}</h3></div><BookOpen size={21} className="shrink-0 text-slate-400" /></div>
                <p className="mt-2 text-sm leading-6 text-slate-600">{course.description}</p>
                <div className="mt-3 flex flex-wrap gap-1.5">{course.skills.map((skill) => <span key={skill} className="rounded bg-slate-100 px-2 py-1 text-xs text-slate-600">{skill}</span>)}</div>
                <div className="mt-5 flex gap-2">{CERTIFICATION_READ_ONLY || enrolled ? <button onClick={() => toggleLessons(course.id)} className="inline-flex flex-1 items-center justify-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-700">Xem nội dung <ChevronDown size={16} /></button> : <button onClick={() => enroll(course.id)} className="flex-1 rounded-lg bg-red-700 px-3 py-2 text-sm font-semibold text-white hover:bg-red-800">Đăng ký khóa học</button>}</div>
                {openCourse === course.id && <div className="mt-4 border-t border-slate-100 pt-3">{(lessons[course.id] || []).length ? <ol className="space-y-2">{lessons[course.id].map((lesson) => <li key={lesson.id} className="flex gap-3 text-sm"><span className="font-bold text-red-700">{lesson.position}.</span><div><p className="font-semibold text-slate-900">{lesson.title}</p>{lesson.content && <p className="mt-1 whitespace-pre-wrap text-slate-600">{lesson.content}</p>}</div></li>)}</ol> : <p className="text-sm text-slate-500">Khóa học chưa có bài học được công bố.</p>}</div>}
              </article>;
            })}
          </div>
        </section>

        <section>
          <div className="mb-4 flex items-end justify-between gap-3">
            <div>
              <h2 className="text-lg font-bold text-slate-950">Bài đánh giá đang mở</h2>
              <p className="mt-1 text-sm text-slate-500">Danh sách bài đánh giá dự kiến. Chức năng làm bài chưa được mở.</p>
            </div>
            <span className="text-sm font-semibold text-slate-600">{exams.length} bài</span>
          </div>
          {exams.length === 0 ? (
            <div className="border-y border-slate-200 py-10 text-center text-sm text-slate-500">Chưa có bài thi được công bố.</div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {exams.map((exam) => {
                const exhausted = exam.attempts_used >= exam.max_attempts;
                return (
                  <article key={exam.id} className="flex min-h-64 flex-col rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
                    <div className="flex items-start justify-between gap-3">
                      <span className="rounded bg-red-50 px-2 py-1 text-xs font-semibold text-red-700">{exam.course_title}</span>
                      {exam.best_percentage !== null && exam.best_percentage !== undefined && (
                        <span className="text-sm font-bold text-emerald-700">{exam.best_percentage}%</span>
                      )}
                    </div>
                    <h3 className="mt-4 text-lg font-bold text-slate-950">{exam.title}</h3>
                    <p className="mt-2 line-clamp-3 text-sm leading-6 text-slate-600">{exam.description || 'Bài đánh giá năng lực và kiến thức chuyên môn.'}</p>
                    <div className="mt-4 flex flex-wrap gap-x-4 gap-y-2 text-xs text-slate-500">
                      <span className="inline-flex items-center gap-1"><Clock3 size={14} /> {exam.duration_minutes} phút</span>
                      <span className="inline-flex items-center gap-1"><FileCheck2 size={14} /> {exam.question_count} câu</span>
                      <span>Đạt {exam.pass_percentage}%</span>
                    </div>
                    <div className="mt-auto pt-5">
                      <button
                        disabled={CERTIFICATION_READ_ONLY || exhausted}
                        onClick={() => router.push(`/certifications/exams/${exam.id}`)}
                        className="w-full rounded-lg bg-red-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-red-800 disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-500"
                      >
                        {CERTIFICATION_READ_ONLY ? 'Chỉ xem' : exhausted ? 'Đã hết lượt thi' : exam.attempts_used ? 'Tiếp tục / Thi lại' : 'Bắt đầu thi'}
                      </button>
                      <p className="mt-2 text-center text-xs text-slate-400">Lượt {exam.attempts_used}/{exam.max_attempts}</p>
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </section>

        <section>
          <div className="mb-4 flex items-center gap-2">
            <Award className="text-amber-600" size={22} />
            <h2 className="text-lg font-bold text-slate-950">Chứng chỉ của tôi</h2>
          </div>
          {certificates.length === 0 ? (
            <div className="border-y border-slate-200 py-10 text-center text-sm text-slate-500">
              Hoàn thành bài thi đạt yêu cầu để nhận chứng chỉ đầu tiên.
            </div>
          ) : (
            <div className="space-y-3">
              {certificates.map((certificate) => (
                <article key={certificate.id} className="flex flex-col gap-4 rounded-lg border border-slate-200 bg-white p-4 shadow-sm sm:flex-row sm:items-center">
                  <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full border-2 border-amber-500 bg-amber-50 text-amber-700">
                    <GraduationCap size={24} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="font-bold text-slate-950">{certificate.certificate_name}</h3>
                      <span className={`rounded px-2 py-0.5 text-xs font-semibold ${certificate.status === 'revoked' ? 'bg-red-50 text-red-700' : 'bg-emerald-50 text-emerald-700'}`}>
                        {certificate.status === 'revoked' ? 'Đã thu hồi' : 'Hợp lệ'}
                      </span>
                    </div>
                    <p className="mt-1 text-sm text-slate-500">{certificate.certificate_id} · Cấp ngày {new Date(certificate.issued_at).toLocaleDateString('vi-VN')}</p>
                  </div>
                  <div className="flex gap-2">
                    <button onClick={() => router.push(`/verify/${certificate.verification_token}`)} title="Xem trang xác minh" className="rounded-lg border border-slate-200 p-2.5 text-slate-600 hover:border-red-300 hover:text-red-700">
                      <ExternalLink size={18} />
                    </button>
                    <button onClick={() => apiClient.downloadCertificate(certificate)} title="Tải PDF" className="inline-flex items-center gap-2 rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white hover:bg-slate-700">
                      <Download size={17} /> Tải PDF
                    </button>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
