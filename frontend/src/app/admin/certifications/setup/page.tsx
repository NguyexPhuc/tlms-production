'use client';

import { FormEvent, useCallback, useEffect, useState } from 'react';
import { BookOpen, Check, ClipboardList, Layers3, Plus } from 'lucide-react';
import { useRouter } from 'next/navigation';

import { useAuth } from '@/contexts/AuthContext';
import { apiClient } from '@/lib/api';
import { CertificateTemplate, CertificationExam, Course, CourseLesson } from '@/types/certification';
import { Question } from '@/types/question';

export default function CertificationSetupPage() {
  const router = useRouter();
  const { user, isLoading } = useAuth();
  const [courses, setCourses] = useState<Course[]>([]);
  const [exams, setExams] = useState<CertificationExam[]>([]);
  const [templates, setTemplates] = useState<CertificateTemplate[]>([]);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [lessons, setLessons] = useState<Record<string, CourseLesson[]>>({});
  const [selected, setSelected] = useState<string[]>([]);
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [courseForm, setCourseForm] = useState({ code: '', title: '', description: '', skills: '', certificate_template_id: '', is_published: true });
  const [lessonForm, setLessonForm] = useState({ course_id: '', title: '', content: '', position: 1, is_published: true });
  const [examForm, setExamForm] = useState({ course_id: '', title: '', description: '', duration_minutes: 30, pass_percentage: 80, max_attempts: 1, certificate_name: '', is_published: true });

  const load = useCallback(async () => {
    try {
      const [courseRows, examRows, questionRows, templateRows] = await Promise.all([
        apiClient.listAdminCertificationCourses(),
        apiClient.listCertificationExams(true),
        apiClient.listQuestions(),
        apiClient.listCertificateTemplates(),
      ]);
      setCourses(courseRows); setExams(examRows); setQuestions(questionRows.questions); setTemplates(templateRows);
      setExamForm((current) => ({ ...current, course_id: current.course_id || courseRows[0]?.id || '' }));
      setLessonForm((current) => ({ ...current, course_id: current.course_id || courseRows[0]?.id || '' }));
      const lessonEntries = await Promise.all(courseRows.map(async (course) => [course.id, await apiClient.listCourseLessons(course.id, true)] as const));
      setLessons(Object.fromEntries(lessonEntries));
    } catch {
      setError('Không thể tải cấu hình chứng nhận.');
    }
  }, []);

  useEffect(() => {
    if (!isLoading && (!user || !user.roles.includes('admin'))) router.push('/dashboard');
    if (user?.roles.includes('admin')) load();
  }, [isLoading, user, router, load]);

  const createCourse = async (event: FormEvent) => {
    event.preventDefault(); setSaving(true); setError(''); setNotice('');
    try {
      await apiClient.createCertificationCourse({
        ...courseForm,
        code: courseForm.code.trim().toUpperCase(),
        skills: courseForm.skills.split(',').map((item) => item.trim()).filter(Boolean),
        certificate_template_id: courseForm.certificate_template_id || undefined,
      });
      setCourseForm({ code: '', title: '', description: '', skills: '', certificate_template_id: '', is_published: true });
      setNotice('Đã tạo khóa học.'); await load();
    } catch { setError('Không thể tạo khóa học. Kiểm tra mã khóa học không bị trùng.'); }
    finally { setSaving(false); }
  };

  const createExam = async (event: FormEvent) => {
    event.preventDefault();
    if (!examForm.course_id || selected.length === 0) { setError('Chọn khóa học và ít nhất một câu hỏi.'); return; }
    setSaving(true); setError(''); setNotice('');
    try {
      await apiClient.createCertificationExam({
        ...examForm,
        questions: selected.map((questionId, index) => ({ question_id: questionId, position: index + 1, points: 10 })),
      });
      setExamForm((current) => ({ ...current, title: '', description: '', certificate_name: '' }));
      setSelected([]); setNotice('Đã tạo và cấu hình bài thi.'); await load();
    } catch { setError('Không thể tạo bài thi. Câu trắc nghiệm cần có đáp án đúng phía server.'); }
    finally { setSaving(false); }
  };

  const createLesson = async (event: FormEvent) => {
    event.preventDefault();
    if (!lessonForm.course_id) { setError('Chọn khóa học cho bài học.'); return; }
    setSaving(true); setError(''); setNotice('');
    try {
      await apiClient.createCourseLesson(lessonForm.course_id, {
        title: lessonForm.title.trim(), content: lessonForm.content.trim() || undefined,
        position: lessonForm.position, is_published: lessonForm.is_published,
      });
      setLessonForm((current) => ({ ...current, title: '', content: '', position: current.position + 1 }));
      setNotice('Đã thêm bài học.'); await load();
    } catch { setError('Không thể thêm bài học. Vị trí trong khóa học có thể đã tồn tại.'); }
    finally { setSaving(false); }
  };

  const assignTemplate = async (courseId: string, templateId: string) => {
    setError('');
    try {
      await apiClient.updateCertificationCourse(courseId, { certificate_template_id: templateId || null });
      setNotice('Đã cập nhật mẫu chứng chỉ của khóa học.'); await load();
    } catch { setError('Không thể gán mẫu chứng chỉ cho khóa học.'); }
  };

  if (isLoading || !user) return <div className="flex min-h-screen items-center justify-center bg-slate-50 text-sm text-slate-500">Đang tải...</div>;

  const inputClass = 'mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm focus:border-red-500';
  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white"><div className="mx-auto flex min-h-16 max-w-6xl items-center justify-between gap-4 px-4 py-3"><div><p className="text-xs font-semibold uppercase text-red-700">Certification Setup</p><h1 className="text-xl font-bold text-slate-950">Khóa học & Bài thi</h1></div><button onClick={() => router.push('/admin/certifications')} className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700">Quay lại</button></div></header>
      <main className="mx-auto max-w-6xl space-y-7 px-4 py-7">
        {error && <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}
        {notice && <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">{notice}</div>}
        <div className="grid gap-6 lg:grid-cols-[0.8fr_1.2fr]">
          <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex items-center gap-2"><BookOpen size={20} className="text-red-700" /><h2 className="font-bold text-slate-950">Tạo khóa học</h2></div>
            <form onSubmit={createCourse} className="mt-5 space-y-4">
              <label className="block text-sm font-medium text-slate-700">Mã khóa học<input required pattern="[A-Za-z0-9_-]+" value={courseForm.code} onChange={(e) => setCourseForm({ ...courseForm, code: e.target.value })} className={inputClass} placeholder="BACKEND-FOUNDATION" /></label>
              <label className="block text-sm font-medium text-slate-700">Tên khóa học<input required value={courseForm.title} onChange={(e) => setCourseForm({ ...courseForm, title: e.target.value })} className={inputClass} /></label>
              <label className="block text-sm font-medium text-slate-700">Mô tả<textarea rows={3} value={courseForm.description} onChange={(e) => setCourseForm({ ...courseForm, description: e.target.value })} className={inputClass} /></label>
              <label className="block text-sm font-medium text-slate-700">Kỹ năng, cách nhau bằng dấu phẩy<input value={courseForm.skills} onChange={(e) => setCourseForm({ ...courseForm, skills: e.target.value })} className={inputClass} placeholder="SQL, FastAPI, Security" /></label>
              <label className="block text-sm font-medium text-slate-700">Mẫu chứng chỉ<select value={courseForm.certificate_template_id} onChange={(e) => setCourseForm({ ...courseForm, certificate_template_id: e.target.value })} className={inputClass}><option value="">Mẫu mặc định</option>{templates.map((template) => <option key={template.id} value={template.id}>{template.name} · v{template.version}</option>)}</select></label>
              <label className="flex items-center gap-2 text-sm text-slate-700"><input type="checkbox" checked={courseForm.is_published} onChange={(e) => setCourseForm({ ...courseForm, is_published: e.target.checked })} /> Công bố ngay</label>
              <button disabled={saving} className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-red-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-red-800 disabled:bg-slate-300"><Plus size={17} /> Tạo khóa học</button>
            </form>
          </section>

          <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex items-center gap-2"><ClipboardList size={20} className="text-red-700" /><h2 className="font-bold text-slate-950">Tạo bài thi</h2></div>
            <form onSubmit={createExam} className="mt-5 space-y-4">
              <label className="block text-sm font-medium text-slate-700">Khóa học<select required value={examForm.course_id} onChange={(e) => setExamForm({ ...examForm, course_id: e.target.value })} className={inputClass}><option value="">Chọn khóa học</option>{courses.map((course) => <option key={course.id} value={course.id}>{course.title}</option>)}</select></label>
              <label className="block text-sm font-medium text-slate-700">Tên bài thi<input required value={examForm.title} onChange={(e) => setExamForm({ ...examForm, title: e.target.value })} className={inputClass} /></label>
              <label className="block text-sm font-medium text-slate-700">Mô tả<textarea rows={2} value={examForm.description} onChange={(e) => setExamForm({ ...examForm, description: e.target.value })} className={inputClass} /></label>
              <div className="grid grid-cols-3 gap-3"><label className="text-sm font-medium text-slate-700">Phút<input type="number" min={1} max={480} value={examForm.duration_minutes} onChange={(e) => setExamForm({ ...examForm, duration_minutes: Number(e.target.value) })} className={inputClass} /></label><label className="text-sm font-medium text-slate-700">Điểm đạt %<input type="number" min={0} max={100} value={examForm.pass_percentage} onChange={(e) => setExamForm({ ...examForm, pass_percentage: Number(e.target.value) })} className={inputClass} /></label><label className="text-sm font-medium text-slate-700">Số lượt<input type="number" min={1} max={20} value={examForm.max_attempts} onChange={(e) => setExamForm({ ...examForm, max_attempts: Number(e.target.value) })} className={inputClass} /></label></div>
              <label className="block text-sm font-medium text-slate-700">Tên trên chứng chỉ<input value={examForm.certificate_name} onChange={(e) => setExamForm({ ...examForm, certificate_name: e.target.value })} className={inputClass} /></label>
              <fieldset><legend className="text-sm font-medium text-slate-700">Ngân hàng câu hỏi ({selected.length} đã chọn)</legend><div className="mt-2 max-h-64 space-y-2 overflow-y-auto border-y border-slate-100 py-2">{questions.map((question) => { const checked = selected.includes(question.id); return <label key={question.id} className={`flex cursor-pointer items-start gap-3 rounded-lg border p-3 text-sm ${checked ? 'border-red-400 bg-red-50' : 'border-slate-200'}`}><input type="checkbox" checked={checked} onChange={() => setSelected((current) => checked ? current.filter((id) => id !== question.id) : [...current, question.id])} className="mt-0.5" /><span className="flex-1"><strong className="block text-slate-900">{question.title}</strong><span className="text-xs text-slate-500">{question.question_type} · {question.difficulty}</span></span>{checked && <Check size={16} className="text-red-700" />}</label>; })}</div></fieldset>
              <label className="flex items-center gap-2 text-sm text-slate-700"><input type="checkbox" checked={examForm.is_published} onChange={(e) => setExamForm({ ...examForm, is_published: e.target.checked })} /> Công bố ngay</label>
              <button disabled={saving} className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white hover:bg-slate-700 disabled:bg-slate-300"><Plus size={17} /> Tạo bài thi</button>
            </form>
          </section>
        </div>
        <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-center gap-2"><Layers3 size={20} className="text-red-700" /><h2 className="font-bold text-slate-950">Nội dung bài học</h2></div>
          <form onSubmit={createLesson} className="mt-5 grid gap-4 md:grid-cols-2">
            <label className="block text-sm font-medium text-slate-700">Khóa học<select required value={lessonForm.course_id} onChange={(e) => { const courseId = e.target.value; setLessonForm({ ...lessonForm, course_id: courseId, position: (lessons[courseId]?.length || 0) + 1 }); }} className={inputClass}><option value="">Chọn khóa học</option>{courses.map((course) => <option key={course.id} value={course.id}>{course.title}</option>)}</select></label>
            <label className="block text-sm font-medium text-slate-700">Tên bài học<input required value={lessonForm.title} onChange={(e) => setLessonForm({ ...lessonForm, title: e.target.value })} className={inputClass} /></label>
            <label className="block text-sm font-medium text-slate-700 md:col-span-2">Nội dung<textarea rows={4} value={lessonForm.content} onChange={(e) => setLessonForm({ ...lessonForm, content: e.target.value })} className={inputClass} placeholder="Mục tiêu, tài liệu hoặc hướng dẫn học tập" /></label>
            <div className="flex items-end gap-4"><label className="w-32 text-sm font-medium text-slate-700">Vị trí<input type="number" min={1} value={lessonForm.position} onChange={(e) => setLessonForm({ ...lessonForm, position: Number(e.target.value) })} className={inputClass} /></label><label className="mb-2.5 flex items-center gap-2 text-sm text-slate-700"><input type="checkbox" checked={lessonForm.is_published} onChange={(e) => setLessonForm({ ...lessonForm, is_published: e.target.checked })} /> Công bố</label></div>
            <div className="flex items-end"><button disabled={saving} className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-red-700 px-4 py-2.5 text-sm font-semibold text-white disabled:bg-slate-300"><Plus size={17} /> Thêm bài học</button></div>
          </form>
          {lessonForm.course_id && <div className="mt-5 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">{(lessons[lessonForm.course_id] || []).map((lesson) => <div key={lesson.id} className="rounded-lg border border-slate-200 p-3"><p className="text-xs font-semibold text-red-700">Bài {lesson.position}</p><p className="mt-1 text-sm font-semibold text-slate-900">{lesson.title}</p><p className="mt-1 text-xs text-slate-500">{lesson.is_published ? 'Đã công bố' : 'Bản nháp'}</p></div>)}</div>}
        </section>
        <section><h2 className="font-bold text-slate-950">Mẫu chứng chỉ theo khóa học</h2><div className="mt-3 grid gap-3 md:grid-cols-2">{courses.map((course) => <article key={course.id} className="rounded-lg border border-slate-200 bg-white p-4"><p className="text-xs font-semibold uppercase text-red-700">{course.code}</p><h3 className="mt-1 font-bold text-slate-950">{course.title}</h3><select value={course.certificate_template_id || ''} onChange={(e) => assignTemplate(course.id, e.target.value)} className={inputClass}><option value="">Mẫu mặc định</option>{templates.map((template) => <option key={template.id} value={template.id}>{template.name} · v{template.version}</option>)}</select></article>)}</div></section>
        <section><h2 className="font-bold text-slate-950">Đang có {courses.length} khóa học · {exams.length} bài thi</h2><div className="mt-3 grid gap-3 md:grid-cols-2">{exams.map((exam) => <article key={exam.id} className="rounded-lg border border-slate-200 bg-white p-4"><div className="flex items-start justify-between gap-3"><div><p className="text-xs font-semibold uppercase text-red-700">{exam.course_title}</p><h3 className="mt-1 font-bold text-slate-950">{exam.title}</h3></div><span className={`rounded px-2 py-1 text-xs font-semibold ${exam.is_published ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-600'}`}>{exam.is_published ? 'Đã công bố' : 'Bản nháp'}</span></div><p className="mt-2 text-sm text-slate-500">{exam.question_count} câu · {exam.duration_minutes} phút · đạt {exam.pass_percentage}%</p></article>)}</div></section>
      </main>
    </div>
  );
}
