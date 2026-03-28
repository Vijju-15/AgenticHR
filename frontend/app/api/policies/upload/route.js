import { NextResponse } from 'next/server';

const GUIDE_URL = process.env.NEXT_PUBLIC_GUIDE_URL || 'http://localhost:8000';

export async function POST(request) {
  try {
    const form = await request.formData();
    const company_id = form.get('company_id') || 'acme_corp';
    const doc_type = form.get('doc_type') || 'policy';
    const file = form.get('file');

    if (!file) {
      return NextResponse.json({ error: 'File is required' }, { status: 400 });
    }

    const forwardForm = new FormData();
    forwardForm.append('company_id', company_id);
    forwardForm.append('doc_type', doc_type);
    forwardForm.append('file', file);

    const res = await fetch(`${GUIDE_URL}/upload`, {
      method: 'POST',
      body: forwardForm,
      signal: AbortSignal.timeout(30000),
    });

    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (err) {
    console.error('[policies.upload] POST error:', err);
    return NextResponse.json({ error: 'Could not upload policy' }, { status: 500 });
  }
}
