import { NextResponse } from 'next/server';

const ORCHESTRATOR_URL = process.env.NEXT_PUBLIC_ORCHESTRATOR_URL || 'http://localhost:8001';

/**
 * GET /api/meetings?tenant_id=acme_corp&hr_email=...
 * Proxies to orchestrator /meetings
 */
export async function GET(request) {
  const { searchParams } = new URL(request.url);
  const tenant_id    = searchParams.get('tenant_id') || 'acme_corp';
  const hr_email     = searchParams.get('hr_email') || '';
  const intern_email = searchParams.get('intern_email') || '';

  try {
    const qs = new URLSearchParams({ tenant_id });
    if (hr_email)     qs.set('hr_email', hr_email);
    if (intern_email) qs.set('intern_email', intern_email);

    const res = await fetch(`${ORCHESTRATOR_URL}/meetings?${qs}`, {
      cache: 'no-store',
      signal: AbortSignal.timeout(8000),
    });

    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (err) {
    console.error('[meetings] GET error:', err);
    return NextResponse.json({ error: 'Could not fetch meetings' }, { status: 500 });
  }
}

/**
 * POST /api/meetings
 * Body: ScheduleMeetingRequest
 * Proxies to orchestrator /meetings/schedule
 */
export async function POST(request) {
  try {
    const body = await request.json();

    const res = await fetch(`${ORCHESTRATOR_URL}/meetings/schedule`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (err) {
    console.error('[meetings] POST error:', err);
    return NextResponse.json({ error: 'Could not schedule meeting' }, { status: 500 });
  }
}

/**
 * DELETE /api/meetings?meeting_id=xxx
 */
export async function DELETE(request) {
  const { searchParams } = new URL(request.url);
  const meeting_id = searchParams.get('meeting_id');

  if (!meeting_id) {
    return NextResponse.json({ error: 'meeting_id required' }, { status: 400 });
  }

  try {
    const res = await fetch(`${ORCHESTRATOR_URL}/meetings/${meeting_id}`, {
      method: 'DELETE',
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (err) {
    console.error('[meetings] DELETE error:', err);
    return NextResponse.json({ error: 'Could not cancel meeting' }, { status: 500 });
  }
}
