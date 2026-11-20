"""Parent-report evidence, privacy, access, and content regression checks."""
import os
import sys
import secrets
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
from starlette.testclient import TestClient
from app.main import app, pack
from app.db import SessionLocal, StudentDB, UserDB, AttemptDB
from app.auth.security import create_session
from app.parent_report import build_parent_report
from app.bridge_analogies import BRIDGE_ANALOGIES, apply_bridge_analogies
from app.pack_builder import build_pack

CID = 'c8_math_rational_ops'


def answer(cid=CID, correct=False):
    return SimpleNamespace(concept_id=cid, is_correct=correct)


def test_empty_report_does_not_invent_weakness():
    report = build_parent_report(pack, [], '2026-11-19 15:00 UTC')
    assert report['attempts_used'] == 0
    assert report['focus'] == []
    assert 'No saved answers' in report['share_text']


def test_report_uses_answers_not_mastery_and_has_home_activity():
    report = build_parent_report(pack, [answer(), answer(correct=True), answer()], 'now')
    assert report['correct'] == 1
    assert report['focus'][0]['missed'] == 2
    assert report['focus'][0]['attempted'] == 3
    assert 'roti' in report['focus'][0]['activity']
    assert 'mastery' not in report['share_text'].lower()
    assert 'not a grade' in report['share_text']
    assert 'not yet synced' in report['share_text']


def test_correct_answers_do_not_create_gap():
    report = build_parent_report(pack, [answer(correct=True)], 'now')
    assert not report['focus']
    assert '1 of the last 1' in report['summary']


def test_focus_limited_to_two_and_unknown_concepts_do_not_crash():
    report = build_parent_report(pack, [answer(c.id) for c in pack.concepts] + [answer('unknown')], 'now')
    assert len(report['focus']) == 2
    assert 'unknown' not in report['share_text']


@pytest.fixture
def report_access():
    db = SessionLocal()
    sid = 'report_test_' + secrets.token_hex(4)
    student = StudentDB(pseudonymous_id=sid, subject_key='subject_' + sid, class_id='report-A', pin_hash='unused', salt='unused')
    db.add(student)
    user = UserDB(id='teacher_' + sid, username='teacher_' + sid, password_hash='unused', role='teacher', assigned_classes='["report-A"]')
    other = UserDB(id='other_' + sid, username='other_' + sid, password_hash='unused', role='teacher', assigned_classes='["report-B"]')
    db.add_all([user, other]); db.commit()
    own = create_session(db, user_id=user.id, role='teacher')
    wrong = create_session(db, user_id=other.id, role='teacher')
    child = create_session(db, student_id=sid, role='student')
    expired = create_session(db, user_id=user.id, role='teacher', duration_hours=-1)
    for i in range(25):
        db.add(AttemptDB(id=f'{sid}_{i:02}', student_id=sid, question_id='synthetic', concept_id=CID, selected_option_id='synthetic', is_correct=(i >= 5), timestamp=datetime(2026, 11, 19) + timedelta(minutes=i)))
    db.commit()
    yield TestClient(app), db, sid, {'own': own.token, 'wrong': wrong.token, 'child': child.token, 'expired': expired.token}
    db.query(AttemptDB).filter(AttemptDB.student_id == sid).delete()
    db.delete(student); db.commit(); db.close()


def auth(token):
    return {'Authorization': 'Bearer ' + token}


def test_report_requires_authentication(report_access):
    client, _, sid, _ = report_access
    assert client.get(f'/api/teacher/student/{sid}/parent-report').status_code == 401
    assert client.get('/api/teacher/class/report-A/report-students').status_code == 401


@pytest.mark.parametrize('role', ['wrong', 'child', 'expired'])
def test_report_rejects_other_class_students_and_expired_sessions(report_access, role):
    client, _, sid, tokens = report_access
    expected = 401 if role == 'expired' else 403
    assert client.get(f'/api/teacher/student/{sid}/parent-report', headers=auth(tokens[role])).status_code == expected
    assert client.get('/api/teacher/class/report-A/report-students', headers=auth(tokens[role])).status_code == expected


def test_report_last_twenty_only_and_no_identifiers_in_share_text(report_access):
    client, _, sid, tokens = report_access
    res = client.get(f'/api/teacher/student/{sid}/parent-report', headers=auth(tokens['own']))
    assert res.status_code == 200
    assert res.headers['cache-control'] == 'no-store'
    report = res.json()
    assert report['attempts_used'] == 20
    assert report['correct'] == 20  # the oldest five wrong answers are excluded
    for private in (sid, 'report-A', tokens['own'], 'subject_'):
        assert private not in report['share_text']
    roster = client.get('/api/teacher/class/report-A/report-students', headers=auth(tokens['own']))
    assert sid in roster.json()['students']
    assert roster.headers['cache-control'] == 'no-store'


def test_missing_or_deleted_student_has_no_report(report_access):
    client, db, sid, tokens = report_access
    assert client.get('/api/teacher/student/missing-report-id/parent-report', headers=auth(tokens['own'])).status_code == 404


def test_ten_analogies_preserve_routing_and_unreviewed_status():
    assert len(BRIDGE_ANALOGIES) == 10
    rebuilt = build_pack()
    for source in (pack, rebuilt):
        matched = [lesson for lesson in source.lessons if lesson.id in BRIDGE_ANALOGIES and lesson.language == 'en']
        assert len(matched) == 10
        before = [(l.id, l.concept, l.misconception, l.review_record.item_version) for l in matched]
        apply_bridge_analogies(source.lessons)
        assert before == [(l.id, l.concept, l.misconception, l.review_record.item_version) for l in matched]
        for lesson in matched:
            assert lesson.content == BRIDGE_ANALOGIES[lesson.id]
            assert lesson.review_record.status.value == 'author-drafted, unreviewed'
            assert lesson.review_record.item_version >= 2
